"""Supervisor helpers for graph routing and live session orchestration."""

from .prompt import SUPERVISOR_PROMPT, SESSION_SUPERVISOR_PROMPT
from .logic import update_state_from_report
from .state import InterviewState
from agents.shared import build_llm, safe_json_parse


llm = build_llm(temperature=0)


def _candidate_signaled_stuck(answer_text: str) -> bool:
    normalized = " ".join((answer_text or "").lower().split())
    if not normalized:
        return True

    stuck_phrases = [
        "i don't know",
        "i dont know",
        "do not know",
        "not sure",
        "no idea",
        "i have no idea",
        "i'm not sure",
        "im not sure",
        "can't remember",
        "cannot remember",
        "don't remember",
        "do not remember",
        "blanking",
        "skip this",
        "pass on this",
        "move on",
    ]
    return any(phrase in normalized for phrase in stuck_phrases)


def _fallback_session_decision(session: dict, latest_turn: dict | None, latest_evaluation: dict | None):
    latest_turn = latest_turn or {}
    latest_evaluation = latest_evaluation or {}

    if session.get("turn_counter", 1) >= session.get("interview_config", {}).get("total_turns_planned", 1):
        return {
            "action": "end_interview",
            "next_agent": session.get("current_agent", "code"),
            "focus": "wrap_up",
            "acknowledgement": "Thanks, that gives me enough context.",
            "transition": "Let's wrap up the interview here.",
            "reason": "Reached planned turn limit.",
        }

    question_pack = latest_turn.get("question_pack", {})
    followups = question_pack.get("followup_questions", [])
    answer_text = latest_turn.get("user_answer_transcript", "")
    word_count = len(answer_text.split())
    percentage = latest_evaluation.get("percentage", 0)
    current_agent = latest_turn.get("agent_type", session.get("current_agent", "code"))
    candidate_stuck = _candidate_signaled_stuck(answer_text)

    next_agent = session.get("current_agent", "code")
    turn_counter = session.get("turn_counter", 1)
    turn_plan = session.get("turn_plan", [])
    if turn_plan and turn_counter < len(turn_plan):
        next_agent = turn_plan[turn_counter].get("agent_type", next_agent)

    if candidate_stuck:
        if next_agent == current_agent:
            action = "ask_question"
            transition = "No problem, let's leave that one and try a different question."
        else:
            action = "switch_round"
            round_labels = {
                "code": "technical problem-solving",
                "resume": "your past experience",
                "hr": "behavioral and collaboration topics",
            }
            transition = f"No problem. Let's move on and switch into {round_labels.get(next_agent, next_agent)}."
        return {
            "action": action,
            "next_agent": next_agent,
            "focus": "move_on",
            "acknowledgement": "That's okay.",
            "transition": transition,
            "reason": "Candidate explicitly signaled they were stuck.",
        }

    if (not question_pack.get("is_followup")) and followups and (word_count < 35 or percentage < 65):
        return {
            "action": "follow_up",
            "next_agent": current_agent,
            "focus": "depth",
            "acknowledgement": "Thanks, I want to understand that a bit better.",
            "transition": "Let me stay with that for a moment.",
            "reason": "Answer was too shallow for a clean handoff.",
        }

    if next_agent == current_agent:
        action = "ask_question"
        transition = "Let's stay in this area and go one level deeper."
    else:
        action = "switch_round"
        round_labels = {
            "code": "technical problem-solving",
            "resume": "your past experience",
            "hr": "behavioral and collaboration topics",
        }
        transition = f"Let's switch gears a bit and move into {round_labels.get(next_agent, next_agent)}."

    return {
        "action": action,
        "next_agent": next_agent,
        "focus": "coverage",
        "acknowledgement": "Thanks, that was helpful.",
        "transition": transition,
        "reason": "Fallback routing based on turn plan and answer depth.",
    }


def plan_session_next_step(session: dict, latest_turn: dict | None = None, latest_evaluation: dict | None = None):
    if llm is None:
        return _fallback_session_decision(session, latest_turn, latest_evaluation)

    prompt_input = {
        "state": {
            "current_agent": session.get("current_agent"),
            "current_round_type": session.get("current_round_type"),
            "turn_counter": session.get("turn_counter"),
            "turn_plan": session.get("turn_plan", []),
            "selected_types": session.get("interview_config", {}).get("selected_types", []),
            "topics": session.get("interview_config", {}).get("topics", {}),
            "coverage_context": session.get("coverage_context", {}),
            "total_turns_planned": session.get("interview_config", {}).get("total_turns_planned"),
            "company": session.get("interview_config", {}).get("company"),
            "role": session.get("interview_config", {}).get("role"),
            "experience": session.get("interview_config", {}).get("experience", 0),
            "jd": session.get("interview_config", {}).get("jd", ""),
            "candidate_signaled_stuck": _candidate_signaled_stuck((latest_turn or {}).get("user_answer_transcript", "")),
        },
        "latest_turn": latest_turn or {},
        "latest_evaluation": latest_evaluation or {},
    }

    try:
        response = llm.invoke(SESSION_SUPERVISOR_PROMPT.format_messages(**prompt_input)).content
        decision = safe_json_parse(response)
        return {
            "action": decision.get("action", "ask_question"),
            "next_agent": decision.get("next_agent", session.get("current_agent", "code")),
            "focus": decision.get("focus", "coverage"),
            "acknowledgement": decision.get("acknowledgement", "Thanks."),
            "transition": decision.get("transition", "Let's continue."),
            "reason": decision.get("reason", ""),
        }
    except Exception:
        return _fallback_session_decision(session, latest_turn, latest_evaluation)


def supervisor_node(state: InterviewState) -> InterviewState:
    if llm is None:
        state["supervisor_decision"] = {
            "next_agent": "technical",
            "action": "ask_question",
            "focus": "optimization",
        }
        state["latest_agent_report"] = None
        return state

    report = state.get("latest_agent_report")

    prompt_input = {
        "state": {
            "current_round": state["current_round"],
            "difficulty": state["difficulty"],
            "target_signal": state["target_signal"],
            "weakness_map": state["weakness_map"],
            "time_remaining": state["time_remaining"],
        },
        "agent_report": report,
    }

    response = llm.invoke(SUPERVISOR_PROMPT.format_messages(**prompt_input)).content
    decision = safe_json_parse(response)

    update_state_from_report(state, report)

    state["supervisor_decision"] = decision
    state["latest_agent_report"] = None

    return state
