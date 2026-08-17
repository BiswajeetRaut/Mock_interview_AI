"""Technical/Coding agent — 3-step reasoning chain.

Step 1 (REASON):   Given coverage context, what topic/angle should I probe?
Step 2 (GENERATE): Generate the full question pack via LLM.
Step 3 (CRITIQUE): Is this question a duplicate? Is difficulty right? Retry if bad.

This replaces the old single-LLM-call approach with genuine agent reasoning.
"""

from __future__ import annotations

import uuid
from langchain_core.messages import SystemMessage

from agents.technical_coding.prompt import CODE_QUESTION_PROMPT
from agents.shared import build_llm, safe_json_parse, llm_generate_text


# ── Step 1: Reason about what to ask ────────────────────────────────────

_REASON_PROMPT = """\
You are a technical interviewer planning the next question.

Context:
- Company: {company} | Role: {role} | Experience: {experience} yrs
- Difficulty: {difficulty} | Round type: {round_type}
- Topics already asked: {already_asked}
- Topics to AVOID: {avoid_topics}
- Candidate's weak areas: {weakness_tags}
- Candidate's strong areas: {strength_tags}
- Preferred topics from candidate: {selected_topics}
- Supervisor's focus hint: {focus_hint}

Think step-by-step:
1. What topics are still uncovered?
2. Should I probe a weakness, or test a new area?
3. What specific topic and angle would give the most signal?

Return strict JSON:
{{
  "reasoning": "<your step-by-step thinking>",
  "chosen_topic": "<specific topic to ask about>",
  "chosen_angle": "<the angle — e.g., 'edge case handling', 'optimization', 'design tradeoffs'>",
  "why": "<1-sentence justification>"
}}
"""


# ── Step 3: Self-critique the generated question ────────────────────────

_CRITIQUE_PROMPT = """\
You are reviewing a generated interview question for quality.

Question text:
{question_text}

Context:
- Target difficulty: {difficulty}
- Topics already asked: {already_asked}
- Intended topic: {chosen_topic}

Check:
1. Is this question a near-duplicate of something already asked? (check topic overlap)
2. Is the difficulty level appropriate?
3. Is the question clear and well-formed?
4. Does it have a concrete, testable answer?

Return strict JSON:
{{
  "is_acceptable": true or false,
  "issues": ["<issue1>", ...] or [],
  "suggestion": "<how to improve, or 'none' if acceptable>"
}}
"""


def _step1_reason(state: dict) -> dict | None:
    """Step 1: Reason about what topic/angle to probe."""
    coverage = state.get("coverage_context", {})
    constraints = state.get("constraints", {})

    prompt = _REASON_PROMPT.format(
        company=state.get("company", ""),
        role=state.get("role", ""),
        experience=state.get("experience", 0),
        difficulty=state.get("difficulty", "medium"),
        round_type=state.get("round_type", "tech-dsa"),
        already_asked=coverage.get("already_asked_topics", []),
        avoid_topics=coverage.get("avoid_topics", []),
        weakness_tags=coverage.get("weakness_tags", []),
        strength_tags=coverage.get("strength_tags", []),
        selected_topics=constraints.get("selected_topics", []),
        focus_hint=state.get("focus_topic", "general coverage"),
    )

    llm = build_llm(temperature=0.4)
    if not llm:
        return None

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        return safe_json_parse(resp.content)
    except Exception:
        return None


