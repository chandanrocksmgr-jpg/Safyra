from datetime import datetime, timezone
from html import escape
import hmac
import logging
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.email_service import EMAIL_FROM_NAME, send_email
from models.checkout_session import CronEnvelope


router = APIRouter(tags=["order emails"])
logger = logging.getLogger(__name__)


def _money(value: int) -> str:
    return f"₹{value:,.0f}"


def _request_received_html(order: dict) -> str:
    items = "".join(
        f'<tr><td style="padding:10px 0;border-bottom:1px solid #e6dec8"><strong>{escape(item["title"])}</strong><br>'
        f'<span style="font-size:12px;color:#715b52">{escape(item.get("set_type") or "")} {escape(item["size"])} · {escape(item["color"])} · Qty {item["quantity"]}</span></td>'
        f'<td style="padding:10px 0;border-bottom:1px solid #e6dec8;text-align:right">{escape(_money(item["line_total"]))}</td></tr>'
        for item in order["items"]
    )
    address = "<br>".join(escape(str(value)) for value in [order["address"], f'{order["city"]}, {order["state_region"]} {order["postal_code"]}', order["country"]] if value)
    is_payu = order.get("payment_provider") in {"PayU", "SAFYRA Credit"}
    intro = "Your secure PayU payment is awaiting server verification." if is_payu else "No payment is confirmed by this email."
    next_step = "We will email you again as soon as PayU confirms the payment." if is_payu else "SAFYRA will verify product availability and shipping details before providing the next payment step."
    shipping_row = f'<tr><td style="padding-top:8px">India shipping</td><td style="padding-top:8px;text-align:right">{escape(_money(order.get("shipping_amount") or 0))}</td></tr>' if is_payu else ""
    total_row = f'<tr><td style="padding-top:10px"><strong>Total</strong></td><td style="padding-top:10px;text-align:right"><strong>{escape(_money(order.get("total") or order["subtotal"]))}</strong></td></tr>' if is_payu else ""
    if is_payu and order.get("credit_applied"):
        total_row += (f'<tr><td style="padding-top:6px">Paid with SAFYRA Credit</td><td style="padding-top:6px;text-align:right">−{escape(_money(order["credit_applied"]))}</td></tr>'
                      f'<tr><td style="padding-top:6px"><strong>Paid online</strong></td><td style="padding-top:6px;text-align:right"><strong>{escape(_money(order.get("amount_due", 0)))}</strong></td></tr>')
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(order["name"])},</p><h1 style="font:30px Georgia,serif">We received your SAFYRA order request.</h1>'
        f'<p>Your reference is <strong>{escape(order["request_number"])}</strong>. {escape(intro)}</p>'
        f'<table role="presentation" width="100%">{items}<tr><td style="padding-top:14px"><strong>Product subtotal</strong></td><td style="padding-top:14px;text-align:right"><strong>{escape(_money(order["subtotal"]))}</strong></td></tr>{shipping_row}{total_row}</table>'
        f'<p><strong>Delivery summary</strong><br>{address}</p>'
        f'<p>{escape(next_step)} Your order is confirmed only after payment is independently verified.</p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )


def _payment_confirmed_html(order: dict) -> str:
    account_base = order.get("payment_callback_base") or os.environ["PUBLIC_SITE_URL"].rstrip("/")
    invoice_note = f'<p>Your GST invoice is ready in <a href="{escape(account_base)}/account">My Account</a>.</p>' if order.get("invoice_status") == "issued" else ""
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(order["name"])},</p><h1 style="font:30px Georgia,serif">Your payment is confirmed.</h1>'
        f'<p>SAFYRA has independently verified payment for <strong>{escape(order["request_number"])}</strong>.</p>'
        f'<p><strong>Confirmed total: {escape(_money(order.get("total") or order["subtotal"]))}</strong></p>'
        + (f'<p>Paid with SAFYRA Credit: {escape(_money(order["credit_applied"]))} · Paid online: {escape(_money(order.get("amount_due", 0)))}</p>' if order.get("credit_applied") else "")
        + '<p>Your order will now move through SAFYRA’s recorded fulfilment process. Courier and tracking details are shared only after they are entered and verified by the team.</p>'
        f'{invoice_note}'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )


async def send_fulfilment_email(request_id: str, fulfilment_status: str) -> None:
    if fulfilment_status not in {"In production", "Quality check", "Shipped", "Delivered"}:
        return
    now = datetime.now(timezone.utc)
    retry = await db.order_status_notifications.find_one_and_update(
        {"request_id": request_id, "status": fulfilment_status, "delivery_status": "Failed"},
        {"$set": {"delivery_status": "Sending", "attempted_at": now}}, return_document=ReturnDocument.AFTER,
    )
    if not retry:
        try:
            await db.order_status_notifications.insert_one({"request_id": request_id, "status": fulfilment_status, "delivery_status": "Sending", "created_at": now})
        except DuplicateKeyError:
            return
    order = await db.order_requests.find_one({"id": request_id, "payment_status": "Paid"})
    if not order:
        return
    account_base = order.get("payment_callback_base") or os.environ["PUBLIC_SITE_URL"].rstrip("/")
    shipping = ""
    if fulfilment_status == "Shipped":
        shipping = f'<p>Courier: <strong>{escape(order.get("courier_name") or "Recorded in My Account")}</strong><br/>Tracking number: <strong>{escape(order.get("tracking_number") or "Awaiting update")}</strong></p>'
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(order["name"])},</p><h1 style="font:30px Georgia,serif">Your order is {escape(fulfilment_status.lower())}.</h1>'
        f'<p>SAFYRA order <strong>{escape(order["request_number"])}</strong> has moved to <strong>{escape(fulfilment_status)}</strong>.</p>{shipping}'
        f'<p><a href="{escape(account_base)}/account">View order tracking in My Account</a></p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )
    try:
        email_id = await send_email(to=str(order["email"]), subject=f"SAFYRA order {order['request_number']}: {fulfilment_status}", html=html)
        await db.order_status_notifications.update_one({"request_id": request_id, "status": fulfilment_status}, {"$set": {"delivery_status": "Sent", "email_id": email_id, "sent_at": datetime.now(timezone.utc)}})
        await db.order_requests.update_one({"id": request_id}, {"$push": {"history": {"id": __import__("uuid").uuid4().hex, "event": "fulfilment_email", "message": f"{fulfilment_status} email accepted by the provider.", "created_at": datetime.now(timezone.utc), "admin_id": None}}})
    except Exception as exc:
        logger.error("Fulfilment email failed for %s (%s): %s", request_id, fulfilment_status, exc)
        await db.order_status_notifications.update_one({"request_id": request_id, "status": fulfilment_status}, {"$set": {"delivery_status": "Failed"}})


