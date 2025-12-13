# models/interview_model.py
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class InterviewRequest(BaseModel):
    company: str
    role: str
    experience: int
    jd: Optional[str] = None
    resume: Optional[Any] = None
    # make topics flexible but typed: mapping string -> list of strings
    topics: Optional[Dict[str, List[str]]] = {}

class Interview(BaseModel):
    id: str
    company: str
    role: str
    experience: int
    jd: Optional[str] = ""
    resume: Optional[str] = None
    topics: Optional[Dict[str, List[str]]] = {}
