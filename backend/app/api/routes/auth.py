from typing import Any

from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_authenticated_user(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "uid": current_user["uid"],
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "picture": current_user.get("picture"),
    }
