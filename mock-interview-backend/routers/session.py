from fastapi import APIRouter, Depends, HTTPException
from deps import get_current_user
from middleware.rate_limit import (
    SESSION_ANSWER_CAPACITY,
    SESSION_ANSWER_REFILL_PER_MIN,
    SESSION_START_CAPACITY,
    SESSION_START_REFILL_PER_MIN,
    rate_limit_by_ip_and_uid,
)
from models.auth_user import AuthUser
from models.session_models import (
    SessionAnswerRequest,
    SessionEndRequest,
    SessionStartRequest,
    SessionStateResponse,
)
from services.session_engine import end_session, get_session, start_session, submit_answer

router = APIRouter()

_start_rate_limit = rate_limit_by_ip_and_uid("session_start", SESSION_START_CAPACITY, SESSION_START_REFILL_PER_MIN)
_answer_rate_limit = rate_limit_by_ip_and_uid("session_answer", SESSION_ANSWER_CAPACITY, SESSION_ANSWER_REFILL_PER_MIN)


def _get_owned_session(session_id: str, current_user: AuthUser) -> dict:
    """Fetch a session and enforce ownership. 404s before 403s — existence
    of another user's session_id is not information a caller should get."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("owner_uid") != current_user.uid:
        raise HTTPException(status_code=403, detail="You do not have access to this session")
    return session


@router.post("/start", response_model=SessionStateResponse, dependencies=[Depends(_start_rate_limit)])
def session_start(payload: SessionStartRequest, current_user: AuthUser = Depends(get_current_user)):
    return start_session(payload.dict(), owner_uid=current_user.uid)


@router.post("/{session_id}/answer", response_model=SessionStateResponse, dependencies=[Depends(_answer_rate_limit)])
def session_answer(
    session_id: str,
    payload: SessionAnswerRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    session = _get_owned_session(session_id, current_user)

    if session.get("locked"):
        raise HTTPException(status_code=409, detail="Session is processing a previous answer")

    try:
        return submit_answer(session_id, payload.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{session_id}/state", response_model=SessionStateResponse)
def session_state(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    return _get_owned_session(session_id, current_user)


@router.post("/{session_id}/end", response_model=SessionStateResponse)
def session_end(
    session_id: str,
    payload: SessionEndRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    _get_owned_session(session_id, current_user)
    return end_session(session_id, payload.reason)


@router.get("/{session_id}/report")
def session_report(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    session = _get_owned_session(session_id, current_user)
    if session["status"] not in ["completed", "aborted"]:
        return {"status": "pending", "session_id": session_id}

    return {
        "session_id": session["session_id"],
        "candidate_name": session["candidate"]["name"],
        "company": session["interview_config"]["company"],
        "role": session["interview_config"]["role"],
        "interview_date": session["created_at"][:10],
        "overall_score": session["final_scores"]["overall"],
        "overall_verdict": "good" if (session["final_scores"]["overall"] or 0) >= 70 else "average",
        "domain_scores": session["final_scores"],
        "strengths": session["coverage_context"]["strength_tags"][:5],
        "improvement_areas": session["coverage_context"]["weakness_tags"][:5],
        "detailed_turns": session["turns"],
        "hiring_recommendation": "consider"
        if (session["final_scores"]["overall"] or 0) >= 60
        else "no",
    }


@router.get("/{session_id}/logs")
def session_logs(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    session = _get_owned_session(session_id, current_user)
    return {
        "session_id": session_id,
        "status": session.get("status"),
        "current_agent": session.get("current_agent"),
        "current_difficulty": session.get("current_difficulty"),
        "signal_confidence": session.get("signal_confidence"),
        "supervisor_scratchpad": session.get("supervisor_scratchpad", []),
        "latest_question": session.get("latest_question"),
        "coverage_context": session.get("coverage_context"),
        "debug_trace": session.get("debug_trace", []),
    }