async def send_invoice_ready_email(invoice_id: str) -> None:
    try:
        await db.invoice_notifications.insert_one({"invoice_id": invoice_id, "delivery_status": "Sending", "created_at": datetime.now(timezone.utc)})
    except DuplicateKeyError:
        return
    invoice = await db.invoices.find_one({"id": invoice_id, "document_type": "invoice"})
    order = await db.order_requests.find_one({"id": invoice.get("source_request_id")}) if invoice else None
    if not invoice or not order:
        return
    account_base = order.get("payment_callback_base") or os.environ["PUBLIC_SITE_URL"].rstrip("/")
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(order["name"])},</p><h1 style="font:30px Georgia,serif">Your GST invoice is ready.</h1>'
        f'<p>Invoice <strong>{escape(invoice["number"])}</strong> for order <strong>{escape(order["request_number"])}</strong> is stored privately in My Account.</p>'
        f'<p><a href="{escape(account_base)}/account">Open My Account</a></p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )
    try:
        email_id = await send_email(to=str(order["email"]), subject=f"GST invoice ready for SAFYRA order {order['request_number']}", html=html)
        await db.invoice_notifications.update_one({"invoice_id": invoice_id}, {"$set": {"delivery_status": "Sent", "email_id": email_id, "sent_at": datetime.now(timezone.utc)}})
    except Exception as exc:
        logger.error("Invoice-ready email failed for %s: %s", invoice_id, exc)
        await db.invoice_notifications.update_one({"invoice_id": invoice_id}, {"$set": {"delivery_status": "Failed"}})


async def send_order_email(request_id: str, kind: str) -> None:
    if kind not in {"request_received", "payment_confirmed"}:
        return
    prefix = "request_received_email" if kind == "request_received" else "paid_email"
    now = datetime.now(timezone.utc)
    order = await db.order_requests.find_one_and_update(
        {"id": request_id, f"{prefix}_status": "Scheduled"},
        {"$set": {f"{prefix}_status": "Sending", f"{prefix}_attempted_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not order:
        return
    subject = f"SAFYRA order request {order['request_number']} received" if kind == "request_received" else f"Payment confirmed for SAFYRA order {order['request_number']}"
    html = _request_received_html(order) if kind == "request_received" else _payment_confirmed_html(order)
    try:
        email_id = await send_email(to=str(order["email"]), subject=subject, html=html)
        sent_at = datetime.now(timezone.utc)
        await db.order_requests.update_one({"id": request_id}, {
            "$set": {f"{prefix}_status": "Sent", f"{prefix}_sent_at": sent_at, f"{prefix}_id": email_id},
            "$push": {"history": {
                "id": __import__("uuid").uuid4().hex,
                "event": f"{kind}_email",
                "message": "Order request email accepted by the provider." if kind == "request_received" else "Payment confirmation email accepted by the provider.",
                "created_at": sent_at,
                "admin_id": None,
            }},
        })
    except Exception as exc:
        logger.error("Order email failed for %s (%s): %s", request_id, kind, exc)
        await db.order_requests.update_one({"id": request_id}, {
            "$set": {f"{prefix}_status": "Failed"},
            "$push": {"history": {
                "id": __import__("uuid").uuid4().hex,
                "event": f"{kind}_email_failed",
                "message": "Order request email delivery attempt failed." if kind == "request_received" else "Payment confirmation email delivery attempt failed.",
                "created_at": datetime.now(timezone.utc),
                "admin_id": None,
            }},
        })


async def process_order_emails(run_id: str) -> None:
    request_ids = await db.order_requests.distinct("id", {"request_received_email_status": "Scheduled"})
    paid_ids = await db.order_requests.distinct("id", {"paid_email_status": "Scheduled", "payment_status": "Paid", "payment_verified_at": {"$ne": None}})
    for request_id in request_ids[:50]:
        await send_order_email(request_id, "request_received")
    for request_id in paid_ids[:50]:
        await send_order_email(request_id, "payment_confirmed")
    status_retries = await db.order_status_notifications.find({"delivery_status": "Failed"}).limit(25).to_list(25)
    for notification in status_retries:
        await send_fulfilment_email(notification["request_id"], notification["status"])
    await db.cron_runs.update_one({"run_id": run_id}, {"$set": {"completed_at": datetime.now(timezone.utc), "processed": len(request_ids[:50]) + len(paid_ids[:50]) + len(status_retries)}})


@router.post("/cron/order-emails", status_code=status.HTTP_202_ACCEPTED)
async def order_email_cron(
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
    background_tasks.add_task(process_order_emails, run_id)
    return {"accepted": True, "duplicate": False}