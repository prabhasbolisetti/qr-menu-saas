from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import logging

from app.middleware.auth_middleware import require_role
from app.middleware.rate_limit import (
    check_owner_mutation_rate_limit,
    check_upload_rate_limit
)

logger = logging.getLogger(__name__)


def _database_error_detail(operation: str, exc: Exception):

    error_text = str(exc)

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
    get_owner_item_including_deleted,
    get_owner_items,
    get_owner_restaurant,
    get_owner_category_including_deleted,
    restore_owner_category,
    restore_owner_item,
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

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)

    try:
        return update_owner_restaurant_open_state(
            restaurant["id"],
            data.is_open,
            actor=current_user
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

    check_owner_mutation_rate_limit(current_user)

    try:
        restaurant = _owner_restaurant(current_user)
        payload = data.model_dump()
        payload["restaurant_id"] = restaurant["id"]
        category = create_owner_category(
            payload,
            actor=current_user
        )
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create owner category")
        raise HTTPException(
            status_code=500,
            detail="Failed to create category"
        ) from e


@router.put("/categories/{category_id}")
def update_category(
    category_id: str,
    data: UpdateCategorySchema,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    _assert_category_belongs_to_owner(
        restaurant["id"],
        category_id
    )

    return update_owner_category(
        restaurant["id"],
        category_id,
        data,
        actor=current_user
    )


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    _assert_category_belongs_to_owner(
        restaurant["id"],
        category_id
    )

    delete_owner_category(
        restaurant["id"],
        category_id,
        actor=current_user
    )

    return {
        "message": "Category deleted successfully"
    }


@router.post("/categories/{category_id}/restore")
def restore_category(
    category_id: str,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    category = get_owner_category_including_deleted(
        restaurant["id"],
        category_id
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    return restore_owner_category(
        restaurant["id"],
        category_id,
        actor=current_user
    )


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

    check_owner_mutation_rate_limit(current_user)

    try:
        restaurant = _owner_restaurant(current_user)
        _assert_category_belongs_to_owner(
            restaurant["id"],
            data.category_id
        )
        payload = data.model_dump()
        payload["restaurant_id"] = restaurant["id"]
        item = create_owner_item(
            payload,
            actor=current_user
        )
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create owner menu item")
        raise HTTPException(
            status_code=500,
            detail="Failed to create menu item"
        ) from e


@router.put("/items/{item_id}")
def update_item(
    item_id: str,
    data: UpdateMenuItemSchema,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
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
        data,
        actor=current_user
    )


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    delete_owner_item(
        restaurant["id"],
        item_id,
        actor=current_user
    )

    return {
        "message": "Item deleted successfully"
    }


@router.post("/items/{item_id}/restore")
def restore_item(
    item_id: str,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    item = get_owner_item_including_deleted(
        restaurant["id"],
        item_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    category = get_owner_category(
        restaurant["id"],
        item["category_id"]
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail="Item category is not active"
        )

    return restore_owner_item(
        restaurant["id"],
        item_id,
        actor=current_user
    )


@router.patch("/items/{item_id}/toggle")
def toggle_item(
    item_id: str,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    item = _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    return toggle_item_availability(
        restaurant["id"],
        item_id,
        item["is_available"],
        actor=current_user
    )


@router.put("/items/{item_id}/price")
def update_price(
    item_id: str,
    price: float,
    current_user=Depends(require_role("owner"))
):

    check_owner_mutation_rate_limit(current_user)
    restaurant = _owner_restaurant(current_user)
    _assert_item_belongs_to_owner(
        restaurant["id"],
        item_id
    )

    return update_item_price(
        restaurant["id"],
        item_id,
        price,
        actor=current_user
    )


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("owner"))
):

    check_upload_rate_limit(current_user)
    validate_image_upload(file)

    try:
        image_url = upload_image(file.file)
    except RuntimeError as exc:
        logger.exception("Failed to upload owner menu image")
        raise HTTPException(
            status_code=500,
            detail="Image upload failed"
        ) from exc

    return {
        "image_url": image_url
    }
