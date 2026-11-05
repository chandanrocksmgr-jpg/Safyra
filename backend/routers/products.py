from datetime import datetime, timezone
from typing import Optional
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.security import get_optional_user, require_admin
from models.product import DEFAULT_PRODUCTS, Product, ProductCreate, ProductUpdate
from lib.pricing import active_discounts, best_discount
from lib.colors import normalize_color_options
from lib.stitch_fields import stitch_fields
from lib.variants import align_variants, default_variants, legacy_stock_summary

router = APIRouter(prefix="/products", tags=["products"])


class ProductFacets(BaseModel):
    categories: list[str]
    collections: list[str]
    sizes: list[str]
    colors: list[str]
    fabrics: list[str]
    crafts: list[str]
    availabilities: list[str]
    price_min: int
    price_max: int
    has_best_sellers: bool


class ProductBulkUpdate(BaseModel):
    product_ids: list[str] = Field(min_length=1, max_length=200)
    status: Optional[str] = None
    price_mode: Optional[str] = None
    price_value: Optional[int] = Field(default=None, ge=0)
    include_set_types: bool = False
    include_variant_overrides: bool = False
    # Fills Care / Origin only where the product's existing value is blank; never overwrites a value already set.
    care_value: Optional[str] = Field(default=None, max_length=200)
    origin_value: Optional[str] = Field(default=None, max_length=120)


async def _ensure_catalog() -> None:
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([{**product.model_dump(), "variants": default_variants(product.model_dump())} for product in DEFAULT_PRODUCTS])


def _clean(document: dict, discounts: list[dict] | None = None) -> Product:
    cleaned = dict(document)
    cleaned.pop("_id", None)
    if discounts:
        discount = best_discount(cleaned, discounts, cleaned.get("price", 0))
        if discount:
            cleaned["active_discount"] = {key: discount[key] for key in ["id", "name", "discount_type", "value"]}
    return Product(**cleaned)


@router.get("", response_model=list[Product])
async def list_products(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    collection: Optional[str] = Query(default=None),
    fabric: Optional[str] = Query(default=None),
    size: Optional[str] = Query(default=None),
    color: Optional[str] = Query(default=None),
    craft: Optional[str] = Query(default=None),
    availability: Optional[str] = Query(default=None),
    new_arrival: Optional[bool] = Query(default=None),
    min_price: Optional[int] = Query(default=None, ge=0),
    max_price: Optional[int] = Query(default=None, ge=0),
    sort: str = Query(default="featured"),
    user: Optional[dict] = Depends(get_optional_user),
):
    await _ensure_catalog()
    is_admin = bool(user and user.get("role") == "admin")
    filters: dict = {} if is_admin else {"$and": [
        {"is_gift": {"$ne": True}},  # gift products never appear in the storefront catalogue
        {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}},
        {"$or": [{"status": "active"}, {"status": {"$exists": False}}]},
    ]}
    if q:
        synonyms = {"white": "white|ivory|vanilla", "kurta": "kurta|kurti|anarkali|angrakha", "chikan": "chikan|chikankari"}
        token_groups = []
        for token in q.split():
            pattern = synonyms.get(token.lower(), re.escape(token))
            token_groups.append({"$or": [
                {"title": {"$regex": pattern, "$options": "i"}},
                {"fabric": {"$regex": pattern, "$options": "i"}},
                {"craft": {"$regex": pattern, "$options": "i"}},
                {"category": {"$regex": pattern, "$options": "i"}},
                {"collection": {"$regex": pattern, "$options": "i"}},
                {"colors": {"$regex": pattern, "$options": "i"}},
                {"tags": {"$regex": pattern, "$options": "i"}},
                {"occasion": {"$regex": pattern, "$options": "i"}},
                {"style_keywords": {"$regex": pattern, "$options": "i"}},
            ]})
        filters.setdefault("$and", []).extend(token_groups)
    if category:
        filters["category"] = {"$in": category.split(",")}
    if collection:
        filters["collection"] = {"$in": collection.split(",")}
    if fabric:
        filters["fabric"] = {"$in": fabric.split(",")}
    if size:
        filters["sizes"] = {"$in": size.split(",")}
    if color:
        filters["colors"] = {"$in": color.split(",")}
    if craft:
        filters["craft"] = {"$in": craft.split(",")}
    if availability:
        filters["availability"] = {"$in": availability.split(",")}
    if new_arrival is not None:
        filters["new_arrival"] = new_arrival
    if min_price is not None or max_price is not None:
        filters["price"] = {}
        if min_price is not None:
            filters["price"]["$gte"] = min_price
        if max_price is not None:
            filters["price"]["$lte"] = max_price
    sort_map = {
        "price-low": [("price", 1)],
        "price-high": [("price", -1)],
        "newest": [("new_arrival", -1), ("created_at", -1)],
        "best-selling": [("best_seller", -1), ("created_at", -1)],
        "featured": [("featured", -1), ("created_at", -1)],
    }
    documents = await db.products.find(filters).sort(sort_map.get(sort, sort_map["featured"])).to_list(1000)
    discounts = [] if is_admin else await active_discounts()
    return [_clean(document, discounts) for document in documents]


