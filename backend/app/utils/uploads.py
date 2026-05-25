from fastapi import HTTPException, UploadFile, status

from app.config.settings import settings


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp"
}


def validate_image_upload(file: UploadFile):

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, or WebP images are allowed"
        )

    size = getattr(file, "size", None)

    if size is None:
        current_position = file.file.tell()
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(current_position)

    if size and size > settings.max_image_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Image is too large. Maximum allowed size is "
                f"{settings.MAX_IMAGE_UPLOAD_MB}MB"
            )
        )

    file.file.seek(0)
