import pytest
from fastapi.testclient import TestClient

from main import app
from middleware.rate_limit import reset_local_buckets
from services.session_engine import SESSION_STORE


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_session_store():
    """SESSION_STORE is a module-level dict (pre-P2-201) — reset it around
    every test so sessions from one test can't leak into the next."""
    SESSION_STORE.clear()
    yield
    SESSION_STORE.clear()


@pytest.fixture(autouse=True)
def _clean_rate_limit_buckets():
    """In-process rate-limit buckets are also module-level state — reset
    between tests for the same reason, and so a burst in one test doesn't
    trip the limiter in the next."""
    reset_local_buckets()
    yield
    reset_local_buckets()


def seed_session(session_id: str, owner_uid: str, **overrides) -> dict:
    """Insert a session directly into the store, bypassing start_session()
    (and the LLM-backed interview graph it drives) so authorization tests
    stay fast and independent of the agent pipeline."""
    session = {
        "session_id": session_id,
        "thread_id": f"thread_{session_id}",
        "owner_uid": owner_uid,
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "active",
        "candidate": {"user_id": owner_uid, "name": "Test Candidate", "resume_parsed": {}},
        "interview_config": {
            "company": "TestCo", "role": "SDE II", "experience": 2,
            "selected_types": ["tech-dsa"], "topics": {},
        },
        "turn_counter": 0,
        "current_agent": "code",
        "current_difficulty": "medium",
        "coverage_context": {
            "already_asked_topics": [], "avoid_topics": [],
            "weakness_tags": [], "strength_tags": [],
        },
        "turns": [],
        "supervisor_scratchpad": [],
        "signal_confidence": 0.0,
        "final_scores": {},
        "latest_question": {"question_text": "Solve this.", "agent_type": "code"},
        "pending_turn_id": "T_001",
        "locked": False,
        "is_interview_over": False,
        "debug_trace": [],
    }
    session.update(overrides)
    SESSION_STORE[session_id] = session
    return session


def fake_decoded_token(uid: str) -> dict:
    return {
        "uid": uid,
        "email": f"{uid}@example.com",
        "name": uid,
        "firebase": {"sign_in_provider": "google"},
    }
