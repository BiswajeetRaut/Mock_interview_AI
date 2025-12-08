from fastapi import APIRouter
import uuid
from models.interview_model import InterviewRequest, Interview
from data.interviews import DEMO_INTERVIEWS

router = APIRouter()


@router.post("/create")
def create_interview(data: InterviewRequest):
    interview_id = str(uuid.uuid4())
    interview = Interview(
        id=interview_id,
        company=data.company,
        role=data.role,
        experience=data.experience,
        jd=data.jd,
        resume=data.resume,
        topics=data.topics or [],
    )
    DEMO_INTERVIEWS[interview_id] = data
    return {"success": True, "interview": interview}


@router.get("/{interview_id}")
def fetch_interview(interview_id: str):
    print("Fetching interview with ID:", DEMO_INTERVIEWS.keys())
    if interview_id not in DEMO_INTERVIEWS:
        return {"error": "Interview not found"}

    return DEMO_INTERVIEWS[interview_id]
