import os
from typing import Iterable

from fastapi import HTTPException

from lib.db import db
from lib.pricing import active_discounts, applies_to_product, discount_amount, resolve_product_selection


PUBLIC_PRODUCT_FILTER = {
    "$and": [
        {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}},
        {"$or": [{"status": "active"}, {"status": {"$exists": False}}]},
    ]
}


def india_shipping_amount(subtotal: int) -> int:
    threshold = int(os.environ.get("INDIA_FREE_SHIPPING_THRESHOLD", "1000"))
    fee = int(os.environ.get("INDIA_SHIPPING_FEE", "120"))
    return 0 if subtotal >= threshold else fee


def _inventory_plan(product: dict, set_type: str | None, size: str, color: str, quantity: int) -> dict:
    if product.get("availability", "").strip().lower() == "made to order":
        return {"product_id": product["id"], "source": "made_to_order", "quantity": 0}
    selected_set = next(
        (item for item in product.get("set_types", []) if item.get("id") == set_type or item.get("name") == set_type),
        None,
    )
    override = next(
        (
            item for item in product.get("variant_overrides", [])
            if (not selected_set or item.get("set_type_id") == selected_set.get("id"))
            and item.get("size", "") == size
            and item.get("color", "") == color
        ),
        None,
    )
    if override and override.get("stock") is not None:
        return {
            "product_id": product["id"], "source": "override", "quantity": quantity,
            "set_type_id": override.get("set_type_id", ""), "size": size, "color": color,
        }
    if size in product.get("stock_by_size", {}):
        return {"product_id": product["id"], "source": "size", "quantity": quantity, "size": size}
    return {"product_id": product["id"], "source": "global", "quantity": quantity}


async def price_order_items(items: Iterable, discount_code: str | None = None) -> tuple[list[dict], int, int, list[dict]]:
    items = list(items)
    product_ids = list(dict.fromkeys(item.product_id for item in items))
    products = await db.products.find({"$and": [{"id": {"$in": product_ids}}, PUBLIC_PRODUCT_FILTER]}).to_list(len(product_ids))
    product_map = {product["id"]: product for product in products}
    if len(product_map) != len(product_ids):
        raise HTTPException(status_code=422, detail="One or more products are no longer available")
    selections: list[tuple] = []
    regular_subtotal = 0
    for item in items:
        product = product_map[item.product_id]
        if product.get("sizes") and item.size not in product["sizes"]:
            raise HTTPException(status_code=422, detail=f"Invalid size for {product['title']}")
        if product.get("colors") and item.color not in product["colors"]:
            raise HTTPException(status_code=422, detail=f"Invalid colour for {product['title']}")
        try:
            pricing = resolve_product_selection(product, item.set_type, item.size, item.color, [])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{exc} for {product['title']}") from exc
        made_to_order = pricing["availability"].strip().lower() == "made to order"
        if pricing["availability"] == "Currently unavailable" or not product.get("sizes"):
            raise HTTPException(status_code=409, detail=f"{product['title']} is currently unavailable")
        if not made_to_order and pricing["stock"] < item.quantity:
            raise HTTPException(status_code=409, detail=f"Requested quantity is unavailable for {product['title']} in size {item.size}")
        regular_subtotal += pricing["regular_price"] * item.quantity
        selections.append((item, product, pricing))
    discounts = await active_discounts(discount_code, regular_subtotal)
    normalized_code = discount_code.strip().upper() if discount_code else None
    if normalized_code and not any(document.get("promotion_type") == "code" and document.get("code", "").upper() == normalized_code for document in discounts):
        raise HTTPException(status_code=422, detail="This offer code is invalid, inactive or not eligible for this bag")
    if discounts:
        scored = [(discount, sum(
            discount_amount(discount, pricing["regular_price"]) * item.quantity
            for item, product, pricing in selections if applies_to_product(discount, product)
        )) for discount in discounts]
        if normalized_code and not any(score > 0 and discount.get("code", "").upper() == normalized_code for discount, score in scored):
            raise HTTPException(status_code=422, detail="This offer code does not apply to the selected products")
        positive = [(discount, score) for discount, score in scored if score > 0]
        discounts = [max(positive, key=lambda pair: pair[1])[0]] if positive else []
    stored_items: list[dict] = []
    reservations: list[dict] = []
    subtotal = 0
    for item, product, _ in selections:
        pricing = resolve_product_selection(product, item.set_type, item.size, item.color, discounts)
        line_regular = pricing["regular_price"] * item.quantity
        line_total = pricing["price"] * item.quantity
        subtotal += line_total
        stored_items.append({
            "product_id": product["id"], "title": product["title"], "image_url": product.get("image_url", ""),
            "hsn_code": product.get("hsn_code") or ("62063090" if product.get("category") == "Straight Kurtis" and "cotton" in product.get("fabric", "").lower() else "62114922"),
            "set_type": pricing["set_type"], "regular_price": pricing["regular_price"], "price": pricing["price"],
            "compare_at_price": pricing["compare_at_price"], "discount_name": pricing["discount_name"],
            "discount_id": pricing["discount"].get("id") if pricing["discount"] else None,
            "discount_amount": line_regular - line_total, "size": item.size, "color": item.color,
            "quantity": item.quantity, "line_total": line_total,
        })
        reservations.append(_inventory_plan(product, item.set_type, item.size, item.color, item.quantity))
    return stored_items, regular_subtotal, subtotal, reservations


async def reserve_inventory(plans: list[dict]) -> list[dict]:
    reserved: list[dict] = []
    try:
        for plan in plans:
            if plan["source"] == "made_to_order" or plan["quantity"] == 0:
                continue
            quantity = plan["quantity"]
            if plan["source"] == "override":
                match = {
                    "set_type_id": plan["set_type_id"], "size": plan["size"],
                    "color": plan["color"], "stock": {"$gte": quantity},
                }
                result = await db.products.update_one(
                    {"id": plan["product_id"], "variant_overrides": {"$elemMatch": match}},
                    {"$inc": {"variant_overrides.$[variant].stock": -quantity}},
                    array_filters=[{
                        "variant.set_type_id": plan["set_type_id"], "variant.size": plan["size"],
                        "variant.color": plan["color"], "variant.stock": {"$gte": quantity},
                    }],
                )
            elif plan["source"] == "size":
                field = f"stock_by_size.{plan['size']}"
                result = await db.products.update_one(
                    {"id": plan["product_id"], field: {"$gte": quantity}}, {"$inc": {field: -quantity}},
                )
            else:
                result = await db.products.update_one(
                    {"id": plan["product_id"], "stock": {"$gte": quantity}}, {"$inc": {"stock": -quantity}},
                )
            if result.modified_count != 1:
                raise HTTPException(status_code=409, detail="A selected item just became unavailable. Please review your bag.")
            reserved.append(plan)
        return reserved
    except Exception:
        await release_inventory(reserved)
        raise


async def release_inventory(plans: list[dict]) -> None:
    for plan in plans:
        quantity = plan.get("quantity", 0)
        if not quantity:
            continue
        if plan["source"] == "override":
            await db.products.update_one(
                {"id": plan["product_id"]},
                {"$inc": {"variant_overrides.$[variant].stock": quantity}},
                array_filters=[{
                    "variant.set_type_id": plan["set_type_id"], "variant.size": plan["size"],
                    "variant.color": plan["color"],
                }],
            )
        elif plan["source"] == "size":
            await db.products.update_one({"id": plan["product_id"]}, {"$inc": {f"stock_by_size.{plan['size']}": quantity}})
        else:
            await db.products.update_one({"id": plan["product_id"]}, {"$inc": {"stock": quantity}})