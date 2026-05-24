from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException
)

from app.middleware.auth_middleware import require_role

from app.services.cloudinary_service import upload_image

from app.services.admin_service import (
    create_restaurant,
    create_category,
    create_menu_item,
    update_menu_item,
    delete_menu_item
)

from app.schemas.restaurant import (
    CreateRestaurantSchema
)

from app.schemas.category import (
    CreateCategorySchema
)

from app.schemas.menu_item import (
    CreateMenuItemSchema,
    UpdateMenuItemSchema
)

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


@router.post("/upload/image")
def upload_menu_image(
    file: UploadFile = File(...),
    current_user=Depends(require_role("super"))
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


@router.post("/restaurants")
def create_new_restaurant(
    data: CreateRestaurantSchema,
    current_user=Depends(require_role("super"))
):

    restaurant = create_restaurant(data)

    return restaurant


@router.post("/categories")
def create_new_category(
    data: CreateCategorySchema,
    current_user=Depends(require_role("super"))
):

    category = create_category(data)

    return category


@router.post("/items")
def create_new_item(
    data: CreateMenuItemSchema,
    current_user=Depends(require_role("super"))
):

    item = create_menu_item(data)

    return item


@router.put("/items/{item_id}")
def update_item(
    item_id: str,
    data: UpdateMenuItemSchema,
    current_user=Depends(require_role("super"))
):

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