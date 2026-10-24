from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class StaffMember(BaseModel):
    id: str
    email: EmailStr
    name: str
    admin_role: Literal["super", "junior"]
    status: Literal["active", "deactivated"]
    created_at: datetime
    last_login_at: Optional[datetime] = None


class StaffCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str


class StaffUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    status: Optional[Literal["active", "deactivated"]] = None


class StaffPasswordReset(BaseModel):
    new_password: str
