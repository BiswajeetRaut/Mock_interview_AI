"""Supervisor agent — pure LLM-powered reasoning, no deterministic overrides.

The supervisor is a genuine autonomous agent. It receives the full interview
context (history, evaluation, coverage) and reasons step-by-step about what
to do next. The ONLY hard guardrail is the max_turns safety cap — everything
else is decided by the LLM through the ReAct prompt.

Node functions:
  • supervisor_node    — reasons about the answer and decides next action
  • followup_node      — generates a contextual follow-up question via LLM
  • opening_node       — generates the first question with a warm greeting
"""

from __future__ import annotations

import uuid

from langchain_core.messages import SystemMessage

from .prompt import (
    SUPERVISOR_REASONING_PROMPT,
    FOLLOWUP_GENERATION_PROMPT,
    OPENING_GREETING_PROMPT,
)
from .logic import update_coverage_from_evaluation
from .state import InterviewState
from agents.shared import build_llm, safe_json_parse, llm_generate_text, INTERVIEWER_STYLE_RULE


AGENTS = ("code", "resume", "hr")

ROUND_TYPE_TO_AGENT = {
    "tech-dsa": "code",
    "system-design": "code",
    "managerial": "hr",
    "resume-based": "resume",
    "tech-resume": "resume",
}

ROUND_LABELS = {
    "code": "technical problem-solving",
    "resume": "your past experience",
    "hr": "behavioral and collaboration topics",
}

_BANNED_PREFIXES = (
    "i appreciate your", "i appreciate ", "i'd appreciate",
    "that's a great", "great question", "thank you for sharing",
    "thanks for sharing", "that's great", "i'm surprised",
    "i'm disappointed", "it seems we need to start with the basics",
    "i expected more", "that's unfortunate",
)


def _normalize_agent(agent: str | None) -> str:
    """Ensure agent type is valid."""
    return agent if agent in AGENTS else "code"


def _sanitize_text(text: str) -> str:
    """Strip banned opening phrases from LLM-generated text."""
    if not text:
        return text
    cleaned = text.strip()
    lower = cleaned.lower()
    for prefix in sorted(_BANNED_PREFIXES, key=len, reverse=True):
        if lower.startswith(prefix):
            rest = cleaned[len(prefix):].lstrip(" ,;.!-:")
            if rest:
                cleaned = rest[0].upper() + rest[1:]
            break
    return cleaned


def _allowed_agents(state: dict) -> list[str]:
    """Determine which agent types are available for this session."""
    config = state.get("interview_config") or {}
    selected_types = config.get("selected_types") or []
    allowed: list[str] = []
    for rt in selected_types:
        mapped = ROUND_TYPE_TO_AGENT.get(str(rt))
        if mapped and mapped not in allowed:
            allowed.append(mapped)
    if not allowed:
        allowed = list(AGENTS)
    return allowed


def _build_turn_history(turns: list, max_turns: int = 10) -> str:
    """Format completed turns into a readable summary for the supervisor."""
    if not turns:
        return "No previous turns yet — this is the first question."

    lines: list[str] = []
    for t in turns[-max_turns:]:
        tid = t.get("turn_id", "?")
        agent = t.get("agent_type", "?")
        ev = t.get("evaluation") or {}
        pct = ev.get("percentage", "?")
        verdict = ev.get("verdict", "?")
        answer = (t.get("user_answer_transcript") or "")[:100]
        question = (t.get("question_text") or "")[:80]
        weak = ev.get("topics_demonstrated_weak", [])
        strong = ev.get("topics_demonstrated_strong", [])
        difficulty = t.get("difficulty", "?")

        line = (
            f"Turn {tid} [{agent}, {difficulty}] — Score: {pct}% ({verdict})\n"
            f"  Q: {question}…\n"
            f"  A: {answer}…"
        )
        if weak:
            line += f"\n  Weak: {', '.join(weak[:3])}"
        if strong:
            line += f"\n  Strong: {', '.join(strong[:3])}"
        lines.append(line)

    return "\n\n".join(lines)


