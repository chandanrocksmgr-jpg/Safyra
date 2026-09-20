from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from lib.db import db
from models.product import DEFAULT_PRODUCTS, Product, ProductCreate, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


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
    fabric: Optional[str] = Query(default=None),
    sort: str = Query(default="featured"),
):
    await _ensure_catalog()
    filters: dict = {}
    if q:
        filters["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"fabric": {"$regex": q, "$options": "i"}},
            {"craft": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filters["category"] = category
    if fabric:
        filters["fabric"] = fabric
    sort_map = {
        "price-low": [("price", 1)],
        "price-high": [("price", -1)],
        "newest": [("new_arrival", -1), ("created_at", -1)],
        "featured": [("featured", -1), ("created_at", -1)],
    }
    documents = await db.products.find(filters).sort(sort_map.get(sort, sort_map["featured"])).to_list(1000)
    return [_clean(document) for document in documents]


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str):
    await _ensure_catalog()
    document = await db.products.find_one({"id": product_id})
    if not document:
        raise HTTPException(status_code=404, detail="Product not found")
    return _clean(document)


@router.post("", response_model=Product, status_code=201)
async def create_product(input: ProductCreate):
    product = Product(**input.model_dump())
    await db.products.insert_one(product.model_dump())
    return product


@router.patch("/{product_id}", response_model=Product)
async def update_product(product_id: str, input: ProductUpdate):
    existing = await db.products.find_one({"id": product_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    changes = input.model_dump(exclude_none=True)
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.products.update_one({"id": product_id}, {"$set": changes})
    document = await db.products.find_one({"id": product_id})
    return _clean(document)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")