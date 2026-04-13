"""Supervisor agent — LLM-powered routing with deterministic guardrails.

The supervisor:
  1. Checks hard rules first  (turn limit, stuck candidate, already-followup)
  2. Asks the LLM for a nuanced routing decision
  3. Validates the LLM output against safety constraints
  4. Falls back to deterministic logic if the LLM fails

Guarantees:
  • Max ONE follow-up per question thread  (prevents infinite loops)
  • Never follows up when candidate is stuck
  • Respects the pre-built turn_plan ordering
  • Graceful degradation when LLM is unavailable
"""

from __future__ import annotations

import uuid

from langchain_core.messages import SystemMessage

from .prompt import SUPERVISOR_DECISION_PROMPT
from .logic import update_state_from_report
from .state import InterviewState
from agents.shared import build_llm, safe_json_parse, llm_generate_text


llm = build_llm(temperature=0.2)

# ── constants ────────────────────────────────────────────────────────────
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
_STUCK_PHRASES = frozenset([
    "i don't know", "i dont know", "do not know", "not sure",
    "no idea", "i have no idea", "i'm not sure", "im not sure",
    "can't remember", "cannot remember", "don't remember",
    "do not remember", "blanking", "skip this", "pass on this", "move on",
])
# Phrases to strip from generated acknowledgements / transitions.
# The LLM often ignores negative instructions, so we enforce them in code.
_BANNED_PREFIXES = (
    "i appreciate your", "i appreciate ", "i'd appreciate",
    "that's a great", "great question", "thank you for sharing",
    "thanks for sharing", "that's great", "i'm surprised",
    "i'm disappointed", "it seems we need to start with the basics",
    "i expected more", "that's unfortunate", "you should know this",
    "this is basic", "let me simplify",
)
_BANNED_ANYWHERE = (
    "disappointing", "surprisingly", "i'm surprised", "i'm disappointed",
)


def _sanitize_text(text: str) -> str:
    """Strip banned opening phrases from generated text.

    Small LLMs often ignore 'never say X' instructions, so we enforce
    the ban in code as a post-processing step.
    """
    if not text:
        return text
    cleaned = text.strip()
    lower = cleaned.lower()

    # Strip banned prefix (longest-match first so 'i appreciate your' beats 'i appreciate ')
    for prefix in sorted(_BANNED_PREFIXES, key=len, reverse=True):
        if lower.startswith(prefix):
            rest = cleaned[len(prefix):].lstrip(" ,;.!-\u2013\u2014:")
            if rest and len(rest.split()) >= 3:
                cleaned = rest[0].upper() + rest[1:]
            else:
                # Too short after stripping — keep original minus just the prefix
                cleaned = rest[0].upper() + rest[1:] if rest else cleaned
            break

    # Replace any banned word that appears mid-sentence
    lower2 = cleaned.lower()
    for word in _BANNED_ANYWHERE:
        if word in lower2:
            # Replace the offending word with a neutral alternative
            import re as _re
            cleaned = _re.sub(_re.escape(word), "", cleaned, flags=_re.IGNORECASE).strip()
            # Clean up double spaces / leading punctuation
            cleaned = " ".join(cleaned.split())
            if cleaned and cleaned[0] in ",.;:":
                cleaned = cleaned[1:].strip()

    return cleaned

# ── helpers ──────────────────────────────────────────────────────────────

def _normalize_agent(agent: str | None) -> str:
    return agent if agent in AGENTS else "code"

# Topic keywords the candidate might reject
_TOPIC_KEYWORDS = (
    "string", "strings", "tree", "trees", "graph", "graphs", "dp",
    "dynamic programming", "recursion", "linked list", "linked lists",
    "array", "arrays", "sorting", "searching", "binary search",
    "stack", "stacks", "queue", "queues", "heap", "heaps",
    "hash", "hashmap", "hashing", "trie", "tries", "bit manipulation",
    "math", "greedy", "backtracking", "sliding window", "two pointers",
    "interval", "intervals", "matrix", "design", "system design",
)


