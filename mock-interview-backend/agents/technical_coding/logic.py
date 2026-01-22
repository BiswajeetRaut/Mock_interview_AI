# agents/technical_coding/logic.py
import json


def safe_json_parse(text: str):
    text = text.strip()

    # remove code fences if any
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)
