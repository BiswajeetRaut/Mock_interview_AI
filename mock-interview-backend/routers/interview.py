# routers/interview.py
from fastapi import APIRouter, HTTPException
from models.interview_model import InterviewRequest
import uuid

router = APIRouter()
DEMO_INTERVIEWS = {}

@router.post("/create")
def create_interview(data: InterviewRequest):
    # pydantic validated 'data' already; convert to dict and add id
    interview_id = str(uuid.uuid4())
    payload = data.dict()
    payload["id"] = interview_id
    DEMO_INTERVIEWS[interview_id] = payload
    return {"success": True, "interview": payload}

@router.get("/{interview_id}")
def fetch_interview(interview_id: str):
    if interview_id not in DEMO_INTERVIEWS:
        raise HTTPException(status_code=404, detail="Interview not found")
    return DEMO_INTERVIEWS[interview_id]