def _agent_usage_summary(turns: list, allowed: list[str]) -> str:
    """Count how many turns each agent has been used."""
    counts = {a: 0 for a in allowed}
    for t in turns:
        a = t.get("agent_type", "")
        if a in counts:
            counts[a] += 1
    return ", ".join(f"{a}: {c} turns" for a, c in counts.items())


def _candidate_summary(state: dict) -> str:
    """Build a concise candidate profile string."""
    candidate = state.get("candidate") or {}
    parsed = candidate.get("resume_parsed") or {}
    skills = ", ".join(parsed.get("skills", [])[:8]) or "none listed"
    projects = ", ".join(parsed.get("projects", [])[:3]) or "none listed"
    summary = parsed.get("summary", "")
    name = candidate.get("name", "Candidate")
    return (
        f"Name: {name}\n"
        f"Skills: {skills}\n"
        f"Projects: {projects}\n"
        f"Summary: {summary or 'No resume summary available'}"
    )


def _format_evaluation(evaluation: dict) -> str:
    """Format evaluation results for the supervisor prompt."""
    if not evaluation:
        return "No evaluation available."

    scores = evaluation.get("scores", {})
    score_lines = []
    for key, val in scores.items():
        if isinstance(val, dict):
            score_lines.append(f"  {key}: {val.get('score', '?')}/{val.get('max', 5)} — {val.get('comment', '')}")
        else:
            score_lines.append(f"  {key}: {val}")

    is_clar = evaluation.get("is_clarification_request", False)

    return (
        f"Total: {evaluation.get('total_score', '?')}/{evaluation.get('max_score', '?')} "
        f"({evaluation.get('percentage', '?')}%)\n"
        f"Verdict: {evaluation.get('verdict', '?')}\n"
        f"Is clarification request: {'YES' if is_clar else 'no'}\n"
        f"Dimension scores:\n" + "\n".join(score_lines) + "\n"
        f"Feedback: {evaluation.get('feedback_summary', '')}\n"
        f"Weak tags: {evaluation.get('topics_demonstrated_weak', [])}\n"
        f"Strong tags: {evaluation.get('topics_demonstrated_strong', [])}"
    )


# ── MAIN SUPERVISOR NODE ────────────────────────────────────────────────

