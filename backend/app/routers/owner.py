from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import get_current_user

router = APIRouter(
    prefix="/owner",
    tags=["Owner"]
)

@router.get("/")
def owner_dashboard(
    current_user=Depends(get_current_user)
):
    return {
        "message": "Owner route protected",
        "user": current_user
    }