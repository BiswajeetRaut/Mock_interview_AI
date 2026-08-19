# deps.py
from typing import Optional

from fastapi import Header, HTTPException
from firebase_admin import auth
from models.auth_user import AuthUser


def get_current_user(authorization: Optional[str] = Header(None)) -> AuthUser:
    # Header(None) — not Header(...) — is required here: a *required* header
    # makes FastAPI itself raise its own 422 on a missing header before this
    # function ever runs, which bypasses the 401 below entirely.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    try:
        decoded_token = auth.verify_id_token(token)
        return AuthUser.from_firebase(decoded_token)
    except Exception as e:
        print("Auth error:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
