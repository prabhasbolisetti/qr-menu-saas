from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    SUPABASE_URL = os.getenv(
        "SUPABASE_URL"
    )

    SUPABASE_ANON_KEY = os.getenv(
        "SUPABASE_ANON_KEY"
    )

    SUPABASE_SERVICE_ROLE_KEY = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )

    CLOUDINARY_CLOUD_NAME = os.getenv(
        "CLOUDINARY_CLOUD_NAME"
    )

    CLOUDINARY_API_KEY = os.getenv(
        "CLOUDINARY_API_KEY"
    )

    CLOUDINARY_API_SECRET = os.getenv(
        "CLOUDINARY_API_SECRET"
    )

    FRONTEND_PUBLIC_BASE_URL = os.getenv(
        "FRONTEND_PUBLIC_BASE_URL",
        "http://127.0.0.1:5173"
    )


settings = Settings()
