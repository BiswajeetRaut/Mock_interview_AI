"""Session Engine — thin orchestrator for the agentic interview graph.

The engine is NO LONGER the brain. It is a simple wrapper that:
  1. start_session()  → builds initial state, invokes graph (which generates
                        first question and interrupts at WAIT_FOR_ANSWER)
  2. submit_answer()  → resumes the graph with the answer (graph evaluates,
                        supervisor reasons, agent generates next question,
                        then interrupts again)
  3. end_session()    → computes final scores from the turns recorded in state
  4. get_session()    → returns current state

All interview logic (routing, difficulty adaptation, follow-ups, when to end)
lives in the LangGraph pipeline — not here.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from io import BytesIO
import json
import os
import re
from urllib.request import Request, urlopen
import uuid
from typing import Any, Dict, List, Optional

from agents.supervisor.graph import app as interview_graph
from agents.shared import build_llm, safe_json_parse, llm_generate_text
from agents.supervisor.node import ROUND_TYPE_TO_AGENT

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from redis import Redis
except ImportError:
    Redis = None

from langgraph.types import Command


# ── Configuration ────────────────────────────────────────────────────────

SESSION_STORE: Dict[str, Dict[str, Any]] = {}
# Mapping of session_id → LangGraph thread_id (for checkpointer)
THREAD_STORE: Dict[str, str] = {}

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "7200"))
REDIS_URL = os.getenv("REDIS_URL", "").strip()
_REDIS_CLIENT = Redis.from_url(REDIS_URL, decode_responses=True) if Redis and REDIS_URL else None

DEFAULT_MAX_TURNS = 12  # hard safety cap — the only guardrail

ROUND_LABELS = {
    "code": "technical problem-solving",
    "resume": "your past experience",
    "hr": "behavioral and collaboration topics",
}


# ── Persistence ──────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_session(session: Dict[str, Any]) -> None:
    sid = session["session_id"]
    if _REDIS_CLIENT:
        _REDIS_CLIENT.set(f"session:{sid}", json.dumps(session), ex=SESSION_TTL_SECONDS)
        return
    SESSION_STORE[sid] = session


def _fetch_session(session_id: str) -> Optional[Dict[str, Any]]:
    if _REDIS_CLIENT:
        raw = _REDIS_CLIENT.get(f"session:{session_id}")
        return json.loads(raw) if raw else None
    return SESSION_STORE.get(session_id)


# ── Resume processing (kept from original — this is pure data extraction) ──

def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    if not pdf_bytes or PdfReader is None:
        return ""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except Exception:
        return ""


def _extract_resume_text(resume_content: Dict[str, Any]) -> str:
    if not isinstance(resume_content, dict):
        return ""
    fmt = (resume_content.get("format") or "text").strip().lower()
    data = resume_content.get("data") or ""
    if not data:
        return ""

    if fmt == "text":
        return str(data).strip()
    if fmt == "pdf_base64":
        try:
            return _extract_text_from_pdf_bytes(base64.b64decode(data, validate=False))
        except Exception:
            return ""
    if fmt == "url":
        try:
            req = Request(str(data), headers={"User-Agent": "MockInterviewAI/1.0"})
            with urlopen(req, timeout=8) as resp:
                raw = resp.read()
                ct = (resp.headers.get("Content-Type") or "").lower()
            if "pdf" in ct or str(data).lower().endswith(".pdf"):
                return _extract_text_from_pdf_bytes(raw)
            return raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
    return str(data).strip()


def _parse_resume_simple(text: str) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    skills: List[str] = []
    for line in lines:
        if "skill" in line.lower():
            skills.extend(t.strip() for t in line.split(":")[-1].split(","))
    return {"skills": [s for s in skills if s][:8], "projects": [], "education": [], "topics": [], "summary": ""}


def _parse_resume_with_llm(text: str) -> Dict[str, Any]:
    llm = build_llm()
    if not llm or not text.strip():
        return {}
    prompt = (
        "Extract structured resume details. Return valid JSON only:\n"
        '{"skills": [...], "projects": [...], "education": [...], '
        '"topics": [...], "summary": "..."}\n\n'
        f"Resume:\n{text[:12000]}"
    )
    try:
        resp = llm.invoke(prompt)
        parsed = safe_json_parse(resp.content if hasattr(resp, "content") else str(resp))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _merge_resume(simple: dict, llm_result: dict) -> dict:
    merged = dict(simple)
    for key in ["skills", "projects", "education", "topics"]:
        vals = llm_result.get(key)
        if isinstance(vals, list):
            merged[key] = [str(v).strip() for v in vals if str(v).strip()][:12]
    if isinstance(llm_result.get("summary"), str) and llm_result["summary"].strip():
        merged["summary"] = llm_result["summary"].strip()
    return merged


# ── Session lifecycle ────────────────────────────────────────────────────

def start_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize a session and invoke the graph to generate the first question.

    The graph runs: FIRST_QUESTION → OPENING → WAIT_FOR_ANSWER (interrupt)
    We extract the current state at the interrupt point and return it.
    """
    print("Starting session with payload:", payload)
    session_id = f"S_{uuid.uuid4().hex[:8]}"
    thread_id = f"thread_{uuid.uuid4().hex}"

    # ── Parse resume ─────────────────────────────────────────────────
    resume_content = payload.get("resume_content", {}) or {}
    resume_text = _extract_resume_text(resume_content)
    parsed_resume = _merge_resume(
        _parse_resume_simple(resume_text),
        _parse_resume_with_llm(resume_text),
    )

    # ── Normalize topics ─────────────────────────────────────────────
    topics = {}
    for rt, vals in (payload.get("topics", {}) or {}).items():
        if isinstance(vals, list):
            topics[rt] = [str(v) for v in vals if str(v).strip()]

    # Merge inferred resume topics
    inferred = parsed_resume.get("topics", [])
    if inferred:
        existing = topics.get("resume-based", [])
        seen = {t.lower() for t in existing}
        for t in inferred:
            if t.lower() not in seen:
                existing.append(t)
                seen.add(t.lower())
        topics["resume-based"] = existing[:12]

    # ── Determine allowed agents ─────────────────────────────────────
    selected_types = payload.get("selected_types", [])
    if not selected_types:
        selected_types = list(topics.keys()) or ["tech-dsa"]

    # ── Build initial graph state ────────────────────────────────────
    max_turns = min(payload.get("total_turns_planned", 8), DEFAULT_MAX_TURNS)

    initial_state = {
        "session_id": session_id,
        "interview_config": {
            "company": payload["company"],
            "role": payload["role"],
            "experience": payload.get("experience", 0),
            "jd": payload.get("jd"),
            "difficulty": payload.get("difficulty", "medium"),
            "language_preference": payload.get("language_preference", "python"),
            "total_turns_planned": max_turns,
            "selected_types": selected_types,
            "topics": topics,
        },
        "candidate": {
            "user_id": payload.get("user_id", "anonymous"),
            "name": payload.get("candidate_name", "Candidate"),
            "resume_parsed": parsed_resume,
        },
        "turn_counter": 0,
        "max_turns": max_turns,
        "current_difficulty": payload.get("difficulty", "medium"),
        "current_agent": "code",  # will be set by FIRST_QUESTION node
        "coverage_context": {
            "already_asked_topics": [],
            "avoid_topics": [],
            "weakness_tags": [],
            "strength_tags": [],
        },
        "turns": [],
        "supervisor_scratchpad": [],
        "signal_confidence": 0.0,
        "is_interview_over": False,
    }

    # ── Invoke the graph — it will run until WAIT_FOR_ANSWER interrupts ──
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = interview_graph.invoke(initial_state, config=config)
    except Exception as e:
        # If graph invocation fails, the interrupt data should be in the checkpoint
        result = None

    # ── Read the graph state at the interrupt point ──────────────────
    graph_state = interview_graph.get_state(config)
    state_values = graph_state.values if graph_state else initial_state

    # ── Build session for persistence ────────────────────────────────
    question_pack = state_values.get("current_question_pack") or state_values.get("next_question_pack") or {}

    session = {
        "session_id": session_id,
        "thread_id": thread_id,
        "created_at": _now_iso(),
        "status": "active",
        "candidate": state_values.get("candidate", initial_state["candidate"]),
        "interview_config": state_values.get("interview_config", initial_state["interview_config"]),
        "turn_counter": state_values.get("turn_counter", 0),
        "current_agent": state_values.get("current_agent", "code"),
        "current_difficulty": state_values.get("current_difficulty", "medium"),
        "coverage_context": state_values.get("coverage_context", initial_state["coverage_context"]),
        "turns": state_values.get("turns", []),
        "supervisor_scratchpad": state_values.get("supervisor_scratchpad", []),
        "signal_confidence": state_values.get("signal_confidence", 0.0),
        "final_scores": {},
        "latest_question": question_pack,
        "pending_turn_id": "T_001",
        "locked": False,
        "is_interview_over": False,
        "debug_trace": [],
    }

    THREAD_STORE[session_id] = thread_id
    _persist_session(session)
    return session


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _fetch_session(session_id)


