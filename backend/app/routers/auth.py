from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth_middleware import get_current_user
from app.schemas.user import LoginSchema
from app.services.supabase_service import supabase


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


def _role_from_user(user):

    app_metadata = getattr(user, "app_metadata", None) or {}
    user_metadata = getattr(user, "user_metadata", None) or {}

    return (
        app_metadata.get("role")
        or user_metadata.get("role")
    )


@router.post("/login")
def login(data: LoginSchema):

    try:
        response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if not session or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    role = _role_from_user(user)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not configured"
        )

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": role
        }
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):

    return {
        "user": current_user
    }
