from pydantic import BaseModel


class CreateCategorySchema(BaseModel):

    restaurant_id: str

    name: str

    display_order: int = 0

    icon_emoji: str | None = None