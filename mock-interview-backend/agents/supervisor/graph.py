"""Supervisor Graph — True multiagent orchestration via LangGraph.

Each graph invocation processes ONE answer submission through a pipeline
of autonomous agents:

    EVALUATE → SUPERVISOR → { FOLLOWUP | TECHNICAL | RESUME | HR | END }

• EVALUATE    — LLM scores the candidate's answer against the rubric
• SUPERVISOR  — LLM decides next action (with deterministic guardrails)
• FOLLOWUP    — builds a follow-up from the previous question pack
• TECHNICAL   — LLM generates a fresh coding / system-design question
• RESUME      — LLM generates a fresh resume-based question
• HR          — LLM generates a fresh behavioral question

The flow is strictly linear (no cycles), so recursion is impossible.
"""

from __future__ import annotations

import uuid

from langgraph.graph import StateGraph, END
from .state import InterviewState
from .node import supervisor_decide_node, followup_node, _normalize_agent
from agents.evaluator.node import evaluate_answer_node
from agents.technical_coding.node import generate_coding_question
from agents.resume_based.node import generate_resume_question
from agents.manegerial.node import generate_hr_question
from agents.shared import llm_generate_text


# ── Agent wrapper nodes ──────────────────────────────────────────────────
# Each wrapper extracts what the specialist needs from InterviewState,
# calls the specialist's LLM function, and writes `next_question_pack`.

def _extract_context(state: InterviewState) -> dict:
    """Common fields every agent needs."""
    config = state.get("interview_config") or {}
    spec = state.get("next_turn_spec") or state.get("current_turn_spec") or {}
    return {
        "company": config.get("company", ""),
        "role": config.get("role", ""),
        "experience": config.get("experience", 0),
        "job_description": config.get("jd", ""),
        "coverage_context": state.get("coverage_context") or {},
        "preferred_topics": spec.get("topics", []),
        "round_type": spec.get("round_type", "tech-dsa"),
    }


def technical_agent_node(state: InterviewState) -> dict:
    """Wrapper: generates a technical / coding question via LLM."""
    ctx = _extract_context(state)
    config = state.get("interview_config") or {}
    rt = ctx["round_type"]

    try:
        qp = generate_coding_question({
            "request_id": f"REQ_{uuid.uuid4().hex[:8]}",
            "session_id": state.get("session_id", ""),
            "task": "generate_coding_question",
            "company": ctx["company"],
            "role": ctx["role"],
            "experience": ctx["experience"],
            "job_description": ctx["job_description"],
            "difficulty": config.get("difficulty", "medium"),
            "round_type": rt,
            "language_preference": config.get("language_preference", "python"),
            "coverage_context": ctx["coverage_context"],
            "constraints": {
                "question_type": "system_design" if rt == "system-design" else "dsa",
                "must_include_followups": True,
                "max_time_minutes": 25,
                "needs_test_cases": True,
                "should_be_interview_realistic": True,
                "selected_topics": ctx["preferred_topics"],
            },
        })
        if qp:
            qp.setdefault("agent_type", "code")
            qp.setdefault("round_type", rt)
            qp.setdefault("question_id", f"Q_CODE_{uuid.uuid4().hex[:6]}")
            qp.setdefault("core_question_text", qp.get("question_text", ""))
            qp.setdefault("followup_questions", [])
            return {"next_question_pack": qp}
    except Exception:
        pass

    return {"next_question_pack": _fallback_code_question(ctx, rt)}


def resume_agent_node(state: InterviewState) -> dict:
    """Wrapper: generates a resume-based question via LLM."""
    ctx = _extract_context(state)
    candidate = state.get("candidate") or {}
    pr = candidate.get("resume_parsed") or {}
    skills = ", ".join(pr.get("skills", [])[:6]) or "No skills"
    projects = ", ".join(pr.get("projects", [])[:3]) or "No projects"
    topics = ", ".join(pr.get("topics", [])[:6]) or "No topics"
    summary = f"Skills: {skills}. Projects: {projects}. Topics: {topics}."
    if pr.get("summary"):
        summary += f" {pr['summary']}"

    try:
        qp = generate_resume_question({**ctx, "resume_summary": summary})
        if qp:
            qp.setdefault("agent_type", "resume")
            qp.setdefault("round_type", ctx["round_type"])
            qp.setdefault("question_id", f"Q_RES_{uuid.uuid4().hex[:6]}")
            qp.setdefault("core_question_text", qp.get("question_text", ""))
            qp.setdefault("followup_questions", [])
            return {"next_question_pack": qp}
    except Exception:
        pass

    return {"next_question_pack": _llm_fallback_question(
        "resume", ctx["round_type"], ctx["role"], ctx["company"],
        f"Ask about a project from the candidate's resume relevant to {ctx['role']}.",
    )}


