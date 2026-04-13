import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage


load_dotenv()

# ── Style rule injected into every interviewer-facing LLM call ────────
INTERVIEWER_STYLE_RULE = (
    "\n\nSTYLE RULES (mandatory):\n"
    "- NEVER start with or use: \"I appreciate\", \"I'd appreciate\", "
    "\"That's a great\", \"Great question\", \"That's great\", "
    "\"Thank you for sharing\", or \"Thanks for sharing\".\n"
    "- NEVER be condescending, surprised, or judgmental. BANNED phrases: "
    "\"I'm surprised\", \"I'm disappointed\", \"it seems we need to start "
    "with the basics\", \"I expected more\", \"that's unfortunate\", "
    "\"you should know this\", \"this is basic\", \"let me simplify\", "
    "\"I'm shocked\", \"disappointing\", \"surprisingly\".\n"
    "- ALWAYS be warm, supportive, and professional. If the candidate "
    "doesn't know something, be ENCOURAGING, not critical.\n"
    "- Use DIRECT, VARIED openers: reference what the candidate "
    "actually said, use the topic name, start with an action verb, "
    "or state a fact.\n"
    "- Good examples: \"Your point about X is solid.\", "
    "\"Interesting approach to the sliding window.\", "
    "\"No problem — let's try a different area.\", "
    "\"Totally fine, let's move on to something else.\"\n"
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
