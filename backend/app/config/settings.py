from dotenv import load_dotenv

import os
from urllib.parse import urlparse

load_dotenv()


class Settings:

    def __init__(self):

        self.ENVIRONMENT = os.getenv(
            "ENVIRONMENT",
            "development"
        )

        self.SUPABASE_URL = os.getenv(
            "SUPABASE_URL"
        )

        self.SUPABASE_ANON_KEY = os.getenv(
            "SUPABASE_ANON_KEY"
        )

        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY"
        )

        self.CLOUDINARY_CLOUD_NAME = os.getenv(
            "CLOUDINARY_CLOUD_NAME"
        )

        self.CLOUDINARY_API_KEY = os.getenv(
            "CLOUDINARY_API_KEY"
        )

        self.CLOUDINARY_API_SECRET = os.getenv(
            "CLOUDINARY_API_SECRET"
        )

        self.FRONTEND_PUBLIC_BASE_URL = os.getenv(
            "FRONTEND_PUBLIC_BASE_URL",
            "https://qr-menu-saas-ten.vercel.app"
        )

        self.BACKEND_CORS_ORIGINS = os.getenv(
            "BACKEND_CORS_ORIGINS",
            (
                "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
                "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,"
                "https://qr-menu-saas-ten.vercel.app"
            )
        )

        self.BACKEND_ALLOWED_HOSTS = os.getenv(
            "BACKEND_ALLOWED_HOSTS",
            "*"
        )

        self.BACKEND_CORS_ORIGIN_REGEX = os.getenv(
            "BACKEND_CORS_ORIGIN_REGEX",
            r"https://.*\.vercel\.app"
        )

        self.SUPABASE_POSTGREST_TIMEOUT_SECONDS = float(
            os.getenv(
                "SUPABASE_POSTGREST_TIMEOUT_SECONDS",
                "2.5"
            )
        )

        self.PUBLIC_MENU_CACHE_TTL_SECONDS = int(
            os.getenv(
                "PUBLIC_MENU_CACHE_TTL_SECONDS",
                "120"
            )
        )

        self.PUBLIC_MENU_STALE_SECONDS = int(
            os.getenv(
                "PUBLIC_MENU_STALE_SECONDS",
                "900"
            )
        )

        self.PUBLIC_MENU_CACHE_MAX_SIZE = int(
            os.getenv(
                "PUBLIC_MENU_CACHE_MAX_SIZE",
                "512"
            )
        )

        self.PUBLIC_MENU_SINGLEFLIGHT_WAIT_SECONDS = float(
            os.getenv(
                "PUBLIC_MENU_SINGLEFLIGHT_WAIT_SECONDS",
                "2.2"
            )
        )

        self.MAX_IMAGE_UPLOAD_MB = int(
            os.getenv(
                "MAX_IMAGE_UPLOAD_MB",
                "5"
            )
        )

        self.CLOUDINARY_FOLDER = os.getenv(
            "CLOUDINARY_FOLDER",
            "qr-menu/menu-items"
        )

    @property
    def is_production(self):

        return self.ENVIRONMENT.lower() == "production"

    @property
    def cors_origins(self):

        return [
            origin.strip().rstrip("/")
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def allowed_hosts(self):

        return [
            host.strip()
            for host in self.BACKEND_ALLOWED_HOSTS.split(",")
            if host.strip()
        ]

    @property
    def max_image_upload_bytes(self):

        return self.MAX_IMAGE_UPLOAD_MB * 1024 * 1024

    def missing_required_backend_values(self):

        required_values = {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_ANON_KEY": self.SUPABASE_ANON_KEY,
            "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
            "FRONTEND_PUBLIC_BASE_URL": self.FRONTEND_PUBLIC_BASE_URL,
            "BACKEND_CORS_ORIGINS": self.BACKEND_CORS_ORIGINS
        }

        return [
            key
            for key, value in required_values.items()
            if not value
        ]

    def validate_backend_config(self):

        missing = self.missing_required_backend_values()

        if missing:
            raise RuntimeError(
                "Missing required backend environment variables: "
                + ", ".join(missing)
            )

        parsed_frontend_url = urlparse(
            self.FRONTEND_PUBLIC_BASE_URL
        )

        if (
            parsed_frontend_url.scheme not in {"http", "https"}
            or not parsed_frontend_url.netloc
        ):
            raise RuntimeError(
                "FRONTEND_PUBLIC_BASE_URL must be an absolute http(s) URL"
            )


settings = Settings()
