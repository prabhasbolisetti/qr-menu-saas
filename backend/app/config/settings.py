from dotenv import load_dotenv

import os
from urllib.parse import urlparse

load_dotenv()


class Settings:

    def __init__(self):
        configured_cors_origins = os.getenv(
            "BACKEND_CORS_ORIGINS"
        )

        configured_cors_origin_regex = os.getenv(
            "BACKEND_CORS_ORIGIN_REGEX"
        )

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

        self.RENDER_EXTERNAL_HOSTNAME = os.getenv(
            "RENDER_EXTERNAL_HOSTNAME"
        )

        self.RENDER_EXTERNAL_URL = os.getenv(
            "RENDER_EXTERNAL_URL"
        )

        development_cors_origins = (
            "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
            "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,"
            "https://qr-menu-saas-ten.vercel.app"
        )

        # Production startup must not fail just because a deploy target missed a
        # new env var. Missing CORS config is still dangerous because browsers
        # cannot call the API from the frontend, so production falls back to an
        # empty allow-list and main.py emits a high-severity warning.
        self.BACKEND_CORS_ORIGINS = (
            configured_cors_origins
            if configured_cors_origins is not None
            else ("" if self.is_production else development_cors_origins)
        )

        configured_allowed_hosts = os.getenv(
            "BACKEND_ALLOWED_HOSTS"
        )

        self.BACKEND_ALLOWED_HOSTS = (
            configured_allowed_hosts
            if configured_allowed_hosts and configured_allowed_hosts.strip()
            else self._default_allowed_hosts()
        )

        self.BACKEND_CORS_ORIGIN_REGEX = configured_cors_origin_regex
        self._cors_origins_configured = configured_cors_origins is not None
        self._cors_origin_regex_configured = configured_cors_origin_regex is not None

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

        self.RATE_LIMIT_STORAGE_URL = os.getenv(
            "RATE_LIMIT_STORAGE_URL"
        )

        self.SENTRY_DSN = os.getenv(
            "SENTRY_DSN"
        )

        self.SENTRY_TRACES_SAMPLE_RATE = float(
            os.getenv(
                "SENTRY_TRACES_SAMPLE_RATE",
                "0.1"
            )
        )

        self.LOG_FORMAT = os.getenv(
            "LOG_FORMAT",
            "json" if self.is_production else "text"
        )

    @property
    def is_production(self):

        return self.ENVIRONMENT.lower() == "production"

    def _default_allowed_hosts(self):

        if not self.is_production:
            return "*"

        render_hostname = (
            self.RENDER_EXTERNAL_HOSTNAME
            or urlparse(self.RENDER_EXTERNAL_URL or "").hostname
        )

        return render_hostname or ""

    @property
    def cors_origins(self):

        origins = [
            origin.strip().rstrip("/")
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

        if not self.is_production:
            return origins

        return [
            origin
            for origin in origins
            if origin != "*"
        ]

    @property
    def cors_origin_regex(self):

        if self.is_production:
            return None

        return self.BACKEND_CORS_ORIGIN_REGEX

    @property
    def cors_origins_missing_in_production(self):

        return self.is_production and not self._cors_origins_configured

    @property
    def cors_regex_ignored_in_production(self):

        return self.is_production and self._cors_origin_regex_configured

    @property
    def cors_wildcard_ignored_in_production(self):

        if not self.is_production:
            return False

        configured_origins = [
            origin.strip().rstrip("/")
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

        return "*" in configured_origins

    @property
    def allowed_hosts(self):

        return [
            host.strip()
            for host in self.BACKEND_ALLOWED_HOSTS.split(",")
            if host.strip()
        ]

    @property
    def allowed_hosts_missing_in_production(self):

        return self.is_production and not self.allowed_hosts

    @property
    def max_image_upload_bytes(self):

        return self.MAX_IMAGE_UPLOAD_MB * 1024 * 1024

    def missing_required_backend_values(self):

        required_values = {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_ANON_KEY": self.SUPABASE_ANON_KEY,
            "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
            "FRONTEND_PUBLIC_BASE_URL": self.FRONTEND_PUBLIC_BASE_URL
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

        if self.is_production:
            if "*" in self.allowed_hosts:
                raise RuntimeError(
                    "BACKEND_ALLOWED_HOSTS cannot contain '*' in production"
                )

            if not self.RATE_LIMIT_STORAGE_URL:
                raise RuntimeError(
                    "RATE_LIMIT_STORAGE_URL must be configured in production"
                )


settings = Settings()