def _step2_generate(state: dict, reasoning: dict | None) -> dict | None:
    """Step 2: Generate the full question pack."""
    coverage = state.get("coverage_context", {})
    constraints = state.get("constraints", {})

    # Inject reasoning into the generation
    extra_context = ""
    if reasoning:
        extra_context = (
            f"\n\nAGENT REASONING (follow this direction):\n"
            f"Chosen topic: {reasoning.get('chosen_topic', 'general')}\n"
            f"Chosen angle: {reasoning.get('chosen_angle', 'standard')}\n"
            f"Justification: {reasoning.get('why', '')}\n"
        )

    prompt = CODE_QUESTION_PROMPT.format(
        company=state.get("company", ""),
        role=state.get("role", ""),
        experience=state.get("experience", 0),
        job_description=state.get("job_description", ""),
        difficulty=state.get("difficulty", "medium"),
        round_type=state.get("round_type", "tech-dsa"),
        language=state.get("language_preference", "python"),
        already_asked_topics=coverage.get("already_asked_topics", []),
        avoid_topics=coverage.get("avoid_topics", []),
        weakness_tags=coverage.get("weakness_tags", []),
        strength_tags=coverage.get("strength_tags", []),
        question_type=constraints.get("question_type", "dsa"),
        selected_topics=constraints.get("selected_topics", []),
        must_include_followups=constraints.get("must_include_followups", True),
        max_time_minutes=constraints.get("max_time_minutes", 25),
        needs_test_cases=constraints.get("needs_test_cases", True),
        should_be_interview_realistic=constraints.get("should_be_interview_realistic", True),
    ) + extra_context

    llm = build_llm()
    if not llm:
        return None

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        parsed = safe_json_parse(resp.content)
        return parsed.get("question_pack")
    except Exception:
        return None


def _step3_critique(question_pack: dict, state: dict) -> dict | None:
    """Step 3: Self-critique — check for duplicates and quality."""
    coverage = state.get("coverage_context", {})

    prompt = _CRITIQUE_PROMPT.format(
        question_text=question_pack.get("question_text", "")[:500],
        difficulty=state.get("difficulty", "medium"),
        already_asked=coverage.get("already_asked_topics", []),
        chosen_topic=question_pack.get("topic_tags", ["unknown"])[0] if question_pack.get("topic_tags") else "unknown",
    )

    llm = build_llm(temperature=0.1)
    if not llm:
        return {"is_acceptable": True, "issues": [], "suggestion": "none"}

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        return safe_json_parse(resp.content)
    except Exception:
        return {"is_acceptable": True, "issues": [], "suggestion": "none"}


def _fallback_question(state: dict) -> dict:
    """Emergency fallback when all LLM steps fail."""
    role = state.get("role", "the role")
    company = state.get("company", "the company")
    difficulty = state.get("difficulty", "medium")
    round_type = state.get("round_type", "tech-dsa")

    text = llm_generate_text(
        f"Generate a single {difficulty} {'system design' if round_type == 'system-design' else 'DSA'} "
        f"interview question for {role} at {company}. Include an example. Return ONLY the question.",
        temperature=0.6,
    )
    if not text:
        text = f"Solve a coding problem relevant to {role}. Discuss your approach and time complexity."

    return {
        "question_id": f"Q_CODE_{uuid.uuid4().hex[:6]}",
        "agent_type": "code",
        "round_type": round_type,
        "difficulty": difficulty,
        "topic_tags": ["general"],
        "question_text": text,
        "core_question_text": text,
        "followup_questions": [],
        "rubric": {
            "dimensions": [
                {"key": "correctness", "max_score": 5},
                {"key": "complexity", "max_score": 5},
                {"key": "edge_cases", "max_score": 5},
                {"key": "code_quality", "max_score": 5},
            ],
            "max_total": 20,
        },
    }


# ── Public API ──────────────────────────────────────────────────────────

def generate_coding_question_node(state: dict) -> dict:
    """LangGraph node — 3-step reasoning chain for coding questions."""
    max_attempts = 2

    for attempt in range(max_attempts):
        # Step 1: Reason
        reasoning = _step1_reason(state)

        # Step 2: Generate
        question_pack = _step2_generate(state, reasoning)
        if not question_pack:
            continue

        # Step 3: Critique
        critique = _step3_critique(question_pack, state)
        if critique and critique.get("is_acceptable", True):
            return {**state, "agent_type": "code", "question_pack": question_pack}

        # If critique says not acceptable, retry with the suggestion
        if critique and critique.get("suggestion"):
            state = {**state, "focus_topic": critique["suggestion"]}

    # All attempts failed — use fallback
    return {**state, "agent_type": "code", "question_pack": _fallback_question(state)}


def generate_coding_question(state: dict) -> dict:
    """Convenience wrapper — returns just the question_pack."""
    result = generate_coding_question_node(state)
    qp = result.get("question_pack")
    if not qp:
        raise RuntimeError("Failed to generate coding question after all attempts")
    return qp
