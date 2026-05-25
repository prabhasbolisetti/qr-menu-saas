from pydantic import BaseModel, Field, field_validator


def _normalize_slug(value: str):

    if not isinstance(value, str):
        return value

    return value.strip().lower()


class CreateRestaurantSchema(BaseModel):

    owner_id: str

    name: str = Field(min_length=2, max_length=120)

    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    city: str = Field(min_length=2, max_length=80)

    logo_url: str | None = None

    is_active: bool = True

    is_open: bool = True

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value):

        return _normalize_slug(value)


class OnboardRestaurantSchema(BaseModel):

    owner_email: str

    owner_password: str = Field(min_length=8, max_length=128)

    owner_full_name: str | None = None

    name: str = Field(min_length=2, max_length=120)

    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    city: str = Field(min_length=2, max_length=80)

    logo_url: str | None = None

    is_active: bool = True

    is_open: bool = True

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value):

        return _normalize_slug(value)


class UpdateRestaurantOpenStateSchema(BaseModel):

    is_open: bool
