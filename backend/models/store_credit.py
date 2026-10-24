from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class StoreCreditIssue(BaseModel):
    amount: int = Field(ge=1, le=1_000_000, description="Whole rupees")


class StoreCreditGrant(BaseModel):
    id: str
    amount: int
    remaining: int
    issued_at: datetime
    expires_at: datetime
    status: Literal["Active", "Used", "Expired"]


class StoreCreditActivity(BaseModel):
    id: str
    type: Literal["issued", "redeemed", "restored"]
    amount: int
    request_number: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class StoreCreditSummary(BaseModel):
    balance: int
    next_expiry: Optional[datetime] = None
    next_expiry_amount: int = 0
    grants: list[StoreCreditGrant] = Field(default_factory=list)
    activity: list[StoreCreditActivity] = Field(default_factory=list)


class AdminCustomerRow(BaseModel):
    id: str
    name: str
    email: str
    phone: str = ""
    created_at: Optional[datetime] = None
    credit_balance: int = 0


class AdminCustomerOrder(BaseModel):
    request_number: str
    total: int
    credit_applied: int = 0
    payment_status: str
    fulfilment_status: str = ""
    created_at: Optional[datetime] = None


class AdminCustomerDetail(AdminCustomerRow):
    credits: StoreCreditSummary
    orders: list[AdminCustomerOrder] = Field(default_factory=list)
