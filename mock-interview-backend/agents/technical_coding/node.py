from langchain_core.messages import SystemMessage

from agents.technical_coding.prompt import CODE_QUESTION_PROMPT
from agents.shared import build_llm, safe_json_parse
from agents.technical_coding.state import CodeAgentState


def generate_coding_question_node(state: CodeAgentState) -> CodeAgentState:
    llm = build_llm()
    if llm is None:
        return {**state, "error": "LLM is not configured"}

    coverage = state.get("coverage_context", {})
    constraints = state.get("constraints", {})

    prompt = CODE_QUESTION_PROMPT.format(
        company=state.get("company", ""),
        role=state.get("role", ""),
        experience=state.get("experience", 0),
        job_description=state.get("job_description", ""),
        difficulty=state.get("difficulty", "easy"),
        round_type=state.get("round_type", "tech-dsa"),
        language=state.get("language_preference", "javascript"),

        already_asked_topics=coverage.get("already_asked_topics", []),
        avoid_topics=coverage.get("avoid_topics", []),
        weakness_tags=coverage.get("weakness_tags", []),
        strength_tags=coverage.get("strength_tags", []),

        question_type=constraints.get("question_type", "dsa"),
        selected_topics=constraints.get("selected_topics", []),
        must_include_followups=constraints.get("must_include_followups", True),
        max_time_minutes=constraints.get("max_time_minutes", 25),
        needs_test_cases=constraints.get("needs_test_cases", True),
        should_be_interview_realistic=constraints.get(
            "should_be_interview_realistic", True),
    )

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        parsed = safe_json_parse(resp.content)

        # parsed must contain { "question_pack": {...} }
        question_pack = parsed.get("question_pack")
        if not question_pack:
            return {**state, "error": "LLM did not return question_pack"}

        return {
            **state,
            "agent_type": "code",
            "question_pack": question_pack,
        }

    except Exception as e:
        return {**state, "error": f"Failed to generate coding question: {str(e)}"}


def generate_coding_question(state: CodeAgentState):
    result = generate_coding_question_node(state)
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result.get("question_pack")
