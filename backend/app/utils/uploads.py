from fastapi import HTTPException, UploadFile, status
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.config.settings import settings


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp"
}

ALLOWED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp"
}

MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def validate_image_upload(file: UploadFile):

    declared_content_type = (file.content_type or "").lower()

    if declared_content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, or WebP images are allowed"
        )

    file.file.seek(0)
    content = file.file.read(settings.max_image_upload_bytes + 1)
    size = len(content)

    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty"
        )

    if size > settings.max_image_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Image is too large. Maximum allowed size is "
                f"{settings.MAX_IMAGE_UPLOAD_MB}MB"
            )
        )

    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
            actual_content_type = ALLOWED_IMAGE_FORMATS.get(image.format)

        with Image.open(BytesIO(content)) as image:
            image.load()
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        file.file.seek(0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image"
        ) from exc

    if actual_content_type not in ALLOWED_IMAGE_TYPES:
        file.file.seek(0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, or WebP images are allowed"
        )

    if actual_content_type != declared_content_type:
        file.file.seek(0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image type does not match uploaded content"
        )

    if width * height > MAX_IMAGE_PIXELS:
        file.file.seek(0)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image dimensions are too large"
        )

    file.file.seek(0)

    return {
        "content_type": actual_content_type,
        "size": size,
        "width": width,
        "height": height
    }
