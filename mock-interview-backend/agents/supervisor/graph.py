"""Agentic Interview Graph — looping multi-agent pipeline with human-in-the-loop.

Architecture:
    FIRST_QUESTION → OPENING → WAIT_FOR_ANSWER → EVALUATE → SUPERVISOR →
        ┌→ FOLLOWUP  ─────────────────────────────────────┐
        ├→ TECHNICAL → DECORATE → WAIT_FOR_ANSWER ────────┤
        ├→ RESUME    → DECORATE → WAIT_FOR_ANSWER ────────┤
        ├→ HR        → DECORATE → WAIT_FOR_ANSWER ────────┤
        └→ END                                             │
                          ↑                                │
                          └────────────────────────────────┘
                          (loops back: EVALUATE → SUPERVISOR → ...)

The graph LOOPS. Each cycle:
  1. An agent generates a question
  2. WAIT_FOR_ANSWER interrupts execution (waits for human input)
  3. EVALUATE scores the answer
  4. SUPERVISOR reasons about what to do next (genuine LLM reasoning)
  5. Routes to the next agent → back to step 1

The graph only exits when SUPERVISOR sets is_interview_over=True.

session_engine uses:
  - graph.invoke() to start (generates first question, then interrupts)
  - graph.invoke(Command(resume=answer)) to resume after each answer
"""

from __future__ import annotations

import uuid

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from .state import InterviewState
from .node import (
    supervisor_node,
    followup_node,
    opening_node,
    _normalize_agent,
    ROUND_LABELS,
    ROUND_TYPE_TO_AGENT,
    _sanitize_text,
)
from agents.evaluator.node import evaluate_answer_node
from agents.technical_coding.node import generate_coding_question
from agents.resume_based.node import generate_resume_question
from agents.manegerial.node import generate_hr_question
from agents.shared import llm_generate_text


# ── Agent wrapper nodes ─────────────────────────────────────────────────

def _extract_agent_context(state: InterviewState) -> dict:
    """Extract common fields that specialist agents need."""
    config = state.get("interview_config") or {}
    decision = state.get("supervisor_decision") or {}
    return {
        "company": config.get("company", ""),
        "role": config.get("role", ""),
        "experience": config.get("experience", 0),
        "job_description": config.get("jd", ""),
        "difficulty": state.get("current_difficulty", "medium"),
        "coverage_context": state.get("coverage_context") or {},
        "focus_topic": decision.get("focus_topic"),
    }


def technical_agent_node(state: InterviewState) -> dict:
    """Generates a coding/system-design question with 3-step reasoning."""
    ctx = _extract_agent_context(state)
    config = state.get("interview_config") or {}
    decision = state.get("supervisor_decision") or {}
    # Determine round type from supervisor hint or config
    selected_types = config.get("selected_types", [])
    round_type = "tech-dsa"
    for st in selected_types:
        if ROUND_TYPE_TO_AGENT.get(st) == "code":
            round_type = st
            break

    try:
        qp = generate_coding_question({
            "request_id": f"REQ_{uuid.uuid4().hex[:8]}",
            "session_id": state.get("session_id", ""),
            "task": "generate_coding_question",
            "company": ctx["company"],
            "role": ctx["role"],
            "experience": ctx["experience"],
            "job_description": ctx["job_description"],
            "difficulty": ctx["difficulty"],
            "round_type": round_type,
            "language_preference": config.get("language_preference", "python"),
            "coverage_context": ctx["coverage_context"],
            "focus_topic": ctx.get("focus_topic"),
            "constraints": {
                "question_type": "system_design" if round_type == "system-design" else "dsa",
                "must_include_followups": True,
                "max_time_minutes": 25,
                "needs_test_cases": True,
                "should_be_interview_realistic": True,
                "selected_topics": config.get("topics", {}).get(round_type, []),
            },
        })
        if qp:
            qp.setdefault("agent_type", "code")
            qp.setdefault("round_type", round_type)
            qp.setdefault("question_id", f"Q_CODE_{uuid.uuid4().hex[:6]}")
            qp.setdefault("core_question_text", qp.get("question_text", ""))
            qp.setdefault("followup_questions", [])
            # Extract test cases from examples if not present
            if "test_cases" not in qp and qp.get("examples"):
                qp["test_cases"] = [
                    {"input": ex.get("input"), "expected_output": ex.get("output")}
                    for ex in qp["examples"] if ex.get("output") is not None
                ]
            return {"next_question_pack": qp}
    except Exception:
        pass

    # LLM fallback
    fallback_text = llm_generate_text(
        f"Generate a {ctx['difficulty']} coding interview question for {ctx['role']} at {ctx['company']}. "
        f"Include an example with input/output. Return ONLY the question text.",
        temperature=0.6,
    ) or f"Solve a coding problem relevant to {ctx['role']}."

    return {"next_question_pack": {
        "question_id": f"Q_CODE_{uuid.uuid4().hex[:6]}",
        "agent_type": "code", "round_type": round_type,
        "question_text": fallback_text, "core_question_text": fallback_text,
        "followup_questions": [],
        "rubric": {"dimensions": [
            {"key": "correctness", "max_score": 5}, {"key": "complexity", "max_score": 5},
            {"key": "edge_cases", "max_score": 5}, {"key": "code_quality", "max_score": 5},
        ], "max_total": 20},
    }}


