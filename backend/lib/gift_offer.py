"""First-order gift offer: one admin-chosen gift product, added automatically to a qualifying first order."""

import logging
from html import escape

from lib.dates import now_in_app_tz
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
        stock=int(product.get("stock") or 0),
    )


async def has_previous_order(email: str, customer_id: str | None) -> bool:
    """A shopper qualifies only on their very first order — any earlier request or order disqualifies them."""
    clauses: list[dict] = [{"email": email.lower()}]
    if customer_id:
        clauses.append({"customer_id": customer_id})
    existing = await db.order_requests.find_one({"$or": clauses, "cancelled": {"$ne": True}})
    return existing is not None


async def notify_low_gift_stock(product: dict, remaining: int, low_threshold: int) -> None:
    """Email the shop once a day when the live gift reaches its low-stock mark (or runs out)."""
    if remaining > low_threshold:
        return
    from lib.admin_alerts import alert_recipient
    from lib.email_service import send_email

    recipient = alert_recipient()
    if not recipient:
        return

    today = now_in_app_tz().date().isoformat()
    marker = await db.site_content.find_one({"id": "gift_offer"}, {"low_stock_alert_date": 1})
    if (marker or {}).get("low_stock_alert_date") == today and remaining > 0:
        return
    await db.site_content.update_one({"id": "gift_offer"}, {"$set": {"low_stock_alert_date": today}}, upsert=True)
    subject = f"SAFYRA gift stock: {product['title']} " + ("is out of stock" if remaining <= 0 else f"has {remaining} left")
    body = (
        '<div style="font-family:Georgia,serif;color:#2c1a14">'
        f'<h1 style="font-size:19px;margin:0 0 10px">{escape(product["title"])}</h1>'
        f'<p style="margin:0 0 6px">The first-order gift has <strong>{remaining}</strong> piece(s) left.</p>'
        + ('<p style="margin:0 0 6px">No further orders will receive a gift until you restock or choose another gift.</p>' if remaining <= 0
           else '<p style="margin:0 0 6px">Restock it, or switch the active gift, before the offer runs dry.</p>')
        + '<p style="margin:14px 0 0"><a href="https://safyra.co/admin/gift-offer">Open the gift offer</a></p></div>'
    )
    try:
        await send_email(to=recipient, subject=subject, html=body)
    except Exception as exc:  # an alert must never break a checkout
        logging.getLogger(__name__).error("Gift low-stock alert failed: %s", exc)


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
    # Claim one piece atomically so the offer can never promise more gifts than exist.
    claimed = await db.products.update_one({"id": product["id"], "is_gift": True, "stock": {"$gte": 1}}, {"$inc": {"stock": -1}})
    if not claimed.modified_count:
        logging.getLogger(__name__).warning("First-order gift %s is out of stock", product["id"])
        return None
    remaining = int(product.get("stock") or 0) - 1
    await notify_low_gift_stock(product, remaining, int(settings.get("low_stock_threshold") or 0))
    logging.getLogger(__name__).info("First-order gift %s granted to %s (%d left)", product["id"], email, remaining)
    return {
        "product_id": product["id"], "title": product["title"], "image_url": product.get("image_url", ""),
        "hsn_code": product.get("hsn_code") or "62114922", "set_type": "", "regular_price": 0, "price": 0,
        "compare_at_price": None, "discount_name": "First-order gift", "discount_id": None, "discount_amount": 0,
        "size": (product.get("sizes") or ["Free size"])[0], "color": (product.get("colors") or [""])[0],
        "quantity": 1, "line_total": 0, "is_gift": True,
    }
