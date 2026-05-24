from pydantic import BaseModel


class CreateMenuItemSchema(BaseModel):

    restaurant_id: str

    category_id: str

    name: str

    description: str | None = None

    price: float

    mrp_price: float | None = None

    image_url: str | None = None

    is_available: bool = True

    is_veg: bool = False

    is_special: bool = False

    display_order: int = 0


class UpdateMenuItemSchema(BaseModel):

    name: str | None = None

    description: str | None = None

    price: float | None = None

    mrp_price: float | None = None

    image_url: str | None = None

    is_available: bool | None = None

    is_veg: bool | None = None

    is_special: bool | None = None

    display_order: int | None = None