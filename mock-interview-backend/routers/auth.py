# backend/routers/auth.py
from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta

router = APIRouter()

class FakeGoogleLoginRequest(BaseModel):
    # any dummy data if you want, not required
    demo: str | None = None

class AuthUser(BaseModel):
    id: str
    name: str
    email: str
    picture: str | None = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser

@router.post("/google/fake", response_model=AuthResponse)
def fake_google_login(body: FakeGoogleLoginRequest | None = None):
    """
    Fake Google login:
    - No real Google OAuth
    - Always returns the same demo user
    """

    user = AuthUser(
        id=str(uuid.uuid4()),
        name="Demo User",
        email="demo.user@example.com",
        picture="https://avatar.iran.liara.run/public/",  # random avatar
    )

    # totally fake token, just for demo
    fake_token = f"demo-token-{uuid.uuid4()}"
    return AuthResponse(
        access_token=fake_token,
        user=user,
    )
