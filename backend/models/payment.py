from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from models.order_request import OrderRequestCreate


class PaymentQuoteRequest(OrderRequestCreate):
    pass


class PaymentQuoteResponse(BaseModel):
    regular_subtotal: int
    discount_total: int
    subtotal: int
    shipping_amount: int
    total: int
    currency: Literal["INR"] = "INR"


class PayUCheckoutResponse(PaymentQuoteResponse):
    action: str
    fields: dict[str, str]
    request_number: str
    transaction_id: str


class PaymentStatusResponse(BaseModel):
    transaction_id: str
    request_number: str
    status: Literal["pending", "paid", "failed"]
    amount: int
    currency: Literal["INR"] = "INR"
    updated_at: datetime