from pydantic import BaseModel, Field


class CreateCategorySchema(BaseModel):

    restaurant_id: str

    name: str = Field(min_length=1, max_length=80)

    display_order: int = 0

    icon_emoji: str | None = Field(default=None, max_length=16)


class OwnerCreateCategorySchema(BaseModel):

    name: str = Field(min_length=1, max_length=80)

    display_order: int = 0

    icon_emoji: str | None = Field(default=None, max_length=16)


class UpdateCategorySchema(BaseModel):

    name: str | None = Field(default=None, min_length=1, max_length=80)

    display_order: int | None = None

    icon_emoji: str | None = Field(default=None, max_length=16)
