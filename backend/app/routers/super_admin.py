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
    get_categories,
    get_category_for_restaurant,
    create_menu_item,
    update_menu_item,
    delete_menu_item,
    get_all_restaurants,
    get_restaurant_by_id,
    get_menu_item_by_id,
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
        restaurant = create_restaurant(data)
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
        result = onboard_restaurant(data)
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
            data.is_open
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
        logger.info(f"Creating category: {data}")
        restaurant = get_restaurant_by_id(data.restaurant_id)
        if not restaurant:
            raise HTTPException(
                status_code=404,
                detail="Restaurant not found"
            )
        category = create_category(data)
        logger.info(f"Category created successfully: {category}")
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create category: {str(e)}"
        ) from e


@router.put("/categories/{category_id}")
def update_existing_category(
    category_id: str,
    data: UpdateCategorySchema,
    current_user=Depends(require_role("super"))
):

    return update_category(
        category_id,
        data
    )


@router.delete("/categories/{category_id}")
def delete_existing_category(
    category_id: str,
    current_user=Depends(require_role("super"))
):

    delete_category(category_id)

    return {
        "message": "Category deleted successfully"
    }


@router.post("/items")
def create_new_item(
    data: CreateMenuItemSchema,
    current_user=Depends(require_role("super"))
):

    try:
        logger.info(f"Creating menu item: {data}")
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
        item = create_menu_item(data)
        logger.info(f"Menu item created successfully: {item}")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create menu item: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create menu item: {str(e)}"
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
        data
    )

    return item


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    current_user=Depends(require_role("super"))
):

    delete_menu_item(item_id)

    return {
        "message": "Item deleted successfully"
    }


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("super"))
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
