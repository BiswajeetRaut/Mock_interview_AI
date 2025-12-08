from pydantic import BaseModel
from typing import List, Optional


class InterviewRequest(BaseModel):
    company: str
    role: str
    experience: int
    jd: Optional[str] = None
    resume: Optional[str] = None
    topics: Optional[dict]


class Interview(BaseModel):
    id: str
    company: str
    role: str
    experience: int
    jd: Optional[str] = ""
    resume: Optional[str] = None
    topics: Optional[dict]
