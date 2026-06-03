from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging

from app.services.supabase_service import auth_supabase, supabase


bearer_scheme = HTTPBearer(auto_error=False)
VALID_ROLES = {"super", "owner"}
logger = logging.getLogger(__name__)


def _get_profile(user_id: str):

    try:
        response = (
            supabase.table("profiles")
            .select("id,email,role,full_name")
            .eq("id", user_id)
            .single()
            .execute()
        )

        return response.data
    except Exception:
        logger.exception(
            "Failed to load user profile",
            extra={
                "fields": {
                    "user_id": user_id
                }
            }
        )
        return None


def build_user_identity(user):

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = user.id
    profile = _get_profile(user_id)
    role = (profile or {}).get("role")

    if role not in VALID_ROLES:
        role = None

    if not role:
        logger.warning(
            "Authenticated user has no configured database role",
            extra={
                "fields": {
                    "user_id": user_id,
                    "email": getattr(user, "email", None)
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not configured"
        )

    return {
        "user_id": user_id,
        "email": getattr(user, "email", None),
        "role": role
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
):

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token"
        )

    try:
        response = auth_supabase.auth.get_user(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return build_user_identity(getattr(response, "user", None))


def require_role(required_role: str):

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden"
            )

        return current_user

    return role_checker
