from pydantic import BaseModel


class CreateRestaurantSchema(BaseModel):

    owner_id: str

    name: str

    slug: str

    city: str

    logo_url: str | None = None

    is_active: bool = True