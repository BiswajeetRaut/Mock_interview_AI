"""Resume-based agent — 3-step reasoning chain.

Step 1 (REASON):   What aspect of the candidate's experience to probe?
Step 2 (GENERATE): Generate the question via LLM.
Step 3 (CRITIQUE): Is it a duplicate? Is it relevant to the resume?
"""

from __future__ import annotations

import uuid
from langchain_core.messages import SystemMessage

from agents.resume_based.prompt import RESUME_QUESTION_PROMPT
from agents.shared import build_llm, safe_json_parse, llm_generate_text


_REASON_PROMPT = """\
You are planning a resume-based interview question.

Candidate's resume summary: {resume_summary}
Topics already asked: {already_asked}
Topics to AVOID: {avoid_topics}
Candidate weak areas: {weakness_tags}
Preferred topics: {preferred_topics}
Focus hint from supervisor: {focus_hint}

Think step-by-step:
1. What resume projects/skills haven't been explored yet?
2. Should I probe a weakness (e.g., lack of quantified results) or explore a new area?
3. What specific aspect of their experience would give the most signal?

Return strict JSON:
{{
  "reasoning": "<your thinking>",
  "chosen_angle": "<e.g., 'ownership in X project', 'decision-making under ambiguity'>",
  "why": "<justification>"
}}
"""

_CRITIQUE_PROMPT = """\
Review this resume-based interview question:

Question: {question_text}
Resume summary: {resume_summary}
Already asked topics: {already_asked}

Check:
1. Is it relevant to the candidate's actual experience?
2. Is it a duplicate of a previous question?
3. Does it invite a STAR-style response?

Return strict JSON:
{{
  "is_acceptable": true or false,
  "issues": [],
  "suggestion": "<improvement or 'none'>"
}}
"""


def _fallback(state: dict) -> dict:
    role = state.get("role", "the role")
    topic = (state.get("preferred_topics") or ["ownership"])[0]
    return {
        "question_id": f"Q_RES_{uuid.uuid4().hex[:6]}",
        "agent_type": "resume",
        "topic_tag": topic.lower().replace(" ", "_"),
        "question_text": (
            f"Tell me about a project where you demonstrated {topic} "
            f"relevant to {role}. Walk me through the situation, your actions, and the outcome."
        ),
        "core_question_text": "",
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
        "followup_questions": [],
    }


def generate_resume_question(state: dict) -> dict:
    """3-step reasoning chain for resume questions."""
    coverage = state.get("coverage_context", {})
    resume_summary = state.get("resume_summary", "")
    llm = build_llm()
    if not llm:
        return _fallback(state)

    # Step 1: Reason
    reasoning = None
    try:
        reason_prompt = _REASON_PROMPT.format(
            resume_summary=resume_summary[:500],
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
        extra = f"\n\nAGENT REASONING:\nAngle: {reasoning.get('chosen_angle', '')}\nWhy: {reasoning.get('why', '')}\n"

    try:
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
                resume_summary=resume_summary[:300],
                already_asked=coverage.get("already_asked_topics", []),
            )
            cresp = build_llm(temperature=0.1).invoke([SystemMessage(content=critique_prompt)])
            critique = safe_json_parse(cresp.content)
            if critique and not critique.get("is_acceptable", True):
                # Retry once with suggestion
                retry_prompt = prompt + f"\n\nPREVIOUS ATTEMPT REJECTED: {critique.get('suggestion', '')}\nGenerate a DIFFERENT question."
                resp2 = llm.invoke([SystemMessage(content=retry_prompt)])
                parsed2 = safe_json_parse(resp2.content)
                qp = parsed2.get("question_pack") or qp
        except Exception:
            pass  # critique failed, use original

        qp.setdefault("core_question_text", qp.get("question_text", ""))
        qp.setdefault("followup_questions", [])
        return qp

    except Exception:
        return _fallback(state)


def resume_agent_node(state: dict) -> dict:
    """LangGraph-compatible wrapper."""
    qp = generate_resume_question(state)
    state["agent_type"] = "resume"
    state["question_pack"] = qp
    return state