def resume_agent_node(state: InterviewState) -> dict:
    """Generates a resume-based question with 3-step reasoning."""
    ctx = _extract_agent_context(state)
    candidate = state.get("candidate") or {}
    pr = candidate.get("resume_parsed") or {}
    skills = ", ".join(pr.get("skills", [])[:6]) or "No skills"
    projects = ", ".join(pr.get("projects", [])[:3]) or "No projects"
    topics = ", ".join(pr.get("topics", [])[:6]) or "No topics"
    summary = f"Skills: {skills}. Projects: {projects}. Topics: {topics}."
    if pr.get("summary"):
        summary += f" {pr['summary']}"

    try:
        qp = generate_resume_question({
            **ctx,
            "resume_summary": summary,
            "preferred_topics": (state.get("interview_config") or {}).get("topics", {}).get("resume-based", []),
        })
        if qp:
            qp.setdefault("agent_type", "resume")
            qp.setdefault("round_type", "resume-based")
            qp.setdefault("question_id", f"Q_RES_{uuid.uuid4().hex[:6]}")
            qp.setdefault("core_question_text", qp.get("question_text", ""))
            qp.setdefault("followup_questions", [])
            return {"next_question_pack": qp}
    except Exception:
        pass

    return {"next_question_pack": {
        "question_id": f"Q_RES_{uuid.uuid4().hex[:6]}",
        "agent_type": "resume", "round_type": "resume-based",
        "question_text": f"Tell me about a project relevant to {ctx['role']}.",
        "core_question_text": f"Tell me about a project relevant to {ctx['role']}.",
        "followup_questions": [],
        "rubric": {"dimensions": [
            {"key": "situation_clarity", "max_score": 5}, {"key": "action_ownership", "max_score": 5},
            {"key": "result_quantified", "max_score": 5}, {"key": "honesty_depth", "max_score": 5},
        ], "max_total": 20},
    }}


def hr_agent_node(state: InterviewState) -> dict:
    """Generates an HR/behavioral question with 3-step reasoning."""
    ctx = _extract_agent_context(state)

    try:
        qp = generate_hr_question({
            **ctx,
            "preferred_topics": (state.get("interview_config") or {}).get("topics", {}).get("managerial", []),
        })
        if qp:
            qp.setdefault("agent_type", "hr")
            qp.setdefault("round_type", "managerial")
            qp.setdefault("question_id", f"Q_HR_{uuid.uuid4().hex[:6]}")
            qp.setdefault("core_question_text", qp.get("question_text", ""))
            qp.setdefault("followup_questions", [])
            return {"next_question_pack": qp}
    except Exception:
        pass

    return {"next_question_pack": {
        "question_id": f"Q_HR_{uuid.uuid4().hex[:6]}",
        "agent_type": "hr", "round_type": "managerial",
        "question_text": "Tell me about a challenging team situation you navigated.",
        "core_question_text": "Tell me about a challenging team situation you navigated.",
        "followup_questions": [],
        "rubric": {"dimensions": [
            {"key": "self_awareness", "max_score": 5}, {"key": "communication", "max_score": 5},
            {"key": "proactiveness", "max_score": 5}, {"key": "outcome_focus", "max_score": 5},
        ], "max_total": 20},
    }}


# ── Decorate node ────────────────────────────────────────────────────────

def decorate_question_node(state: InterviewState) -> dict:
    """Prepend the supervisor's short prefix to the question."""
    qp = state.get("next_question_pack") or {}
    decision = state.get("supervisor_decision") or {}

    # Use single 'prefix' field (max ~10 words), fall back to old fields
    prefix = _sanitize_text(
        decision.get("prefix")
        or decision.get("acknowledgement", "")
    ).strip()
    # Hard cap: if prefix is too long, just take first sentence
    if prefix and len(prefix.split()) > 15:
        prefix = prefix.split(".")[0].strip() + "."

    if prefix:
        core = qp.get("core_question_text", qp.get("question_text", ""))
        qp = dict(qp)
        qp["question_text"] = f"{prefix} {core}".strip()

    return {"current_question_pack": qp, "next_question_pack": qp}


# ── First question node ─────────────────────────────────────────────────