@router.get("/facets", response_model=ProductFacets)
async def product_facets():
    await _ensure_catalog()
    public_filter = {"$and": [
        {"is_gift": {"$ne": True}},
        {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}},
        {"$or": [{"status": "active"}, {"status": {"$exists": False}}]},
    ]}
    documents = await db.products.find(public_filter).to_list(1000)
    values = lambda field: sorted({value for document in documents for value in (document.get(field) if isinstance(document.get(field), list) else [document.get(field)]) if value})
    prices = [document["price"] for document in documents if document.get("price") is not None]
    return ProductFacets(
        categories=values("category"),
        collections=values("collection"),
        sizes=values("sizes"),
        colors=values("colors"),
        fabrics=values("fabric"),
        crafts=values("craft"),
        availabilities=values("availability"),
        price_min=min(prices, default=0),
        price_max=max(prices, default=0),
        has_best_sellers=any(document.get("best_seller") for document in documents),
    )


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str, user: Optional[dict] = Depends(get_optional_user)):
    await _ensure_catalog()
    filters: dict = {"$or": [{"id": product_id}, {"slug": product_id}]}
    if not user or user.get("role") != "admin":
        filters["$and"] = [
            {"is_gift": {"$ne": True}},
            {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}},
            {"$or": [{"status": "active"}, {"status": {"$exists": False}}]},
        ]
    document = await db.products.find_one(filters)
    if not document:
        raise HTTPException(status_code=404, detail="Product not found")
    discounts = [] if user and user.get("role") == "admin" else await active_discounts()
    return _clean(document, discounts)


def _color_fields(product: dict) -> dict:
    """Keep `colors` (names) and `color_options` (swatch + assigned photos) in step with each other."""
    gallery = product.get("image_urls") or ([product["image_url"]] if product.get("image_url") else [])
    colors, options = normalize_color_options(product.get("colors") or [], product.get("color_options") or [], gallery)
    return {"colors": colors, "color_options": options}


PUBLISH_REQUIRES_PHOTO = "Add at least one product photo before setting status to Active."


@router.post("", response_model=Product, status_code=201)
async def create_product(input: ProductCreate, _: dict = Depends(require_admin)):
    document = Product(**input.model_dump()).model_dump()
    document.update(stitch_fields(document))
    document.update(_color_fields(document))
    if document.get("variants"):  # admin editor always sends the table; legacy API payloads keep size-level stock
        document.update(_variant_fields(document, document["variants"]))
    product = Product(**document)
    if product.status == "active" and not product.image_url.strip():
        raise HTTPException(status_code=422, detail=PUBLISH_REQUIRES_PHOTO)
    if product.status == "active" and product.price <= 0:
        raise HTTPException(status_code=422, detail="Set a price above ₹0 before setting status to Active.")
    existing_with_slug = await db.products.find_one({"slug": product.slug})
    if existing_with_slug:
        raise HTTPException(status_code=409, detail=f"That slug is already used by \"{existing_with_slug.get('title', 'another product')}\" — change the URL slug and try again")
    try:
        await db.products.insert_one(product.model_dump())
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="A product with this slug already exists") from exc
    return product


