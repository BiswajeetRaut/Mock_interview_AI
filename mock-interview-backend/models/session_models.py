from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


AgentType = Literal["code", "resume", "hr"]


class ResumeContent(BaseModel):
    format: Literal["text", "pdf_base64", "url"] = "text"
    data: str = ""


class SessionStartRequest(BaseModel):
    user_id: str = "anonymous"
    candidate_name: str = "Candidate"
    company: str
    role: str
    experience: int = 0
    jd: Optional[str] = None
    resume: Any = None
    topics: Dict[str, Any] = Field(default_factory=dict)
    selected_types: List[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    language_preference: str = "python"
    resume_content: ResumeContent = Field(default_factory=ResumeContent)
    total_turns_planned: int = 8
    turn_distribution: Dict[AgentType, int] = Field(
        default_factory=lambda: {"code": 3, "resume": 3, "hr": 2}
    )


class SessionAnswerRequest(BaseModel):
    answer_text: str
    request_id: Optional[str] = None
    code_submitted: Optional[str] = None
    language: Optional[str] = None
    time_taken_seconds: int = 0


class SessionEndRequest(BaseModel):
    reason: Literal["completed", "aborted", "manual_end"] = "completed"


class SessionStateResponse(BaseModel):
    session_id: str
    created_at: str
    status: str
    candidate: Dict[str, Any]
    interview_config: Dict[str, Any]
    turn_counter: int
    current_agent: AgentType
    coverage_context: Dict[str, Any]
    turns: List[Dict[str, Any]]
    final_scores: Dict[str, Any]
    latest_question: Optional[Dict[str, Any]] = None
    pending_turn_id: Optional[str] = None
    locked: bool = False
