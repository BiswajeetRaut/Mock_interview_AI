from datetime import datetime

from fastapi import APIRouter, Depends

from deps import get_current_user
from firebase_admin_init import db
from models.auth_user import AuthUser


router = APIRouter()


@router.post("/google")
def google_auth(current_user: AuthUser = Depends(get_current_user)):
    user_ref = db.collection("users").document(current_user.uid)
    doc = user_ref.get()

    if doc.exists:
        return {
            "success": True,
            "user": doc.to_dict(),
            "isNew": False,
        }

    new_user = {
        "uid": current_user.uid,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.picture,
        "provider": current_user.provider,
        "role": "user",
        "createdAt": datetime.utcnow().isoformat(),
    }

    user_ref.set(new_user)

    return {
        "success": True,
        "user": new_user,
        "isNew": True,
    }
