from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


CheckoutSessionStatus = Literal["In progress", "Abandoned", "Completed"]
ReminderStatus = Literal["Not scheduled", "Scheduled", "Sending", "Sent", "Failed"]


class CheckoutSessionItemInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: str = Field(min_length=1, max_length=80)
    set_type: Optional[str] = Field(default=None, max_length=100)
    size: str = Field(min_length=1, max_length=40)
    color: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=20)


class CheckoutSessionUpsert(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    session_key: str = Field(min_length=20, max_length=100)
    name: str = Field(min_length=2, max_length=80)
    email: Optional[EmailStr] = None
    phone: str = Field(default="", max_length=32)
    address: str = Field(default="", max_length=300)
    city: str = Field(default="", max_length=120)
    state_region: str = Field(default="", max_length=120)
    postal_code: str = Field(default="", max_length=24)
    country: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=2000)
    whatsapp_opt_in: bool = False
    marketing_email_opt_in: bool = False
    items: list[CheckoutSessionItemInput] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def require_contact(self):
        if not self.email and len("".join(char for char in self.phone if char.isdigit())) < 7:
            raise ValueError("A valid email address or mobile number is required")
        return self


class CheckoutSessionSummary(BaseModel):
    id: str
    checkout_number: str
    status: CheckoutSessionStatus
    last_activity_at: datetime


class CheckoutSessionStoredItem(BaseModel):
    product_id: str
    title: str
    image_url: str
    set_type: Optional[str] = None
    size: str
    color: str
    quantity: int
    regular_price: int
    price: int
    discount_name: Optional[str] = None
    line_total: int


class CheckoutActivity(BaseModel):
    event: str
    message: str
    created_at: datetime


class CheckoutSessionAdmin(BaseModel):
    id: str
    checkout_number: str
    session_key: str
    status: CheckoutSessionStatus
    name: str
    email: Optional[EmailStr] = None
    phone: str = ""
    address: str = ""
    city: str = ""
    state_region: str = ""
    postal_code: str = ""
    country: str = ""
    note: str = ""
    whatsapp_opt_in: bool = False
    marketing_email_opt_in: bool = False
    items: list[CheckoutSessionStoredItem] = Field(default_factory=list)
    regular_subtotal: int = 0
    subtotal: int = 0
    discount_total: int = 0
    reminder_status: ReminderStatus = "Not scheduled"
    reminder_sent_at: Optional[datetime] = None
    reminder_email_id: Optional[str] = None
    completed_order_request_id: Optional[str] = None
    completed_request_number: Optional[str] = None
    internal_notes: str = ""
    started_at: datetime
    last_activity_at: datetime
    activity: list[CheckoutActivity] = Field(default_factory=list)


class CheckoutSessionAdminUpdate(BaseModel):
    internal_notes: str = Field(max_length=5000)


class CheckoutSessionList(BaseModel):
    items: list[CheckoutSessionAdmin]
    total: int
    page: int
    page_size: int


class CronEnvelope(BaseModel):
    event: str
    schedule_id: Optional[str] = None
    run_id: Optional[str] = None
    dispatch_time: Optional[str] = None
    job_id: Optional[str] = None
    data: None = None