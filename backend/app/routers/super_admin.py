from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException
)

from app.middleware.auth_middleware import require_role

from app.services.cloudinary_service import upload_image


router = APIRouter(
    prefix="/super",
    tags=["Super Admin"]
)


@router.get("/")
def super_dashboard(
    current_user=Depends(require_role("super"))
):
    return {
        "message": "Super admin protected",
        "user": current_user
    }


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("super"))
):

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Only image files allowed"
        )

    image_url = upload_image(file.file)

    return {
        "image_url": image_url
    }