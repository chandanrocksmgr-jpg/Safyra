from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


WaitlistStatus = Literal["Waiting", "Contacted", "Converted", "Closed"]


class WaitlistCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: str = Field(min_length=1, max_length=80)
    customer_name: str = Field(min_length=2, max_length=100)
    mobile: str = Field(min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    size: Optional[str] = Field(default=None, max_length=40)
    color: Optional[str] = Field(default=None, max_length=80)


class WaitlistSubmission(BaseModel):
    id: str
    product_title: str
    size: Optional[str] = None
    color: Optional[str] = None
    status: WaitlistStatus
    created_at: datetime


class WaitlistRequestAdmin(BaseModel):
    id: str
    product_id: str
    product_title: str
    product_slug: str
    product_image_url: str
    customer_name: str
    mobile: str
    email: Optional[EmailStr] = None
    size: Optional[str] = None
    color: Optional[str] = None
    status: WaitlistStatus
    admin_notes: str = ""
    created_at: datetime
    updated_at: datetime


class WaitlistAdminUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: Optional[WaitlistStatus] = None
    admin_notes: Optional[str] = Field(default=None, max_length=5000)