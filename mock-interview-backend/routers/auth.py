# # backend/routers/auth.py
# from pydantic import BaseModel
# import uuid
# from fastapi import APIRouter, Depends
# from firebase_admin_init import db
# from deps import get_current_user
# from datetime import datetime

# router = APIRouter()

# class FakeGoogleLoginRequest(BaseModel):
#     # any dummy data if you want, not required
#     demo: str | None = None

# class AuthUserSample(BaseModel):
#     id: str
#     name: str
#     email: str
#     picture: str | None = None

# class AuthResponse(BaseModel):
#     access_token: str
#     token_type: str = "bearer"
#     user: AuthUserSample

# @router.post("/google/fake", response_model=AuthResponse)
# def fake_google_login(body: FakeGoogleLoginRequest | None = None):
#     """
#     Fake Google login:
#     - No real Google OAuth
#     - Always returns the same demo user
#     """

#     user = AuthUserSample(
#         id=str(uuid.uuid4()),
#         name="Demo User",
#         email="demo.user@example.com",
#         picture="https://avatar.iran.liara.run/public/",  # random avatar
#     )

#     # totally fake token, just for demo
#     fake_token = f"demo-token-{uuid.uuid4()}"
#     return AuthResponse(
#         access_token=fake_token,
#         user=user,
#     )

# @router.post("/google")
# def google_auth(user=Depends(get_current_user)):
#     uid = user["uid"]
#     email = user.get("email")
#     name = user.get("name", "")
#     picture = user.get("picture", "")

#     user_ref = db.collection("users").document(uid)
#     doc = user_ref.get()

#     # ✅ If user already exists
#     if doc.exists:
#         return {
#             "success": True,
#             "user": doc.to_dict(),
#             "isNew": False
#         }

#     # ✅ Create new user
#     new_user = {
#         "uid": uid,
#         "email": email,
#         "name": name,
#         "avatar": picture,
#         "role": "user",
#         "createdAt": datetime.utcnow().isoformat()
#     }

#     user_ref.set(new_user)

#     return {
#         "success": True,
#         "user": new_user,
#         "isNew": True
#     }


from fastapi import APIRouter, Depends
from firebase_admin_init import db
from deps import get_current_user
from models.auth_user import AuthUser
from datetime import datetime

router = APIRouter()

@router.post("/google")
def google_auth(current_user: AuthUser = Depends(get_current_user)):
    user_ref = db.collection("users").document(current_user.uid)
    doc = user_ref.get()

    if doc.exists:
        return {
            "success": True,
            "user": doc.to_dict(),
            "isNew": False
        }

    new_user = {
        "uid": current_user.uid,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.picture,
        "provider": current_user.provider,
        "role": "user",
        "createdAt": datetime.utcnow().isoformat()
    }

    user_ref.set(new_user)

    return {
        "success": True,
        "user": new_user,
        "isNew": True
    }
