"""Staff management — Super Admin only. Creates and controls catalogue-only Junior Admin accounts."""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException

from lib.db import db
from lib.security import hash_secret, is_super_admin, require_super_admin, validate_password
from models.staff import StaffCreate, StaffMember, StaffPasswordReset, StaffUpdate

router = APIRouter(prefix="/admin/staff", tags=["staff"])


def _row(user: dict) -> StaffMember:
    return StaffMember(
        id=user["id"], email=str(user["email"]), name=user.get("name", ""),
        admin_role="junior" if user.get("admin_role") == "junior" else "super",
        status="deactivated" if user.get("status") == "deactivated" else "active",
        created_at=user["created_at"], last_login_at=user.get("last_login_at"),
    )


async def _junior(staff_id: str) -> dict:
    """Only junior accounts are editable through this API, so a Super Admin can never be demoted or deleted here."""
    user = await db.users.find_one({"id": staff_id, "role": "admin"})
    if not user:
        raise HTTPException(status_code=404, detail="Staff account not found")
    if is_super_admin(user):
        raise HTTPException(status_code=403, detail="Super Admin accounts cannot be changed here")
    return user


@router.get("", response_model=list[StaffMember])
async def list_staff(_: dict = Depends(require_super_admin)):
    cursor = db.users.find({"role": "admin"}).sort("created_at", 1)
    return [_row(user) async for user in cursor]


@router.post("", response_model=StaffMember, status_code=201)
async def create_junior_admin(input: StaffCreate, _: dict = Depends(require_super_admin)):
    validate_password(input.password)
    email = str(input.email).strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    now = datetime.now(timezone.utc)
    user = {
        "id": str(uuid.uuid4()), "email": email, "name": input.name.strip(), "phone": "",
        "role": "admin", "admin_role": "junior", "status": "active",  # creation is hard-coded to junior
        "email_verified": True, "email_verified_at": now, "picture_url": "",
        "auth_providers": ["password"], "password_hash": hash_secret(input.password),
        "wishlist_ids": [], "cart": [], "orders": [], "created_at": now, "updated_at": now,
    }
    await db.users.insert_one(user)
    return _row(user)


@router.patch("/{staff_id}", response_model=StaffMember)
async def update_junior_admin(staff_id: str, input: StaffUpdate, _: dict = Depends(require_super_admin)):
    await _junior(staff_id)
    changes: dict = {"updated_at": datetime.now(timezone.utc)}
    if input.name is not None:
        changes["name"] = input.name.strip()
    if input.status is not None:
        changes["status"] = input.status
    updated = await db.users.find_one_and_update({"id": staff_id}, {"$set": changes}, return_document=True)
    if input.status == "deactivated":
        await db.sessions.delete_many({"user_id": staff_id})  # sign the account out everywhere immediately
    return _row(updated)


@router.put("/{staff_id}/password", status_code=204)
async def reset_junior_password(staff_id: str, input: StaffPasswordReset, _: dict = Depends(require_super_admin)):
    await _junior(staff_id)
    validate_password(input.new_password)
    await db.users.update_one({"id": staff_id}, {"$set": {"password_hash": hash_secret(input.new_password), "updated_at": datetime.now(timezone.utc)}})
    await db.sessions.delete_many({"user_id": staff_id})


@router.delete("/{staff_id}", status_code=204)
async def delete_junior_admin(staff_id: str, _: dict = Depends(require_super_admin)):
    await _junior(staff_id)
    await db.users.delete_one({"id": staff_id})
    await db.sessions.delete_many({"user_id": staff_id})
