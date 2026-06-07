import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.middleware.rate_limit import check_public_menu_rate_limit
from app.services.menu_service import (
    get_restaurant_by_slug,
    get_public_menu_metadata_by_slug,
    PublicMenuLoadError,
    RestaurantLookupError
)
from app.services.qr_service import build_qr_response

logger = logging.getLogger(__name__)

PUBLIC_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

router = APIRouter(
    prefix="/menu",
    tags=["Public Menu"],
    dependencies=[Depends(check_public_menu_rate_limit)]
)


def _normalize_slug(slug: str):

    return slug.strip().lower()


def _validate_public_slug(slug: str):

    normalized_slug = _normalize_slug(slug)

    if not PUBLIC_SLUG_PATTERN.fullmatch(normalized_slug):
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    return normalized_slug


def _set_qr_cache_headers(response: Response):

    response.headers["Cache-Control"] = (
        "public, max-age=86400, stale-while-revalidate=604800"
    )
    response.headers["Vary"] = "Accept-Encoding"


@router.get("/{slug}/qr")
def get_menu_qr(slug: str, response: Response):

    slug = _validate_public_slug(slug)

    try:
        restaurant = get_restaurant_by_slug(slug)
    except RestaurantLookupError as exc:
        logger.error(
            "Failed to load QR restaurant slug=%s error=%s",
            slug,
            exc,
            exc_info=True
        )
        raise HTTPException(
            status_code=503,
            detail="Menu service temporarily unavailable"
        ) from exc

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    _set_qr_cache_headers(response)

    return build_qr_response(restaurant)


@router.get("/{slug}")
def get_menu(slug: str, request: Request, response: Response):

    slug = _validate_public_slug(slug)

    try:
        menu_metadata = get_public_menu_metadata_by_slug(slug)
    except (PublicMenuLoadError, RestaurantLookupError) as exc:
        logger.error(
            "Failed to load public menu restaurant slug=%s error=%s",
            slug,
            exc,
            exc_info=True
        )
        raise HTTPException(
            status_code=503,
            detail="Menu service temporarily unavailable"
        ) from exc

    menu_response = menu_metadata["payload"] if menu_metadata else None

    if not menu_response:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    if menu_response.get("inactive"):
        raise HTTPException(
            status_code=403,
            detail="Restaurant inactive"
        )

    etag = menu_metadata["etag"]

    response.headers["Cache-Control"] = (
        "public, max-age=60, stale-while-revalidate=300, stale-if-error=900"
    )
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Vary"] = "Accept-Encoding"

    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(
            status_code=304,
            headers={
                "Cache-Control": response.headers["Cache-Control"],
                "ETag": response.headers["ETag"],
                "Vary": response.headers["Vary"]
            }
        )

    return menu_response
