"""Gift offer API: public offer copy, signed-in eligibility, and Super Admin controls."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from lib.db import db
from lib.gift_offer import GIFT_CATEGORY, active_gift_product, get_gift_settings, gift_summary, has_previous_order
from lib.security import get_optional_user, require_super_admin
from models.gift_offer import GiftEligibility, GiftOfferPublic, GiftOfferSettings, GiftOfferUpdate, GiftProductSummary

router = APIRouter(prefix="/gift-offer", tags=["gift-offer"])


async def _public_payload() -> GiftOfferPublic:
    settings = await get_gift_settings()
    product = await active_gift_product(settings)
    return GiftOfferPublic(**settings, product=gift_summary(product) if product else None)


@router.get("", response_model=GiftOfferPublic)
async def read_gift_offer():
    return await _public_payload()


@router.get("/eligibility", response_model=GiftEligibility)
async def gift_eligibility(subtotal: int = Query(default=0, ge=0), user: dict | None = Depends(get_optional_user)):
    settings = await get_gift_settings()
    product = await active_gift_product(settings)
    threshold = int(settings.get("threshold") or 0)
    summary: GiftProductSummary | None = gift_summary(product) if product else None
    if not settings.get("enabled") or not product:
        return GiftEligibility(eligible=False, reason="The gift offer is not running right now.", threshold=threshold)
    if not user or user.get("role") != "customer":
        return GiftEligibility(eligible=False, reason="Sign in or create an account to claim the first-order gift.", threshold=threshold, product=summary)
    if await has_previous_order(str(user.get("email") or ""), user.get("id")):
        return GiftEligibility(eligible=False, reason="The gift is for your first SAFYRA order only.", threshold=threshold, product=summary)
    if subtotal < threshold:
        return GiftEligibility(eligible=False, reason=f"Add ₹{threshold - subtotal:,} more to receive your gift.", threshold=threshold, shortfall=threshold - subtotal, product=summary)
    return GiftEligibility(eligible=True, reason="Your first-order gift will be added at checkout.", threshold=threshold, product=summary)


@router.get("/settings", response_model=GiftOfferSettings)
async def read_gift_settings(_: dict = Depends(require_super_admin)):
    return GiftOfferSettings(**await get_gift_settings())


@router.put("/settings", response_model=GiftOfferSettings)
async def update_gift_settings(input: GiftOfferUpdate, _: dict = Depends(require_super_admin)):
    changes = input.model_dump(exclude_unset=True)
    merged = GiftOfferSettings(**{**await get_gift_settings(), **changes})
    if merged.product_id:
        # Only one gift can be active at a time, and it must be a product marked as a gift.
        product = await db.products.find_one({"id": merged.product_id, "is_gift": True})
        if not product:
            raise HTTPException(status_code=422, detail="Choose a product marked as a gift product")
    if merged.enabled and not merged.product_id:
        raise HTTPException(status_code=422, detail="Choose the active gift product before starting the offer")
    await db.site_content.update_one(
        {"id": "gift_offer"},
        {"$set": {**merged.model_dump(), "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"id": "gift_offer"}},
        upsert=True,
    )
    return merged


@router.get("/products", response_model=list[GiftProductSummary])
async def list_gift_products(_: dict = Depends(require_super_admin)):
    """Every product marked as a gift, so the admin can choose which one is active."""
    products = await db.products.find({"$or": [{"is_gift": True}, {"category": GIFT_CATEGORY}]}).sort("title", 1).to_list(200)
    return [gift_summary(product) for product in products]
