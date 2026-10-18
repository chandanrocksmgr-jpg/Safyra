from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html import escape
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pymongo import ReturnDocument

from lib.db import db
from lib.email_service import EMAIL_FROM_NAME, send_email
from lib.security import get_current_user
from models.verification import VerificationConfirm, VerificationResponse, VerificationSendResponse
from routers.order_requests import _sync_customer_order


router = APIRouter(prefix="/email-verification", tags=["email verification"])
logger = logging.getLogger(__name__)


def _origin(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    host = forwarded or request.url.netloc
    hostname = host.split(":", 1)[0].lower()
    allowed = hostname in {"safyra.co", "www.safyra.co", "localhost"} or hostname.endswith((".emergent.host", ".preview.emergentagent.com"))
    if not allowed:
        raise HTTPException(status_code=400, detail="Unrecognised account host")
    scheme = "http" if hostname == "localhost" else "https"
    return f"{scheme}://{host}"


async def send_verification_email(user_id: str, origin: str) -> None:
    user = await db.users.find_one({"id": user_id, "role": "customer"})
    if not user or user.get("email_verified"):
        return
    token = secrets.token_urlsafe(40)
    now = datetime.now(timezone.utc)
    await db.email_verification_tokens.delete_many({"user_id": user_id, "used_at": None})
    await db.email_verification_tokens.insert_one({
        "token_hash": sha256(token.encode()).hexdigest(), "user_id": user_id, "email": user["email"],
        "created_at": now, "expires_at": now + timedelta(hours=24), "used_at": None,
    })
    link = f"{origin}/verify-email?token={token}"
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(user["name"])},</p><h1 style="font:30px Georgia,serif">Confirm your SAFYRA email.</h1>'
        '<p>This private link confirms your email and safely brings eligible guest orders into My Account. It expires in 24 hours.</p>'
        f'<p><a href="{escape(link)}" style="display:inline-block;padding:14px 20px;background:#261c19;color:#fff;text-decoration:none">Confirm my email</a></p>'
        '<p>If you did not create a SAFYRA account, you can ignore this message.</p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )
    try:
        email_id = await send_email(to=str(user["email"]), subject="Confirm your SAFYRA email", html=html)
        await db.users.update_one({"id": user_id}, {"$set": {
            "verification_email_id": email_id, "verification_email_status": "Sent", "verification_sent_at": now,
        }})
    except Exception as exc:
        logger.error("Verification email failed for user %s: %s", user_id, exc)
        await db.users.update_one({"id": user_id}, {"$set": {
            "verification_email_status": "Failed", "verification_sent_at": now,
        }})


@router.post("/send", response_model=VerificationSendResponse)
async def send_verification(request: Request, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    if user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Customer account required")
    sent_at = user.get("verification_sent_at")
    if sent_at:
        sent_at = sent_at if sent_at.tzinfo else sent_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - sent_at < timedelta(seconds=60):
            return VerificationSendResponse()
    background_tasks.add_task(send_verification_email, user["id"], _origin(request))
    return VerificationSendResponse()


@router.post("/confirm", response_model=VerificationResponse)
async def confirm_verification(input: VerificationConfirm):
    now = datetime.now(timezone.utc)
    record = await db.email_verification_tokens.find_one_and_update(
        {"token_hash": sha256(input.token.encode()).hexdigest(), "used_at": None, "expires_at": {"$gt": now}},
        {"$set": {"used_at": now}}, return_document=ReturnDocument.AFTER,
    )
    if not record:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired")
    user = await db.users.find_one({"id": record["user_id"], "email": record["email"]})
    if not user:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired")
    await db.users.update_one({"id": user["id"]}, {"$set": {"email_verified": True, "email_verified_at": now, "updated_at": now}})
    requests = await db.order_requests.find({"email": user["email"], "payment_status": "Paid", "customer_id": None}).to_list(500)
    request_ids = [item["id"] for item in requests]
    if request_ids:
        await db.order_requests.update_many({"id": {"$in": request_ids}}, {"$set": {"customer_id": user["id"]}})
        await db.orders.update_many({"source_request_id": {"$in": request_ids}}, {"$set": {"customer_id": user["id"]}})
        await db.invoices.update_many({"source_request_id": {"$in": request_ids}}, {"$set": {"customer_id": user["id"]}})
        orders = await db.orders.find({"source_request_id": {"$in": request_ids}}).to_list(500)
        for order in orders:
            await _sync_customer_order(order)
    return VerificationResponse(verified=True, claimed_orders=len(request_ids))