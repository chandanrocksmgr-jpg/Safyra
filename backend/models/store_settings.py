from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StoreSettingsUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    gstin: Optional[str] = Field(default=None, max_length=15)
    registered_address: Optional[str] = Field(default=None, max_length=500)
    seller_state: Optional[str] = Field(default=None, max_length=100)
    state_code: Optional[str] = Field(default=None, pattern=r"^$|^\d{2}$")
    gst_slab_threshold: Optional[int] = Field(default=None, gt=0)
    gst_rate_lower: Optional[float] = Field(default=None, gt=0, le=100)
    gst_rate_upper: Optional[float] = Field(default=None, gt=0, le=100)
    cotton_hsn_code: Optional[str] = Field(default=None, pattern=r"^\d{8}$")
    other_hsn_code: Optional[str] = Field(default=None, pattern=r"^\d{8}$")
    support_email: Optional[EmailStr] = None
    support_phone: Optional[str] = Field(default=None, max_length=32)
    authorised_signatory: Optional[str] = Field(default=None, max_length=120)
    invoice_prefix: Optional[str] = Field(default=None, pattern=r"^[A-Z0-9-]{2,20}$")
    credit_note_prefix: Optional[str] = Field(default=None, pattern=r"^[A-Z0-9-]{2,20}$")


class StoreSettings(BaseModel):
    id: str = "store"
    legal_name: str = "SAFYRA CHIKANKARI"
    gstin: str = ""
    registered_address: str = ""
    seller_state: str = ""
    state_code: str = ""
    gst_slab_threshold: int = 2500
    gst_rate_lower: float = 5
    gst_rate_upper: float = 18
    cotton_hsn_code: str = "62063090"
    other_hsn_code: str = "62114922"
    support_email: Optional[EmailStr] = None
    support_phone: str = ""
    authorised_signatory: str = ""
    invoice_prefix: str = "SAFYRA"
    invoice_next_number: int = 1
    credit_note_prefix: str = "CN-SAFYRA"
    credit_note_next_number: int = 1
    tax_inclusive: bool = True
    invoice_ready: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GenerateInvoicesResponse(BaseModel):
    generated: int
    blocked: int