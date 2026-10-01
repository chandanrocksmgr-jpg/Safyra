from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.security import get_optional_user, require_admin
from models.catalog_group import CatalogGroup, CatalogGroupCreate, CatalogGroupUpdate


router = APIRouter(prefix="/catalog-groups", tags=["catalog-groups"])


def _slugify(value: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))


def _clean(document: dict) -> CatalogGroup:
    document.pop("_id", None)
    return CatalogGroup(**document)


async def _ensure_groups() -> None:
    if await db.catalog_groups.count_documents({}) > 0:
        return
    products = await db.products.find({}).sort("created_at", 1).to_list(1000)
    groups: list[CatalogGroup] = []
    for group_type, field in (("category", "category"), ("collection", "collection")):
        seen: set[str] = set()
        for product in products:
            name = str(product.get(field, "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            groups.append(CatalogGroup(
                name=name,
                slug=_slugify(name),
                group_type=group_type,
                image_url=product.get("image_url", ""),
                status="active",
                sort_order=len(seen) * 10,
            ))
    if groups:
        await db.catalog_groups.insert_many([group.model_dump() for group in groups])


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