@router.patch("/{product_id}", response_model=Product)
async def update_product(product_id: str, input: ProductUpdate, _: dict = Depends(require_admin)):
    existing = await db.products.find_one({"id": product_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    changes = input.model_dump(exclude_unset=True)
    if changes.get("slug") and changes["slug"] != existing.get("slug"):
        slug_owner = await db.products.find_one({"slug": changes["slug"], "id": {"$ne": product_id}})
        if slug_owner:
            raise HTTPException(status_code=409, detail=f"That slug is already used by \"{slug_owner.get('title', 'another product')}\" — change the URL slug and try again")
    merged = {**existing, **changes}
    changes.update(stitch_fields(merged))
    merged.update(changes)
    if {"colors", "color_options", "image_urls", "image_url"} & changes.keys():
        changes.update(_color_fields(merged))
        merged.update(changes)
    if changes.get("variants") or ("variants" not in changes and existing.get("variants") and {"set_types", "sizes", "colors"} & changes.keys()):
        # Keep an existing variant table aligned when options change; never invent one for legacy size-stock updates.
        changes.update(_variant_fields(merged, merged.get("variants") or []))
    if merged.get("status") == "active" and not (merged.get("image_url") or "").strip():
        raise HTTPException(status_code=422, detail=PUBLISH_REQUIRES_PHOTO)
    if merged.get("status") == "active" and (merged.get("price") or 0) <= 0:
        raise HTTPException(status_code=422, detail="Set a price above ₹0 before setting status to Active.")
    changes["updated_at"] = datetime.now(timezone.utc)
    try:
        await db.products.update_one({"id": product_id}, {"$set": changes})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="A product with this slug already exists") from exc
    document = await db.products.find_one({"id": product_id})
    return _clean(document)


def _variant_fields(product: dict, variants: list[dict]) -> dict:
    """Align the variant table with the product's options and mirror totals into the legacy stock fields."""
    keys = [(item.get("set_type_id", ""), item.get("color", ""), item.get("size", "")) for item in variants]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="Each combination, colour and size can only appear once in the variant table")
    set_ids = [item.get("id") for item in product.get("set_types", [])]
    if len(set_ids) != len(set(set_ids)) or len({item.get("name", "").strip().casefold() for item in product.get("set_types", [])}) != len(set_ids):
        raise HTTPException(status_code=422, detail="Each combination needs a unique name")
    aligned = align_variants(product, variants)
    stock, stock_by_size = legacy_stock_summary(aligned)
    return {"variants": aligned, "stock": stock, "stock_by_size": stock_by_size}


@router.post("/bulk", response_model=list[Product])
async def bulk_update_products(input: ProductBulkUpdate, _: dict = Depends(require_admin)):
    documents = await db.products.find({"id": {"$in": input.product_ids}}).to_list(len(input.product_ids))
    if len(documents) != len(set(input.product_ids)):
        raise HTTPException(status_code=404, detail="One or more selected products were not found")
    if input.status and input.status not in {"active", "draft", "archived"}:
        raise HTTPException(status_code=422, detail="Invalid product status")
    if input.price_mode and input.price_mode not in {"set", "increase_percent", "decrease_percent"}:
        raise HTTPException(status_code=422, detail="Invalid price update mode")
    if not input.status and not input.price_mode and not input.care_value and not input.origin_value:
        raise HTTPException(status_code=422, detail="Choose a status, price update, or Care/Origin fill-in")

    def changed_price(value: int) -> int:
        if input.price_value is None:
            return value
        if input.price_mode == "set":
            return input.price_value
        multiplier = 1 + input.price_value / 100 if input.price_mode == "increase_percent" else 1 - input.price_value / 100
        return max(0, round(value * multiplier))

    now = datetime.now(timezone.utc)
    for document in documents:
        changes: dict = {"updated_at": now}
        if input.status:
            changes["status"] = input.status
        if input.price_mode:
            changes["price"] = changed_price(document["price"])
            if input.include_set_types:
                changes["set_types"] = [{**item, "price": changed_price(item["price"])} for item in document.get("set_types", [])]
            if input.include_variant_overrides:
                changes["variant_overrides"] = [{**item, **({"price": changed_price(item["price"])} if item.get("price") is not None else {})} for item in document.get("variant_overrides", [])]
                changes["variants"] = [{**item, **({"price": changed_price(item["price"])} if item.get("price") is not None else {})} for item in document.get("variants", [])]
        if input.care_value and not (document.get("care") or "").strip():
            changes["care"] = input.care_value
        if input.origin_value and not (document.get("origin") or "").strip():
            changes["origin"] = input.origin_value
        await db.products.update_one({"id": document["id"]}, {"$set": changes})
    updated = await db.products.find({"id": {"$in": input.product_ids}}).to_list(len(input.product_ids))
    return [_clean(document) for document in updated]


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, _: dict = Depends(require_admin)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")