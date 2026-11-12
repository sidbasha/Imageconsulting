import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Language = Literal["en", "ar"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    preferred_language: Language = "en"
    # Eligibility facts (rows 2, 3). Optional here; the app asks for them at sign-up,
    # and customer features stay closed until they are given.
    date_of_birth: date | None = None
    gender: Literal["female", "male"] | None = None
    country_code: str | None = Field(default=None, pattern="^[A-Za-z]{2}$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    preferred_language: str
    role: str


class UserUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    preferred_language: Language | None = None
