from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html import escape
import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pymongo import ReturnDocument

from lib.db import db
from lib.email_service import EMAIL_FROM_NAME, send_email
from lib.security import hash_secret, validate_password
from models.password_reset import PasswordResetConfirm, PasswordResetRequest, PasswordResetResponse
from routers.email_verification import _origin

router = APIRouter(prefix="/auth/password-reset", tags=["password reset"])
logger = logging.getLogger(__name__)

TOKEN_TTL_MINUTES = 10


async def send_password_reset_email(email: str, origin: str) -> None:
    user = await db.users.find_one({"email": email, "role": "customer"})
    if not user:
        return
    token = secrets.token_urlsafe(40)
    now = datetime.now(timezone.utc)
    await db.password_reset_tokens.delete_many({"user_id": user["id"], "used_at": None})
    await db.password_reset_tokens.insert_one({
        "token_hash": sha256(token.encode()).hexdigest(), "user_id": user["id"], "email": user["email"],
        "created_at": now, "expires_at": now + timedelta(minutes=TOKEN_TTL_MINUTES), "used_at": None,
    })
    link = f"{origin}/reset-password?token={token}"
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(user.get("name") or "there")},</p><h1 style="font:30px Georgia,serif">Reset your SAFYRA password.</h1>'
        f'<p>Use this private link to choose a new password. It can be used once and expires in {TOKEN_TTL_MINUTES} minutes.</p>'
        f'<p><a href="{escape(link)}" style="display:inline-block;padding:14px 20px;background:#261c19;color:#fff;text-decoration:none">Choose a new password</a></p>'
        '<p>If you did not ask to reset your password, you can ignore this message and your current password stays active.</p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for passwords or card details by email.</p>'
        '</td></tr></table>'
    )
    try:
        await send_email(to=str(user["email"]), subject="Reset your SAFYRA password", html=html)
    except Exception as exc:
        logger.error("Password reset email failed for %s: %s", email, exc)


@router.post("/request", response_model=PasswordResetResponse)
async def request_password_reset(input: PasswordResetRequest, request: Request, background_tasks: BackgroundTasks):
    email = str(input.email).strip().lower()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    attempts = await db.password_reset_tokens.count_documents({"email": email, "created_at": {"$gte": cutoff}})
    if attempts < 5:
        background_tasks.add_task(send_password_reset_email, email, _origin(request))
    # Always generic: never reveal whether an account exists for this email.
    return PasswordResetResponse()


@router.post("/confirm", status_code=204)
async def confirm_password_reset(input: PasswordResetConfirm):
    validate_password(input.new_password)
    now = datetime.now(timezone.utc)
    record = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": sha256(input.token.encode()).hexdigest(), "used_at": None, "expires_at": {"$gt": now}},
        {"$set": {"used_at": now}}, return_document=ReturnDocument.AFTER,
    )
    if not record:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")
    user = await db.users.find_one({"id": record["user_id"], "email": record["email"]})
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "password_hash": hash_secret(input.new_password), "updated_at": now,
    }, "$addToSet": {"auth_providers": "password"}})
    await db.sessions.delete_many({"user_id": user["id"]})
