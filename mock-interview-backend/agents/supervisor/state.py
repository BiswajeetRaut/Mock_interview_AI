"""Interview State Definition — shared schema for the LangGraph interview workflow.

Each graph invocation processes ONE answer submission:
    EVALUATE → SUPERVISOR → { FOLLOWUP | TECHNICAL | RESUME | HR | END }

Fields are split into:
  • session context  — populated by session_engine before graph invocation
  • per-turn inputs  — the answer + question being processed
  • per-turn outputs — written by graph nodes, read by session_engine after
"""

from typing import TypedDict, Dict, List, Optional, Any


class InterviewState(TypedDict, total=False):
    """Complete state that flows through the interview graph."""

    # ── session context (read-only during graph execution) ────────────
    session_id: str
    interview_config: Dict[str, Any]   # company, role, experience, difficulty, jd, topics, …
    candidate: Dict[str, Any]          # name, resume_parsed, …
    turn_counter: int
    turn_plan: List[Dict[str, Any]]
    current_agent: str
    current_turn_spec: Dict[str, Any]
    coverage_context: Dict[str, Any]
    turns: List[Dict[str, Any]]        # history of completed turns

    # ── per-turn inputs (set before graph invocation) ─────────────────
    answer_text: str
    current_question_pack: Dict[str, Any]

    # ── per-turn outputs (written by graph nodes) ─────────────────────
    evaluation: Dict[str, Any]              # ← EVALUATE node
    supervisor_decision: Dict[str, Any]     # ← SUPERVISOR node
    next_turn_spec: Dict[str, Any]          # ← SUPERVISOR node
    next_question_pack: Dict[str, Any]      # ← agent / FOLLOWUP node
    is_interview_over: bool                 # ← SUPERVISOR node

    # ── legacy fields (backward compat with old graph / cli) ─────────
    current_round: str
    difficulty: str
    target_signal: str
    company_style: str
    weakness_map: Dict[str, List[str]]
    strength_map: Dict[str, List[str]]
    time_remaining: int
    latest_agent_report: Optional[dict]
    final_scores: Optional[dict]
    latest_turn: Optional[Dict[str, Any]]
    latest_evaluation: Optional[Dict[str, Any]]
