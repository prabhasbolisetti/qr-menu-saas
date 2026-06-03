from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException
)
import logging

from app.middleware.auth_middleware import (
    require_role
)
from app.middleware.rate_limit import check_upload_rate_limit

logger = logging.getLogger(__name__)


def _database_error_detail(operation: str, exc: Exception):

    error_text = str(exc)

    return f"{operation} failed"


def _database_error_status(exc: Exception):

    error_text = str(exc)

    if "is_open" in error_text and "restaurants" in error_text:
        return 503

    return 500


from app.services.cloudinary_service import (
    upload_image
)

from app.services.qr_service import (
    build_qr_response
)

from app.services.menu_service import (
    get_all_items
)

from app.services.admin_service import (
    create_owner_account,
    create_restaurant,
    onboard_restaurant,
    create_category,
    update_category,
    delete_category,
    restore_category,
    get_categories,
    get_category_for_restaurant,
    get_category_by_id_including_deleted,
    create_menu_item,
    update_menu_item,
    delete_menu_item,
    restore_menu_item,
    get_all_restaurants,
    get_restaurant_by_id,
    get_menu_item_by_id,
    get_menu_item_by_id_including_deleted,
    update_restaurant_open_state
)

from app.schemas.restaurant import (
    CreateRestaurantSchema,
    OnboardRestaurantSchema,
    UpdateRestaurantOpenStateSchema
)

from app.schemas.category import (
    CreateCategorySchema,
    UpdateCategorySchema
)

from app.schemas.menu_item import (
    CreateMenuItemSchema,
    UpdateMenuItemSchema
)

from app.schemas.user import (
    CreateOwnerSchema
)
from app.utils.uploads import validate_image_upload

router = APIRouter(
    prefix="/super",
    tags=["Super Admin"]
)


@router.get("/")
def super_dashboard(
    current_user=Depends(require_role("super"))
):

    return {
        "message": "Super admin protected",
        "user": current_user
    }


@router.get("/restaurants")
def get_restaurants(
    current_user=Depends(require_role("super"))
):

    restaurants = get_all_restaurants()

    return restaurants


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(
    restaurant_id: str,
    current_user=Depends(require_role("super"))
):

    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    return restaurant


@router.get("/restaurants/{restaurant_id}/qr")
def get_restaurant_qr(
    restaurant_id: str,
    current_user=Depends(require_role("super"))
):

    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    return build_qr_response(restaurant)


@router.get("/restaurants/{restaurant_id}/categories")
def get_restaurant_categories(
    restaurant_id: str,
    current_user=Depends(require_role("super"))
):

    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    try:
        return get_categories(restaurant_id)
    except Exception as e:
        logger.error(
            "Failed to fetch categories restaurant_id=%s error=%s",
            restaurant_id,
            e,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch categories"
        ) from e


@router.get("/restaurants/{restaurant_id}/items")
def get_restaurant_items(
    restaurant_id: str,
    current_user=Depends(require_role("super"))
):

    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    try:
        return get_all_items(restaurant_id)
    except Exception as e:
        logger.error(
            "Failed to fetch items restaurant_id=%s error=%s",
            restaurant_id,
            e,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch menu items"
        ) from e


@router.post("/owners")
def create_owner(
    data: CreateOwnerSchema,
    current_user=Depends(require_role("super"))
):

    return create_owner_account(data)


@router.post("/restaurants")
def create_new_restaurant(
    data: CreateRestaurantSchema,
    current_user=Depends(require_role("super"))
):

    try:
        restaurant = create_restaurant(
            data,
            actor=current_user
        )
    except Exception as e:
        logger.error("Failed to create restaurant: %s", e, exc_info=True)
        raise HTTPException(
            status_code=_database_error_status(e),
            detail=_database_error_detail("Create restaurant", e)
        ) from e

    return restaurant


@router.post("/restaurants/onboard")
def onboard_new_restaurant(
    data: OnboardRestaurantSchema,
    current_user=Depends(require_role("super"))
):

    try:
        result = onboard_restaurant(
            data,
            actor=current_user
        )
    except Exception as e:
        logger.error("Failed to onboard restaurant: %s", e, exc_info=True)
        raise HTTPException(
            status_code=_database_error_status(e),
            detail=_database_error_detail("Onboard restaurant", e)
        ) from e

    result["qr"] = build_qr_response(result["restaurant"])

    return result


