from langchain_core.messages import SystemMessage

from agents.manegerial.prompt import HR_QUESTION_PROMPT
from agents.shared import build_llm, safe_json_parse


def _fallback_hr_question(state):
    company = state.get("company", "the company")
    preferred_topics = state.get("preferred_topics", [])
    topic_hint = preferred_topics[0] if preferred_topics else "conflict resolution"
    return {
        "question_id": "Q_HR_FALLBACK",
        "agent_type": "hr",
        "topic_tag": topic_hint.lower().replace(" ", "_"),
        "question_text": f"Tell me about a time you had to demonstrate {topic_hint} while working toward a goal relevant to {company}. How did you handle it and what happened next?",
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
            "What would you change about your approach now?",
            "How did that experience affect how you work with people afterward?",
        ],
    }


def generate_hr_question(state):
    llm = build_llm()
    if llm is None:
        return _fallback_hr_question(state)
    coverage = state.get("coverage_context", {})

    prompt = HR_QUESTION_PROMPT.format(
        company=state.get("company", ""),
        role=state.get("role", ""),
        experience=state.get("experience", 0),
        job_description=state.get("job_description", ""),
        preferred_topics=state.get("preferred_topics", []),
        already_asked_topics=coverage.get("already_asked_topics", []),
        weakness_tags=coverage.get("weakness_tags", []),
        strength_tags=coverage.get("strength_tags", []),
    )

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        parsed = safe_json_parse(resp.content)
        return parsed.get("question_pack") or _fallback_hr_question(state)
    except Exception:
        return _fallback_hr_question(state)


def hr_agent_node(state):
    question_pack = generate_hr_question(state)
    state["agent_type"] = "hr"
    state["question_pack"] = question_pack
    return state
