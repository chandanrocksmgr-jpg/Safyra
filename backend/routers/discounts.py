from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lib.db import db
from lib.pricing import discount_amount, effective_discount_status
from lib.security import require_admin
from models.discount import Discount, DiscountCreate, DiscountUpdate


router = APIRouter(prefix="/discounts", tags=["discounts"])


class DiscountPreviewItem(BaseModel):
    product_id: str
    title: str
    regular_price: int
    final_price: int


class DiscountPreview(BaseModel):
    items: list[DiscountPreviewItem]
    affected_products: int


async def _affected_count(document: dict) -> int:
    conditions: list[dict] = []
    if document.get("product_ids"):
        conditions.append({"id": {"$in": document["product_ids"]}})
    if document.get("collections"):
        conditions.append({"collection": {"$in": document["collections"]}})
    return await db.products.count_documents({"$or": conditions}) if conditions else 0


async def _response(document: dict) -> Discount:
    cleaned = dict(document)
    cleaned.pop("_id", None)
    cleaned["effective_status"] = effective_discount_status(cleaned)
    cleaned["affected_products"] = await _affected_count(cleaned)
    return Discount(**cleaned)


@router.get("", response_model=list[Discount])
async def list_discounts(_: dict = Depends(require_admin)):
    documents = await db.discounts.find({}).sort("created_at", -1).to_list(500)
    return [await _response(document) for document in documents]


@router.post("/preview", response_model=DiscountPreview)
async def preview_discount(input: DiscountCreate, _: dict = Depends(require_admin)):
    conditions: list[dict] = []
    if input.product_ids:
        conditions.append({"id": {"$in": input.product_ids}})
    if input.collections:
        conditions.append({"collection": {"$in": input.collections}})
    products = await db.products.find({"$or": conditions}).sort("title", 1).to_list(500)
    items = [DiscountPreviewItem(
        product_id=product["id"], title=product["title"], regular_price=product["price"],
        final_price=max(0, product["price"] - discount_amount(input.model_dump(), product["price"])),
    ) for product in products]
    return DiscountPreview(items=items, affected_products=len(items))


@router.post("", response_model=Discount, status_code=201)
async def create_discount(input: DiscountCreate, _: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    document = {**input.model_dump(), "id": __import__("uuid").uuid4().hex, "created_at": now, "updated_at": now}
    await db.discounts.insert_one(document)
    return await _response(document)


@router.patch("/{discount_id}", response_model=Discount)
async def update_discount(discount_id: str, input: DiscountUpdate, _: dict = Depends(require_admin)):
    existing = await db.discounts.find_one({"id": discount_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Discount not found")
    changes = input.model_dump(exclude_unset=True)
    merged = {**existing, **changes}
    DiscountCreate(**{key: merged[key] for key in DiscountCreate.model_fields})
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.discounts.update_one({"id": discount_id}, {"$set": changes})
    return await _response(await db.discounts.find_one({"id": discount_id}))