def submit_answer(session_id: str, answer_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Resume the graph with the candidate's answer.

    The graph was paused at WAIT_FOR_ANSWER. We resume it with the answer.
    It will: EVALUATE → SUPERVISOR → AGENT → DECORATE → WAIT_FOR_ANSWER (interrupt again)
    Or: EVALUATE → SUPERVISOR → END (if interview is over)
    """
    session = _fetch_session(session_id)
    if not session:
        raise ValueError("Session not found")
    if session["status"] != "active":
        raise ValueError("Session is not active")
    if session.get("locked"):
        raise RuntimeError("Session is locked while evaluating another answer")

    session["locked"] = True
    _persist_session(session)

    try:
        thread_id = THREAD_STORE.get(session_id) or session.get("thread_id")
        if not thread_id:
            raise ValueError("No thread_id for session — cannot resume graph")

        config = {"configurable": {"thread_id": thread_id}}

        # Resume the graph with the answer
        resume_data = {"answer_text": answer_payload.get("answer_text", "")}

        try:
            interview_graph.invoke(
                Command(resume=resume_data),
                config=config,
            )
        except Exception:
            pass  # Graph may have ended or interrupted again — both are OK

        # Read the updated graph state
        graph_state = interview_graph.get_state(config)
        state_values = graph_state.values if graph_state else {}

        is_over = state_values.get("is_interview_over", False)
        decision = state_values.get("supervisor_decision") or {}

        # ── Handle clarification (supervisor re-presents same question) ──
        if decision.get("action") == "clarify":
            clar_text = decision.get("clarification_response", "")
            if clar_text:
                qp = dict(session.get("latest_question") or {})
                qp["question_text"] = clar_text
                session["latest_question"] = qp
            session["locked"] = False
            _persist_session(session)
            return session

        # ── Update session from graph state ──────────────────────────
        session["turns"] = state_values.get("turns", session["turns"])
        session["turn_counter"] = state_values.get("turn_counter", session["turn_counter"])
        session["current_agent"] = state_values.get("current_agent", session["current_agent"])
        session["current_difficulty"] = state_values.get("current_difficulty", session["current_difficulty"])
        session["coverage_context"] = state_values.get("coverage_context", session["coverage_context"])
        session["supervisor_scratchpad"] = state_values.get("supervisor_scratchpad", [])
        session["signal_confidence"] = state_values.get("signal_confidence", 0.0)
        session["pending_turn_id"] = f"T_{session['turn_counter'] + 1:03d}"

        if is_over:
            session["status"] = "completed"
            session["final_scores"] = _compute_final_scores(session)
            session["latest_question"] = None
            session["is_interview_over"] = True
        else:
            # Get the next question from the graph state
            next_qp = state_values.get("current_question_pack") or state_values.get("next_question_pack")
            session["latest_question"] = next_qp

        session["locked"] = False
        _persist_session(session)
        return session

    except Exception as e:
        session["locked"] = False
        _persist_session(session)
        raise


def end_session(session_id: str, reason: str) -> Dict[str, Any]:
    """Manually end the session and compute final scores."""
    session = _fetch_session(session_id)
    if not session:
        raise ValueError("Session not found")
    if session["status"] not in ("completed", "aborted"):
        session["status"] = "aborted" if reason in ("aborted", "manual_end") else "completed"
        session["final_scores"] = _compute_final_scores(session)
        session["is_interview_over"] = True
        _persist_session(session)
    return session


# ── Score computation (pure data — no LLM) ──────────────────────────────

def _compute_final_scores(session: Dict[str, Any]) -> Dict[str, Any]:
    grouped: Dict[str, List[int]] = {"code": [], "resume": [], "hr": []}
    for turn in session.get("turns", []):
        agent = turn.get("agent_type", "code")
        ev = turn.get("evaluation") or {}
        pct = ev.get("percentage")
        if pct is not None and agent in grouped:
            grouped[agent].append(int(pct))

    domain_scores: Dict[str, Any] = {}
    all_scores: List[int] = []
    for key in ("code", "resume", "hr"):
        if grouped[key]:
            avg = round(sum(grouped[key]) / len(grouped[key]), 2)
            domain_scores[key] = {
                "score": avg,
                "turns_evaluated": len(grouped[key]),
                "verdict": "strong" if avg >= 80 else "good" if avg >= 65 else "needs_improvement",
            }
            all_scores.extend(grouped[key])
        else:
            domain_scores[key] = {"score": None, "turns_evaluated": 0, "verdict": None}

    domain_scores["overall"] = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    return domain_scores
