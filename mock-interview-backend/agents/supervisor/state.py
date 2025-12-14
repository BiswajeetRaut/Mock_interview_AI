"""Interview State Definition - Shared state schema for the entire interview workflow.

This module defines the InterviewState TypedDict that represents the complete
state of an interview as it flows through different agents.
"""

from typing import TypedDict, Dict, List, Optional


class InterviewState(TypedDict):
    """Complete state schema for interview workflow.

    Tracks interview context, rounds, candidate strengths/weaknesses,
    agent reports, and supervisor decisions throughout the interview.
    """
    session_id: str

    current_round: str          # technical | resume | hr
    difficulty: str
    target_signal: str
    company_style: str

    weakness_map: Dict[str, List[str]]
    strength_map: Dict[str, List[str]]

    time_remaining: int

    latest_agent_report: Optional[dict]
    supervisor_decision: Optional[dict]

    final_scores: Optional[dict]
