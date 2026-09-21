from datetime import datetime, timezone
from typing import Optional
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from lib.db import db
from lib.security import get_optional_user, require_admin
from models.product import DEFAULT_PRODUCTS, Product, ProductCreate, ProductUpdate

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


async def _ensure_catalog() -> None:
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([product.model_dump() for product in DEFAULT_PRODUCTS])


def _clean(document: dict) -> Product:
    document.pop("_id", None)
    return Product(**document)


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
    filters: dict = {} if user and user.get("role") == "admin" else {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}}
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
        filters["$and"] = token_groups
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
    return [_clean(document) for document in documents]


@router.get("/facets", response_model=ProductFacets)
async def product_facets():
    await _ensure_catalog()
    public_filter = {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}}
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
        filters["title"] = {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}
    document = await db.products.find_one(filters)
    if not document:
        raise HTTPException(status_code=404, detail="Product not found")
    return _clean(document)


@router.post("", response_model=Product, status_code=201)
async def create_product(input: ProductCreate, _: dict = Depends(require_admin)):
    product = Product(**input.model_dump())
    await db.products.insert_one(product.model_dump())
    return product


@router.patch("/{product_id}", response_model=Product)
async def update_product(product_id: str, input: ProductUpdate, _: dict = Depends(require_admin)):
    existing = await db.products.find_one({"id": product_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    changes = input.model_dump(exclude_none=True)
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.products.update_one({"id": product_id}, {"$set": changes})
    document = await db.products.find_one({"id": product_id})
    return _clean(document)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, _: dict = Depends(require_admin)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")