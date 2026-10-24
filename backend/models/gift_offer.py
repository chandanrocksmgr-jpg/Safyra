from typing import Optional

from pydantic import BaseModel, Field


class GiftOfferSettings(BaseModel):
    """Admin-controlled first-order gift offer. Exactly one gift product can be active."""
    enabled: bool = False
    threshold: int = Field(default=5000, ge=0, le=1_000_000)
    product_id: str = ""
    headline: str = Field(default="A surprise gift on your first order", min_length=1, max_length=120)
    subtext: str = Field(default="Spend ₹5,000 or more on your first SAFYRA order and a handcrafted gift joins your parcel.", min_length=1, max_length=400)
    terms: str = Field(default="One gift product will get automatically added if the cart value is greater than or equal to ₹5,000. Valid on the first order of a registered customer only, one gift per customer, while the chosen gift lasts. The gift carries no cash value and cannot be exchanged or returned.", min_length=1, max_length=1200)


class GiftProductSummary(BaseModel):
    id: str
    title: str
    image_url: str
    value: int


class GiftOfferPublic(BaseModel):
    enabled: bool
    threshold: int
    headline: str
    subtext: str
    terms: str
    product: Optional[GiftProductSummary] = None


class GiftOfferUpdate(BaseModel):
    enabled: Optional[bool] = None
    threshold: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    product_id: Optional[str] = None
    headline: Optional[str] = Field(default=None, min_length=1, max_length=120)
    subtext: Optional[str] = Field(default=None, min_length=1, max_length=400)
    terms: Optional[str] = Field(default=None, min_length=1, max_length=1200)


class GiftEligibility(BaseModel):
    """Whether the signed-in shopper would receive the gift with the cart value they sent."""
    eligible: bool
    reason: str
    threshold: int
    shortfall: int = 0
    product: Optional[GiftProductSummary] = None
