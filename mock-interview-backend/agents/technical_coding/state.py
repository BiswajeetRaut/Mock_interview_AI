# agents/technical_coding/state.py
from typing import TypedDict, Dict, Any, List, Optional


class CodeAgentState(TypedDict, total=False):
    # supervisor request
    request_id: str
    session_id: str
    turn_id: str
    task: str  # generate_coding_question

    company: str
    role: str
    difficulty: str
    language_preference: str

    coverage_context: Dict[str, Any]
    constraints: Dict[str, Any]

    # output
    agent_type: str
    question_pack: Dict[str, Any]
    error: str
