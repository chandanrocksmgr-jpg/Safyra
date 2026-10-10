from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


PaymentStatus = Literal["Unpaid", "Payment pending", "Paid"]
FulfilmentStatus = Literal["Request received", "Confirmed", "Processing", "Ready to ship", "Shipped", "Delivered"]
RefundStatus = Literal["Not initiated", "Processing", "Refunded", "Failed"]
EmailDeliveryStatus = Literal["Not scheduled", "Scheduled", "Sending", "Sent", "Failed"]


class OrderRequestItemInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: str = Field(min_length=1, max_length=80)
    set_type: Optional[str] = Field(default=None, max_length=100)
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
    checkout_session_id: Optional[str] = Field(default=None, max_length=100)
    items: list[OrderRequestItemInput] = Field(min_length=1, max_length=40)


class OrderRequestResponse(BaseModel):
    request_number: str
    received_at: datetime


class OrderRequestStoredItem(BaseModel):
    product_id: str
    title: str
    image_url: str
    set_type: Optional[str] = None
    regular_price: int = 0
    price: int
    compare_at_price: Optional[int] = None
    discount_name: Optional[str] = None
    discount_amount: int = 0
    size: str
    color: str
    quantity: int
    line_total: int


class OrderHistoryEvent(BaseModel):
    id: str
    event: str
    message: str
    created_at: datetime
    admin_id: Optional[str] = None


class OrderRequestAdmin(BaseModel):
    id: str
    request_number: str
    received_at: datetime
    customer_id: Optional[str] = None
    name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    state_region: str
    postal_code: str
    country: str
    country_code: str
    shipping: Literal["india", "international"]
    note: str = ""
    items: list[OrderRequestStoredItem] = Field(default_factory=list)
    subtotal: int = 0
    regular_subtotal: int = 0
    discount_total: int = 0
    shipping_amount: Optional[int] = None
    tax_amount: Optional[int] = None
    total: Optional[int] = None
    record_type: Literal["Request", "Confirmed"] = "Request"
    payment_status: PaymentStatus = "Unpaid"
    payment_verified_at: Optional[datetime] = None
    payment_provider: Optional[str] = None
    payment_transaction_id: Optional[str] = None
    payu_payment_id: Optional[str] = None
    payment_gateway_status: Optional[str] = None
    payment_error: str = ""
    payment_created_at: Optional[datetime] = None
    inventory_reservation_status: Optional[str] = None
    fulfilment_status: FulfilmentStatus = "Request received"
    courier_name: str = ""
    shipping_details: str = ""
    tracking_number: str = ""
    tracking_link: str = ""
    internal_notes: str = ""
    cancelled: bool = False
    cancellation_reason: str = ""
    cancelled_at: Optional[datetime] = None
    refund_status: RefundStatus = "Not initiated"
    refund_reason: str = ""
    refund_amount: int = 0
    refund_reference: str = ""
    refund_confirmed_at: Optional[datetime] = None
    converted_order_id: Optional[str] = None
    request_received_email_status: EmailDeliveryStatus = "Not scheduled"
    request_received_email_sent_at: Optional[datetime] = None
    request_received_email_id: Optional[str] = None
    paid_email_status: EmailDeliveryStatus = "Not scheduled"
    paid_email_sent_at: Optional[datetime] = None
    paid_email_id: Optional[str] = None
    history: list[OrderHistoryEvent] = Field(default_factory=list)


class OrderRequestAdminUpdate(BaseModel):
    payment_status: Optional[PaymentStatus] = None
    payment_verified: bool = False
    fulfilment_status: Optional[FulfilmentStatus] = None
    shipping_verified: bool = False
    courier_name: Optional[str] = Field(default=None, max_length=120)
    shipping_details: Optional[str] = Field(default=None, max_length=1000)
    tracking_number: Optional[str] = Field(default=None, max_length=160)
    tracking_link: Optional[str] = Field(default=None, max_length=500)
    internal_notes: Optional[str] = Field(default=None, max_length=5000)
    refund_status: Optional[RefundStatus] = None
    refund_reason: Optional[str] = Field(default=None, max_length=1000)
    refund_amount: Optional[int] = Field(default=None, ge=0)
    refund_reference: Optional[str] = Field(default=None, max_length=200)
    refund_confirmed: bool = False

    @field_validator("tracking_link")
    @classmethod
    def valid_tracking_link(cls, value: Optional[str]) -> Optional[str]:
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Tracking link must begin with http:// or https://")
        return value


class OrderCancellationRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class OrderConversionResponse(BaseModel):
    order_id: str
    order_number: str
    converted_at: datetime


class OrderRequestList(BaseModel):
    items: list[OrderRequestAdmin]
    total: int
    page: int
    page_size: int