def supervisor_node(state: InterviewState) -> dict:
    """LangGraph node — the agentic supervisor reasons and decides.

    This is a PURE LLM reasoning agent. The only hard guardrail is max_turns.
    Everything else — follow-up decisions, agent routing, difficulty changes,
    when to end — is decided by the LLM through chain-of-thought reasoning.

    Reads: evaluation, current_question_pack, answer_text, interview_config,
           turns, coverage_context, supervisor_scratchpad, signal_confidence
    Writes: supervisor_decision, is_interview_over, current_agent,
            current_difficulty, supervisor_scratchpad, signal_confidence,
            coverage_context, turns (appends current turn)
    """
    evaluation = state.get("evaluation") or {}
    question_pack = state.get("current_question_pack") or {}
    answer_text = state.get("answer_text", "")
    config = state.get("interview_config") or {}
    turns = list(state.get("turns") or [])
    coverage = dict(state.get("coverage_context") or {})
    scratchpad = list(state.get("supervisor_scratchpad") or [])

    tc = int(state.get("turn_counter", 0))
    max_turns = int(state.get("max_turns", 12))
    current_agent = _normalize_agent(state.get("current_agent", "code"))
    current_difficulty = state.get("current_difficulty", "medium")
    allowed = _allowed_agents(state)

    # ── Record the completed turn ────────────────────────────────────
    turn_record = {
        "turn_id": f"T_{tc:03d}",
        "agent_type": current_agent,
        "difficulty": current_difficulty,
        "round_type": question_pack.get("round_type", ""),
        "question_id": question_pack.get("question_id", ""),
        "question_text": question_pack.get("question_text", ""),
        "question_pack": question_pack,
        "user_answer_transcript": answer_text,
        "evaluation": evaluation,
    }
    turns.append(turn_record)

    # ── Update coverage from evaluation ──────────────────────────────
    coverage = update_coverage_from_evaluation(coverage, evaluation)
    topic_tag = question_pack.get("topic_tag") or (question_pack.get("topic_tags") or [""])[0] if question_pack.get("topic_tags") else ""
    if topic_tag:
        asked = list(coverage.get("already_asked_topics", []))
        if topic_tag not in asked:
            asked.append(topic_tag)
        coverage["already_asked_topics"] = asked

    # ── HARD GUARDRAIL: max turns reached → end ──────────────────────
    if tc >= max_turns:
        closing = llm_generate_text(
            f"You are a warm interviewer ending a mock interview at {config.get('company', '')} "
            f"for {config.get('role', '')}. The interview has reached the maximum number of questions. "
            f"Write a brief, warm closing message (2-3 sentences) thanking the candidate and "
            f"mentioning you'll share feedback shortly. Do NOT use 'I appreciate'.",
            temperature=0.7,
        ) or "That wraps up our session. You'll receive detailed feedback shortly."

        decision = {
            "action": "end_interview",
            "next_agent": current_agent,
            "thought": f"Turn {tc} reached max_turns {max_turns}. Must end.",
            "acknowledgement": "",
            "transition": "",
            "closing_message": closing,
            "reason": "Hard cap: maximum turns reached.",
            "signal_confidence": 1.0,
        }
        scratchpad.append(f"[Turn {tc}] HARD CAP: max_turns reached → ending interview.")

        return {
            "supervisor_decision": decision,
            "is_interview_over": True,
            "turns": turns,
            "coverage_context": coverage,
            "supervisor_scratchpad": scratchpad,
            "signal_confidence": 1.0,
            "turn_counter": tc,
        }

    # ── LLM REASONING — the core agentic decision ───────────────────
    prev_scratchpad = "\n".join(scratchpad[-5:]) if scratchpad else "No previous reasoning yet."

    prompt = SUPERVISOR_REASONING_PROMPT.format(
        company=config.get("company", ""),
        role=config.get("role", ""),
        experience=config.get("experience", 0),
        current_difficulty=current_difficulty,
        turn_counter=tc,
        max_turns=max_turns,
        allowed_agents=", ".join(allowed),
        selected_types=", ".join(config.get("selected_types", [])),
        candidate_summary=_candidate_summary(state),
        asked_topics=", ".join(coverage.get("already_asked_topics", [])) or "none yet",
        avoid_topics=", ".join(coverage.get("avoid_topics", [])) or "none",
        weakness_tags=", ".join(coverage.get("weakness_tags", [])[:10]) or "none yet",
        strength_tags=", ".join(coverage.get("strength_tags", [])[:10]) or "none yet",
        agent_usage_summary=_agent_usage_summary(turns, allowed),
        turn_history=_build_turn_history(turns[:-1]),  # exclude current (already in "Current Turn")
        current_agent=current_agent,
        question_text=question_pack.get("question_text", "")[:400],
        answer_text=answer_text[:600],
        evaluation_summary=_format_evaluation(evaluation),
        previous_scratchpad=prev_scratchpad,
    )

    llm = build_llm(temperature=0.3)
    decision = None

    if llm:
        try:
            resp = llm.invoke([SystemMessage(content=prompt + INTERVIEWER_STYLE_RULE)])
            decision = safe_json_parse(resp.content)
        except Exception:
            decision = None

    # ── Fallback if LLM fails (minimal, not deterministic routing) ──
    if not decision or not isinstance(decision, dict) or "action" not in decision:
        # Simple heuristic ONLY as emergency fallback
        pct = int(evaluation.get("percentage", 50))
        is_clar = evaluation.get("is_clarification_request", False)

        if is_clar:
            action = "clarify"
        elif pct < 30 and len(answer_text.split()) < 10:
            action = "ask_question"
        else:
            action = "ask_question"

        decision = {
            "thought": f"LLM failed. Emergency fallback: {action}. Score was {pct}%.",
            "signal_confidence": 0.3,
            "action": action,
            "next_agent": allowed[(tc + 1) % len(allowed)] if action != "clarify" else current_agent,
            "next_difficulty": current_difficulty,
            "focus_topic": None,
            "acknowledgement": "Let's continue.",
            "transition": "",
            "reason": "LLM reasoning failed — using minimal fallback.",
        }

    # ── Consistency check 1: same agent too many turns in a row ──────
    # Count consecutive turns with the same agent at the tail of history
    consecutive_same = 0
    for t in reversed(turns):
        if t.get("agent_type") == current_agent:
            consecutive_same += 1
        else:
            break
    if consecutive_same >= 3 and decision.get("action") in ("follow_up", "ask_question") and decision.get("next_agent") == current_agent:
        other_agents = [a for a in allowed if a != current_agent]
        if other_agents:
            decision["action"] = "ask_question"
            decision["next_agent"] = other_agents[0]
            decision["prefix"] = ""
            decision["thought"] += f" [Consistency: {consecutive_same} consecutive turns on {current_agent}, forcing switch.]"

    # ── Consistency check 2: low-effort answer but follow_up chosen ──
    pct = int(evaluation.get("percentage", 50))
    word_count = len(answer_text.split())
    is_clarification = evaluation.get("is_clarification_request", False)

    if (not is_clarification
        and pct < 30
        and word_count < 15
        and decision.get("action") in ("follow_up", "clarify")):
        other_agents = [a for a in allowed if a != current_agent]
        decision["action"] = "ask_question"
        decision["next_agent"] = other_agents[0] if other_agents else allowed[(tc + 1) % len(allowed)]
        decision["prefix"] = "No problem."
        decision["thought"] += " [Consistency fix: low score + short answer but follow_up chosen → ask_question instead.]"

    # ── Validate and normalize the decision ──────────────────────────
    decision["next_agent"] = _normalize_agent(decision.get("next_agent"))
    if decision["next_agent"] not in allowed:
        decision["next_agent"] = allowed[0]

    new_difficulty = decision.get("next_difficulty", current_difficulty)
    if new_difficulty not in ("easy", "medium", "hard"):
        new_difficulty = current_difficulty

    # Sanitize text
    if decision.get("prefix"):
        decision["prefix"] = _sanitize_text(decision["prefix"])
    # Back-compat: also sanitize old fields if LLM still outputs them
    if decision.get("acknowledgement"):
        decision["acknowledgement"] = _sanitize_text(decision["acknowledgement"])
    if decision.get("transition"):
        decision["transition"] = _sanitize_text(decision["transition"])

    # Record reasoning in scratchpad
    thought = decision.get("thought", "No reasoning provided.")
    scratchpad.append(f"[Turn {tc}] {thought}")

    confidence = float(decision.get("signal_confidence", 0.5))
    is_over = decision.get("action") == "end_interview"

    # ── Handle clarification ─────────────────────────────────────────
    if decision.get("action") == "clarify" and not decision.get("clarification_response"):
        core_q = question_pack.get("core_question_text", question_pack.get("question_text", ""))
        clar_resp = llm_generate_text(
            f"The candidate asked a clarifying question about the problem instead of answering.\n\n"
            f"Original problem:\n{core_q[:500]}\n\n"
            f"Candidate's question:\n{answer_text[:400]}\n\n"
            f"Answer their question helpfully, then re-present the problem so they can attempt it.",
            temperature=0.5,
        )
        decision["clarification_response"] = clar_resp or f"Good question! Here's the problem again: {core_q}"

    # If clarification, DON'T increment turn counter (don't penalize for asking)
    if decision.get("action") == "clarify":
        # Remove the turn we just appended — clarifications don't count
        turns.pop()
        return {
            "supervisor_decision": decision,
            "is_interview_over": False,
            "turns": turns,
            "coverage_context": coverage,
            "supervisor_scratchpad": scratchpad,
            "signal_confidence": confidence,
            "turn_counter": tc,  # don't increment
            "current_agent": current_agent,
            "current_difficulty": current_difficulty,
        }

    return {
        "supervisor_decision": decision,
        "is_interview_over": is_over,
        "turns": turns,
        "coverage_context": coverage,
        "supervisor_scratchpad": scratchpad,
        "signal_confidence": confidence,
        "turn_counter": tc + 1,  # increment for real answers
        "current_agent": decision["next_agent"],
        "current_difficulty": new_difficulty,
    }


