from pydantic import BaseModel, Field, model_validator


def _mrp_is_valid(price, mrp_price):

    return mrp_price is None or price is None or mrp_price >= price


class CreateMenuItemSchema(BaseModel):

    restaurant_id: str

    category_id: str

    name: str = Field(min_length=1, max_length=120)

    description: str | None = Field(default=None, max_length=500)

    price: float = Field(gt=0)

    mrp_price: float | None = Field(default=None, ge=0)

    image_url: str | None = None

    is_available: bool = True

    is_veg: bool = False

    is_special: bool = False

    is_bestseller: bool = False

    display_order: int = 0

    @model_validator(mode="after")
    def validate_mrp_price(self):

        if not _mrp_is_valid(self.price, self.mrp_price):
            raise ValueError("MRP price cannot be lower than selling price")

        return self


class OwnerCreateMenuItemSchema(BaseModel):

    category_id: str

    name: str = Field(min_length=1, max_length=120)

    description: str | None = Field(default=None, max_length=500)

    price: float = Field(gt=0)

    mrp_price: float | None = Field(default=None, ge=0)

    image_url: str | None = None

    is_available: bool = True

    is_veg: bool = False

    is_special: bool = False

    is_bestseller: bool = False

    display_order: int = 0

    @model_validator(mode="after")
    def validate_mrp_price(self):

        if not _mrp_is_valid(self.price, self.mrp_price):
            raise ValueError("MRP price cannot be lower than selling price")

        return self


class UpdateMenuItemSchema(BaseModel):

    category_id: str | None = None

    name: str | None = Field(default=None, min_length=1, max_length=120)

    description: str | None = Field(default=None, max_length=500)

    price: float | None = Field(default=None, gt=0)

    mrp_price: float | None = Field(default=None, ge=0)

    image_url: str | None = None

    is_available: bool | None = None

    is_veg: bool | None = None

    is_special: bool | None = None

    is_bestseller: bool | None = None

    display_order: int | None = None

    @model_validator(mode="after")
    def validate_mrp_price(self):

        if not _mrp_is_valid(self.price, self.mrp_price):
            raise ValueError("MRP price cannot be lower than selling price")

        return self
