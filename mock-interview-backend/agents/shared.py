import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()


def build_llm(model: str = "llama-3.1-8b-instant", temperature: float = 0.2):
    if not os.getenv("GROQ_API_KEY"):
        return None
    return ChatGroq(model=model, temperature=temperature, max_retries=0, timeout=8)


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
