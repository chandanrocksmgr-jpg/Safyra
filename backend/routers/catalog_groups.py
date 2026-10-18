from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.security import get_optional_user, require_admin
from models.catalog_group import CatalogGroup, CatalogGroupCreate, CatalogGroupUpdate


router = APIRouter(prefix="/catalog-groups", tags=["catalog-groups"])

REQUIRED_CATEGORIES = [
    ("Anarkali Sets", "anarkali-sets", 10),
    ("Angrakha Suits", "angrakha-suits", 20),
    ("Straight Kurtis", "straight-kurtis", 30),
    ("Stitched Sets", "stitched-sets", 40),
    ("Sarees", "sarees", 50),
    ("Dupattas", "dupattas", 60),
    ("Chikankari Bottoms", "chikankari-bottoms", 70),
    ("Unstitched Sets", "unstitched-sets", 80),
]


def _slugify(value: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))


def _clean(document: dict) -> CatalogGroup:
    document.pop("_id", None)
    return CatalogGroup(**document)


async def _ensure_groups() -> None:
    products = await db.products.find({}).sort("created_at", 1).to_list(1000)
    category_documents = await db.catalog_groups.find({"group_type": "category"}).to_list(1000)
    existing_categories = {document["slug"]: document for document in category_documents}
    product_images = {product.get("category"): product.get("image_url", "") for product in products}
    for name, slug, sort_order in REQUIRED_CATEGORIES:
        existing = existing_categories.get(slug)
        if not existing:
            group = CatalogGroup(
                name=name, slug=slug, group_type="category", image_url=product_images.get(name, ""),
                status="active", sort_order=sort_order, show_on_home=bool(product_images.get(name)),
            )
            await db.catalog_groups.insert_one(group.model_dump())
        elif existing.get("name") != name or existing.get("status") != "active" or existing.get("sort_order") != sort_order:
            await db.catalog_groups.update_one(
                {"id": existing["id"]},
                {"$set": {"name": name, "status": "active", "sort_order": sort_order, "updated_at": datetime.now(timezone.utc)}},
            )
    existing_collection_slugs = {
        document["slug"] for document in await db.catalog_groups.find({"group_type": "collection"}).to_list(1000)
    }
    seen_collections: set[str] = set()
    for product in products:
        name = str(product.get("collection", "")).strip()
        slug = _slugify(name)
        if not name or slug in seen_collections or slug in existing_collection_slugs:
            continue
        seen_collections.add(slug)
        group = CatalogGroup(
            name=name, slug=slug, group_type="collection", image_url=product.get("image_url", ""),
            status="active", sort_order=(len(existing_collection_slugs) + len(seen_collections)) * 10,
        )
        await db.catalog_groups.insert_one(group.model_dump())


@router.get("", response_model=list[CatalogGroup])
async def list_catalog_groups(
    include_all: bool = Query(default=False),
    user: dict | None = Depends(get_optional_user),
):
    await _ensure_groups()
    is_admin = bool(user and user.get("role") == "admin")
    filters = {} if include_all and is_admin else {"status": "active"}
    documents = await db.catalog_groups.find(filters).sort([("sort_order", 1), ("name", 1)]).to_list(1000)
    return [_clean(document) for document in documents]


@router.post("", response_model=CatalogGroup, status_code=201)
async def create_catalog_group(input: CatalogGroupCreate, _: dict = Depends(require_admin)):
    group = CatalogGroup(**input.model_dump())
    try:
        await db.catalog_groups.insert_one(group.model_dump())
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="A group with this type and slug already exists") from exc
    return group


@router.patch("/{group_id}", response_model=CatalogGroup)
async def update_catalog_group(group_id: str, input: CatalogGroupUpdate, _: dict = Depends(require_admin)):
    if not await db.catalog_groups.find_one({"id": group_id}):
        raise HTTPException(status_code=404, detail="Catalog group not found")
    changes = input.model_dump(exclude_unset=True)
    changes["updated_at"] = datetime.now(timezone.utc)
    try:
        await db.catalog_groups.update_one({"id": group_id}, {"$set": changes})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="A group with this type and slug already exists") from exc
    document = await db.catalog_groups.find_one({"id": group_id})
    return _clean(document)


@router.delete("/{group_id}", status_code=204)
async def delete_catalog_group(group_id: str, _: dict = Depends(require_admin)):
    # Retained for backwards compatibility, but deletion is deliberately soft:
    # catalog relationships and merchandising data must never be destroyed here.
    result = await db.catalog_groups.update_one(
        {"id": group_id},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Catalog group not found")