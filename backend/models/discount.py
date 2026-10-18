from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiscountType = Literal["percentage", "fixed"]
DiscountStatus = Literal["draft", "scheduled", "active", "paused", "expired"]
PromotionType = Literal["automatic", "code"]


class DiscountFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    promotion_type: PromotionType = "code"
    code: Optional[str] = Field(default=None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: DiscountType
    value: int = Field(gt=0)
    minimum_subtotal: int = Field(default=0, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    product_ids: list[str] = Field(default_factory=list, max_length=500)
    collections: list[str] = Field(default_factory=list, max_length=100)
    starts_at: datetime
    ends_at: datetime
    status: DiscountStatus = "draft"

    @model_validator(mode="after")
    def validate_discount(self):
        if self.discount_type == "percentage" and self.value > 100:
            raise ValueError("Percentage discounts cannot exceed 100")
        if self.ends_at <= self.starts_at:
            raise ValueError("Discount end must be after its start")
        if not self.product_ids and not self.collections:
            raise ValueError("Select at least one product or collection")
        if self.promotion_type == "code" and not self.code:
            raise ValueError("A coupon code is required")
        if self.promotion_type == "automatic" and self.code:
            raise ValueError("Automatic offers cannot have a coupon code")
        return self


class DiscountCreate(DiscountFields):
    pass


class DiscountUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    promotion_type: Optional[PromotionType] = None
    code: Optional[str] = Field(default=None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: Optional[DiscountType] = None
    value: Optional[int] = Field(default=None, gt=0)
    minimum_subtotal: Optional[int] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    product_ids: Optional[list[str]] = Field(default=None, max_length=500)
    collections: Optional[list[str]] = Field(default=None, max_length=100)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    status: Optional[DiscountStatus] = None


class Discount(DiscountFields):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_status: DiscountStatus = "draft"
    affected_products: int = 0
    usage_count: int = 0