from datetime import datetime, timezone
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.invoice_service import generate_credit_note_for_order, generate_invoice_for_order
from lib.order_pricing import price_order_items
from lib.security import get_optional_user, require_admin
from models.order_request import (
    OrderCancellationRequest,
    OrderConversionResponse,
    OrderHistoryEvent,
    OrderRequestAdmin,
    OrderRequestAdminUpdate,
    OrderRequestCreate,
    OrderRequestResponse,
)
from routers.order_emails import send_fulfilment_email, send_order_email


router = APIRouter(prefix="/order-requests", tags=["order requests"])

FULFILMENT_STEPS = ["Request received", "Confirmed", "In production", "Quality check", "Shipped", "Delivered"]
PUBLIC_PRODUCT_FILTER = {"title": {"$not": {"$regex": "^(tscheck|test|debug|placeholder)", "$options": "i"}}}


def _history_event(event: str, message: str, admin_id: str | None = None, created_at: datetime | None = None) -> dict:
    return OrderHistoryEvent(
        id=str(uuid.uuid4()), event=event, message=message,
        created_at=created_at or datetime.now(timezone.utc), admin_id=admin_id,
    ).model_dump()


def _with_defaults(document: dict) -> dict:
    cleaned = dict(document)
    cleaned.pop("_id", None)
    cleaned.setdefault("payment_status", "Unpaid")
    cleaned.setdefault("payment_verified_at", None)
    cleaned.setdefault("payment_provider", None)
    cleaned.setdefault("payment_transaction_id", None)
    cleaned.setdefault("payu_payment_id", None)
    cleaned.setdefault("payment_gateway_status", None)
    cleaned.setdefault("payment_error", "")
    cleaned.setdefault("payment_created_at", None)
    cleaned.setdefault("inventory_reservation_status", None)
    cleaned.setdefault("regular_subtotal", cleaned.get("subtotal", 0))
    cleaned.setdefault("discount_total", 0)
    cleaned.setdefault("discount_code", None)
    cleaned.setdefault("discount_ids", [])
    cleaned.setdefault("shipping_amount", None)
    cleaned.setdefault("tax_amount", None)
    cleaned.setdefault("total", None)
    cleaned.setdefault("record_type", "Request")
    cleaned.setdefault("fulfilment_status", "Request received")
    cleaned["fulfilment_status"] = {"Processing": "In production", "Ready to ship": "Quality check"}.get(cleaned["fulfilment_status"], cleaned["fulfilment_status"])
    cleaned.setdefault("courier_name", "")
    cleaned.setdefault("shipping_details", "")
    cleaned.setdefault("tracking_number", "")
    cleaned.setdefault("tracking_link", "")
    cleaned.setdefault("internal_notes", "")
    cleaned.setdefault("cancelled", False)
    cleaned.setdefault("cancellation_reason", "")
    cleaned.setdefault("cancelled_at", None)
    cleaned.setdefault("refund_status", "Not initiated")
    cleaned.setdefault("refund_reason", "")
    cleaned.setdefault("refund_amount", 0)
    cleaned.setdefault("refund_reference", "")
    cleaned.setdefault("refund_confirmed_at", None)
    cleaned.setdefault("converted_order_id", None)
    cleaned.setdefault("request_received_email_status", "Not scheduled")
    cleaned.setdefault("request_received_email_sent_at", None)
    cleaned.setdefault("request_received_email_id", None)
    cleaned.setdefault("paid_email_status", "Not scheduled")
    cleaned.setdefault("paid_email_sent_at", None)
    cleaned.setdefault("paid_email_id", None)
    cleaned.setdefault("invoice_id", None)
    cleaned.setdefault("invoice_number", "")
    cleaned.setdefault("invoice_status", "not_ready")
    cleaned.setdefault("invoice_error", "")
    cleaned.setdefault("credit_note_id", None)
    cleaned.setdefault("credit_note_number", "")
    cleaned.setdefault("history", [_history_event("request_received", "Order request received.", created_at=cleaned["received_at"])])
    return cleaned