@router.patch("/restaurants/{restaurant_id}/open-state")
def update_restaurant_open_status(
    restaurant_id: str,
    data: UpdateRestaurantOpenStateSchema,
    current_user=Depends(require_role("super"))
):

    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )

    try:
        return update_restaurant_open_state(
            restaurant_id,
            data.is_open,
            actor=current_user
        )
    except Exception as e:
        logger.error(
            "Failed to update restaurant open status restaurant_id=%s error=%s",
            restaurant_id,
            e,
            exc_info=True
        )
        raise HTTPException(
            status_code=_database_error_status(e),
            detail=_database_error_detail("Update restaurant open state", e)
        ) from e


@router.post("/categories")
def create_new_category(
    data: CreateCategorySchema,
    current_user=Depends(require_role("super"))
):

    try:
        restaurant = get_restaurant_by_id(data.restaurant_id)
        if not restaurant:
            raise HTTPException(
                status_code=404,
                detail="Restaurant not found"
            )
        category = create_category(
            data,
            actor=current_user
        )
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create category")
        raise HTTPException(
            status_code=500,
            detail="Failed to create category"
        ) from e


@router.put("/categories/{category_id}")
def update_existing_category(
    category_id: str,
    data: UpdateCategorySchema,
    current_user=Depends(require_role("super"))
):

    return update_category(
        category_id,
        data,
        actor=current_user
    )


@router.delete("/categories/{category_id}")
def delete_existing_category(
    category_id: str,
    current_user=Depends(require_role("super"))
):

    delete_category(
        category_id,
        actor=current_user
    )

    return {
        "message": "Category deleted successfully"
    }


@router.post("/categories/{category_id}/restore")
def restore_existing_category(
    category_id: str,
    current_user=Depends(require_role("super"))
):

    category = get_category_by_id_including_deleted(category_id)

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    return restore_category(
        category_id,
        actor=current_user
    )


@router.post("/items")
def create_new_item(
    data: CreateMenuItemSchema,
    current_user=Depends(require_role("super"))
):

    try:
        restaurant = get_restaurant_by_id(data.restaurant_id)
        if not restaurant:
            raise HTTPException(
                status_code=404,
                detail="Restaurant not found"
            )
        category = get_category_for_restaurant(
            data.restaurant_id,
            data.category_id
        )
        if not category:
            raise HTTPException(
                status_code=400,
                detail="Category does not belong to restaurant"
            )
        item = create_menu_item(
            data,
            actor=current_user
        )
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create menu item")
        raise HTTPException(
            status_code=500,
            detail="Failed to create menu item"
        ) from e


@router.put("/items/{item_id}")
def update_item(
    item_id: str,
    data: UpdateMenuItemSchema,
    current_user=Depends(require_role("super"))
):

    existing_item = get_menu_item_by_id(item_id)

    if not existing_item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    if data.category_id:
        category = get_category_for_restaurant(
            existing_item["restaurant_id"],
            data.category_id
        )

        if not category:
            raise HTTPException(
                status_code=400,
                detail="Category does not belong to item restaurant"
            )

    item = update_menu_item(
        item_id,
        data,
        actor=current_user
    )

    return item


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    current_user=Depends(require_role("super"))
):

    delete_menu_item(
        item_id,
        actor=current_user
    )

    return {
        "message": "Item deleted successfully"
    }


@router.post("/items/{item_id}/restore")
def restore_item(
    item_id: str,
    current_user=Depends(require_role("super"))
):

    item = get_menu_item_by_id_including_deleted(item_id)

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    category = get_category_for_restaurant(
        item["restaurant_id"],
        item["category_id"]
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail="Item category is not active"
        )

    return restore_menu_item(
        item_id,
        actor=current_user
    )


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("super"))
):

    check_upload_rate_limit(current_user)
    validate_image_upload(file)

    try:
        image_url = upload_image(file.file)
    except RuntimeError as exc:
        logger.exception("Failed to upload super admin menu image")
        raise HTTPException(
            status_code=500,
            detail="Image upload failed"
        ) from exc

    return {
        "image_url": image_url
    }
