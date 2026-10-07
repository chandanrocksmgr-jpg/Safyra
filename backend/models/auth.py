from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: Literal["customer", "admin"]
    phone: str = ""
    created_at: datetime


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user: UserPublic


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class RecoveryQuestionResponse(BaseModel):
    question: str


class AdminRecoveryRequest(BaseModel):
    email: EmailStr
    answer: str = Field(min_length=2, max_length=120)
    new_password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=24)


class SavedCartItem(BaseModel):
    key: str
    productId: str
    slug: str = ""
    title: str
    imageUrl: str
    price: int
    compareAtPrice: Optional[int] = None
    setType: str = ""
    size: str
    color: str
    quantity: int = Field(ge=1, le=20)


class AccountStateUpdate(BaseModel):
    wishlist_ids: list[str] = Field(default_factory=list)
    cart: list[SavedCartItem] = Field(default_factory=list)


class OrderItem(BaseModel):
    product_name: str
    image_url: str
    set_type: str = ""
    size: str
    color: str
    quantity: int
    price: int


class TrackingStep(BaseModel):
    label: str
    completed: bool
    date: str = ""


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    placed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str
    total: int
    invoice_number: str
    is_demo: bool = False
    items: list[OrderItem] = Field(default_factory=list)
    tracking: list[TrackingStep] = Field(default_factory=list)


class AccountResponse(BaseModel):
    user: UserPublic
    wishlist_ids: list[str] = Field(default_factory=list)
    cart: list[SavedCartItem] = Field(default_factory=list)
    orders: list[Order] = Field(default_factory=list)