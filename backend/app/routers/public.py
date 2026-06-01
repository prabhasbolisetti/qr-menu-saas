import logging

from fastapi import APIRouter, HTTPException, Response

from app.services.menu_service import (
    get_restaurant_by_slug,
    get_public_menu_by_slug,
    RestaurantLookupError
)
from app.services.qr_service import build_qr_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/menu",
    tags=["Public Menu"]
)


@router.get("/{slug}/qr")
def get_menu_qr(slug: str):

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

    return build_qr_response(restaurant)


@router.get("/{slug}")
def get_menu(slug: str, response: Response):

    try:
        menu_response = get_public_menu_by_slug(slug)
    except RestaurantLookupError as exc:
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

    response.headers["Cache-Control"] = (
        "public, max-age=30, stale-while-revalidate=120"
    )

    return menu_response
