from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from app.middleware.auth_middleware import (
    require_role
)

from app.services.owner_service import (
    get_owner_restaurant,
    get_owner_items,
    toggle_item_availability,
    update_item_price
)

router = APIRouter(
    prefix="/owner",
    tags=["Owner"]
)


@router.get("/restaurant")
def owner_restaurant(
    current_user=Depends(require_role("owner"))
):

    restaurant = get_owner_restaurant(
        current_user["user_id"]
    )

    return restaurant


@router.get("/items")
def owner_items(
    current_user=Depends(require_role("owner"))
):

    restaurant = get_owner_restaurant(
        current_user["user_id"]
    )

    items = get_owner_items(
        restaurant["id"]
    )

    return items


@router.patch("/items/{item_id}/toggle")
def toggle_item(
    item_id: str,
    current_user=Depends(require_role("owner"))
):

    restaurant = get_owner_restaurant(
        current_user["user_id"]
    )

    items = get_owner_items(
        restaurant["id"]
    )

    item = next(
        (
            i for i in items
            if i["id"] == item_id
        ),
        None
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    updated = toggle_item_availability(
        item_id,
        item["is_available"]
    )

    return updated


@router.put("/items/{item_id}/price")
def update_price(
    item_id: str,
    price: float,
    current_user=Depends(require_role("owner"))
):

    restaurant = get_owner_restaurant(
        current_user["user_id"]
    )

    items = get_owner_items(
        restaurant["id"]
    )

    item = next(
        (
            i for i in items
            if i["id"] == item_id
        ),
        None
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    updated = update_item_price(
        item_id,
        price
    )

    return updated