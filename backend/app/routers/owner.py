from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import logging

from app.middleware.auth_middleware import require_role

logger = logging.getLogger(__name__)


def _database_error_detail(operation: str, exc: Exception):

    error_text = str(exc)

    if "is_open" in error_text and "restaurants" in error_text:
        return (
            f"{operation} failed: database migration required "
            "for restaurants.is_open"
        )

    return f"{operation} failed"


def _database_error_status(exc: Exception):

    error_text = str(exc)

    if "is_open" in error_text and "restaurants" in error_text:
        return 503

    return 500


from app.schemas.category import OwnerCreateCategorySchema, UpdateCategorySchema
from app.schemas.menu_item import OwnerCreateMenuItemSchema, UpdateMenuItemSchema
from app.schemas.restaurant import UpdateRestaurantOpenStateSchema
from app.services.cloudinary_service import upload_image
from app.services.owner_service import (
    create_owner_category,
    create_owner_item,
    delete_owner_category,
    delete_owner_item,
    get_owner_categories,
    get_owner_category,
    get_owner_item,
    get_owner_items,
    get_owner_restaurant,
    toggle_item_availability,
    update_item_price,
    update_owner_category,
    update_owner_item,
    update_owner_restaurant_open_state,
)
from app.services.qr_service import build_qr_response
from app.utils.uploads import validate_image_upload


router = APIRouter(
    prefix="/owner",
    tags=["Owner"]
)


def _owner_restaurant(current_user):

    restaurant = get_owner_restaurant(
        current_user["user_id"]
    )

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Owner restaurant not found"
        )

    return restaurant


def _assert_category_belongs_to_owner(restaurant_id: str, category_id: str):

    category = get_owner_category(
        restaurant_id,
        category_id
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    return category


def _assert_item_belongs_to_owner(restaurant_id: str, item_id: str):

    item = get_owner_item(
        restaurant_id,
        item_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    return item


@router.get("/restaurant")
def owner_restaurant(
    current_user=Depends(require_role("owner"))
):

    return _owner_restaurant(current_user)


@router.get("/restaurant/qr")
def owner_restaurant_qr(
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)

    return build_qr_response(restaurant)


@router.patch("/restaurant/open-state")
def update_restaurant_open_state(
    data: UpdateRestaurantOpenStateSchema,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)

    try:
        return update_owner_restaurant_open_state(
            restaurant["id"],
            data.is_open
        )
    except Exception as e:
        logger.error(
            "Failed to update owner restaurant open state restaurant_id=%s error=%s",
            restaurant["id"],
            e,
            exc_info=True
        )
        raise HTTPException(
            status_code=_database_error_status(e),
            detail=_database_error_detail("Update restaurant open state", e)
        ) from e


@router.get("/categories")
def owner_categories(
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)

    return get_owner_categories(
        restaurant["id"]
    )


@router.post("/categories")
def create_category(
    data: OwnerCreateCategorySchema,
    current_user=Depends(require_role("owner"))
):

    try:
        restaurant = _owner_restaurant(current_user)
        payload = data.model_dump()
        payload["restaurant_id"] = restaurant["id"]
        logger.info("Owner creating category payload=%s", payload)
        category = create_owner_category(payload)
        logger.info(f"Category created: {category}")
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create owner category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create category: {str(e)}"
        ) from e


@router.put("/categories/{category_id}")
def update_category(
    category_id: str,
    data: UpdateCategorySchema,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    _assert_category_belongs_to_owner(
        restaurant["id"],
        category_id
    )

    return update_owner_category(
        restaurant["id"],
        category_id,
        data
    )


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    _assert_category_belongs_to_owner(
        restaurant["id"],
        category_id
    )

    delete_owner_category(
        restaurant["id"],
        category_id
    )

    return {
        "message": "Category deleted successfully"
    }


@router.get("/items")
def owner_items(
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)

    return get_owner_items(
        restaurant["id"]
    )


@router.post("/items")
def create_item(
    data: OwnerCreateMenuItemSchema,
    current_user=Depends(require_role("owner"))
):

    try:
        restaurant = _owner_restaurant(current_user)
        _assert_category_belongs_to_owner(
            restaurant["id"],
            data.category_id
        )
        payload = data.model_dump()
        payload["restaurant_id"] = restaurant["id"]
        logger.info("Owner creating menu item payload=%s", payload)
        item = create_owner_item(payload)
        logger.info(f"Menu item created: {item}")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create owner menu item: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create menu item: {str(e)}"
        ) from e


@router.put("/items/{item_id}")
def update_item(
    item_id: str,
    data: UpdateMenuItemSchema,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    if data.category_id:
        _assert_category_belongs_to_owner(
            restaurant["id"],
            data.category_id
        )

    return update_owner_item(
        restaurant["id"],
        item_id,
        data
    )


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    delete_owner_item(
        restaurant["id"],
        item_id
    )

    return {
        "message": "Item deleted successfully"
    }


@router.patch("/items/{item_id}/toggle")
def toggle_item(
    item_id: str,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    item = _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    return toggle_item_availability(
        restaurant["id"],
        item_id,
        item["is_available"]
    )


@router.put("/items/{item_id}/price")
def update_price(
    item_id: str,
    price: float,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    return update_item_price(
        restaurant["id"],
        item_id,
        price
    )


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("owner"))
):

    validate_image_upload(file)

    try:
        image_url = upload_image(file.file)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc

    return {
        "image_url": image_url
    }