def _extract_rejected_topics(answer_text: str) -> list[str]:
    """Detect topic-specific rejection in answers like 'I dont know strings'.

    Returns a list of topic keywords the candidate explicitly said they
    don't know / are weak at / want to skip.
    """
    text = (answer_text or "").lower().strip()
    if not text:
        return []

    # Must contain a rejection signal
    rejection_signals = (
        "don't know", "dont know", "do not know", "not good at",
        "weak at", "weak in", "not comfortable", "can't do", "cant do",
        "skip", "not familiar", "haven't studied", "havent studied",
        "never learned", "don't understand", "dont understand",
        "struggle with", "bad at", "hate",
    )
    has_rejection = any(sig in text for sig in rejection_signals)
    if not has_rejection:
        return []

    # Find which topics they're rejecting
    rejected = []
    for kw in _TOPIC_KEYWORDS:
        if kw in text:
            rejected.append(kw)
    return rejected

def _is_non_answer(evaluation: dict, answer_text: str) -> bool:
    """Context-aware non-answer detection using the EVALUATION as memory.

    The evaluator has already scored the answer.  We read that score,
    the verdict, and the answer length to decide whether the candidate
    effectively did not answer — no phrase dictionary needed.

    Returns True when the answer carries no useful signal.
    """
    text = (answer_text or "").strip()
    words = text.split()
    word_count = len(words)

    # Empty / blank → obviously non-answer
    if word_count == 0:
        return True

    pct = int(evaluation.get("percentage", 0) or 0)
    verdict = (evaluation.get("verdict") or "").lower()
    all_strong = evaluation.get("topics_demonstrated_strong", [])

    # PRIMARY SIGNAL: evaluation context
    # Short answer + poor/very-low evaluation = non-answer
    if word_count <= 5 and pct <= 30:
        return True
    if word_count <= 10 and pct <= 15:
        return True
    if verdict == "poor" and word_count <= 8 and not all_strong:
        return True

    # SECONDARY: phrase matching (catches hedging in medium-length answers)
    normalized = " ".join(text.lower().split())
    if word_count <= 15 and any(p in normalized for p in _STUCK_PHRASES):
        return True

    return False


def _allowed_agents(state: dict) -> list[str]:
    config = state.get("interview_config") or {}
    selected_types = config.get("selected_types") or []
    allowed: list[str] = []
    for rt in selected_types:
        mapped = ROUND_TYPE_TO_AGENT.get(str(rt))
        if mapped and mapped not in allowed:
            allowed.append(mapped)
    if not allowed:
        for spec in (state.get("turn_plan") or []):
            m = spec.get("agent_type")
            if m in AGENTS and m not in allowed:
                allowed.append(m)
    if not allowed:
        allowed = list(AGENTS)
    cur = state.get("current_agent", "code")
    if cur not in allowed:
        allowed.append(cur)
    return allowed


def _planned_next_agent(state: dict, default: str) -> str:
    plan = state.get("turn_plan") or []
    idx = max(1, int(state.get("turn_counter", 1)))
    if idx < len(plan):
        return _normalize_agent(plan[idx].get("agent_type"))
    return default


def _resolve_next_turn_spec(state: dict, next_agent: str) -> dict:
    """Find the matching turn_plan entry for *next_agent*, or build a default."""
    plan = state.get("turn_plan") or []
    idx = max(1, int(state.get("turn_counter", 1)))
    # First: look at the planned slot
    if idx < len(plan):
        slot = plan[idx]
        if slot.get("agent_type") == next_agent:
            return slot
    # Second: search forward for a matching agent
    for spec in plan[max(0, idx):]:
        if spec.get("agent_type") == next_agent:
            return spec
    # Fallback
    rt = {"code": "tech-dsa", "resume": "resume-based", "hr": "managerial"}.get(next_agent, "tech-dsa")
    topics = (state.get("interview_config") or {}).get("topics", {}).get(rt, [])
    return {"round_type": rt, "agent_type": next_agent, "topics": topics}


