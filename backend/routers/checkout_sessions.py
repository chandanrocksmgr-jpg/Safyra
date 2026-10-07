from datetime import datetime, timedelta, timezone
from html import escape
import hmac
import logging
import os
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.email_service import EMAIL_FROM_NAME, send_email
from lib.pricing import active_discounts, resolve_product_selection
from lib.security import require_admin
from models.checkout_session import (
    CheckoutActivity,
    CheckoutSessionAdmin,
    CheckoutSessionAdminUpdate,
    CheckoutSessionList,
    CheckoutSessionSummary,
    CheckoutSessionUpsert,
    CronEnvelope,
)


router = APIRouter(tags=["checkout sessions"])
logger = logging.getLogger(__name__)
PUBLIC_PRODUCT_FILTER = {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}}
ABANDON_AFTER = timedelta(minutes=30)
REMIND_AFTER = timedelta(hours=2)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _activity(event: str, message: str, now: datetime | None = None) -> dict:
    return CheckoutActivity(event=event, message=message, created_at=now or datetime.now(timezone.utc)).model_dump()


def _clean(document: dict) -> dict:
    cleaned = dict(document)
    cleaned.pop("_id", None)
    cleaned.setdefault("reminder_status", "Not scheduled")
    cleaned.setdefault("reminder_sent_at", None)
    cleaned.setdefault("reminder_email_id", None)
    cleaned.setdefault("completed_order_request_id", None)
    cleaned.setdefault("completed_request_number", None)
    cleaned.setdefault("internal_notes", "")
    cleaned.setdefault("marketing_email_opt_in", False)
    cleaned.setdefault("whatsapp_opt_in", False)
    cleaned.setdefault("activity", [])
    return cleaned


async def _priced_items(items) -> tuple[list[dict], int, int]:
    product_ids = list(dict.fromkeys(item.product_id for item in items))
    products = await db.products.find({"$and": [{"id": {"$in": product_ids}}, PUBLIC_PRODUCT_FILTER]}).to_list(len(product_ids))
    product_map = {product["id"]: product for product in products}
    if len(product_map) != len(product_ids):
        raise HTTPException(status_code=422, detail="One or more products are no longer available")
    discounts = await active_discounts()
    stored, regular_subtotal, subtotal = [], 0, 0
    for item in items:
        product = product_map[item.product_id]
        if product.get("sizes") and item.size not in product["sizes"]:
            raise HTTPException(status_code=422, detail=f"Invalid size for {product['title']}")
        if product.get("colors") and item.color not in product["colors"]:
            raise HTTPException(status_code=422, detail=f"Invalid colour for {product['title']}")
        try:
            pricing = resolve_product_selection(product, item.set_type, item.size, item.color, discounts)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{exc} for {product['title']}") from exc
        line_regular = pricing["regular_price"] * item.quantity
        line_total = pricing["price"] * item.quantity
        regular_subtotal += line_regular
        subtotal += line_total
        stored.append({
            "product_id": product["id"], "title": product["title"], "image_url": product.get("image_url", ""),
            "set_type": pricing["set_type"], "size": item.size, "color": item.color, "quantity": item.quantity,
            "regular_price": pricing["regular_price"], "price": pricing["price"],
            "discount_name": pricing["discount_name"], "line_total": line_total,
        })
    return stored, regular_subtotal, subtotal


