from __future__ import annotations

from datetime import datetime, timezone
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


def _build_turn_plan(turn_distribution: Dict[str, int], total_turns: int) -> List[str]:
    remaining = {
        "code": max(0, int(turn_distribution.get("code", 0))),
        "resume": max(0, int(turn_distribution.get("resume", 0))),
        "hr": max(0, int(turn_distribution.get("hr", 0))),
    }
    plan: List[str] = []
    while len(plan) < total_turns and sum(remaining.values()) > 0:
        for agent in AGENT_ORDER:
            if remaining[agent] > 0 and len(plan) < total_turns:
                plan.append(agent)
                remaining[agent] -= 1
    # Fallback if distribution sum is lower than requested turns
    while len(plan) < total_turns:
        plan.append(AGENT_ORDER[len(plan) % len(AGENT_ORDER)])
    return plan


def _generate_code_question(role: str, company: str, difficulty: str) -> Dict[str, Any]:
    return {
        "question_id": f"Q_CODE_{uuid.uuid4().hex[:6]}",
        "agent_type": "code",
        "topic_tags": ["arrays", "sliding_window"],
        "difficulty": difficulty,
        "question_text": f"Given an integer array nums, return the minimum length subarray with sum >= target. Discuss an approach expected for a {role} interview at {company}.",
        "input_output_format": {"input": "nums: int[], target: int", "output": "int"},
        "constraints": ["1 <= n <= 1e5", "1 <= nums[i] <= 1e4"],
        "expected_solution_outline": ["sliding window", "expand right", "shrink left when sum >= target"],
        "time_space_targets": {"expected_time": "O(n)", "expected_space": "O(1)"},
        "rubric": {
            "dimensions": [
                {"key": "correctness", "max_score": 5},
                {"key": "complexity", "max_score": 5},
                {"key": "edge_cases", "max_score": 5},
                {"key": "code_quality", "max_score": 5},
            ],
            "max_total": 20,
        },
        "followup_questions": [
            "Why is this valid only for positive integers?",
            "How would your solution change with negative numbers?",
        ],
    }


def _generate_resume_question() -> Dict[str, Any]:
    return {
        "question_id": f"Q_RES_{uuid.uuid4().hex[:6]}",
        "agent_type": "resume",
        "topic_tag": "project_challenges",
        "question_text": "Tell me about a real project challenge from your resume and walk through Situation, Task, Action, and Result.",
        "expected_framework": "STAR",
        "rubric": {
            "dimensions": [
                {"key": "situation_clarity", "max_score": 5},
                {"key": "action_ownership", "max_score": 5},
                {"key": "result_quantified", "max_score": 5},
                {"key": "honesty_depth", "max_score": 5},
            ],
            "max_total": 20,
        },
        "followup_questions": [
            "What would you do differently next time?",
            "What metric proved success?",
        ],
    }


def _generate_hr_question() -> Dict[str, Any]:
    return {
        "question_id": f"Q_HR_{uuid.uuid4().hex[:6]}",
        "agent_type": "hr",
        "topic_tag": "adaptability",
        "question_text": "Describe a situation where project requirements changed suddenly. How did you adapt?",
        "rubric": {
            "dimensions": [
                {"key": "self_awareness", "max_score": 5},
                {"key": "communication", "max_score": 5},
                {"key": "proactiveness", "max_score": 5},
                {"key": "outcome_focus", "max_score": 5},
            ],
            "max_total": 20,
        },
        "followup_questions": [
            "How did your communication style help in this situation?",
            "What did you learn that changed your approach afterwards?",
        ],
    }


def _generate_question(agent_type: str, role: str, company: str, difficulty: str) -> Dict[str, Any]:
    if agent_type == "code":
        return _generate_code_question(role, company, difficulty)
    if agent_type == "resume":
        return _generate_resume_question()
    return _generate_hr_question()


def _score_from_answer(answer_text: str, max_score: int) -> int:
    words = len(answer_text.split())
    if words >= 120:
        return max_score
    if words >= 80:
        return max(1, max_score - 1)
    if words >= 40:
        return max(1, max_score - 2)
    if words >= 20:
        return max(1, max_score - 3)
    return 1