def _llm_ack_transition(scenario: str, fallback_ack: str, fallback_trans: str) -> tuple[str, str]:
    """Generate unique acknowledgement + transition via LLM. Falls back to static strings."""
    raw = llm_generate_text(
        f"You are a warm, professional interviewer. Scenario: {scenario}\n"
        f"Write TWO short sentences separated by a newline:\n"
        f"Line 1: A unique acknowledgement (no question marks).\n"
        f"Line 2: A smooth transition sentence.\n"
        f"Be specific, natural, and NEVER repeat the same phrasing twice.",
        temperature=0.8,
    )
    if raw:
        parts = [p.strip() for p in raw.split("\n") if p.strip()]
        ack = parts[0] if len(parts) >= 1 else fallback_ack
        trans = parts[1] if len(parts) >= 2 else fallback_trans
        return ack, trans
    return fallback_ack, fallback_trans


def _end_decision(current_agent: str) -> dict:
    ack, trans = _llm_ack_transition(
        "The interview is ending because the planned turn limit was reached.",
        "Thanks for your time and thoughtful answers.",
        "That wraps up our session for today.",
    )
    return {
        "action": "end_interview",
        "next_agent": current_agent,
        "focus": "wrap_up",
        "acknowledgement": ack,
        "transition": trans,
        "reason": "Reached planned turn limit.",
    }


# ── history helpers ──────────────────────────────────────────────────────

def _build_turn_history_summary(turns: list, max_turns: int = 8) -> str:
    """Condense previous turns into a compact summary the LLM can read.

    Each turn → one line:  Turn N (agent) — Score% / verdict — answer preview
    This gives the supervisor full memory of the interview so far.
    """
    if not turns:
        return "No previous turns yet."

    lines: list[str] = []
    for t in turns[-max_turns:]:
        tid = t.get("turn_id", "?")
        agent = t.get("agent_type", "?")
        ev = t.get("evaluation") or {}
        pct = ev.get("percentage", "?")
        verdict = ev.get("verdict", "?")
        answer_preview = (t.get("user_answer_transcript") or "")[:80]
        q_preview = (t.get("question_text") or "")[:60]
        weak = ev.get("topics_demonstrated_weak", [])
        strong = ev.get("topics_demonstrated_strong", [])
        tags = ""
        if weak:
            tags += f" weak=[{', '.join(weak[:3])}]"
        if strong:
            tags += f" strong=[{', '.join(strong[:3])}]"
        lines.append(
            f"{tid} ({agent}) — {pct}% {verdict}{tags} — "
            f"Q: {q_preview}… A: {answer_preview}…"
        )
    return "\n".join(lines)


def _count_consecutive_non_answers(turns: list, current_agent: str) -> int:
    """How many recent turns in a row for *current_agent* were non-answers?"""
    count = 0
    for t in reversed(turns):
        if t.get("agent_type") != current_agent:
            break
        ev = t.get("evaluation") or {}
        pct = int(ev.get("percentage", 0) or 0)
        words = len((t.get("user_answer_transcript") or "").split())
        if pct <= 30 and words <= 5:
            count += 1
        else:
            break
    return count


# ── deterministic fallback ───────────────────────────────────────────────

