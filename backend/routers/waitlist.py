from datetime import datetime, timezone
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.security import require_admin
from models.waitlist import WaitlistAdminUpdate, WaitlistCreate, WaitlistRequestAdmin, WaitlistStatus, WaitlistSubmission


router = APIRouter(prefix="/waitlist", tags=["waitlist"])
ACTIVE_STATUSES = {"Waiting", "Contacted"}
PUBLIC_PRODUCT_FILTER = {
    "$and": [
        {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}},
        {"$or": [{"status": "active"}, {"status": {"$exists": False}}]},
    ]
}


def _normalise_mobile(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = f"91{digits[1:]}"
    elif len(digits) == 10:
        digits = f"91{digits}"
    if not 10 <= len(digits) <= 15:
        raise HTTPException(status_code=422, detail="Enter a valid mobile number with country code")
    return digits


def _normalise_email(value: str | None) -> str | None:
    return value.strip().casefold() if value else None


def _variant_key(value: str | None) -> str:
    return value.strip().casefold() if value else "-"


def _active_key(product_id: str, size_value: str | None, color_value: str | None, contact: str) -> str:
    return "|".join([product_id, _variant_key(size_value), _variant_key(color_value), contact])


def _is_genuinely_unavailable(product: dict) -> bool:
    if product.get("availability") == "Currently unavailable" or not product.get("sizes"):
        return True
    if product.get("availability", "").strip().casefold() == "made to order":
        return False
    sizes = product.get("sizes", [])
    size_stock = product.get("stock_by_size", {})
    fallback = max(0, product.get("stock", 0))
    return all(max(0, size_stock.get(size, fallback)) < 1 for size in sizes)


def _clean(document: dict) -> dict:
    cleaned = dict(document)
    cleaned.pop("_id", None)
    return cleaned


async def _find_request(request_id: str) -> dict:
    document = await db.waitlist_requests.find_one({"id": request_id})
    if not document:
        raise HTTPException(status_code=404, detail="Waitlist request not found")
    return _clean(document)


@router.post("", response_model=WaitlistSubmission, status_code=status.HTTP_201_CREATED)
async def create_waitlist_request(input: WaitlistCreate):
    product = await db.products.find_one({"id": input.product_id, **PUBLIC_PRODUCT_FILTER})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not _is_genuinely_unavailable(product):
        raise HTTPException(status_code=409, detail="This product is currently available to purchase")

    sizes = product.get("sizes", [])
    size_value = input.size.strip() if input.size else None
    if sizes:
        if not size_value:
            raise HTTPException(status_code=422, detail="Select a size for this stitched product")
        if size_value not in sizes:
            raise HTTPException(status_code=422, detail="Select a size configured for this product")
    elif size_value:
        raise HTTPException(status_code=422, detail="Size does not apply to this product")

    colors = product.get("colors", [])
    color_value = input.color.strip() if input.color else None
    if len(colors) > 1:
        if not color_value:
            raise HTTPException(status_code=422, detail="Select a colour for this product")
        if color_value not in colors:
            raise HTTPException(status_code=422, detail="Select a colour configured for this product")
    elif len(colors) == 1:
        color_value = colors[0]
    elif color_value:
        raise HTTPException(status_code=422, detail="Colour does not apply to this product")

    mobile_normalised = _normalise_mobile(input.mobile)
    email_normalised = _normalise_email(str(input.email) if input.email else None)
    contact_conditions: list[dict] = [{"mobile_normalised": mobile_normalised}]
    if email_normalised:
        contact_conditions.append({"email_normalised": email_normalised})
    duplicate = await db.waitlist_requests.find_one({
        "product_id": product["id"],
        "size_key": _variant_key(size_value),
        "color_key": _variant_key(color_value),
        "status": {"$in": list(ACTIVE_STATUSES)},
        "$or": contact_conditions,
    })
    if duplicate:
        raise HTTPException(status_code=409, detail="You already have an active waitlist request for this piece and selection")

    now = datetime.now(timezone.utc)
    document = {
        "id": str(uuid.uuid4()),
        "product_id": product["id"],
        "product_title": product["title"],
        "product_slug": product["slug"],
        "product_image_url": product.get("image_url", ""),
        "customer_name": input.customer_name,
        "mobile": input.mobile,
        "mobile_normalised": mobile_normalised,
        "email": str(input.email).casefold() if input.email else None,
        "email_normalised": email_normalised,
        "size": size_value,
        "size_key": _variant_key(size_value),
        "color": color_value,
        "color_key": _variant_key(color_value),
        "status": "Waiting",
        "admin_notes": "",
        "created_at": now,
        "updated_at": now,
        "active_mobile_key": _active_key(product["id"], size_value, color_value, mobile_normalised),
    }
    if email_normalised:
        document["active_email_key"] = _active_key(product["id"], size_value, color_value, email_normalised)
    try:
        await db.waitlist_requests.insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="You already have an active waitlist request for this piece and selection") from exc
    return WaitlistSubmission(**document)


@router.get("", response_model=list[WaitlistRequestAdmin])
async def list_waitlist_requests(
    q: str = Query(default="", max_length=160),
    status_filter: WaitlistStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    _: dict = Depends(require_admin),
):
    conditions: list[dict] = []
    if q.strip():
        pattern = re.escape(q.strip())
        conditions.append({"$or": [
            {"product_title": {"$regex": pattern, "$options": "i"}},
            {"customer_name": {"$regex": pattern, "$options": "i"}},
            {"mobile": {"$regex": pattern, "$options": "i"}},
            {"email": {"$regex": pattern, "$options": "i"}},
        ]})
    if status_filter:
        conditions.append({"status": status_filter})
    filters = {"$and": conditions} if conditions else {}
    documents = await db.waitlist_requests.find(filters).sort("created_at", -1).to_list(limit)
    return [WaitlistRequestAdmin(**_clean(document)) for document in documents]


@router.get("/{request_id}", response_model=WaitlistRequestAdmin)
async def get_waitlist_request(request_id: str, _: dict = Depends(require_admin)):
    return WaitlistRequestAdmin(**await _find_request(request_id))


@router.patch("/{request_id}", response_model=WaitlistRequestAdmin)
async def update_waitlist_request(request_id: str, input: WaitlistAdminUpdate, _: dict = Depends(require_admin)):
    existing = await _find_request(request_id)
    now = datetime.now(timezone.utc)
    set_changes: dict = {"updated_at": now}
    unset_changes: dict = {}
    if input.admin_notes is not None:
        set_changes["admin_notes"] = input.admin_notes
    if input.status is not None:
        set_changes["status"] = input.status
        if input.status in ACTIVE_STATUSES:
            set_changes["active_mobile_key"] = _active_key(existing["product_id"], existing.get("size"), existing.get("color"), existing["mobile_normalised"])
            if existing.get("email_normalised"):
                set_changes["active_email_key"] = _active_key(existing["product_id"], existing.get("size"), existing.get("color"), existing["email_normalised"])
        else:
            unset_changes = {"active_mobile_key": "", "active_email_key": ""}
    update: dict = {"$set": set_changes}
    if unset_changes:
        update["$unset"] = unset_changes
    try:
        await db.waitlist_requests.update_one({"id": request_id}, update)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Another active request already exists for this customer and selection") from exc
    return WaitlistRequestAdmin(**await _find_request(request_id))