from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import logging
import secrets
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import EmailStr, TypeAdapter
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.email_service import EMAIL_FROM_NAME, send_email
from lib.security import hash_secret, start_session
from models.auth import GoogleAuthResponse, GoogleSessionExchange, UserPublic
from routers.email_verification import _origin, claim_paid_guest_orders


router = APIRouter(prefix="/auth/google", tags=["google auth"])
logger = logging.getLogger(__name__)
SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


async def send_google_linked_email(user_id: str, origin: str) -> None:
    now = datetime.now(timezone.utc)
    notification = await db.google_link_notifications.find_one_and_update(
        {"user_id": user_id, "status": "Failed"},
        {"$set": {"status": "Sending", "attempted_at": now}}, return_document=ReturnDocument.AFTER,
    )
    if not notification:
        try:
            await db.google_link_notifications.insert_one({"user_id": user_id, "status": "Sending", "created_at": now})
        except DuplicateKeyError:
            return
    user = await db.users.find_one({"id": user_id, "role": "customer"})
    if not user:
        return
    account_url = f"{origin}/account"
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(user["name"])},</p><h1 style="font:30px Georgia,serif">Google sign-in is ready for your SAFYRA account.</h1>'
        '<p>You can now use your verified Google email to return to your saved wishlist, bag and eligible paid orders.</p>'
        f'<p><a href="{escape(account_url)}" style="display:inline-block;padding:14px 20px;background:#261c19;color:#fff;text-decoration:none">Open My Account</a></p>'
        '<p>If you did not make this change, contact SAFYRA customer care. We never ask for your password or card details by email.</p>'
        f'<p style="font-size:12px;color:#715b52">Sent by {escape(EMAIL_FROM_NAME)}.</p>'
        '</td></tr></table>'
    )
    try:
        email_id = await send_email(to=str(user["email"]), subject="Google sign-in added to your SAFYRA account", html=html)
        await db.google_link_notifications.update_one({"user_id": user_id}, {"$set": {"status": "Sent", "email_id": email_id, "sent_at": datetime.now(timezone.utc)}})
    except Exception as exc:
        logger.error("Google account email failed for user %s: %s", user_id, exc)
        await db.google_link_notifications.update_one({"user_id": user_id}, {"$set": {"status": "Failed"}})


@router.post("/session", response_model=GoogleAuthResponse)
async def exchange_google_session(input: GoogleSessionExchange, request: Request, response: Response, background_tasks: BackgroundTasks):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            provider_response = await client.get(SESSION_DATA_URL, headers={"X-Session-ID": input.session_id})
        provider_response.raise_for_status()
        provider = provider_response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Emergent Google session exchange failed: %s", exc)
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified") from exc
    if not provider.get("id") or not provider.get("email") or not provider.get("session_token"):
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(provider["email"])).strip().lower()
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Google account did not provide a valid email") from exc
    existing = await db.users.find_one({"email": email})
    if existing and existing.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Google sign-in is available for customer accounts only")
    exchange_hash = sha256(input.session_id.encode()).hexdigest()
    try:
        await db.oauth_exchanges.insert_one({"session_id_hash": exchange_hash, "provider": "google", "created_at": datetime.now(timezone.utc)})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="This Google sign-in response has already been used") from exc
    now = datetime.now(timezone.utc)
    if existing:
        await db.users.update_one({"id": existing["id"]}, {"$set": {
            "email_verified": True, "email_verified_at": now,
            "picture_url": str(provider.get("picture") or existing.get("picture_url") or ""),
            "google_subject": str(provider["id"]), "updated_at": now,
        }, "$addToSet": {"auth_providers": "google"}})
        user_id = existing["id"]
    else:
        user_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": user_id, "email": email, "name": str(provider.get("name") or email.split("@", 1)[0])[:80],
            "phone": "", "role": "customer", "email_verified": True, "email_verified_at": now,
            "picture_url": str(provider.get("picture") or ""), "google_subject": str(provider["id"]),
            "auth_providers": ["google"], "password_hash": hash_secret(secrets.token_urlsafe(48)),
            "wishlist_ids": [], "cart": [], "orders": [], "created_at": now, "updated_at": now,
        })
    user = await db.users.find_one({"id": user_id})
    claimed_orders = await claim_paid_guest_orders(user_id, email)
    await start_session(user_id, response, days=7, oauth_callback=True)
    background_tasks.add_task(send_google_linked_email, user_id, _origin(request))
    return GoogleAuthResponse(user=UserPublic(**user), claimed_orders=claimed_orders)