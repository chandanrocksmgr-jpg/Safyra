from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: Literal["customer", "admin"]
    admin_role: Literal["super", "junior"] = "super"
    phone: str = ""
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None
    picture_url: str = ""
    auth_providers: list[str] = Field(default_factory=list)
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


class GoogleSessionExchange(BaseModel):
    session_id: str = Field(min_length=16, max_length=500)


class GoogleAuthResponse(AuthResponse):
    claimed_orders: int = 0


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
    setTypeId: str = ""
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
    invoice_id: Optional[str] = None
    invoice_number: str = ""
    invoice_status: str = "not_ready"
    courier_name: str = ""
    tracking_number: str = ""
    tracking_link: str = ""
    is_demo: bool = False
    items: list[OrderItem] = Field(default_factory=list)
    tracking: list[TrackingStep] = Field(default_factory=list)

    @field_validator("courier_name", "tracking_number", "tracking_link", "invoice_number", mode="before")
    @classmethod
    def _blank_when_missing(cls, value: object) -> object:
        # Order snapshots copied at confirmation store null until courier/tracking details are entered.
        return "" if value is None else value


class SavedAddressInput(BaseModel):
    label: str = Field(default="Home", min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=24)
    address: str = Field(min_length=5, max_length=300)
    city: str = Field(min_length=1, max_length=80)
    state_region: str = Field(default="", max_length=80)
    postal_code: str = Field(default="", max_length=20)
    country: str = Field(default="India", min_length=2, max_length=80)
    is_default: bool = False


class SavedAddress(SavedAddressInput):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AccountResponse(BaseModel):
    user: UserPublic
    wishlist_ids: list[str] = Field(default_factory=list)
    cart: list[SavedCartItem] = Field(default_factory=list)
    orders: list[Order] = Field(default_factory=list)
    addresses: list[SavedAddress] = Field(default_factory=list)