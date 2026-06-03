import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config.settings import settings
from app.utils.logging import (
    configure_logging,
    reset_request_id,
    set_request_id
)

from app.routers import (
    auth,
    public,
    owner,
    super_admin
)

configure_logging()
logger = logging.getLogger(__name__)


def init_sentry():

    if not settings.is_production or not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ModuleNotFoundError:
        logger.exception("Sentry SDK is not installed")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
        ]
    )


init_sentry()

logger.info(
    "ENVIRONMENT VALUE: %s",
    settings.ENVIRONMENT
)

app = FastAPI(
    title="QR Menu API",
    version="1.0.0",
    description=(
        "Backend API for restaurant onboarding, owner menu management, "
        "public QR menus, and image-backed menu operations."
    )
)

allowed_origins = settings.cors_origins

logger.info(
    "Allowed CORS origins: %s",
    allowed_origins
)

if "*" not in settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=None if settings.is_production else settings.BACKEND_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=512
)

app.include_router(auth.router)

app.include_router(public.router)

app.include_router(owner.router)

app.include_router(super_admin.router)


@app.middleware("http")
async def request_tracing(request: Request, call_next):

    request_id = (
        request.headers.get("x-request-id")
        or str(uuid4())
    )
    token = set_request_id(request_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request error",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path
                }
            }
        )
        raise
    finally:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )
        logger.info(
            "request.completed",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms
                }
            }
        )
        reset_request_id(token)

    response.headers["X-Request-ID"] = request_id

    return response


@app.middleware("http")
async def add_security_headers(request, call_next):

    response = await call_next(request)

    response.headers.setdefault(
        "X-Content-Type-Options",
        "nosniff"
    )

    response.headers.setdefault(
        "X-Frame-Options",
        "DENY"
    )

    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
    )

    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()"
    )

    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains"
        )

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):

    logger.exception(
        "Unhandled application exception",
        extra={
            "fields": {
                "method": request.method,
                "path": request.url.path
            }
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error"
        }
    )


@app.get("/")
def root():

    return {
        "message": "QR Menu API Running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "qr-menu-api",
        "version": app.version,
        "environment": settings.ENVIRONMENT
    }

if not settings.is_production:

    @app.get("/debug-env")
    def debug_env():

        import os

        return {
            "ENVIRONMENT_os": os.getenv("ENVIRONMENT"),
            "settings_ENVIRONMENT": settings.ENVIRONMENT,
            "is_production": settings.is_production
        }
