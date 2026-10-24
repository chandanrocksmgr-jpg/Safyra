"""Variant-level inventory (Shopify-style): one row per combination (set type) × colour × size.

When a product has `variants`, they are the single source of truth for stock and optional price, for every
availability label (ready stock and made to order alike). Products without variants keep the legacy
size-level fields (`stock_by_size` / `stock`) untouched.
"""

import itertools
import logging
import uuid

from lib.db import get_db

logger = logging.getLogger(__name__)


def uses_variants(product: dict) -> bool:
    return bool(product.get("variants"))


def selected_set_type(product: dict, set_type: str | None) -> dict | None:
    if not set_type:
        return None
    return next((item for item in product.get("set_types", []) if item.get("id") == set_type or item.get("name") == set_type), None)


def find_variant(product: dict, set_type_id: str, size: str, color: str) -> dict | None:
    # A dimension the product does not use is stored as "" (carts send placeholders such as "As shown").
    size = size if product.get("sizes") else ""
    color = color if product.get("colors") else ""
    return next((
        item for item in product.get("variants", [])
        if item.get("set_type_id", "") == set_type_id and item.get("size", "") == size and item.get("color", "") == color
    ), None)


def is_sellable(variant: dict | None) -> bool:
    return bool(variant and variant.get("available", True) and int(variant.get("stock") or 0) > 0)


def all_variants_sold_out(product: dict) -> bool:
    return not any(is_sellable(item) for item in product.get("variants", []))


def variant_label(set_type: str | None, size: str | None, color: str | None) -> str:
    return " · ".join(part for part in [set_type or "", f"Size {size}" if size else "", color or ""] if part)


def variant_grid(product: dict) -> list[tuple[str, str, str]]:
    """Every (set_type_id, colour, size) the product offers; empty strings when a dimension is not used."""
    set_ids = [item["id"] for item in product.get("set_types", []) if item.get("id")] or [""]
    colors = product.get("colors") or [""]
    sizes = product.get("sizes") or [""]
    return list(itertools.product(set_ids, colors, sizes))


def align_variants(product: dict, variants: list[dict]) -> list[dict]:
    """Keep the variant table in step with the product's combinations, colours and sizes.

    Rows for removed options are dropped; new option combinations are added with 0 stock (never guessed).
    """
    by_key = {(item.get("set_type_id", ""), item.get("color", ""), item.get("size", "")): item for item in variants}
    aligned = []
    for set_id, color, size in variant_grid(product):
        existing = by_key.get((set_id, color, size))
        aligned.append({
            "id": (existing or {}).get("id") or str(uuid.uuid4()),
            "set_type_id": set_id, "color": color, "size": size,
            "price": (existing or {}).get("price"), "mrp": (existing or {}).get("mrp"),
            "stock": max(0, int((existing or {}).get("stock") or 0)),
            "available": bool((existing or {}).get("available", True)),
        })
    return aligned


def legacy_stock_summary(variants: list[dict]) -> tuple[int, dict[str, int]]:
    """Totals mirrored into `stock` / `stock_by_size` for admin lists and older readers."""
    by_size: dict[str, int] = {}
    for item in variants:
        if item.get("size") and item.get("available", True):
            by_size[item["size"]] = by_size.get(item["size"], 0) + max(0, int(item.get("stock") or 0))
    total = sum(max(0, int(item.get("stock") or 0)) for item in variants if item.get("available", True))
    return total, by_size


def default_variants(product: dict) -> list[dict]:
    """First-time rows for an existing product, carrying over its current size / override stock (no invented stock)."""
    stock_by_size = product.get("stock_by_size") or {}
    fallback = max(0, int(product.get("stock") or 0))
    overrides = product.get("variant_overrides") or []
    rows = []
    for set_id, color, size in variant_grid(product):
        override = next((item for item in overrides if item.get("set_type_id", "") == set_id and item.get("size", "") == size and item.get("color", "") == color), None)
        stock = override["stock"] if override and override.get("stock") is not None else stock_by_size.get(size, fallback)
        rows.append({
            "id": str(uuid.uuid4()), "set_type_id": set_id, "color": color, "size": size,
            "price": override.get("price") if override else None, "mrp": override.get("mrp") if override else None,
            "stock": max(0, int(stock or 0)), "available": True,
        })
    return rows


async def migrate_product_variants() -> None:
    """Idempotent: give every product without a variant table its colour × size rows once."""
    products = get_db().products
    migrated = 0
    async for product in products.find({"variants": {"$exists": False}}):
        rows = default_variants(product)
        result = await products.update_one({"id": product["id"], "variants": {"$exists": False}}, {"$set": {"variants": rows}})
        migrated += result.modified_count
    if migrated:
        logger.info("Created variant inventory tables for %d products", migrated)