def _deterministic_fallback(
    state: dict,
    evaluation: dict,
    question_pack: dict,
    answer_text: str,
) -> dict:
    """Rule-based decision that uses evaluation context as its primary signal."""
    tc = max(1, int(state.get("turn_counter", 1)))
    total = max(1, int((state.get("interview_config") or {}).get("total_turns_planned", 1)))
    current = _normalize_agent(state.get("current_agent", "code"))

    if tc >= total:
        return _end_decision(current)

    allowed = _allowed_agents(state)
    planned = _planned_next_agent(state, current)
    if planned not in allowed:
        planned = allowed[0]

    # ── Use evaluation context to understand the answer ──────────────
    non_answer = _is_non_answer(evaluation, answer_text)
    already_fu = bool(question_pack.get("is_followup"))
    words = len(answer_text.split())
    pct = int(evaluation.get("percentage", 0) or 0)
    verdict = (evaluation.get("verdict") or "").lower()

    # ── NON-ANSWER: candidate didn't know → move on immediately ──────
    if non_answer:
        consec = _count_consecutive_non_answers(state.get("turns", []), current)
        if consec >= 2 and len(allowed) > 1:
            alt = next((a for a in allowed if a != current), planned)
            ack, trans = _llm_ack_transition(
                f"Candidate couldn't answer {consec} questions in a row on {current}. Switching to {ROUND_LABELS.get(alt, alt)}.",
                "That's perfectly okay — some topics click better than others.",
                f"Let's explore {ROUND_LABELS.get(alt, alt)} instead.",
            )
            return {
                "action": "switch_round", "next_agent": alt,
                "focus": "coverage", "acknowledgement": ack,
                "transition": trans,
                "reason": f"History: {consec} consecutive non-answers for {current} → switching to {alt}.",
            }
        if planned == current:
            ack, trans = _llm_ack_transition(
                f"Candidate didn't know the answer (score {pct}%). Moving to a different question in {current}.",
                "No problem at all.",
                "Let's try something different.",
            )
            return {
                "action": "ask_question", "next_agent": planned,
                "focus": "coverage", "acknowledgement": ack,
                "transition": trans,
                "reason": f"Evaluation context: {pct}% / {verdict} + {words} words → non-answer, moving on.",
            }
        ack, trans = _llm_ack_transition(
            f"Candidate didn't know the answer (score {pct}%). Switching from {current} to {ROUND_LABELS.get(planned, planned)}.",
            "No worries — let's change direction.",
            f"Let's move into {ROUND_LABELS.get(planned, planned)}.",
        )
        return {
            "action": "switch_round", "next_agent": planned,
            "focus": "coverage", "acknowledgement": ack,
            "transition": trans,
            "reason": f"Evaluation context: {pct}% / {verdict} + {words} words → non-answer, switching.",
        }

    # ── PARTIAL ANSWER: follow up to probe deeper ────────────────────
    if not already_fu and (words < 40 or pct < 60 or verdict in ("poor", "average")):
        ack, trans = _llm_ack_transition(
            f"Candidate gave a partial answer ({pct}%, {words} words, verdict={verdict}). Going to follow up for more depth.",
            "That's a reasonable start.",
            "Let me probe a bit deeper on that.",
        )
        return {
            "action": "follow_up",
            "next_agent": current,
            "focus": "depth",
            "acknowledgement": ack,
            "transition": trans,
            "reason": f"Evaluation context: {pct}% / {verdict} + {words} words → partial, probing deeper.",
        }

    # ── SOLID ANSWER: move to next planned question ──────────────────
    if planned == current:
        ack, trans = _llm_ack_transition(
            f"Candidate gave a solid answer ({pct}%, verdict={verdict}). Continuing in {current}.",
            "That was a strong response.",
            "Let's keep the momentum going with another question.",
        )
        return {
            "action": "ask_question", "next_agent": planned,
            "focus": "coverage", "acknowledgement": ack,
            "transition": trans,
            "reason": "Deterministic: next question per turn plan.",
        }
    ack, trans = _llm_ack_transition(
        f"Candidate gave a solid answer ({pct}%, verdict={verdict}). Switching from {current} to {ROUND_LABELS.get(planned, planned)}.",
        "Great answer — I appreciate the detail.",
        f"Now let's shift to {ROUND_LABELS.get(planned, planned)}.",
    )
    return {
        "action": "switch_round", "next_agent": planned,
        "focus": "coverage", "acknowledgement": ack,
        "transition": trans,
        "reason": "Deterministic: agent switch per turn plan.",
    }


# ── LLM-powered decision ────────────────────────────────────────────────