# ── FOLLOW-UP NODE ──────────────────────────────────────────────────────

def followup_node(state: InterviewState) -> dict:
    """LangGraph node — generates a contextual follow-up question via LLM.

    Uses evaluation context + candidate's answer to generate a targeted
    follow-up. No hardcoded templates.
    """
    qp = state.get("current_question_pack") or {}
    answer = state.get("answer_text", "")
    evaluation = state.get("evaluation") or {}
    config = state.get("interview_config") or {}
    core = qp.get("core_question_text", qp.get("question_text", ""))
    weak_tags = evaluation.get("topics_demonstrated_weak", [])
    pct = int(evaluation.get("percentage", 0))
    verdict = (evaluation.get("verdict") or "").lower()
    hints = qp.get("hints", qp.get("expected_solution_outline", []))
    decision = state.get("supervisor_decision") or {}

    prompt = FOLLOWUP_GENERATION_PROMPT.format(
        company=config.get("company", "a tech company"),
        role=config.get("role", "Software Engineer"),
        original_question=core[:400],
        word_count=len(answer.split()),
        score_pct=pct,
        verdict=verdict,
        answer_text=answer[:500],
        weak_tags=", ".join(weak_tags) if weak_tags else "none identified",
        hints=str(hints[:3]) if hints else "none",
    )

    text = llm_generate_text(prompt, temperature=0.5)
    if not text:
        text = f"Could you elaborate on your approach to {core[:100]}?"

    # Build the follow-up question pack
    # NOTE: Do NOT prepend ack/transition here — decorate_question_node
    # handles that downstream. Adding it here causes double-prepend.

    pack = dict(qp)
    pack["question_id"] = f"Q_FUP_{uuid.uuid4().hex[:6]}"
    pack["core_question_text"] = text
    pack["question_text"] = text
    pack["is_followup"] = True
    pack["followup_depth"] = int(qp.get("followup_depth", 0)) + 1
    pack["parent_question_id"] = qp.get("question_id")

    return {"next_question_pack": pack}


