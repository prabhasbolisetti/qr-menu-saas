from pydantic import BaseModel, Field


class LoginSchema(BaseModel):

    email: str

    password: str = Field(min_length=6)


class CreateOwnerSchema(BaseModel):

    email: str

    password: str = Field(min_length=6)

    full_name: str | None = None
