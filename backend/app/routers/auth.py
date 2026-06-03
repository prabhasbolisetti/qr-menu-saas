from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth_middleware import build_user_identity, get_current_user
from app.middleware.rate_limit import check_login_rate_limit
from app.schemas.user import LoginSchema
from app.services.supabase_service import auth_supabase


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post(
    "/login",
    dependencies=[Depends(check_login_rate_limit)]
)
def login(data: LoginSchema):

    try:
        response = auth_supabase.auth.sign_in_with_password({
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

    current_user = build_user_identity(user)

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "user": {
            "id": current_user["user_id"],
            "email": current_user["email"],
            "role": current_user["role"]
        }
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):

    return {
        "user": current_user
    }
