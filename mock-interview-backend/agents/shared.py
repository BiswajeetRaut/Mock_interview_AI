import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage


load_dotenv()

# ── Style rule injected into every interviewer-facing LLM call ────────
INTERVIEWER_STYLE_RULE = (
    "\n\nSTYLE RULES (mandatory):\n"
    "- Be CONCISE. Questions should be 1-3 sentences max. No preamble.\n"
    "- NEVER repeat or paraphrase the same idea twice in your response.\n"
    "- NEVER start with or use: \"I appreciate\", \"I'd appreciate\", "
    "\"That's a great\", \"Great question\", \"That's great\", "
    "\"Thank you for sharing\", or \"Thanks for sharing\".\n"
    "- NEVER say \"let's dive deeper\", \"let's explore further\", "
    "\"let's break it down\", \"walk me through\", \"let's revisit\", "
    "\"Solid approach\", \"Good approach\". "
    "These are overused. Just ask the question directly.\n"
    "- NEVER be condescending, surprised, or judgmental.\n"
    "- If the candidate says they don't know, say \"No problem\" and "
    "move on immediately. Do NOT rephrase the same question.\n"
    "- Use DIRECT, VARIED openers. Good examples: "
    "\"Your point about X is solid.\", "
    "\"Interesting approach.\", "
    "\"No problem, let's move on.\"\n"
)


def build_llm(model: str = "llama-3.1-8b-instant", temperature: float = 0.2):
    if not os.getenv("GROQ_API_KEY"):
        return None
    return ChatGroq(model=model, temperature=temperature, max_retries=0, timeout=8)


def llm_generate_text(prompt: str, temperature: float = 0.6) -> str | None:
    """Quick LLM call that returns raw text (not JSON). Returns None on failure."""
    _llm = build_llm(temperature=temperature)
    if _llm is None:
        return None
    try:
        full_prompt = prompt + INTERVIEWER_STYLE_RULE
        resp = _llm.invoke([SystemMessage(content=full_prompt)])
        return (resp.content or "").strip()
    except Exception:
        return None


def safe_json_parse(text: str):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise
