"""Admin alerts for freshly paid orders: one email to the shop inbox plus an in-panel alert the admin acknowledges."""

import logging
import os
import uuid
from datetime import datetime, timezone
from html import escape

from pymongo.errors import DuplicateKeyError

from lib.db import get_db
from lib.email_service import EMAIL_FROM_NAME, send_email

logger = logging.getLogger(__name__)


def alert_recipient() -> str:
    return os.environ.get("ADMIN_ALERT_EMAIL", "").strip()


def _money(value: object) -> str:
    return f"₹{int(value or 0):,}"


def _alert_html(order: dict, admin_url: str) -> str:
    lines = "".join(
        f'<tr><td style="padding:6px 0">{escape(str(item.get("title", "")))}'
        f'<br><span style="font-size:12px;color:#715b52">{escape(" · ".join(str(part) for part in [item.get("set_type"), item.get("size"), item.get("color")] if part))}</span></td>'
        f'<td style="padding:6px 0;text-align:right">× {int(item.get("quantity", 1))}</td></tr>'
        for item in order.get("items", [])
    )
    credit = int(order.get("credit_applied") or 0)
    credit_note = f" (includes SAFYRA Credit {_money(credit)})" if credit else ""
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p style="margin:0 0 6px;letter-spacing:.14em;font-size:11px;text-transform:uppercase;color:#8a6a53">New paid order</p>'
        f'<h1 style="font:28px Georgia,serif;margin:0 0 14px">{escape(str(order.get("request_number", "")))}</h1>'
        f'<p style="margin:0 0 4px"><strong>{escape(str(order.get("name", "")))}</strong> · {escape(str(order.get("mobile", "")))}</p>'
        f'<p style="margin:0 0 14px">{escape(str(order.get("email", "")))}</p>'
        f'<table role="presentation" width="100%" style="font-size:14px;border-top:1px solid #e4d9c6">{lines}</table>'
        f'<p style="margin:14px 0 4px">Shipping: {_money(order.get("shipping_amount"))}</p>'
        f'<p style="margin:0 0 4px"><strong>Total paid: {_money(order.get("total"))}</strong>{credit_note}</p>'
        f'<p style="margin:0 0 18px;font-size:13px;color:#715b52">Paid via {escape(str(order.get("payment_provider", "PayU")))} · '
        f'{escape(str(order.get("city", "")))}, {escape(str(order.get("state_region", "")))}</p>'
        f'<p><a href="{escape(admin_url)}/admin/orders" style="background:#2c1a14;color:#fff;padding:12px 20px;text-decoration:none">Open the order</a></p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)} order alerts.</p>'
        '</td></tr></table>'
    )


async def notify_admin_new_order(request_id: str) -> None:
    """Fires once per paid order: records the in-panel alert, then emails the shop inbox."""
    db = get_db()
    order = await db.order_requests.find_one({"id": request_id})
    if not order:
        return
    alert = {
        "id": uuid.uuid4().hex,
        "request_id": request_id,
        "request_number": order.get("request_number", ""),
        "customer_name": order.get("name", ""),
        "customer_email": str(order.get("email", "")),
        "customer_mobile": str(order.get("mobile", "")),
        "total": int(order.get("total") or 0),
        "item_count": sum(int(item.get("quantity", 1)) for item in order.get("items", [])),
        "payment_provider": order.get("payment_provider", ""),
        "created_at": datetime.now(timezone.utc),
        "acknowledged_at": None,
        "acknowledged_by": None,
        "email_status": "Sending",
    }
    try:
        await db.admin_order_alerts.insert_one(alert)
    except DuplicateKeyError:  # already alerted for this order
        return
    recipient = alert_recipient()
    if not recipient:
        await db.admin_order_alerts.update_one({"id": alert["id"]}, {"$set": {"email_status": "No recipient configured"}})
        return
    admin_url = (order.get("payment_callback_base") or os.environ.get("PUBLIC_SITE_URL", "")).rstrip("/")
    try:
        email_id = await send_email(
            to=recipient,
            subject=f"New SAFYRA order {order.get('request_number', '')} · {_money(order.get('total'))}",
            html=_alert_html(order, admin_url),
        )
        await db.admin_order_alerts.update_one({"id": alert["id"]}, {"$set": {"email_status": "Sent", "email_id": email_id}})
    except Exception as exc:
        logger.error("Admin order alert email failed for %s: %s", request_id, exc)
        await db.admin_order_alerts.update_one({"id": alert["id"]}, {"$set": {"email_status": "Failed"}})
