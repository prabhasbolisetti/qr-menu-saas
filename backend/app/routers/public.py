from fastapi import APIRouter, HTTPException

from app.services.menu_service import (
    get_restaurant_by_slug,
    get_categories,
    get_available_items,
    build_menu_response
)
from app.services.qr_service import build_qr_response

router = APIRouter(
    prefix="/menu",
    tags=["Public Menu"]
)


@router.get("/{slug}/qr")
def get_menu_qr(slug: str):

    restaurant = get_restaurant_by_slug(slug)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    return build_qr_response(restaurant)


@router.get("/{slug}")
def get_menu(slug: str):

    restaurant = get_restaurant_by_slug(slug)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    if not restaurant["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Restaurant inactive"
        )

    categories = get_categories(restaurant["id"])

    items = get_available_items(restaurant["id"])

    response = build_menu_response(
        restaurant,
        categories,
        items
    )

    return response