def _evaluate_answer(agent_type: str, answer_text: str, question_pack: Dict[str, Any]) -> Dict[str, Any]:
    rubric_dims = question_pack.get("rubric", {}).get("dimensions", [])
    scores: Dict[str, Dict[str, Any]] = {}
    total = 0
    max_total = 0
    for dim in rubric_dims:
        key = dim["key"]
        max_score = int(dim.get("max_score", 5))
        score = _score_from_answer(answer_text, max_score)
        scores[key] = {
            "score": score,
            "max": max_score,
            "comment": f"{key.replace('_', ' ').title()} evaluated for {agent_type} answer.",
        }
        total += score
        max_total += max_score

    percentage = round((total / max_total) * 100) if max_total else 0
    weak_tags = [key for key, item in scores.items() if item["score"] <= max(1, item["max"] // 2)]
    strong_tags = [key for key, item in scores.items() if item["score"] >= item["max"] - 1]
    verdict = "excellent" if percentage >= 85 else "good" if percentage >= 70 else "average" if percentage >= 50 else "poor"

    return {
        "scores": scores,
        "total_score": total,
        "max_score": max_total,
        "percentage": percentage,
        "verdict": verdict,
        "feedback_summary": f"{agent_type.upper()} rubric evaluation completed.",
        "suggested_improvements": [f"Improve {tag.replace('_', ' ')}." for tag in weak_tags[:3]],
        "topics_demonstrated_weak": weak_tags,
        "topics_demonstrated_strong": strong_tags,
    }


def _compute_final_scores(session: Dict[str, Any]) -> Dict[str, Any]:
    grouped: Dict[str, List[int]] = {"code": [], "resume": [], "hr": []}
    for turn in session["turns"]:
        grouped[turn["agent_type"]].append(turn["evaluation"]["percentage"])

    domain_scores: Dict[str, Any] = {}
    all_scores: List[int] = []
    for key in ["code", "resume", "hr"]:
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

    overall = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    domain_scores["overall"] = overall
    return domain_scores


def _next_agent(session: Dict[str, Any], next_turn_counter: int) -> str:
    turn_plan = session.get("turn_plan", AGENT_ORDER)
    if 1 <= next_turn_counter <= len(turn_plan):
        return turn_plan[next_turn_counter - 1]
    return AGENT_ORDER[(next_turn_counter - 1) % len(AGENT_ORDER)]


def start_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = f"S_{uuid.uuid4().hex[:8]}"
    parsed_resume = _parse_resume_text(payload["resume_content"]["data"])
    created_at = _now_iso()

    turn_plan = _build_turn_plan(payload["turn_distribution"], payload["total_turns_planned"])
    first_agent = turn_plan[0] if turn_plan else "code"
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
        "turn_plan": turn_plan,
        "turn_counter": 1,
        "current_agent": first_agent,
        "coverage_context": {
            "already_asked_topics": [],
            "avoid_topics": [],
            "weakness_tags": [],
            "strength_tags": [],
        },
        "turns": [],
        "final_scores": {
            "code": {"score": None, "turns_evaluated": 0, "verdict": None},
            "resume": {"score": None, "turns_evaluated": 0, "verdict": None},
            "hr": {"score": None, "turns_evaluated": 0, "verdict": None},
            "overall": None,
        },
        "pending_turn_id": f"T_{1:03d}",
        "latest_question": _generate_question(
            first_agent, payload["role"], payload["company"], payload["difficulty"]
        ),
        "locked": False,
        "request_cache": {},
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

    request_id = answer_payload.get("request_id")
    if request_id and request_id in session["request_cache"]:
        return session

    session["locked"] = True
    try:
        agent_type = session["current_agent"]
        question_pack = session["latest_question"] or _generate_question(
            agent_type,
            session["interview_config"]["role"],
            session["interview_config"]["company"],
            session["interview_config"]["difficulty"],
        )
        evaluation = _evaluate_answer(agent_type, answer_payload["answer_text"], question_pack)
        turn = {
            "turn_id": session["pending_turn_id"],
            "agent_type": agent_type,
            "question_id": question_pack["question_id"],
            "question_text": question_pack["question_text"],
            "question_pack": question_pack,
            "user_answer_transcript": answer_payload["answer_text"],
            "evaluation": evaluation,
            "completed_at": _now_iso(),
        }
        session["turns"].append(turn)
        session["coverage_context"]["already_asked_topics"].append(
            question_pack.get("topic_tag") or ",".join(question_pack.get("topic_tags", []))
        )

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
            if request_id:
                session["request_cache"][request_id] = turn["turn_id"]
            return session

        session["turn_counter"] += 1
        session["current_agent"] = _next_agent(session, session["turn_counter"])
        session["pending_turn_id"] = f"T_{session['turn_counter']:03d}"
        session["latest_question"] = _generate_question(
            session["current_agent"],
            session["interview_config"]["role"],
            session["interview_config"]["company"],
            session["interview_config"]["difficulty"],
        )
        if request_id:
            session["request_cache"][request_id] = turn["turn_id"]
        return session
    finally:
        session["locked"] = False


def end_session(session_id: str, reason: str) -> Dict[str, Any]:
    session = SESSION_STORE[session_id]
    if session["status"] != "completed":
        session["status"] = "aborted" if reason in {"aborted", "manual_end"} else "completed"
        session["final_scores"] = _compute_final_scores(session)
    return session
