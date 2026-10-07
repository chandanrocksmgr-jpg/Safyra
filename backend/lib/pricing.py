from datetime import datetime, timezone
from typing import Iterable

from lib.db import db


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def effective_discount_status(discount: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    saved = discount.get("status", "draft")
    if saved in {"draft", "paused"}:
        return saved
    start = _aware(discount["starts_at"])
    end = _aware(discount["ends_at"])
    if now >= end:
        return "expired"
    if now < start:
        return "scheduled"
    return "active"


def applies_to_product(discount: dict, product: dict) -> bool:
    return product.get("id") in discount.get("product_ids", []) or product.get("collection") in discount.get("collections", [])


def discount_amount(discount: dict, price: int) -> int:
    if discount.get("discount_type") == "percentage":
        return min(price, round(price * discount.get("value", 0) / 100))
    return min(price, discount.get("value", 0))


def best_discount(product: dict, discounts: Iterable[dict], price: int) -> dict | None:
    candidates = [discount for discount in discounts if effective_discount_status(discount) == "active" and applies_to_product(discount, product)]
    return max(candidates, key=lambda discount: discount_amount(discount, price), default=None)


async def active_discounts() -> list[dict]:
    now = datetime.now(timezone.utc)
    documents = await db.discounts.find({
        "status": {"$in": ["active", "scheduled"]},
        "starts_at": {"$lte": now},
        "ends_at": {"$gt": now},
    }).to_list(500)
    return documents


def resolve_product_selection(product: dict, set_type: str | None, size: str, color: str, discounts: Iterable[dict]) -> dict:
    regular_price = product.get("price", 0)
    compare_at = product.get("mrp")
    selected_set = None
    set_types = product.get("set_types", [])
    if set_types:
        selected_set = next((item for item in set_types if item.get("id") == set_type or item.get("name") == set_type), None)
        if not selected_set:
            raise ValueError("Select a valid set type")
        regular_price = selected_set["price"]
        compare_at = selected_set.get("mrp")
    override = next((item for item in product.get("variant_overrides", []) if
        (not selected_set or item.get("set_type_id") == selected_set.get("id")) and
        item.get("size", "") == size and item.get("color", "") == color), None)
    if override:
        regular_price = override.get("price") if override.get("price") is not None else regular_price
        compare_at = override.get("mrp") if override.get("mrp") is not None else compare_at
    discount = best_discount(product, discounts, regular_price)
    amount = discount_amount(discount, regular_price) if discount else 0
    price = max(0, regular_price - amount)
    if amount and (compare_at is None or compare_at < regular_price):
        compare_at = regular_price
    stock = override.get("stock") if override and override.get("stock") is not None else product.get("stock_by_size", {}).get(size, product.get("stock", 0))
    availability = override.get("availability") if override and override.get("availability") else product.get("availability", "")
    return {
        "set_type": selected_set.get("name") if selected_set else None,
        "regular_price": regular_price,
        "compare_at_price": compare_at,
        "price": price,
        "discount_amount": amount,
        "discount_name": discount.get("name") if discount else None,
        "discount": discount,
        "stock": max(0, stock),
        "availability": availability,
    }