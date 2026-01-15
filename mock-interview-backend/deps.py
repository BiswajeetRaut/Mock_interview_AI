# deps.py
from fastapi import Header, HTTPException
from firebase_admin import auth
from models.auth_user import AuthUser

def get_current_user(authorization: str = Header(...)) -> AuthUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    token = authorization.split(" ")[1]

    try:
        decoded_token = auth.verify_id_token(token)
        return AuthUser.from_firebase(decoded_token)  # ✅ FIX
    except Exception as e:
        print("Auth error:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