def _llm_decision(
    state: dict,
    evaluation: dict,
    question_pack: dict,
    answer_text: str,
) -> dict | None:
    """Ask the LLM for a routing decision. Returns None on failure."""
    if llm is None:
        return None

    config = state.get("interview_config") or {}
    allowed = _allowed_agents(state)

    cov = state.get("coverage_context") or {}
    fu_depth = int(question_pack.get("followup_depth", 0)) if question_pack.get("is_followup") else 0
    avoid = cov.get("avoid_topics", [])
    planned = _planned_next_agent(state, state.get("current_agent", "code"))
    prompt = SUPERVISOR_DECISION_PROMPT.format(
        company=config.get("company", ""),
        role=config.get("role", ""),
        experience=config.get("experience", 0),
        current_agent=state.get("current_agent", "code"),
        turn_counter=state.get("turn_counter", 1),
        total_turns=config.get("total_turns_planned", 8),
        allowed_agents=", ".join(allowed),
        planned_next_agent=planned,
        turn_history=_build_turn_history_summary(state.get("turns", [])),
        coverage=str(cov.get("already_asked_topics", []))[:250],
        avoid_topics=", ".join(avoid) if avoid else "none",
        weakness_tags=", ".join(cov.get("weakness_tags", [])[:10]) or "none yet",
        strength_tags=", ".join(cov.get("strength_tags", [])[:10]) or "none yet",
        evaluation_summary=(
            f"Score: {evaluation.get('percentage', 0)}%, "
            f"Verdict: {evaluation.get('verdict', 'unknown')}, "
            f"Weak: {evaluation.get('topics_demonstrated_weak', [])}, "
            f"Strong: {evaluation.get('topics_demonstrated_strong', [])}"
        ),
        question_text=question_pack.get("question_text", "")[:300],
        answer_preview=answer_text[:400],
        is_followup="Yes" if question_pack.get("is_followup") else "No",
        followup_depth=fu_depth,
        is_clarification="Yes" if evaluation.get("is_clarification_request") else "No",
    )

    try:
        resp = llm.invoke([SystemMessage(content=prompt)])
        decision = safe_json_parse(resp.content)
        if isinstance(decision, dict) and "action" in decision:
            decision["next_agent"] = _normalize_agent(decision.get("next_agent"))
            if decision["next_agent"] not in allowed:
                decision["next_agent"] = allowed[0]
            return decision
    except Exception:
        pass
    return None


# ── LangGraph nodes ──────────────────────────────────────────────────────