# ── OPENING NODE ────────────────────────────────────────────────────────

def opening_node(state: InterviewState) -> dict:
    """LangGraph node — generates the opening greeting before the first question.

    Called once at the start. Decorates the first question_pack with a
    warm, personalized greeting.
    """
    config = state.get("interview_config") or {}
    candidate = state.get("candidate") or {}
    qp = state.get("next_question_pack") or {}
    agent_type = qp.get("agent_type", "code")
    round_type = qp.get("round_type", "tech-dsa")

    name = (candidate.get("name") or "there").split()[0]

    greeting = llm_generate_text(
        OPENING_GREETING_PROMPT.format(
            candidate_name=name,
            company=config.get("company", ""),
            role=config.get("role", ""),
        ),
        temperature=0.5,
    )

    if not greeting:
        greeting = f"Hi {name}, welcome to your mock interview!"

    # Strip any questions the LLM snuck into the greeting
    greeting = greeting.split("?")[0].rstrip() + "." if "?" in greeting else greeting.rstrip()

    # Prepend greeting to the question
    core_q = qp.get("core_question_text", qp.get("question_text", ""))
    decorated = dict(qp)
    decorated["question_text"] = f"{greeting} {core_q}".strip()

    return {"current_question_pack": decorated, "next_question_pack": decorated}