def first_question_node(state: InterviewState) -> dict:
    """Generate the very first question of the interview.

    Determines the first agent type from selected_types and generates.
    """
    config = state.get("interview_config") or {}
    selected_types = config.get("selected_types") or ["tech-dsa"]
    first_type = selected_types[0]
    first_agent = ROUND_TYPE_TO_AGENT.get(first_type, "code")

    # Dispatch to the appropriate agent
    state_copy = dict(state)
    state_copy["current_agent"] = first_agent

    if first_agent == "code":
        result = technical_agent_node(state_copy)
    elif first_agent == "resume":
        result = resume_agent_node(state_copy)
    else:
        result = hr_agent_node(state_copy)

    return {
        "next_question_pack": result.get("next_question_pack"),
        "current_agent": first_agent,
    }


# ── Wait for answer (human-in-the-loop) ─────────────────────────────────

def wait_for_answer_node(state: InterviewState) -> dict:
    """Interrupts the graph and waits for the candidate's answer.

    When session_engine calls graph.invoke(Command(resume={"answer_text": "..."})),
    execution resumes and the answer is injected into state.
    """
    # Interrupt — the graph pauses here and returns control to session_engine
    answer = interrupt({
        "question": state.get("current_question_pack", {}),
        "turn_counter": state.get("turn_counter", 0),
        "session_id": state.get("session_id", ""),
    })

    # When resumed, `answer` contains the data passed via Command(resume=...)
    return {"answer_text": answer.get("answer_text", "")}


# ── Router ───────────────────────────────────────────────────────────────

def route_after_supervisor(state: InterviewState) -> str:
    """Conditional edge: read supervisor's decision and route to next node."""
    if state.get("is_interview_over"):
        return END

    decision = state.get("supervisor_decision") or {}
    action = decision.get("action", "ask_question")

    if action == "end_interview":
        return END

    if action == "clarify":
        # Re-present the same question — go back to WAIT_FOR_ANSWER
        return "WAIT_FOR_ANSWER"

    if action == "follow_up":
        return "FOLLOWUP"

    # ask_question — route to the appropriate agent
    agent = _normalize_agent(decision.get("next_agent"))
    return {"code": "TECHNICAL", "resume": "RESUME", "hr": "HR"}.get(agent, "TECHNICAL")


def route_followup_to_wait(state: InterviewState) -> str:
    """After generating a follow-up, go to WAIT_FOR_ANSWER."""
    return "WAIT_FOR_ANSWER"


# ── Build & compile ─────────────────────────────────────────────────────

def build_interview_graph():
    """Build the agentic interview graph with looping and human-in-the-loop.

    Flow:
      FIRST_QUESTION → OPENING → WAIT_FOR_ANSWER → EVALUATE → SUPERVISOR →
        → TECHNICAL/RESUME/HR → DECORATE → WAIT_FOR_ANSWER → EVALUATE → SUPERVISOR → ...
        → FOLLOWUP → WAIT_FOR_ANSWER → EVALUATE → SUPERVISOR → ...
        → END (when supervisor decides)
    """
    g = StateGraph(InterviewState)

    # ── Nodes ────────────────────────────────────────────────────────
    g.add_node("FIRST_QUESTION", first_question_node)
    g.add_node("OPENING", opening_node)
    g.add_node("WAIT_FOR_ANSWER", wait_for_answer_node)
    g.add_node("EVALUATE", evaluate_answer_node)
    g.add_node("SUPERVISOR", supervisor_node)
    g.add_node("FOLLOWUP", followup_node)
    g.add_node("TECHNICAL", technical_agent_node)
    g.add_node("RESUME", resume_agent_node)
    g.add_node("HR", hr_agent_node)
    g.add_node("DECORATE", decorate_question_node)

    # ── Edges ────────────────────────────────────────────────────────

    # Start: generate first question → greet → wait for answer
    g.set_entry_point("FIRST_QUESTION")
    g.add_edge("FIRST_QUESTION", "OPENING")
    g.add_edge("OPENING", "WAIT_FOR_ANSWER")

    # After answer: evaluate → supervisor decides
    g.add_edge("WAIT_FOR_ANSWER", "EVALUATE")
    g.add_edge("EVALUATE", "SUPERVISOR")

    # Supervisor routes conditionally
    g.add_conditional_edges(
        "SUPERVISOR",
        route_after_supervisor,
        {
            "FOLLOWUP": "FOLLOWUP",
            "TECHNICAL": "TECHNICAL",
            "RESUME": "RESUME",
            "HR": "HR",
            "WAIT_FOR_ANSWER": "WAIT_FOR_ANSWER",  # clarification: re-ask same Q
            END: END,
        },
    )

    # Follow-up → decorate → wait for next answer (LOOP)
    g.add_edge("FOLLOWUP", "DECORATE")

    # Agent → decorate → wait for next answer (LOOP)
    g.add_edge("TECHNICAL", "DECORATE")
    g.add_edge("RESUME", "DECORATE")
    g.add_edge("HR", "DECORATE")

    # Decorate → wait for answer (completes the loop)
    g.add_edge("DECORATE", "WAIT_FOR_ANSWER")

    return g.compile(checkpointer=MemorySaver(), interrupt_before=[])


# Module-level compiled graph — imported by session_engine
app = build_interview_graph()
