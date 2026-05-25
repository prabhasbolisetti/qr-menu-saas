from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.supabase_service import supabase


bearer_scheme = HTTPBearer(auto_error=False)


def _metadata_value(user, key: str):

    app_metadata = getattr(user, "app_metadata", None) or {}
    user_metadata = getattr(user, "user_metadata", None) or {}

    return (
        app_metadata.get(key)
        or user_metadata.get(key)
    )


def _profile_role(user_id: str):

    try:
        response = (
            supabase.table("profiles")
            .select("role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if response.data:
            return response.data.get("role")
    except Exception:
        return None

    return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
):

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token"
        )

    try:
        response = supabase.auth.get_user(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = getattr(response, "user", None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = user.id
    role = _metadata_value(user, "role") or _profile_role(user_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not configured"
        )

    return {
        "user_id": user_id,
        "email": getattr(user, "email", None),
        "role": role
    }


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