async def _mark_abandoned(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    result = await db.checkout_sessions.update_many(
        {"status": "In progress", "last_activity_at": {"$lte": now - ABANDON_AFTER}, "completed_order_request_id": None},
        {"$set": {"status": "Abandoned", "updated_at": now}, "$push": {"activity": _activity("abandoned", "Checkout became inactive for 30 minutes.", now)}},
    )
    return result.modified_count


@router.put("/checkout-sessions", response_model=CheckoutSessionSummary)
async def upsert_checkout_session(input: CheckoutSessionUpsert):
    stored_items, regular_subtotal, subtotal = await _priced_items(input.items)
    now = datetime.now(timezone.utc)
    existing = await db.checkout_sessions.find_one({"session_key": input.session_key})
    reminder_status = existing.get("reminder_status", "Not scheduled") if existing else "Not scheduled"
    if reminder_status not in {"Sent", "Failed", "Sending"}:
        reminder_status = "Scheduled" if input.email else "Not scheduled"
    values = input.model_dump(exclude={"items"})
    values.update({
        "items": stored_items, "regular_subtotal": regular_subtotal, "subtotal": subtotal,
        "discount_total": regular_subtotal - subtotal, "status": "In progress", "reminder_status": reminder_status,
        "last_activity_at": now, "updated_at": now,
    })
    if existing:
        await db.checkout_sessions.update_one({"id": existing["id"]}, {"$set": values, "$push": {"activity": _activity("updated", "Checkout details updated.", now)}})
        document = await db.checkout_sessions.find_one({"id": existing["id"]})
    else:
        document = {
            **values, "id": str(uuid.uuid4()), "checkout_number": f"SAF-CHK-{now:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            "started_at": now, "completed_order_request_id": None, "completed_request_number": None,
            "reminder_sent_at": None, "reminder_email_id": None, "internal_notes": "",
            "activity": [_activity("started", "Checkout started with valid contact details.", now)],
        }
        try:
            await db.checkout_sessions.insert_one(document)
        except DuplicateKeyError:
            document = await db.checkout_sessions.find_one({"session_key": input.session_key})
    return CheckoutSessionSummary(**_clean(document))


@router.get("/checkout-sessions", response_model=CheckoutSessionList)
async def list_checkout_sessions(
    q: str = Query(default="", max_length=160),
    checkout_status: str | None = Query(default=None, alias="status"),
    reminder_status: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: dict = Depends(require_admin),
):
    await _mark_abandoned()
    conditions: list[dict] = []
    if q.strip():
        pattern = re.escape(q.strip())
        conditions.append({"$or": [
            {"checkout_number": {"$regex": pattern, "$options": "i"}}, {"name": {"$regex": pattern, "$options": "i"}},
            {"email": {"$regex": pattern, "$options": "i"}}, {"phone": {"$regex": pattern, "$options": "i"}},
            {"items.title": {"$regex": pattern, "$options": "i"}},
        ]})
    if checkout_status:
        conditions.append({"status": checkout_status})
    if reminder_status:
        conditions.append({"reminder_status": reminder_status})
    filters = {"$and": conditions} if conditions else {}
    total = await db.checkout_sessions.count_documents(filters)
    direction = 1 if sort == "oldest" else -1
    documents = await db.checkout_sessions.find(filters).sort("last_activity_at", direction).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return CheckoutSessionList(items=[CheckoutSessionAdmin(**_clean(document)) for document in documents], total=total, page=page, page_size=page_size)


@router.get("/checkout-sessions/{session_id}", response_model=CheckoutSessionAdmin)
async def get_checkout_session(session_id: str, _: dict = Depends(require_admin)):
    await _mark_abandoned()
    document = await db.checkout_sessions.find_one({"id": session_id})
    if not document:
        raise HTTPException(status_code=404, detail="Checkout session not found")
    return CheckoutSessionAdmin(**_clean(document))


@router.patch("/checkout-sessions/{session_id}", response_model=CheckoutSessionAdmin)
async def update_checkout_session(session_id: str, input: CheckoutSessionAdminUpdate, _: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    document = await db.checkout_sessions.find_one_and_update(
        {"id": session_id},
        {"$set": {"internal_notes": input.internal_notes, "updated_at": now}, "$push": {"activity": _activity("admin_note", "Internal Admin note updated.", now)}},
        return_document=ReturnDocument.AFTER,
    )
    if not document:
        raise HTTPException(status_code=404, detail="Checkout session not found")
    return CheckoutSessionAdmin(**_clean(document))


def _recovery_html(session: dict) -> str:
    public_site = os.environ["PUBLIC_SITE_URL"].rstrip("/")
    item_rows = []
    for item in session["items"]:
        set_type = f" — {escape(item['set_type'])}" if item.get("set_type") else ""
        item_rows.append(f"<li>{escape(item['title'])}{set_type}</li>")
    items = "".join(item_rows)
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(session["name"])},</p><p>You left a SAFYRA checkout unfinished. Your selection is still available to review:</p>'
        f'<ul>{items}</ul><p><a href="{public_site}/checkout" style="display:inline-block;padding:12px 18px;background:#261c19;color:#fff;text-decoration:none">Return to your checkout</a></p>'
        f'<p style="font-size:12px;color:#715b52">Checkout reference {escape(session["checkout_number"])}. No payment was taken. This is the only automated reminder for this checkout.</p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )


async def process_checkout_recovery(run_id: str) -> None:
    now = datetime.now(timezone.utc)
    await _mark_abandoned(now)
    candidates = await db.checkout_sessions.find({
        "status": "Abandoned", "email": {"$ne": None}, "reminder_status": "Scheduled",
        "last_activity_at": {"$lte": now - REMIND_AFTER}, "completed_order_request_id": None,
    }).sort("last_activity_at", 1).limit(50).to_list(50)
    for candidate in candidates:
        claimed = await db.checkout_sessions.find_one_and_update(
            {"id": candidate["id"], "reminder_status": "Scheduled", "completed_order_request_id": None},
            {"$set": {"reminder_status": "Sending", "reminder_attempted_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            continue
        try:
            email_id = await send_email(to=str(claimed["email"]), subject="Your SAFYRA checkout is waiting", html=_recovery_html(claimed))
            await db.checkout_sessions.update_one({"id": claimed["id"]}, {
                "$set": {"reminder_status": "Sent", "reminder_sent_at": datetime.now(timezone.utc), "reminder_email_id": email_id},
                "$push": {"activity": _activity("reminder_sent", "One checkout recovery email was sent.")},
            })
        except Exception as exc:
            logger.error("Checkout recovery email failed for %s: %s", claimed["id"], exc)
            await db.checkout_sessions.update_one({"id": claimed["id"]}, {
                "$set": {"reminder_status": "Failed"},
                "$push": {"activity": _activity("reminder_failed", "The one permitted recovery email attempt failed.")},
            })
    await db.cron_runs.update_one({"run_id": run_id}, {"$set": {"completed_at": datetime.now(timezone.utc), "processed": len(candidates)}})


@router.post("/cron/checkout-recovery", status_code=status.HTTP_202_ACCEPTED)
async def checkout_recovery_cron(
    input: CronEnvelope,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
    x_webhook_id: str | None = Header(default=None),
):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    expected = os.environ["WEBHOOK_CRON_SECRET"]
    supplied = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid cron authorization")
    run_id = x_webhook_id or input.run_id
    if not run_id:
        raise HTTPException(status_code=400, detail="Cron run id is required")
    try:
        await db.cron_runs.insert_one({"run_id": run_id, "received_at": datetime.now(timezone.utc), "schedule_id": input.schedule_id})
    except DuplicateKeyError:
        return {"accepted": True, "duplicate": True}
    background_tasks.add_task(process_checkout_recovery, run_id)
    return {"accepted": True, "duplicate": False}