import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config.settings import settings

from app.routers import (
    auth,
    public,
    owner,
    super_admin
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger(__name__).info(
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

logging.getLogger(__name__).info(
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

app.include_router(public.router)

app.include_router(owner.router)

app.include_router(super_admin.router)


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

@app.get("/debug-env")
def debug_env():

    import os

    return {
        "ENVIRONMENT_os": os.getenv("ENVIRONMENT"),
        "settings_ENVIRONMENT": settings.ENVIRONMENT,
        "is_production": settings.is_production
    }