from __future__ import annotations

from datetime import datetime, timezone
import random
import uuid
from typing import Any, Dict, List, Optional


SESSION_STORE: Dict[str, Dict[str, Any]] = {}

AGENT_ORDER: List[str] = ["code", "resume", "hr"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_resume_text(text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skill_tokens: List[str] = []
    for line in lines:
        if "skill" in line.lower():
            skill_tokens.extend([token.strip() for token in line.split(":")[-1].split(",")])
    return {
        "skills": [token for token in skill_tokens if token][:8],
        "experience_years": 0,
        "projects": [],
        "education": [],
        "claimed_strengths": [],
    }


def _generate_question(agent_type: str, role: str, company: str, difficulty: str) -> Dict[str, Any]:
    bank = {
        "code": f"Implement a {difficulty} level DSA solution relevant to {role} interviews at {company}.",
        "resume": "Tell me about one project from your resume where you handled a tough challenge.",
        "hr": "Describe a time you adapted quickly to changing requirements.",
    }
    return {
        "question_id": f"Q_{agent_type.upper()}_{uuid.uuid4().hex[:6]}",
        "agent_type": agent_type,
        "question_text": bank[agent_type],
    }


def _evaluate_answer(agent_type: str, answer_text: str) -> Dict[str, Any]:
    length_score = min(5, max(1, len(answer_text.split()) // 20 + 1))
    clarity_score = random.randint(2, 5)
    depth_score = random.randint(2, 5)
    total = length_score + clarity_score + depth_score
    percentage = round((total / 15) * 100)
    return {
        "scores": {
            "structure": {"score": length_score, "max": 5},
            "clarity": {"score": clarity_score, "max": 5},
            "depth": {"score": depth_score, "max": 5},
        },
        "total_score": total,
        "max_score": 15,
        "percentage": percentage,
        "verdict": "good" if percentage >= 70 else "average",
        "feedback_summary": f"{agent_type.upper()} answer evaluated with structured rubric.",
        "topics_demonstrated_weak": ["depth"] if depth_score <= 2 else [],
        "topics_demonstrated_strong": ["clarity"] if clarity_score >= 4 else [],
    }


def _compute_final_scores(session: Dict[str, Any]) -> Dict[str, Optional[float]]:
    grouped: Dict[str, List[int]] = {"code": [], "resume": [], "hr": []}
    for turn in session["turns"]:
        grouped[turn["agent_type"]].append(turn["evaluation"]["percentage"])

    domain_scores: Dict[str, Optional[float]] = {}
    all_scores: List[int] = []
    for key in ["code", "resume", "hr"]:
        if grouped[key]:
            avg = round(sum(grouped[key]) / len(grouped[key]), 2)
            domain_scores[key] = avg
            all_scores.extend(grouped[key])
        else:
            domain_scores[key] = None

    domain_scores["overall"] = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    return domain_scores


def _next_agent(session: Dict[str, Any]) -> str:
    next_index = (session["turn_counter"] - 1) % len(AGENT_ORDER)
    return AGENT_ORDER[next_index]


def start_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = f"S_{uuid.uuid4().hex[:8]}"
    parsed_resume = _parse_resume_text(payload["resume_content"]["data"])
    created_at = _now_iso()

    session = {
        "session_id": session_id,
        "created_at": created_at,
        "status": "active",
        "candidate": {
            "user_id": payload["user_id"],
            "name": payload["candidate_name"],
            "resume_parsed": parsed_resume,
        },
        "interview_config": {
            "company": payload["company"],
            "role": payload["role"],
            "difficulty": payload["difficulty"],
            "language_preference": payload["language_preference"],
            "total_turns_planned": payload["total_turns_planned"],
            "turn_distribution": payload["turn_distribution"],
        },
        "turn_counter": 1,
        "current_agent": "code",
        "coverage_context": {
            "already_asked_topics": [],
            "avoid_topics": [],
            "weakness_tags": [],
            "strength_tags": [],
        },
        "turns": [],
        "final_scores": {"code": None, "resume": None, "hr": None, "overall": None},
        "pending_turn_id": f"T_{1:03d}",
        "latest_question": _generate_question(
            "code", payload["role"], payload["company"], payload["difficulty"]
        ),
        "locked": False,
    }
    SESSION_STORE[session_id] = session
    return session


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return SESSION_STORE.get(session_id)


def submit_answer(session_id: str, answer_payload: Dict[str, Any]) -> Dict[str, Any]:
    session = SESSION_STORE[session_id]
    if session["status"] != "active":
        raise ValueError("Session is not active")
    if session["locked"]:
        raise RuntimeError("Session is locked while evaluating another answer")

    session["locked"] = True
    try:
        agent_type = session["current_agent"]
        evaluation = _evaluate_answer(agent_type, answer_payload["answer_text"])
        turn = {
            "turn_id": session["pending_turn_id"],
            "agent_type": agent_type,
            "question_id": session["latest_question"]["question_id"],
            "question_text": session["latest_question"]["question_text"],
            "user_answer_transcript": answer_payload["answer_text"],
            "evaluation": evaluation,
            "completed_at": _now_iso(),
        }
        session["turns"].append(turn)

        if evaluation["topics_demonstrated_weak"]:
            session["coverage_context"]["weakness_tags"].extend(
                evaluation["topics_demonstrated_weak"]
            )
        if evaluation["topics_demonstrated_strong"]:
            session["coverage_context"]["strength_tags"].extend(
                evaluation["topics_demonstrated_strong"]
            )

        if session["turn_counter"] >= session["interview_config"]["total_turns_planned"]:
            session["status"] = "completed"
            session["final_scores"] = _compute_final_scores(session)
            session["latest_question"] = None
            session["pending_turn_id"] = None
            return session

        session["turn_counter"] += 1
        session["current_agent"] = _next_agent(session)
        session["pending_turn_id"] = f"T_{session['turn_counter']:03d}"
        session["latest_question"] = _generate_question(
            session["current_agent"],
            session["interview_config"]["role"],
            session["interview_config"]["company"],
            session["interview_config"]["difficulty"],
        )
        return session
    finally:
        session["locked"] = False


def end_session(session_id: str, reason: str) -> Dict[str, Any]:
    session = SESSION_STORE[session_id]
    if session["status"] != "completed":
        session["status"] = "aborted" if reason == "aborted" else "completed"
        session["final_scores"] = _compute_final_scores(session)
    return session
