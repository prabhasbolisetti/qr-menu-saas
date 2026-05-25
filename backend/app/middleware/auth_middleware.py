from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.supabase_service import auth_supabase, supabase


bearer_scheme = HTTPBearer(auto_error=False)
VALID_ROLES = {"super", "owner"}


def _metadata_value(user, key: str):

    app_metadata = getattr(user, "app_metadata", None) or {}
    user_metadata = getattr(user, "user_metadata", None) or {}

    return (
        app_metadata.get(key)
        or user_metadata.get(key)
    )


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
        return None


def _sync_profile_from_metadata(user, role: str):

    if role not in VALID_ROLES:
        return None

    payload = {
        "id": user.id,
        "email": getattr(user, "email", None),
        "role": role,
        "full_name": _metadata_value(user, "full_name")
    }

    try:
        response = (
            supabase.table("profiles")
            .upsert(payload)
            .execute()
        )

        return response.data[0] if response.data else payload
    except Exception:
        return payload


def build_user_identity(user):

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = user.id
    profile = _get_profile(user_id)
    metadata_role = _metadata_value(user, "role")
    role = (profile or {}).get("role") or metadata_role

    if role not in VALID_ROLES:
        role = None

    if not profile and role:
        profile = _sync_profile_from_metadata(user, role)

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
