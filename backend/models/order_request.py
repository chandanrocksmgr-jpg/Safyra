from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrderRequestItemInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: str = Field(min_length=1, max_length=80)
    size: str = Field(min_length=1, max_length=40)
    color: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=20)


class OrderRequestCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=32)
    address: str = Field(min_length=5, max_length=300)
    city: str = Field(min_length=1, max_length=120)
    state_region: str = Field(min_length=1, max_length=120)
    postal_code: str = Field(min_length=1, max_length=24)
    country: str = Field(min_length=2, max_length=120)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    shipping: Literal["india", "international"]
    note: str = Field(default="", max_length=2000)
    items: list[OrderRequestItemInput] = Field(min_length=1, max_length=40)


class OrderRequestResponse(BaseModel):
    request_number: str
    received_at: datetime