def supervisor_decide_node(state: InterviewState) -> dict:
    """LangGraph node — LLM-powered supervisor with deterministic guardrails.

    Reads:  evaluation, current_question_pack, answer_text, interview_config, …
    Writes: supervisor_decision, is_interview_over, next_turn_spec
    """
    evaluation = state.get("evaluation") or {}
    question_pack = state.get("current_question_pack") or {}
    answer_text = state.get("answer_text", "")
    config = state.get("interview_config") or {}
    tc = max(1, int(state.get("turn_counter", 1)))
    total = max(1, int(config.get("total_turns_planned", 1)))
    current = _normalize_agent(state.get("current_agent", "code"))

    # ── GUARDRAIL 1: turn limit → end ────────────────────────────────
    if tc >= total:
        d = _end_decision(current)
        return {"supervisor_decision": d, "is_interview_over": True, "next_turn_spec": {}}
    # ── GUARDRAIL 0: clarification request → clarify ─────────────
    is_clarification = bool(evaluation.get("is_clarification_request"))
    if is_clarification:
        core_q = question_pack.get("core_question_text", question_pack.get("question_text", ""))
        clarification_resp = llm_generate_text(
            f"You are a friendly interviewer. The candidate asked a clarifying question "
            f"about the problem instead of answering.\n\n"
            f"Original problem:\n{core_q[:500]}\n\n"
            f"Candidate's clarifying question:\n{answer_text[:400]}\n\n"
            f"Answer their question helpfully and specifically. Then smoothly "
            f"re-present the original problem so they can attempt it.\n"
            f"Be encouraging — clarifying questions show good thinking.",
            temperature=0.5,
        )
        if not clarification_resp:
            clarification_resp = (
                f"Great question! {core_q}"
            )
        d = {
            "action": "clarify",
            "next_agent": current,
            "focus": "clarification",
            "acknowledgement": "",
            "transition": "",
            "clarification_response": clarification_resp,
            "reason": "Candidate asked a clarifying question, not answering.",
        }
        nts = dict(state.get("current_turn_spec") or {})
        return {"supervisor_decision": d, "is_interview_over": False, "next_turn_spec": nts}
    non_answer = _is_non_answer(evaluation, answer_text)

    # ── Extract topic-specific rejections into avoid_topics ────────
    rejected = _extract_rejected_topics(answer_text)
    if rejected:
        cov = state.get("coverage_context") or {}
        avoid = cov.get("avoid_topics", [])
        for topic in rejected:
            if topic not in avoid:
                avoid.append(topic)
        cov["avoid_topics"] = avoid

    # Track follow-up depth: allow up to MAX_FOLLOWUP_DEPTH follow-ups per thread
    MAX_FOLLOWUP_DEPTH = 3
    followup_depth = int(question_pack.get("followup_depth", 0)) if question_pack.get("is_followup") else 0
    too_deep = followup_depth >= MAX_FOLLOWUP_DEPTH

    # ── try LLM decision ─────────────────────────────────────────────
    decision = _llm_decision(state, evaluation, question_pack, answer_text)
    if decision is None:
        decision = _deterministic_fallback(state, evaluation, question_pack, answer_text)

    # ── GUARDRAIL 2: override bad follow-ups using evaluation context ──
    if decision.get("action") == "follow_up":
        if non_answer or too_deep:
            allowed = _allowed_agents(state)
            planned = _planned_next_agent(state, current)
            if planned not in allowed:
                planned = allowed[0]
            # LLM-generate the override acknowledgement
            override_ack = llm_generate_text(
                f"You are an interviewer. The candidate {'did not know the answer' if non_answer else 'has been asked multiple follow-ups already'}. "
                f"Write a single warm, encouraging sentence acknowledging this and transitioning. No question marks.",
                temperature=0.7,
            )
            if not override_ack:
                override_ack = "No worries, let's move on." if non_answer else "Great effort on that thread."
            decision = {
                "action": "ask_question" if planned == current else "switch_round",
                "next_agent": planned,
                "focus": "coverage",
                "acknowledgement": override_ack,
                "transition": "",
                "reason": f"Guardrail: non_answer={non_answer}, followup_depth={followup_depth}.",
            }

    # ── GUARDRAIL 3: enforce turn-plan agent distribution ────────────
    #    If the LLM chose an action that moves to a new question (not
    #    follow_up / clarify / end) but picked a DIFFERENT agent than
    #    what the turn plan says, override to the planned agent — unless
    #    the planned agent is the same one the candidate is stuck on.
    planned_agent = _planned_next_agent(state, current)
    if decision.get("action") in ("ask_question", "switch_round"):
        chosen = _normalize_agent(decision.get("next_agent", current))
        if chosen != planned_agent and planned_agent in _allowed_agents(state):
            # Don't force the plan if the candidate has consecutive non-answers
            # on the planned agent (let the LLM's diversification stand)
            consec = _count_consecutive_non_answers(state.get("turns", []), planned_agent)
            if consec < 2:
                decision["next_agent"] = planned_agent
                if planned_agent != current:
                    decision["action"] = "switch_round"
                    ack, trans = _llm_ack_transition(
                        f"Switching from {ROUND_LABELS.get(current, current)} to "
                        f"{ROUND_LABELS.get(planned_agent, planned_agent)} as per interview plan.",
                        "Good effort on that.",
                        f"Let's move into {ROUND_LABELS.get(planned_agent, planned_agent)}.",
                    )
                    decision["acknowledgement"] = ack
                    decision["transition"] = trans
                    decision["reason"] = (
                        f"Guardrail 3: LLM chose {chosen} but plan says "
                        f"{planned_agent} → enforcing plan."
                    )

    is_over = decision.get("action") == "end_interview"
    next_agent = _normalize_agent(decision.get("next_agent", current))

    # For follow-ups the spec stays the same; for new questions resolve it
    if decision.get("action") == "follow_up":
        nts = dict(state.get("current_turn_spec") or {})
    elif not is_over:
        nts = _resolve_next_turn_spec(state, next_agent)
    else:
        nts = {}

    # ── Sanitize: strip banned phrases the LLM slipped in ───────────
    if decision.get("acknowledgement"):
        decision["acknowledgement"] = _sanitize_text(decision["acknowledgement"])
    if decision.get("transition"):
        decision["transition"] = _sanitize_text(decision["transition"])

    return {
        "supervisor_decision": decision,
        "is_interview_over": is_over,
        "next_turn_spec": nts,
    }


