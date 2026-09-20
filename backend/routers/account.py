from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from lib.db import db
from lib.security import get_current_user
from models.auth import AccountResponse, AccountStateUpdate, Order, ProfileUpdate, UserPublic

router = APIRouter(prefix="/account", tags=["account"])


def _account(user: dict) -> AccountResponse:
    return AccountResponse(
        user=UserPublic(**user),
        wishlist_ids=user.get("wishlist_ids", []),
        cart=user.get("cart", []),
        orders=user.get("orders", []),
    )


@router.get("", response_model=AccountResponse)
async def get_account(user: dict = Depends(get_current_user)):
    return _account(user)


@router.patch("/profile", response_model=UserPublic)
async def update_profile(input: ProfileUpdate, user: dict = Depends(get_current_user)):
    changes = input.model_dump(exclude_none=True)
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.users.update_one({"id": user["id"]}, {"$set": changes})
    updated = await db.users.find_one({"id": user["id"]})
    return UserPublic(**updated)


@router.put("/state", status_code=204)
async def update_account_state(input: AccountStateUpdate, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "wishlist_ids": input.wishlist_ids,
                "cart": [item.model_dump() for item in input.cart],
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


@router.get("/orders", response_model=list[Order])
async def get_orders(user: dict = Depends(get_current_user)):
    return user.get("orders", [])