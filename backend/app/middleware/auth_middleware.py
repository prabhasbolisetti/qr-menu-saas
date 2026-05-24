from fastapi import Depends, HTTPException


def get_current_user():

    # temporary fake logged-in user
    return {
        "user_id": "123",
        "role": "super"
    }


def require_role(required_role: str):

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=403,
                detail="Forbidden"
            )

        return current_user

    return role_checker