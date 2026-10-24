"""First-order gift offer: one admin-chosen gift product, added automatically to a qualifying first order."""

import logging

from lib.db import db
from models.gift_offer import GiftOfferSettings, GiftProductSummary

GIFT_CATEGORY = "Gift"


async def get_gift_settings() -> dict:
    document = await db.site_content.find_one({"id": "gift_offer"})
    if not document:
        return GiftOfferSettings().model_dump()
    document.pop("_id", None)
    document.pop("id", None)
    document.pop("updated_at", None)
    return GiftOfferSettings(**{**GiftOfferSettings().model_dump(), **document}).model_dump()


async def active_gift_product(settings: dict | None = None) -> dict | None:
    settings = settings or await get_gift_settings()
    if not settings.get("product_id"):
        return None
    product = await db.products.find_one({"id": settings["product_id"], "is_gift": True})
    if product:
        product.pop("_id", None)
    return product


def gift_summary(product: dict) -> GiftProductSummary:
    return GiftProductSummary(
        id=product["id"],
        title=product["title"],
        image_url=product.get("image_url") or (product.get("image_urls") or [""])[0],
        value=int(product.get("price") or 0),
    )


async def has_previous_order(email: str, customer_id: str | None) -> bool:
    """A shopper qualifies only on their very first order — any earlier request or order disqualifies them."""
    clauses: list[dict] = [{"email": email.lower()}]
    if customer_id:
        clauses.append({"customer_id": customer_id})
    existing = await db.order_requests.find_one({"$or": clauses, "cancelled": {"$ne": True}})
    return existing is not None


async def gift_item_for_order(email: str, customer_id: str | None, subtotal: int) -> dict | None:
    """Returns the free gift line to append, or None when the order does not qualify."""
    if not customer_id:  # registered customers only
        return None
    settings = await get_gift_settings()
    if not settings.get("enabled") or subtotal < int(settings.get("threshold") or 0):
        return None
    product = await active_gift_product(settings)
    if not product:
        return None
    if await has_previous_order(email, customer_id):
        return None
    logging.getLogger(__name__).info("First-order gift %s granted to %s", product["id"], email)
    return {
        "product_id": product["id"], "title": product["title"], "image_url": product.get("image_url", ""),
        "hsn_code": product.get("hsn_code") or "62114922", "set_type": "", "regular_price": 0, "price": 0,
        "compare_at_price": None, "discount_name": "First-order gift", "discount_id": None, "discount_amount": 0,
        "size": (product.get("sizes") or ["Free size"])[0], "color": (product.get("colors") or [""])[0],
        "quantity": 1, "line_total": 0, "is_gift": True,
    }