def hr_agent_node(state: InterviewState) -> dict:
    """Wrapper: generates an HR / behavioral question via LLM."""
    ctx = _extract_context(state)

    try:
        qp = generate_hr_question(ctx)
        if qp:
            qp.setdefault("agent_type", "hr")
            qp.setdefault("round_type", ctx["round_type"])
            qp.setdefault("question_id", f"Q_HR_{uuid.uuid4().hex[:6]}")
            qp.setdefault("core_question_text", qp.get("question_text", ""))
            qp.setdefault("followup_questions", [])
            return {"next_question_pack": qp}
    except Exception:
        pass

    return {"next_question_pack": _llm_fallback_question(
        "hr", ctx["round_type"], ctx["role"], ctx["company"],
        "Ask a behavioral question about leadership, teamwork, or conflict resolution.",
    )}


# ── LLM-powered fallback helpers ─────────────────────────────────────────

_RUBRICS = {
    "code": {"dimensions": [
        {"key": "correctness", "max_score": 5}, {"key": "complexity", "max_score": 5},
        {"key": "edge_cases", "max_score": 5}, {"key": "code_quality", "max_score": 5},
    ], "max_total": 20},
    "resume": {"dimensions": [
        {"key": "situation_clarity", "max_score": 5}, {"key": "action_ownership", "max_score": 5},
        {"key": "result_quantified", "max_score": 5}, {"key": "honesty_depth", "max_score": 5},
    ], "max_total": 20},
    "hr": {"dimensions": [
        {"key": "self_awareness", "max_score": 5}, {"key": "communication", "max_score": 5},
        {"key": "proactiveness", "max_score": 5}, {"key": "outcome_focus", "max_score": 5},
    ], "max_total": 20},
}


def _llm_fallback_question(
    agent_type: str, round_type: str, role: str, company: str, hint: str,
) -> dict:
    """Generate a fallback question via LLM when the specialist agent fails."""
    text = llm_generate_text(
        f"You are a senior interviewer at {company} for the role of {role}.\n"
        f"Agent type: {agent_type}. Round: {round_type}.\n"
        f"Task: {hint}\n"
        f"Generate a single, realistic interview question. "
        f"Return ONLY the question text, nothing else.",
        temperature=0.6,
    )
    if not text:
        text = f"Tell me about your experience relevant to {role} at {company}."
    return {
        "question_id": f"Q_{agent_type.upper()}_{uuid.uuid4().hex[:6]}",
        "agent_type": agent_type,
        "round_type": round_type,
        "question_text": text,
        "core_question_text": text,
        "followup_questions": [],
        "rubric": _RUBRICS.get(agent_type, _RUBRICS["code"]),
    }


def _fallback_code_question(ctx: dict, rt: str) -> dict:
    return _llm_fallback_question(
        "code", rt, ctx["role"], ctx["company"],
        "Generate a coding / DSA question appropriate for the role and difficulty.",
    )


# ── Router ───────────────────────────────────────────────────────────────

def _route_after_supervisor(state: InterviewState) -> str:
    """Conditional edge: read supervisor_decision and route."""
    if state.get("is_interview_over"):
        return END

    d = state.get("supervisor_decision") or {}
    action = d.get("action", "ask_question")

    if action == "end_interview":
        return END
    if action == "clarify":
        return END          # no next question needed — session_engine re-presents the original
    if action == "follow_up":
        return "FOLLOWUP"

    agent = _normalize_agent(d.get("next_agent"))
    return {"code": "TECHNICAL", "resume": "RESUME", "hr": "HR"}.get(agent, "TECHNICAL")


# ── Build & compile ──────────────────────────────────────────────────────

def build_interview_graph():
    """Build the per-turn interview graph.

    EVALUATE → SUPERVISOR → { FOLLOWUP | TECHNICAL | RESUME | HR | END }
    Linear, no cycles, no recursion risk.
    """
    g = StateGraph(InterviewState)

    g.add_node("EVALUATE", evaluate_answer_node)
    g.add_node("SUPERVISOR", supervisor_decide_node)
    g.add_node("FOLLOWUP", followup_node)
    g.add_node("TECHNICAL", technical_agent_node)
    g.add_node("RESUME", resume_agent_node)
    g.add_node("HR", hr_agent_node)

    g.set_entry_point("EVALUATE")
    g.add_edge("EVALUATE", "SUPERVISOR")

    g.add_conditional_edges(
        "SUPERVISOR",
        _route_after_supervisor,
        {
            "FOLLOWUP": "FOLLOWUP",
            "TECHNICAL": "TECHNICAL",
            "RESUME": "RESUME",
            "HR": "HR",
            END: END,
        },
    )

    g.add_edge("FOLLOWUP", END)
    g.add_edge("TECHNICAL", END)
    g.add_edge("RESUME", END)
    g.add_edge("HR", END)

    return g.compile()


# Module-level compiled graph — imported by session_engine
app = build_interview_graph()
