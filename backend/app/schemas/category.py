from pydantic import BaseModel


class CreateCategorySchema(BaseModel):

    restaurant_id: str | None = None

    name: str

    display_order: int = 0

    icon_emoji: str | None = None


class UpdateCategorySchema(BaseModel):

    name: str | None = None

    display_order: int | None = None

    icon_emoji: str | None = None
