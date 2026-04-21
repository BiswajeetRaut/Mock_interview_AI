"""HR/Behavioral agent — 3-step reasoning chain.

Step 1 (REASON):   What behavioral competency to probe?
Step 2 (GENERATE): Generate the question via LLM.
Step 3 (CRITIQUE): Is it unique? Is it appropriate for the experience level?
"""

from __future__ import annotations

import uuid
from langchain_core.messages import SystemMessage

from agents.manegerial.prompt import HR_QUESTION_PROMPT
from agents.shared import build_llm, safe_json_parse, llm_generate_text


_REASON_PROMPT = """\
You are planning a behavioral/HR interview question.

Company: {company} | Role: {role} | Experience: {experience} yrs
Topics already asked: {already_asked}
Topics to AVOID: {avoid_topics}
Candidate weak areas: {weakness_tags}
Preferred topics: {preferred_topics}
Focus hint from supervisor: {focus_hint}

Think step-by-step:
1. What behavioral competencies haven't been tested yet?
2. Given the role and experience, what level of leadership/ownership to expect?
3. Should I probe a weak area or test something new?

Return strict JSON:
{{
  "reasoning": "<your thinking>",
  "chosen_competency": "<e.g., 'conflict resolution', 'leading under ambiguity'>",
  "why": "<justification>"
}}
"""

_CRITIQUE_PROMPT = """\
Review this behavioral interview question:

Question: {question_text}
Already asked topics: {already_asked}
Experience level: {experience} years

Check:
1. Is it too similar to a previous question?
2. Is the expected depth appropriate for the experience level?
3. Does it invite concrete examples (not just opinions)?

Return strict JSON:
{{
  "is_acceptable": true or false,
  "issues": [],
  "suggestion": "<improvement or 'none'>"
}}
"""


def _fallback(state: dict) -> dict:
    company = state.get("company", "the company")
    topic = (state.get("preferred_topics") or ["conflict resolution"])[0]
    return {
        "question_id": f"Q_HR_{uuid.uuid4().hex[:6]}",
        "agent_type": "hr",
        "topic_tag": topic.lower().replace(" ", "_"),
        "question_text": (
            f"Tell me about a time you demonstrated {topic} while working at "
            f"a company like {company}. What happened, and what did you learn?"
        ),
        "core_question_text": "",
        "rubric": {
            "dimensions": [
                {"key": "self_awareness", "max_score": 5},
                {"key": "communication", "max_score": 5},
                {"key": "proactiveness", "max_score": 5},
                {"key": "outcome_focus", "max_score": 5},
            ],
            "max_total": 20,
        },
        "followup_questions": [],
    }


def generate_hr_question(state: dict) -> dict:
    """3-step reasoning chain for HR/behavioral questions."""
    coverage = state.get("coverage_context", {})
    llm = build_llm()
    if not llm:
        return _fallback(state)

    # Step 1: Reason
    reasoning = None
    try:
        reason_prompt = _REASON_PROMPT.format(
            company=state.get("company", ""),
            role=state.get("role", ""),
            experience=state.get("experience", 0),
            already_asked=coverage.get("already_asked_topics", []),
            avoid_topics=coverage.get("avoid_topics", []),
            weakness_tags=coverage.get("weakness_tags", []),
            preferred_topics=state.get("preferred_topics", []),
            focus_hint=state.get("focus_topic", "general coverage"),
        )
        resp = llm.invoke([SystemMessage(content=reason_prompt)])
        reasoning = safe_json_parse(resp.content)
    except Exception:
        pass

    # Step 2: Generate
    extra = ""
    if reasoning:
        extra = f"\n\nAGENT REASONING:\nCompetency: {reasoning.get('chosen_competency', '')}\nWhy: {reasoning.get('why', '')}\n"

    try:
        prompt = HR_QUESTION_PROMPT.format(
            company=state.get("company", ""),
            role=state.get("role", ""),
            experience=state.get("experience", 0),
            job_description=state.get("job_description", ""),
            preferred_topics=state.get("preferred_topics", []),
            already_asked_topics=coverage.get("already_asked_topics", []),
            weakness_tags=coverage.get("weakness_tags", []),
            strength_tags=coverage.get("strength_tags", []),
        ) + extra

        resp = llm.invoke([SystemMessage(content=prompt)])
        parsed = safe_json_parse(resp.content)
        qp = parsed.get("question_pack")
        if not qp:
            return _fallback(state)

        # Step 3: Critique
        try:
            critique_prompt = _CRITIQUE_PROMPT.format(
                question_text=qp.get("question_text", "")[:400],
                already_asked=coverage.get("already_asked_topics", []),
                experience=state.get("experience", 0),
            )
            cresp = build_llm(temperature=0.1).invoke([SystemMessage(content=critique_prompt)])
            critique = safe_json_parse(cresp.content)
            if critique and not critique.get("is_acceptable", True):
                retry_prompt = prompt + f"\n\nPREVIOUS ATTEMPT REJECTED: {critique.get('suggestion', '')}\nGenerate a DIFFERENT question."
                resp2 = llm.invoke([SystemMessage(content=retry_prompt)])
                parsed2 = safe_json_parse(resp2.content)
                qp = parsed2.get("question_pack") or qp
        except Exception:
            pass

        qp.setdefault("core_question_text", qp.get("question_text", ""))
        qp.setdefault("followup_questions", [])
        return qp

    except Exception:
        return _fallback(state)


def hr_agent_node(state: dict) -> dict:
    """LangGraph-compatible wrapper."""
    qp = generate_hr_question(state)
    state["agent_type"] = "hr"
    state["question_pack"] = qp
    return state
