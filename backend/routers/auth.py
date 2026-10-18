from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response

from lib.db import db
from lib.security import end_session, get_current_user, get_optional_user, hash_secret, start_session, validate_password, verify_secret
from models.auth import (
    AdminRecoveryRequest,
    AuthResponse,
    LoginRequest,
    PasswordChangeRequest,
    RecoveryQuestionResponse,
    SignupRequest,
    UserPublic,
)
from routers.email_verification import _origin, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _public(user: dict) -> UserPublic:
    return UserPublic(**user)


async def _login(input: LoginRequest, response: Response, role: str) -> AuthResponse:
    email = str(input.email).strip().lower()
    user = await db.users.find_one({"email": email, "role": role})
    if not user or not verify_secret(input.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    await start_session(user["id"], response)
    return AuthResponse(user=_public(user))


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(input: SignupRequest, response: Response, request: Request, background_tasks: BackgroundTasks):
    validate_password(input.password)
    email = str(input.email).strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": input.name.strip(),
        "phone": "",
        "role": "customer",
        "email_verified": False,
        "email_verified_at": None,
        "password_hash": hash_secret(input.password),
        "wishlist_ids": [],
        "cart": [],
        "orders": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(user)
    await start_session(user["id"], response)
    background_tasks.add_task(send_verification_email, user["id"], _origin(request))
    return AuthResponse(user=_public(user))


@router.post("/login", response_model=AuthResponse)
async def customer_login(input: LoginRequest, response: Response):
    return await _login(input, response, "customer")


@router.post("/admin/login", response_model=AuthResponse)
async def admin_login(input: LoginRequest, response: Response):
    return await _login(input, response, "admin")


@router.get("/me", response_model=UserPublic | None)
async def me(user: dict | None = Depends(get_optional_user)):
    return _public(user) if user else None


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    await end_session(request, response)


@router.put("/password", status_code=204)
async def change_password(input: PasswordChangeRequest, user: dict = Depends(get_current_user)):
    if not verify_secret(input.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    validate_password(input.new_password)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_secret(input.new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    await db.sessions.delete_many({"user_id": user["id"]})


@router.get("/admin/recovery-question", response_model=RecoveryQuestionResponse)
async def admin_recovery_question(email: str = Query(min_length=3)):
    user = await db.users.find_one({"email": email.strip().lower(), "role": "admin"})
    if not user or not user.get("security_question"):
        raise HTTPException(status_code=404, detail="No administrator recovery profile found")
    return RecoveryQuestionResponse(question=user["security_question"])


@router.post("/admin/recover", status_code=204)
async def recover_admin(input: AdminRecoveryRequest):
    email = str(input.email).strip().lower()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    attempts = await db.recovery_attempts.count_documents({"email": email, "created_at": {"$gte": cutoff}})
    if attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many recovery attempts. Try again later")
    user = await db.users.find_one({"email": email, "role": "admin"})
    normalized_answer = " ".join(input.answer.strip().lower().split())
    if not user or not verify_secret(normalized_answer, user.get("security_answer_hash", "")):
        await db.recovery_attempts.insert_one({"email": email, "created_at": datetime.now(timezone.utc)})
        raise HTTPException(status_code=400, detail="Recovery answer is incorrect")
    validate_password(input.new_password)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_secret(input.new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    await db.sessions.delete_many({"user_id": user["id"]})
    await db.recovery_attempts.delete_many({"email": email})