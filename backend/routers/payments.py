from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import logging
import os
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.invoice_service import generate_invoice_for_order
from lib.store_credit import credit_balance, hold_credit, restore_credit
from lib.order_pricing import india_shipping_amount, price_order_items, release_inventory, reserve_inventory
from lib.security import get_optional_user
from models.checkout_session import CronEnvelope
from models.payment import PaymentQuoteRequest, PaymentQuoteResponse, PaymentStatusResponse, PayUCheckoutResponse
from lib.admin_alerts import notify_admin_new_order
from routers.order_emails import send_order_email
from routers.order_requests import _convert_request_document, _history_event


router = APIRouter(tags=["payments"])
logger = logging.getLogger(__name__)
PAYU_KEY = os.environ["PAYU_KEY"]
PAYU_SALT = os.environ["PAYU_SALT"]
PAYU_PAYMENT_URL = os.environ.get("PAYU_PAYMENT_URL", "https://secure.payu.in/_payment")
PAYU_VERIFY_URL = os.environ.get("PAYU_VERIFY_URL", "https://info.payu.in/merchant/postservice.php?form=2")
CALLBACK_BASE_FALLBACK = os.environ["PUBLIC_SITE_URL"].rstrip("/")


def _sha512(value: str) -> str:
    return hashlib.sha512(value.encode("utf-8")).hexdigest()


def _request_hash(fields: dict[str, str]) -> str:
    names = ["key", "txnid", "amount", "productinfo", "firstname", "email", "udf1", "udf2", "udf3", "udf4", "udf5"]
    return _sha512("|".join([*(fields.get(name, "") for name in names), "", "", "", "", "", PAYU_SALT]))


def _response_hash(payload: dict[str, str]) -> str:
    values = [
        PAYU_SALT, payload.get("status", ""), "", "", "", "", "",
        payload.get("udf5", ""), payload.get("udf4", ""), payload.get("udf3", ""),
        payload.get("udf2", ""), payload.get("udf1", ""), payload.get("email", ""),
        payload.get("firstname", ""), payload.get("productinfo", ""), payload.get("amount", ""),
        payload.get("txnid", ""), payload.get("key", ""),
    ]
    additional = payload.get("additionalCharges") or payload.get("additional_charges")
    if additional:
        values.insert(0, additional)
    return _sha512("|".join(values))


def _money(value: int) -> str:
    return f"{value:.2f}"


