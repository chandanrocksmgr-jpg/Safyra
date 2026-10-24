"""9pm IST wrap-up of the day's paid orders: revenue, order list and the pieces still to pack."""

from datetime import datetime, timedelta, timezone
from html import escape
import hmac
import logging
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status
from pymongo.errors import DuplicateKeyError

from lib.admin_alerts import alert_recipient
from lib.dates import now_in_app_tz
from lib.db import db
from lib.email_service import EMAIL_FROM_NAME, send_email
from models.checkout_session import CronEnvelope

router = APIRouter(tags=["order digest"])
logger = logging.getLogger(__name__)

PACKING_PENDING = ["Confirmed", "In production", "Quality check", "Ready to dispatch"]


def _money(value: object) -> str:
    return f"₹{int(value or 0):,}"


def _window() -> tuple[datetime, datetime, str]:
    """Today in the shop's timezone (APP_TZ), expressed as a UTC range for Mongo."""
    local_now = now_in_app_tz()
    start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc), (start_local + timedelta(days=1)).astimezone(timezone.utc), start_local.strftime("%d %B %Y")


def _digest_html(day_label: str, orders: list[dict], packing: list[dict], admin_url: str) -> str:
    revenue = sum(int(order.get("total") or 0) for order in orders)
    pieces = sum(int(item.get("quantity", 1)) for order in orders for item in order.get("items", []))
    credit = sum(int(order.get("credit_applied") or 0) for order in orders)
    order_rows = "".join(
        f'<tr><td style="padding:6px 0;border-top:1px solid #ece1cd">{escape(str(order.get("request_number", "")))}'
        f'<br><span style="font-size:12px;color:#715b52">{escape(str(order.get("name", "")))} · '
        f'{sum(int(item.get("quantity", 1)) for item in order.get("items", []))} pieces</span></td>'
        f'<td style="padding:6px 0;border-top:1px solid #ece1cd;text-align:right">{_money(order.get("total"))}</td></tr>'
        for order in orders
    ) or '<tr><td style="padding:10px 0;color:#715b52">No paid orders today.</td></tr>'
    packing_rows = "".join(
        f'<li style="margin-bottom:6px">{escape(str(item["title"]))} '
        f'<span style="color:#715b52">{escape(" · ".join(str(part) for part in [item.get("set_type"), item.get("size"), item.get("color")] if part))} × {item["quantity"]}</span>'
        f'<br><span style="font-size:12px;color:#8a6a53">{escape(item["orders"])}</span></li>'
        for item in packing
    ) or '<li style="color:#715b52">Nothing waiting to be packed.</li>'
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        '<p style="margin:0 0 6px;letter-spacing:.14em;font-size:11px;text-transform:uppercase;color:#8a6a53">Daily wrap-up</p>'
        f'<h1 style="font:28px Georgia,serif;margin:0 0 4px">{escape(day_label)}</h1>'
        f'<p style="margin:0 0 18px;font-size:15px"><strong>{len(orders)} paid {"order" if len(orders) == 1 else "orders"}</strong> · '
        f'{_money(revenue)} · {pieces} {"piece" if pieces == 1 else "pieces"} sold'
        f'{f" · {_money(credit)} settled with SAFYRA Credit" if credit else ""}</p>'
        f'<table role="presentation" width="100%" style="font-size:14px">{order_rows}</table>'
        f'<h2 style="font:19px Georgia,serif;margin:24px 0 8px">Pieces to pack ({sum(int(item["quantity"]) for item in packing)})</h2>'
        f'<ul style="font-size:14px;padding-left:18px;margin:0">{packing_rows}</ul>'
        f'<p style="margin:22px 0 0"><a href="{escape(admin_url)}/admin/orders" style="background:#2c1a14;color:#fff;padding:12px 20px;text-decoration:none">Open order management</a></p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)} order alerts.</p>'
        '</td></tr></table>'
    )


async def send_order_digest(run_id: str) -> None:
    start, end, day_label = _window()
    orders = await db.order_requests.find({
        "payment_status": "Paid", "payment_verified_at": {"$gte": start, "$lt": end},
    }).sort("payment_verified_at", 1).to_list(200)
    outstanding = await db.order_requests.find({
        "payment_status": "Paid", "fulfilment_status": {"$in": PACKING_PENDING},
        "cancellation_status": {"$ne": "Cancelled"},
    }).sort("payment_verified_at", 1).to_list(200)
    packing: dict[tuple, dict] = {}
    for order in outstanding:
        for item in order.get("items", []):
            key = (item.get("title", ""), item.get("set_type") or "", item.get("size") or "", item.get("color") or "")
            row = packing.setdefault(key, {"title": key[0], "set_type": key[1], "size": key[2], "color": key[3], "quantity": 0, "order_numbers": []})
            row["quantity"] += int(item.get("quantity", 1))
            row["order_numbers"].append(str(order.get("request_number", "")))
    packing_rows = sorted(packing.values(), key=lambda row: (-row["quantity"], row["title"]))
    for row in packing_rows:
        row["orders"] = ", ".join(dict.fromkeys(row["order_numbers"]))
    recipient = alert_recipient()
    if not recipient:
        logger.error("Daily order digest skipped: ADMIN_ALERT_EMAIL is not configured")
        return
    admin_url = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/")
    try:
        email_id = await send_email(
            to=recipient,
            subject=f"SAFYRA daily wrap-up · {day_label} · {len(orders)} paid {'order' if len(orders) == 1 else 'orders'}",
            html=_digest_html(day_label, orders, packing_rows, admin_url),
        )
        await db.cron_runs.update_one({"run_id": run_id}, {"$set": {
            "completed_at": datetime.now(timezone.utc), "processed": len(orders), "email_id": email_id,
        }})
    except Exception as exc:
        logger.error("Daily order digest email failed: %s", exc)


@router.post("/cron/order-digest", status_code=status.HTTP_202_ACCEPTED)
async def order_digest_cron(
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
    background_tasks.add_task(send_order_digest, run_id)
    return {"accepted": True, "duplicate": False}