async def _find_request(request_id: str) -> dict:
    document = await db.order_requests.find_one({"$or": [{"id": request_id}, {"request_number": request_id}]})
    if not document:
        raise HTTPException(status_code=404, detail="Order request not found")
    return _with_defaults(document)


def _customer_order_snapshot(order: dict) -> dict:
    current_step = FULFILMENT_STEPS.index(order["fulfilment_status"])
    history = order.get("history", [])
    tracking = []
    for index, label in enumerate(FULFILMENT_STEPS[1:]):
        event = next((item for item in reversed(history) if label in item.get("message", "")), None)
        tracking.append({
            "label": "Order confirmed" if label == "Confirmed" else label,
            "completed": index + 1 <= current_step,
            "date": event["created_at"].strftime("%d %b %Y") if event and hasattr(event.get("created_at"), "strftime") else "",
        })
    return {
        "id": order["id"], "order_number": order["order_number"], "placed_at": order["converted_at"],
        "status": "Cancelled" if order.get("cancelled") else order["fulfilment_status"],
        "total": order.get("total") or order["subtotal"], "invoice_id": order.get("invoice_id"),
        "invoice_number": order.get("invoice_number", ""), "invoice_status": order.get("invoice_status", "not_ready"),
        "credit_note_id": order.get("credit_note_id"), "credit_note_number": order.get("credit_note_number", ""),
        "courier_name": order.get("courier_name", ""), "tracking_number": order.get("tracking_number", ""),
        "tracking_link": order.get("tracking_link", ""),
        "is_demo": False,
        "items": [{
            "product_name": item["title"], "image_url": item["image_url"], "size": item["size"],
            "color": item["color"], "quantity": item["quantity"], "price": item["price"],
        } for item in order["items"]],
        "tracking": tracking,
    }