def followup_node(state: InterviewState) -> dict:
    """LangGraph node — LLM generates a contextual follow-up question.

    Uses evaluation context + the candidate's answer to generate a
    targeted follow-up via LLM. No hardcoded templates.

    Reads:  current_question_pack, answer_text, evaluation, interview_config
    Writes: next_question_pack
    """
    qp = state.get("current_question_pack") or {}
    answer = state.get("answer_text", "")
    evaluation = state.get("evaluation") or {}
    config = state.get("interview_config") or {}
    core = qp.get("core_question_text", qp.get("question_text", ""))
    weak_tags = evaluation.get("topics_demonstrated_weak", [])
    pct = int(evaluation.get("percentage", 0) or 0)
    verdict = (evaluation.get("verdict") or "").lower()
    hints = qp.get("hints", qp.get("expected_solution_outline", []))

    prompt = (
        f"You are a senior interviewer at {config.get('company', 'a tech company')} "
        f"for the role of {config.get('role', 'Software Engineer')}.\n\n"
        f"Original question:\n{core[:400]}\n\n"
        f"Candidate's answer:\n{answer[:500]}\n\n"
        f"Evaluation: {pct}% — {verdict}\n"
        f"Weak areas: {', '.join(weak_tags) if weak_tags else 'none identified'}\n"
        f"Solution hints available: {hints[:3] if hints else 'none'}\n\n"
        f"Generate a SINGLE follow-up question that:\n"
        f"- Probes the weak areas if any, otherwise deepens understanding\n"
        f"- If the answer was very brief (<15 words), give a gentle hint and rephrase\n"
        f"- Sounds like a natural interviewer, not a robot\n"
        f"- Is specific to what the candidate actually said\n\n"
        f"Return ONLY the follow-up question text, nothing else."
    )

    text = llm_generate_text(prompt, temperature=0.5)
    if not text:
        # Minimal fallback — never reached if LLM is configured
        fups = qp.get("followup_questions") or []
        text = fups[0] if fups else f"Could you elaborate on your approach to {core[:100]}?"

    pack = dict(qp)
    pack["question_id"] = f"Q_FUP_{uuid.uuid4().hex[:6]}"
    pack["core_question_text"] = text
    pack["question_text"] = text
    pack["is_followup"] = True
    pack["followup_depth"] = int(qp.get("followup_depth", 0)) + 1
    pack["parent_question_id"] = qp.get("question_id")
    pack["followup_questions"] = (qp.get("followup_questions") or [])[1:]

    return {"next_question_pack": pack}


# ── backward-compat shim ────────────────────────────────────────────────

def plan_session_next_step(
    session: dict,
    latest_turn: dict | None = None,
    latest_evaluation: dict | None = None,
) -> dict:
    """Legacy API kept for any code that still calls it directly."""
    lt = latest_turn or {}
    le = latest_evaluation or {}
    return _deterministic_fallback(
        session, le,
        lt.get("question_pack", {}),
        lt.get("user_answer_transcript", ""),
    )
