from langchain_core.messages import SystemMessage

from agents.resume_based.prompt import RESUME_QUESTION_PROMPT
from agents.shared import build_llm, safe_json_parse


def _fallback_resume_question(state):
    role = state.get("role", "the role")
    preferred_topics = state.get("preferred_topics", [])
    topic_hint = preferred_topics[0] if preferred_topics else "ownership"
    return {
        "question_id": "Q_RESUME_FALLBACK",
        "agent_type": "resume",
        "topic_tag": topic_hint.lower().replace(" ", "_"),
        "question_text": f"Tell me about a project from your resume where you demonstrated {topic_hint} relevant to {role}. What was the problem, what decisions did you make, and what outcome did you drive?",
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
            "What trade-off did you personally make there?",
            "What would you do differently if you had to do it again?",
        ],
    }


def generate_resume_question(state):
    llm = build_llm()
    if llm is None:
        return _fallback_resume_question(state)
    coverage = state.get("coverage_context", {})
    resume_summary = state.get("resume_summary", "")

    prompt = RESUME_QUESTION_PROMPT.format(
        company=state.get("company", ""),
        role=state.get("role", ""),
        experience=state.get("experience", 0),
        resume_summary=resume_summary,
        job_description=state.get("job_description", ""),
        preferred_topics=state.get("preferred_topics", []),
        already_asked_topics=coverage.get("already_asked_topics", []),
        weakness_tags=coverage.get("weakness_tags", []),
        strength_tags=coverage.get("strength_tags", []),
    )

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        parsed = safe_json_parse(resp.content)
        return parsed.get("question_pack") or _fallback_resume_question(state)
    except Exception:
        return _fallback_resume_question(state)


def resume_agent_node(state):
    question_pack = generate_resume_question(state)
    state["agent_type"] = "resume"
    state["question_pack"] = question_pack
    return state