async def _sync_customer_order(order: dict) -> None:
    if not order.get("customer_id"):
        return
    snapshot = _customer_order_snapshot(order)
    await db.users.update_one(
        {"id": order["customer_id"]},
        {"$pull": {"orders": {"id": order["id"]}}},
    )
    await db.users.update_one(
        {"id": order["customer_id"]},
        {"$push": {"orders": snapshot}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )


async def _sync_converted_order(request_document: dict) -> None:
    order_id = request_document.get("converted_order_id")
    if not order_id:
        return
    sync_fields = {key: request_document[key] for key in [
        "payment_status", "payment_verified_at", "fulfilment_status", "courier_name", "shipping_details",
        "tracking_number", "tracking_link", "internal_notes", "cancelled", "cancellation_reason",
        "cancelled_at", "refund_status", "refund_reason", "refund_amount", "refund_reference",
        "refund_confirmed_at", "history",
    ]}
    sync_fields["updated_at"] = datetime.now(timezone.utc)
    await db.orders.update_one({"id": order_id}, {"$set": sync_fields})
    order = await db.orders.find_one({"id": order_id})
    if order:
        order.pop("_id", None)
        await _sync_customer_order(order)


@router.post("", response_model=OrderRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_order_request(input: OrderRequestCreate, background_tasks: BackgroundTasks, user: dict | None = Depends(get_optional_user)):
    if input.country_code == "IN":
        raise HTTPException(status_code=422, detail="India orders must use secure PayU checkout")
    stored_items, regular_subtotal, subtotal, _ = await price_order_items(input.items, input.discount_code)

    received_at = datetime.now(timezone.utc)
    request_number = f"SAF-REQ-{received_at:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    document = input.model_dump(exclude={"items"})
    document.update({
        "id": str(uuid.uuid4()),
        "request_number": request_number,
        "received_at": received_at,
        "customer_id": user.get("id") if user and user.get("email_verified") and user.get("email") == str(input.email).lower() else None,
        "items": stored_items,
        "subtotal": subtotal,
        "regular_subtotal": regular_subtotal,
        "discount_total": regular_subtotal - subtotal,
        "discount_ids": list(dict.fromkeys(item["discount_id"] for item in stored_items if item.get("discount_id"))),
        "shipping_amount": None,
        "tax_amount": None,
        "total": None,
        "record_type": "Request",
        "payment_status": "Unpaid",
        "fulfilment_status": "Request received",
        "refund_status": "Not initiated",
        "request_received_email_status": "Scheduled",
        "request_received_email_sent_at": None,
        "request_received_email_id": None,
        "paid_email_status": "Not scheduled",
        "paid_email_sent_at": None,
        "paid_email_id": None,
        "cancelled": False,
        "history": [_history_event("request_received", "Order request received.", created_at=received_at)],
    })
    await db.order_requests.insert_one(document)
    if input.checkout_session_id:
        await db.checkout_sessions.update_one(
            {"$or": [{"id": input.checkout_session_id}, {"session_key": input.checkout_session_id}]},
            {
                "$set": {
                    "status": "Completed",
                    "completed_order_request_id": document["id"],
                    "completed_request_number": request_number,
                    "completed_at": received_at,
                    "updated_at": received_at,
                },
                "$push": {"activity": {
                    "event": "completed",
                    "message": f"Checkout completed as order request {request_number}.",
                    "created_at": received_at,
                }},
            },
        )
    background_tasks.add_task(send_order_email, document["id"], "request_received")
    return OrderRequestResponse(request_number=request_number, received_at=received_at)


@router.get("", response_model=list[OrderRequestAdmin])
async def list_order_requests(
    q: str = Query(default="", max_length=160),
    payment_status: str | None = Query(default=None),
    fulfilment_status: str | None = Query(default=None),
    cancelled: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    _: dict = Depends(require_admin),
):
    conditions: list[dict] = []
    if q.strip():
        pattern = re.escape(q.strip())
        conditions.append({"$or": [
            {"request_number": {"$regex": pattern, "$options": "i"}},
            {"name": {"$regex": pattern, "$options": "i"}},
            {"email": {"$regex": pattern, "$options": "i"}},
            {"phone": {"$regex": pattern, "$options": "i"}},
            {"tracking_number": {"$regex": pattern, "$options": "i"}},
            {"items.title": {"$regex": pattern, "$options": "i"}},
        ]})
    if payment_status:
        conditions.append({"$or": [{"payment_status": payment_status}, {"payment_status": {"$exists": False}}]} if payment_status == "Unpaid" else {"payment_status": payment_status})
    if fulfilment_status:
        conditions.append({"$or": [{"fulfilment_status": fulfilment_status}, {"fulfilment_status": {"$exists": False}}]} if fulfilment_status == "Request received" else {"fulfilment_status": fulfilment_status})
    if cancelled is not None:
        conditions.append({"cancelled": cancelled})
    filters = {"$and": conditions} if conditions else {}
    documents = await db.order_requests.find(filters).sort("received_at", -1).to_list(limit)
    return [OrderRequestAdmin(**_with_defaults(document)) for document in documents]


@router.get("/{request_id}", response_model=OrderRequestAdmin)
async def get_order_request(request_id: str, _: dict = Depends(require_admin)):
    return OrderRequestAdmin(**await _find_request(request_id))


@router.patch("/{request_id}", response_model=OrderRequestAdmin)
async def update_order_request(request_id: str, input: OrderRequestAdminUpdate, background_tasks: BackgroundTasks, admin: dict = Depends(require_admin)):
    existing = await _find_request(request_id)
    if existing["cancelled"]:
        raise HTTPException(status_code=409, detail="Cancelled orders cannot be updated")
    now = datetime.now(timezone.utc)
    changes: dict = {}
    events: list[dict] = []

    effective_payment = input.payment_status or existing["payment_status"]
    if input.payment_status and input.payment_status != existing["payment_status"]:
        if existing["payment_status"] == "Paid":
            raise HTTPException(status_code=409, detail="A verified paid status cannot be reversed")
        if input.payment_status == "Paid":
            if existing.get("payment_provider") == "PayU":
                raise HTTPException(status_code=409, detail="PayU payments can only be confirmed by a verified gateway response")
            if not input.payment_verified:
                raise HTTPException(status_code=422, detail="Explicit payment verification is required")
            changes["payment_verified_at"] = now
            changes["paid_email_status"] = "Scheduled"
        changes["payment_status"] = input.payment_status
        events.append(_history_event("payment_status", f"Payment status changed to {input.payment_status}.", admin["id"], now))

    if input.fulfilment_status and input.fulfilment_status != existing["fulfilment_status"]:
        if input.fulfilment_status != "Request received" and effective_payment != "Paid":
            raise HTTPException(status_code=409, detail="Payment must be verified before fulfilment can proceed")
        changes["fulfilment_status"] = input.fulfilment_status
        events.append(_history_event("fulfilment_status", f"Fulfilment status changed to {input.fulfilment_status}.", admin["id"], now))

    for field in ["courier_name", "shipping_details", "tracking_number", "tracking_link", "internal_notes"]:
        value = getattr(input, field)
        if value is not None and value != existing[field]:
            changes[field] = value.strip()
            events.append(_history_event(field, f"{field.replace('_', ' ').capitalize()} updated.", admin["id"], now))

    effective_refund_status = input.refund_status or existing["refund_status"]
    refund_reason = input.refund_reason if input.refund_reason is not None else existing["refund_reason"]
    refund_amount = input.refund_amount if input.refund_amount is not None else existing["refund_amount"]
    if input.refund_status and input.refund_status != existing["refund_status"]:
        if existing["refund_status"] == "Refunded":
            raise HTTPException(status_code=409, detail="A confirmed refund cannot be reversed")
        if effective_payment != "Paid":
            raise HTTPException(status_code=409, detail="Only paid orders can enter refund processing")
        if effective_refund_status != "Not initiated" and (not refund_reason.strip() or refund_amount <= 0):
            raise HTTPException(status_code=422, detail="Refund reason and amount are required")
        if effective_refund_status == "Refunded":
            if not input.refund_confirmed:
                raise HTTPException(status_code=422, detail="Gateway or payment confirmation is required before marking Refunded")
            changes["refund_confirmed_at"] = now
        changes["refund_status"] = effective_refund_status
        events.append(_history_event("refund_status", f"Refund status changed to {effective_refund_status}.", admin["id"], now))
    for field in ["refund_reason", "refund_amount", "refund_reference"]:
        value = getattr(input, field)
        if value is not None:
            changes[field] = value.strip() if isinstance(value, str) else value

    if not changes:
        return OrderRequestAdmin(**existing)
    update: dict = {"$set": changes}
    if events:
        update["$push"] = {"history": {"$each": events}}
    await db.order_requests.update_one({"id": existing["id"]}, update)
    updated = await _find_request(existing["id"])
    await _sync_converted_order(updated)
    if changes.get("paid_email_status") == "Scheduled":
        background_tasks.add_task(send_order_email, existing["id"], "payment_confirmed")
    if changes.get("fulfilment_status") in {"In production", "Quality check", "Shipped", "Delivered"}:
        background_tasks.add_task(send_fulfilment_email, existing["id"], changes["fulfilment_status"])
    if changes.get("refund_status") == "Refunded" and updated.get("converted_order_id"):
        await generate_credit_note_for_order(updated["converted_order_id"])
    return OrderRequestAdmin(**updated)


@router.post("/{request_id}/cancel", response_model=OrderRequestAdmin)
async def cancel_order_request(request_id: str, input: OrderCancellationRequest, admin: dict = Depends(require_admin)):
    existing = await _find_request(request_id)
    if existing["cancelled"]:
        return OrderRequestAdmin(**existing)
    if existing["fulfilment_status"] == "Delivered":
        raise HTTPException(status_code=409, detail="A delivered order cannot be cancelled")
    now = datetime.now(timezone.utc)
    event = _history_event("cancelled", "Order cancelled by SAFYRA. Reason recorded internally.", admin["id"], now)
    await db.order_requests.update_one(
        {"id": existing["id"]},
        {"$set": {"cancelled": True, "cancellation_reason": input.reason.strip(), "cancelled_at": now}, "$push": {"history": event}},
    )
    updated = await _find_request(existing["id"])
    await _sync_converted_order(updated)
    return OrderRequestAdmin(**updated)


async def _convert_request_document(request_document: dict, actor_id: str | None, message: str = "Order request converted to an order.") -> OrderConversionResponse:
    if request_document.get("converted_order_id"):
        order = await db.orders.find_one({"id": request_document["converted_order_id"]})
        if order:
            return OrderConversionResponse(order_id=order["id"], order_number=order["order_number"], converted_at=order["converted_at"])

    now = datetime.now(timezone.utc)
    order_id = str(uuid.uuid4())
    conversion_event = _history_event("converted", message, actor_id, now)
    copy_fields = [
        "request_number", "customer_id", "name", "email", "phone", "address", "city", "state_region",
        "postal_code", "country", "country_code", "shipping", "note", "items", "subtotal", "regular_subtotal",
        "discount_total", "discount_code", "discount_ids", "shipping_amount", "tax_amount", "total", "record_type", "payment_status",
        "payment_verified_at", "payment_provider", "payment_transaction_id", "payu_payment_id", "payment_gateway_status",
        "fulfilment_status", "courier_name", "shipping_details", "tracking_number", "tracking_link", "internal_notes",
        "cancelled", "cancellation_reason", "cancelled_at", "refund_status", "refund_reason", "refund_amount",
        "refund_reference", "refund_confirmed_at", "invoice_id", "invoice_number", "invoice_status", "invoice_error",
        "credit_note_id", "credit_note_number",
    ]
    order = {
        **{key: request_document.get(key) for key in copy_fields},
        "id": order_id, "order_number": request_document["request_number"], "source_request_id": request_document["id"],
        "converted_at": now, "updated_at": now, "history": [*request_document["history"], conversion_event],
    }
    try:
        await db.orders.insert_one(order)
    except DuplicateKeyError:
        order = await db.orders.find_one({"source_request_id": request_document["id"]})
        if not order:
            raise
        order_id = order["id"]
        now = order["converted_at"]
    await db.order_requests.update_one(
        {"id": request_document["id"]},
        {"$set": {"converted_order_id": order_id}, "$push": {"history": conversion_event}},
    )
    order = await db.orders.find_one({"id": order_id})
    if order:
        order.pop("_id", None)
        await _sync_customer_order(order)
        print(f"DEBUG_TSCHECK convert order={order['id']} payment_status={order.get('payment_status')!r}", flush=True)
        if order.get("payment_status") == "Paid":
            result = await generate_invoice_for_order(order["id"])
            print(f"DEBUG_TSCHECK generate_invoice_for_order result={result}", flush=True)
    return OrderConversionResponse(order_id=order_id, order_number=request_document["request_number"], converted_at=now)


@router.post("/{request_id}/convert", response_model=OrderConversionResponse)
async def convert_order_request(request_id: str, admin: dict = Depends(require_admin)):
    request_document = await _find_request(request_id)
    if request_document["cancelled"]:
        raise HTTPException(status_code=409, detail="Cancelled requests cannot be converted")
    if request_document["payment_status"] != "Paid" or request_document["fulfilment_status"] == "Request received":
        raise HTTPException(status_code=409, detail="Verify payment and confirm fulfilment before conversion")
    return await _convert_request_document(request_document, actor_id=admin["id"])