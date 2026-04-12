# routers/interview.py
from datetime import datetime, timezone
import random
from fastapi import APIRouter, HTTPException
from models.interview_model import InterviewRequest
import uuid
from pydantic import BaseModel
from data.interviews import DEMO_INTERVIEWS

router = APIRouter()


class ReplyRequest(BaseModel):
    user_message: str


class CompleteInterviewRequest(BaseModel):
    duration_seconds: int = 0

@router.post("/create")
def create_interview(data: InterviewRequest):
    interview_id = str(uuid.uuid4())
    payload = data.dict()
    payload["id"] = interview_id
    payload["status"] = "in_progress"
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["ended_at"] = None
    payload["duration_seconds"] = 0
    payload["transcript"] = [
        {
            "speaker": "AI",
            "text": "Welcome! I'm your AI interviewer. Tell me about yourself.",
            "time": datetime.now(timezone.utc).isoformat(),
        }
    ]
    payload["score"] = None
    payload["feedback"] = None
    DEMO_INTERVIEWS[interview_id] = payload
    return {"success": True, "interview": payload}


@router.get("/{interview_id}")
def fetch_interview(interview_id: str):
    if interview_id not in DEMO_INTERVIEWS:
        raise HTTPException(status_code=404, detail="Interview not found")
    return DEMO_INTERVIEWS[interview_id]


@router.get("")
def list_interviews():
    interviews = list(DEMO_INTERVIEWS.values())
    interviews.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    return {"interviews": interviews}


@router.post("/{interview_id}/reply")
def add_reply(interview_id: str, data: ReplyRequest):
    interview = DEMO_INTERVIEWS.get(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    entry = {
        "speaker": "YOU",
        "text": data.user_message,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    interview["transcript"].append(entry)
    return {"success": True, "entry": entry}


@router.post("/{interview_id}/complete")
def complete_interview(interview_id: str, data: CompleteInterviewRequest):
    interview = DEMO_INTERVIEWS.get(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.get("status") == "completed":
        return {"success": True, "interview": interview}

    score = random.randint(65, 92)
    interview["status"] = "completed"
    interview["ended_at"] = datetime.now(timezone.utc).isoformat()
    interview["duration_seconds"] = data.duration_seconds
    interview["score"] = score
    interview["feedback"] = {
        "summary": "Good structure overall. Keep improving depth on trade-offs.",
        "strengths": [
            "Clear communication",
            "Reasonable problem-solving approach",
        ],
        "improvements": [
            "Cover more edge cases",
            "Improve scalability explanations",
        ],
    }
    return {"success": True, "interview": interview}