def _request_base(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    host = forwarded_host or request.url.netloc
    hostname = host.split(":", 1)[0].lower()
    allowed = hostname in {"safyra.co", "www.safyra.co", "localhost"} or hostname.endswith((".emergent.host", ".preview.emergentagent.com"))
    if not allowed:
        raise HTTPException(status_code=400, detail="Unrecognised checkout host")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    if hostname != "localhost":
        scheme = "https"
    return f"{scheme}://{host}".rstrip("/")


def _fields(document: dict) -> dict[str, str]:
    callback_base = document.get("payment_callback_base") or CALLBACK_BASE_FALLBACK
    fields = {
        "key": PAYU_KEY,
        "txnid": document["payment_transaction_id"],
        "amount": _money(_amount_due(document)),
        "productinfo": document["payu_productinfo"],
        "firstname": document["name"],
        "email": str(document["email"]),
        "phone": document["phone"],
        "surl": f"{callback_base}/api/payu/success",
        "furl": f"{callback_base}/api/payu/failure",
        "udf1": document["id"], "udf2": "", "udf3": "", "udf4": "", "udf5": "",
        "address1": document["address"], "city": document["city"], "state": document["state_region"],
        "country": document["country"], "zipcode": document["postal_code"],
    }
    fields["hash"] = _request_hash(fields)
    return fields


def _amount_due(document: dict) -> int:
    """What PayU must collect: the order total minus any SAFYRA Credit applied (older requests have no credit)."""
    return int(document.get("amount_due", document["total"]))


def _quote(document: dict) -> PaymentQuoteResponse:
    return PaymentQuoteResponse(
        regular_subtotal=document["regular_subtotal"], discount_total=document["discount_total"],
        subtotal=document["subtotal"], shipping_amount=document["shipping_amount"], total=document["total"],
        credit_applied=document.get("credit_applied", 0), amount_due=_amount_due(document),
    )


def _credit_customer(user: dict | None) -> dict | None:
    return user if user and user.get("role") == "customer" else None


async def _priced_quote(input: PaymentQuoteRequest, user: dict | None = None) -> tuple[list[dict], list[dict], PaymentQuoteResponse]:
    if input.country_code != "IN" or input.shipping != "india":
        raise HTTPException(status_code=422, detail="PayU checkout is currently available for India delivery only")
    items, regular_subtotal, subtotal, plans = await price_order_items(input.items, input.discount_code)
    shipping_amount = india_shipping_amount(subtotal)
    quote = PaymentQuoteResponse(
        regular_subtotal=regular_subtotal, discount_total=regular_subtotal - subtotal,
        subtotal=subtotal, shipping_amount=shipping_amount, total=subtotal + shipping_amount,
    )
    if quote.total <= 0:
        raise HTTPException(status_code=422, detail="The payable total must be greater than zero")
    customer = _credit_customer(user)
    balance = await credit_balance(customer["id"]) if customer else 0
    # SAFYRA Credit is a payment method: it covers the full total (products, GST and shipping) and never changes tax.
    applied = min(balance, quote.total) if input.use_store_credit else 0
    quote.store_credit_balance = balance
    quote.credit_applied = applied
    quote.amount_due = quote.total - applied
    return items, plans, quote


@router.post("/payments/quote", response_model=PaymentQuoteResponse)
async def quote_payment(input: PaymentQuoteRequest, request: Request):
    _, _, quote = await _priced_quote(input, await get_optional_user(request))
    return quote


@router.post("/payments/create", response_model=PayUCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(input: PaymentQuoteRequest, background_tasks: BackgroundTasks, request: Request):
    user = await get_optional_user(request)
    payment_callback_base = _request_base(request)
    existing = None
    if input.checkout_session_id:
        existing = await db.order_requests.find_one({
            "checkout_session_id": input.checkout_session_id, "payment_provider": "PayU",
            "payment_status": "Payment pending",
        })
    if existing and (existing.get("credit_applied") or input.use_store_credit):
        # Never reuse a pending attempt when credit is involved: release its stock and credit, then start fresh.
        await _mark_failed(existing, "superseded", "Replaced by a new checkout attempt")
        existing = None
    if existing:
        return PayUCheckoutResponse(
            **_quote(existing).model_dump(), action=PAYU_PAYMENT_URL, fields=_fields(existing),
            request_number=existing["request_number"], transaction_id=existing["payment_transaction_id"],
        )
    customer = _credit_customer(user)
    stored_items, plans, quote = await _priced_quote(input, user)
    reservations = await reserve_inventory(plans)
    now = datetime.now(timezone.utc)
    request_number = f"SAF-REQ-{now:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    transaction_id = f"SAF{uuid.uuid4().hex[:20].upper()}"
    credit_allocations: list[dict] = []
    if quote.credit_applied:
        try:
            credit_allocations = await hold_credit(customer["id"], quote.credit_applied, request_number)
        except ValueError as exc:
            await release_inventory(reservations)
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    paid_by_credit = quote.credit_applied > 0 and quote.amount_due == 0
    document = input.model_dump(exclude={"items"})
    document.update({
        "id": str(uuid.uuid4()), "request_number": request_number, "received_at": now,
        # Orders paid partly with credit always belong to the signed-in customer whose credit was used.
        "customer_id": customer["id"] if credit_allocations else user.get("id") if user and user.get("email_verified") and user.get("email") == str(input.email).lower() else None, "items": stored_items,
        **quote.model_dump(exclude={"store_credit_balance", "use_store_credit"}), "record_type": "Request", "payment_status": "Payment pending",
        "credit_allocations": credit_allocations, "credit_status": "held" if credit_allocations else "none",
        "payment_provider": "SAFYRA Credit" if paid_by_credit else "PayU", "payment_transaction_id": transaction_id, "payu_payment_id": None,
        "payment_gateway_status": "initiated", "payment_error": "", "payment_created_at": now,
        "payment_verified_at": None, "payu_productinfo": f"SAFYRA order {request_number}",
        "payment_callback_base": payment_callback_base,
        "inventory_reservations": reservations,
        "discount_ids": list(dict.fromkeys(item["discount_id"] for item in stored_items if item.get("discount_id"))),
        "inventory_reservation_status": "reserved" if reservations else "not_required",
        "fulfilment_status": "Request received", "refund_status": "Not initiated", "cancelled": False,
        "request_received_email_status": "Not scheduled" if paid_by_credit else "Scheduled", "request_received_email_sent_at": None,
        "request_received_email_id": None, "paid_email_status": "Not scheduled",
        "paid_email_sent_at": None, "paid_email_id": None, "converted_order_id": None,
        "history": [_history_event("payment_initiated", f"SAFYRA Credit of ₹{quote.credit_applied:,} applied to the full order total." if paid_by_credit else "Secure PayU payment initiated." + (f" SAFYRA Credit of ₹{quote.credit_applied:,} held." if credit_allocations else ""), created_at=now)],
        "updated_at": now,
    })
    try:
        await db.order_requests.insert_one(document)
    except Exception:
        await release_inventory(reservations)
        if credit_allocations:
            await restore_credit(customer["id"], credit_allocations, request_number)
        raise
    if input.checkout_session_id:
        await db.checkout_sessions.update_one(
            {"$or": [{"id": input.checkout_session_id}, {"session_key": input.checkout_session_id}]},
            {"$set": {
                "status": "Completed", "completed_order_request_id": document["id"],
                "completed_request_number": request_number, "completed_at": now, "updated_at": now,
                "reminder_status": "Not scheduled",
            }, "$push": {"activity": {
                "event": "payment_initiated", "message": f"{'Paid with SAFYRA Credit' if paid_by_credit else 'PayU payment initiated'} for {request_number}.", "created_at": now,
            }}},
        )
    if paid_by_credit:
        await _mark_paid(document, "store_credit", None)
        background_tasks.add_task(send_order_email, document["id"], "payment_confirmed")
        background_tasks.add_task(notify_admin_new_order, document["id"])
        return PayUCheckoutResponse(**quote.model_dump(), action="", fields={}, request_number=request_number, transaction_id=transaction_id, completed=True)
    background_tasks.add_task(send_order_email, document["id"], "request_received")
    return PayUCheckoutResponse(
        **quote.model_dump(), action=PAYU_PAYMENT_URL, fields=_fields(document),
        request_number=request_number, transaction_id=transaction_id,
    )


async def _validated_document(payload: dict[str, str]) -> dict:
    supplied_hash = payload.get("hash", "").lower()
    if not supplied_hash or not hmac.compare_digest(_response_hash(payload).lower(), supplied_hash):
        raise HTTPException(status_code=400, detail="Invalid PayU response hash")
    if payload.get("key") != PAYU_KEY:
        raise HTTPException(status_code=400, detail="Invalid PayU merchant key")
    document = await db.order_requests.find_one({"payment_transaction_id": payload.get("txnid")})
    if not document:
        raise HTTPException(status_code=404, detail="Payment transaction not found")
    try:
        received = Decimal(payload.get("amount", "")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail="Invalid PayU payment amount") from exc
    if received != Decimal(_amount_due(document)).quantize(Decimal("0.01")):
        raise HTTPException(status_code=400, detail="PayU payment amount mismatch")
    return document


async def _release_reservation(document: dict) -> None:
    claimed = await db.order_requests.find_one_and_update(
        {"id": document["id"], "inventory_reservation_status": "reserved"},
        {"$set": {"inventory_reservation_status": "releasing", "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        return
    try:
        await release_inventory(claimed.get("inventory_reservations", []))
        await db.order_requests.update_one(
            {"id": document["id"], "inventory_reservation_status": "releasing"},
            {"$set": {"inventory_reservation_status": "released", "updated_at": datetime.now(timezone.utc)}},
        )
    except Exception:
        await db.order_requests.update_one(
            {"id": document["id"], "inventory_reservation_status": "releasing"},
            {"$set": {"inventory_reservation_status": "reserved", "updated_at": datetime.now(timezone.utc)}},
        )
        raise


async def _mark_failed(document: dict, gateway_status: str, message: str) -> None:
    now = datetime.now(timezone.utc)
    updated = await db.order_requests.find_one_and_update(
        {"id": document["id"], "payment_status": {"$ne": "Paid"}},
        {"$set": {
            "payment_status": "Unpaid", "payment_gateway_status": gateway_status,
            "payment_error": message[:500], "updated_at": now,
        }, "$push": {"history": _history_event("payment_failed", "PayU payment was not completed.", created_at=now)}},
        return_document=ReturnDocument.AFTER,
    )
    if updated:
        await _release_reservation(updated)
        await _restore_held_credit(updated)


async def _restore_held_credit(document: dict) -> None:
    claimed = await db.order_requests.find_one_and_update(
        {"id": document["id"], "credit_status": "held"},
        {"$set": {"credit_status": "restored", "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if claimed:
        await restore_credit(claimed["customer_id"], claimed.get("credit_allocations", []), claimed["request_number"])


async def _mark_paid(document: dict, gateway_status: str, payu_id: str | None) -> bool:
    if document.get("inventory_reservation_status") == "released":
        try:
            reservations = await reserve_inventory(document.get("inventory_reservations", []))
            await db.order_requests.update_one(
                {"id": document["id"]},
                {"$set": {"inventory_reservations": reservations, "inventory_reservation_status": "reserved"}},
            )
            document["inventory_reservation_status"] = "reserved"
        except Exception as exc:
            logger.error("Inventory could not be re-reserved for paid transaction %s: %s", document["payment_transaction_id"], exc)
            document["inventory_reservation_status"] = "manual_review"
    now = datetime.now(timezone.utc)
    reservation_status = "committed" if document.get("inventory_reservation_status") == "reserved" else document.get("inventory_reservation_status", "not_required")
    updated = await db.order_requests.find_one_and_update(
        {"id": document["id"], "payment_status": {"$ne": "Paid"}},
        {"$set": {
            "record_type": "Confirmed", "payment_status": "Paid", "payment_verified_at": now,
            "payment_gateway_status": gateway_status, "payu_payment_id": payu_id,
            "payment_error": "", "fulfilment_status": "Confirmed", "paid_email_status": "Scheduled",
            "inventory_reservation_status": reservation_status, "updated_at": now,
            **({"credit_status": "redeemed"} if document.get("credit_status") == "held" else {}),
        }, "$push": {"history": {"$each": [
            _history_event("payment_verified", "Paid in full with SAFYRA Credit." if gateway_status == "store_credit" else "PayU payment verified server-side.", created_at=now),
            _history_event("fulfilment_status", "Fulfilment status changed to Confirmed.", created_at=now),
        ]}}},
        return_document=ReturnDocument.AFTER,
    )
    current = updated or await db.order_requests.find_one({"id": document["id"]})
    if updated and current and current.get("customer_id"):
        await _remove_purchased_from_saved_bag(current)
    if current and current.get("payment_status") == "Paid":
        conversion = await _convert_request_document(current, actor_id=None, message="PayU-confirmed order created automatically.")
        await generate_invoice_for_order(conversion.order_id)
        if updated and current.get("discount_ids"):
            await db.discounts.update_many({"id": {"$in": current["discount_ids"]}}, {"$inc": {"usage_count": 1}})
    return bool(updated)


async def _remove_purchased_from_saved_bag(order: dict) -> None:
    """Drop the ordered lines from the customer's saved bag so no page can restore them after payment."""
    user = await db.users.find_one({"id": order["customer_id"]}, {"cart": 1})
    if not user or not user.get("cart"):
        return
    bought = {(item["product_id"], item.get("size", ""), item.get("color", "")) for item in order.get("items", [])}
    remaining = [line for line in user["cart"] if (line.get("productId"), line.get("size", ""), line.get("color", "")) not in bought]
    if len(remaining) != len(user["cart"]):
        await db.users.update_one({"id": order["customer_id"]}, {"$set": {"cart": remaining, "updated_at": datetime.now(timezone.utc)}})


async def reconcile_transaction(transaction_id: str) -> None:
    document = await db.order_requests.find_one({"payment_transaction_id": transaction_id})
    if not document or document.get("payment_status") == "Paid":
        return
    command = "verify_payment"
    verification_hash = _sha512(f"{PAYU_KEY}|{command}|{transaction_id}|{PAYU_SALT}")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(PAYU_VERIFY_URL, data={
            "key": PAYU_KEY, "command": command, "hash": verification_hash, "var1": transaction_id,
        })
    response.raise_for_status()
    payload = response.json()
    detail = payload.get("transaction_details", {}).get(transaction_id)
    if not detail:
        created = document.get("payment_created_at", document["received_at"])
        created = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created >= timedelta(minutes=30):
            await _mark_failed(document, "expired", "Payment session expired without a completed PayU transaction")
        return
    gateway_status = str(detail.get("status") or detail.get("unmappedstatus") or "").lower()
    amount = detail.get("amt") or detail.get("amount")
    if amount is not None and Decimal(str(amount)).quantize(Decimal("0.01")) != Decimal(_amount_due(document)).quantize(Decimal("0.01")):
        logger.error("PayU verify amount mismatch for %s", transaction_id)
        return
    if gateway_status == "success":
        became_paid = await _mark_paid(document, gateway_status, str(detail.get("mihpayid") or "") or None)
        if became_paid:
            await send_order_email(document["id"], "payment_confirmed")
            await notify_admin_new_order(document["id"])
    elif gateway_status in {"failure", "failed", "cancelled", "canceled"}:
        await _mark_failed(document, gateway_status, str(detail.get("error_Message") or detail.get("error") or "Payment failed"))
    else:
        await db.order_requests.update_one(
            {"id": document["id"], "payment_status": "Payment pending"},
            {"$set": {"payment_gateway_status": gateway_status or "pending", "updated_at": datetime.now(timezone.utc)}},
        )


async def _callback(request: Request, background_tasks: BackgroundTasks, source: str):
    payload = {key: str(value) for key, value in dict(await request.form()).items()}
    document = await _validated_document(payload)
    gateway_status = payload.get("status", "").lower()
    await db.order_requests.update_one(
        {"id": document["id"]},
        {"$set": {
            "payment_gateway_status": f"return_{gateway_status or source}",
            "payu_payment_id": payload.get("mihpayid") or document.get("payu_payment_id"),
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    if gateway_status == "success":
        background_tasks.add_task(reconcile_transaction, document["payment_transaction_id"])
    else:
        await _mark_failed(document, gateway_status or source, payload.get("error_Message") or "Payment was not completed")
    return RedirectResponse(
        url=f"{document.get('payment_callback_base') or CALLBACK_BASE_FALLBACK}/payment-result?txnid={document['payment_transaction_id']}", status_code=303,
    )


@router.post("/payu/success")
async def payu_success(request: Request, background_tasks: BackgroundTasks):
    return await _callback(request, background_tasks, "success")


@router.post("/payu/failure")
async def payu_failure(request: Request, background_tasks: BackgroundTasks):
    return await _callback(request, background_tasks, "failure")


@router.post("/payu/webhook")
async def payu_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = {key: str(value) for key, value in dict(await request.form()).items()}
    document = await _validated_document(payload)
    gateway_status = payload.get("status", "").lower()
    if gateway_status == "success":
        became_paid = await _mark_paid(document, gateway_status, payload.get("mihpayid"))
        if became_paid:
            background_tasks.add_task(send_order_email, document["id"], "payment_confirmed")
    else:
        await _mark_failed(document, gateway_status or "failure", payload.get("error_Message") or "Payment was not completed")
    return {"ok": True}


@router.get("/payments/{transaction_id}", response_model=PaymentStatusResponse)
async def payment_status(transaction_id: str):
    document = await db.order_requests.find_one({"payment_transaction_id": transaction_id})
    if not document:
        raise HTTPException(status_code=404, detail="Payment transaction not found")
    state = "paid" if document.get("payment_status") == "Paid" else "failed" if document.get("payment_status") == "Unpaid" else "pending"
    updated = document.get("updated_at", document["received_at"])
    return PaymentStatusResponse(
        transaction_id=transaction_id, request_number=document["request_number"], status=state,
        amount=_amount_due(document), credit_applied=document.get("credit_applied", 0), total=document["total"], updated_at=updated,
    )


async def process_payu_reconciliation(run_id: str) -> None:
    candidates = await db.order_requests.find({
        "payment_provider": "PayU", "payment_status": "Payment pending",
        "payment_created_at": {"$lte": datetime.now(timezone.utc) - timedelta(minutes=3)},
    }).sort("payment_created_at", 1).limit(50).to_list(50)
    for document in candidates:
        try:
            await reconcile_transaction(document["payment_transaction_id"])
        except Exception as exc:
            logger.error("PayU reconciliation failed for %s: %s", document["payment_transaction_id"], exc)
    await db.cron_runs.update_one(
        {"run_id": run_id}, {"$set": {"completed_at": datetime.now(timezone.utc), "processed": len(candidates)}},
    )


@router.post("/cron/payu-reconcile", status_code=status.HTTP_202_ACCEPTED)
async def payu_reconcile_cron(
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
    background_tasks.add_task(process_payu_reconciliation, run_id)
    return {"accepted": True, "duplicate": False}