# agents/technical_coding/nodes.py
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from agents.technical_coding.prompt import CODE_QUESTION_PROMPT
from agents.technical_coding.logic import safe_json_parse
from agents.technical_coding.state import CodeAgentState
from dotenv import load_dotenv
load_dotenv()


def build_llm():
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.2)


def generate_coding_question_node(state: CodeAgentState) -> CodeAgentState:
    llm = build_llm()

    coverage = state.get("coverage_context", {})
    constraints = state.get("constraints", {})

    prompt = CODE_QUESTION_PROMPT.format(
        company=state.get("company", ""),
        role=state.get("role", ""),
        difficulty=state.get("difficulty", "easy"),
        language=state.get("language_preference", "javascript"),

        already_asked_topics=coverage.get("already_asked_topics", []),
        avoid_topics=coverage.get("avoid_topics", []),
        weakness_tags=coverage.get("weakness_tags", []),
        strength_tags=coverage.get("strength_tags", []),

        question_type=constraints.get("question_type", "dsa"),
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
