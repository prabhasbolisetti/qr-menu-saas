from app.config.settings import settings


def upload_image(file):

    try:
        import cloudinary
        import cloudinary.uploader
    except ModuleNotFoundError as exc:
        raise RuntimeError("Cloudinary package is not installed") from exc

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )

    result = cloudinary.uploader.upload(file)

    return result["secure_url"]
