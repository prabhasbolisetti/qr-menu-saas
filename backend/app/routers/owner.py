from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.middleware.auth_middleware import require_role
from app.schemas.category import CreateCategorySchema, UpdateCategorySchema
from app.schemas.menu_item import CreateMenuItemSchema, UpdateMenuItemSchema
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
)
from app.services.qr_service import build_qr_response


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
    data: CreateCategorySchema,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    data.restaurant_id = restaurant["id"]

    return create_owner_category(data)


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

    delete_owner_category(category_id)

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
    data: CreateMenuItemSchema,
    current_user=Depends(require_role("owner"))
):

    restaurant = _owner_restaurant(current_user)
    _assert_category_belongs_to_owner(
        restaurant["id"],
        data.category_id
    )
    data.restaurant_id = restaurant["id"]

    return create_owner_item(data)


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

    return update_owner_item(
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

    delete_owner_item(item_id)

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
        item_id,
        price
    )


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("owner"))
):

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Only image files allowed"
        )

    image_url = upload_image(file.file)

    return {
        "image_url": image_url
    }
