"""Evaluator agent — LLM-powered answer scoring.

This agent receives the candidate's answer and the question rubric,
then uses an LLM to produce structured evaluation scores.
Falls back to a word-count heuristic when no LLM is available.
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage

from agents.shared import build_llm, safe_json_parse
from agents.evaluator.prompt import EVALUATE_ANSWER_PROMPT


# ---------------------------------------------------------------------------
# Heuristic fallback (used when LLM is unavailable)
# ---------------------------------------------------------------------------

_CLARIFICATION_SIGNALS = (
    "?", "can you clarify", "could you clarify", "what do you mean",
    "should i", "does that mean", "what exactly", "could you explain",
    "just to confirm", "can you explain", "what should i return",
    "what is the expected", "can i assume", "is it", "are we",
    "what if", "do we need", "what's the", "whats the",
)


def _looks_like_clarification(answer_text: str) -> bool:
    """Cheap heuristic: short text with question-like patterns."""
    text = (answer_text or "").strip().lower()
    words = len(text.split())
    if words > 40:
        return False
    if "?" in text and words <= 25:
        return True
    return any(sig in text for sig in _CLARIFICATION_SIGNALS if sig != "?")


def _heuristic_evaluation(answer_text: str, question_pack: dict) -> dict:
    rubric_dims = question_pack.get("rubric", {}).get("dimensions", [])
    scores: dict = {}
    total = 0
    max_total = 0
    words = len(answer_text.split())
    is_clarification = _looks_like_clarification(answer_text)

    for dim in rubric_dims:
        key = dim["key"]
        mx = int(dim.get("max_score", 5))
        if words >= 120:
            s = mx
        elif words >= 80:
            s = max(1, mx - 1)
        elif words >= 40:
            s = max(1, mx - 2)
        elif words >= 20:
            s = max(1, mx - 3)
        else:
            s = 1
        scores[key] = {"score": s, "max": mx, "comment": f"Heuristic for {key}."}
        total += s
        max_total += mx

    pct = round((total / max_total) * 100) if max_total else 0
    weak = [k for k, v in scores.items() if v["score"] <= max(1, v["max"] // 2)]
    strong = [k for k, v in scores.items() if v["score"] >= v["max"] - 1]
    verdict = (
        "excellent" if pct >= 85
        else "good" if pct >= 70
        else "average" if pct >= 50
        else "poor"
    )
    return {
        "is_clarification_request": is_clarification,
        "scores": scores,
        "total_score": total,
        "max_score": max_total,
        "percentage": pct,
        "verdict": verdict,
        "feedback_summary": "Evaluated using heuristic fallback.",
        "suggested_improvements": [f"Improve {t.replace('_', ' ')}." for t in weak[:3]],
        "topics_demonstrated_weak": weak,
        "topics_demonstrated_strong": strong,
    }


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def evaluate_answer_node(state: dict) -> dict:
    """LangGraph node — evaluates the candidate's answer.

    Reads:
        state["current_question_pack"], state["answer_text"],
        state["interview_config"]

    Writes:
        {"evaluation": <structured scores dict>}
    """
    question_pack = state.get("current_question_pack") or {}
    answer_text = state.get("answer_text", "")
    config = state.get("interview_config") or {}
    agent_type = question_pack.get("agent_type", "code")

    llm = build_llm(temperature=0)
    if llm is None:
        return {"evaluation": _heuristic_evaluation(answer_text, question_pack)}

    # ── build prompt inputs ──────────────────────────────────────────
    rubric = question_pack.get("rubric") or {}
    dims = rubric.get("dimensions", [])
    max_dim_score = dims[0].get("max_score", 5) if dims else 5
    dim_lines = "\n".join(
        f"- {d['key']} (max {d.get('max_score', 5)})" for d in dims
    ) or "- overall_quality (max 5)"

    expected_hints = ""
    if question_pack.get("expected_solution_outline"):
        expected_hints = ", ".join(question_pack["expected_solution_outline"])
    elif question_pack.get("expected_framework"):
        expected_hints = f"Expected framework: {question_pack['expected_framework']}"

    prompt_text = EVALUATE_ANSWER_PROMPT.format(
        company=config.get("company", ""),
        role=config.get("role", ""),
        agent_type=agent_type,
        question_text=question_pack.get("question_text", "")[:600],
        expected_hints=expected_hints or "No specific hints.",
        max_dim_score=max_dim_score,
        rubric_dimensions=dim_lines,
        answer_text=answer_text[:2000],
    )

    try:
        resp = llm.invoke([SystemMessage(content=prompt_text)])
        parsed = safe_json_parse(resp.content)
        if isinstance(parsed, dict) and "scores" in parsed:
            # Ensure all required fields exist
            parsed.setdefault("total_score", sum(
                v.get("score", 0) for v in parsed["scores"].values()
            ))
            parsed.setdefault("max_score", sum(
                v.get("max", 5) for v in parsed["scores"].values()
            ))
            mx = parsed["max_score"] or 1
            parsed.setdefault("percentage", round(parsed["total_score"] / mx * 100))
            pct = parsed["percentage"]
            parsed.setdefault("verdict",
                "excellent" if pct >= 85
                else "good" if pct >= 70
                else "average" if pct >= 50
                else "poor"
            )
            parsed.setdefault("feedback_summary", "LLM evaluation completed.")
            parsed.setdefault("suggested_improvements", [])
            parsed.setdefault("topics_demonstrated_weak", [])
            parsed.setdefault("topics_demonstrated_strong", [])
            parsed.setdefault("is_clarification_request", False)

            # Override: the small LLM often misses clarifications.
            # If the heuristic detects one, trust it — it's purpose-built.
            if not parsed["is_clarification_request"] and _looks_like_clarification(answer_text):
                parsed["is_clarification_request"] = True

            return {"evaluation": parsed}
    except Exception:
        pass

    return {"evaluation": _heuristic_evaluation(answer_text, question_pack)}
