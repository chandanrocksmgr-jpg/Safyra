from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from models.order_request import OrderRequestCreate


class PaymentQuoteRequest(OrderRequestCreate):
    use_store_credit: bool = False


class PaymentQuoteResponse(BaseModel):
    regular_subtotal: int
    discount_total: int
    subtotal: int
    shipping_amount: int
    total: int
    credit_applied: int = 0
    amount_due: int = 0
    store_credit_balance: int = 0
    currency: Literal["INR"] = "INR"


class PayUCheckoutResponse(PaymentQuoteResponse):
    action: str
    fields: dict[str, str]
    request_number: str
    transaction_id: str
    completed: bool = False  # True when SAFYRA Credit covered the whole total and no PayU step is needed


class PaymentStatusResponse(BaseModel):
    transaction_id: str
    request_number: str
    status: Literal["pending", "paid", "failed"]
    amount: int
    credit_applied: int = 0
    total: int = 0
    currency: Literal["INR"] = "INR"
    updated_at: datetime