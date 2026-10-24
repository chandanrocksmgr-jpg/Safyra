from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from lib.db import db
from lib.security import get_current_user
from models.auth import AccountResponse, AccountStateUpdate, Order, ProfileUpdate, SavedAddress, SavedAddressInput, UserPublic

router = APIRouter(prefix="/account", tags=["account"])


def _account(user: dict) -> AccountResponse:
    return AccountResponse(
        user=UserPublic(**user),
        wishlist_ids=user.get("wishlist_ids", []),
        cart=user.get("cart", []),
        orders=user.get("orders", []),
        addresses=_addresses(user),
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


MAX_ADDRESSES = 10


def _addresses(user: dict) -> list[SavedAddress]:
    return [SavedAddress(**address) for address in user.get("addresses", [])]


def _address_key(address: SavedAddressInput) -> tuple:
    return tuple(" ".join(value.lower().split()) for value in (address.name, address.address, address.postal_code, address.country))


def _with_default(addresses: list[SavedAddress], default_id: str | None) -> list[SavedAddress]:
    """Exactly one default whenever any address exists."""
    if not addresses:
        return addresses
    if default_id is None or not any(address.id == default_id for address in addresses):
        default_id = next((address.id for address in addresses if address.is_default), addresses[0].id)
    return [address.model_copy(update={"is_default": address.id == default_id}) for address in addresses]


async def _save_addresses(user: dict, addresses: list[SavedAddress]) -> list[SavedAddress]:
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"addresses": [address.model_dump() for address in addresses], "updated_at": datetime.now(timezone.utc)}},
    )
    return addresses


def _find(addresses: list[SavedAddress], address_id: str) -> SavedAddress:
    match = next((address for address in addresses if address.id == address_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Address not found")
    return match


@router.get("/addresses", response_model=list[SavedAddress])
async def list_addresses(user: dict = Depends(get_current_user)):
    return _addresses(user)


@router.post("/addresses", response_model=list[SavedAddress], status_code=201)
async def add_address(input: SavedAddressInput, user: dict = Depends(get_current_user)):
    addresses = _addresses(user)
    duplicate = next((address for address in addresses if _address_key(address) == _address_key(input)), None)
    if duplicate:  # saving the same delivery address twice (e.g. from checkout) refreshes it instead
        updated = SavedAddress(**input.model_dump(), id=duplicate.id)
        addresses = [updated if address.id == duplicate.id else address for address in addresses]
        return await _save_addresses(user, _with_default(addresses, updated.id if input.is_default else None))
    if len(addresses) >= MAX_ADDRESSES:
        raise HTTPException(status_code=400, detail=f"You can save up to {MAX_ADDRESSES} addresses")
    created = SavedAddress(**input.model_dump())
    addresses.append(created)
    return await _save_addresses(user, _with_default(addresses, created.id if input.is_default or len(addresses) == 1 else None))


@router.put("/addresses/{address_id}", response_model=list[SavedAddress])
async def update_address(address_id: str, input: SavedAddressInput, user: dict = Depends(get_current_user)):
    addresses = _addresses(user)
    current = _find(addresses, address_id)
    updated = SavedAddress(**input.model_dump(), id=address_id)
    addresses = [updated if address.id == address_id else address for address in addresses]
    # Unticking "default" on the current default keeps it default; another address must be chosen instead.
    default_id = address_id if input.is_default or current.is_default else None
    return await _save_addresses(user, _with_default(addresses, default_id))


@router.post("/addresses/{address_id}/default", response_model=list[SavedAddress])
async def set_default_address(address_id: str, user: dict = Depends(get_current_user)):
    addresses = _addresses(user)
    _find(addresses, address_id)
    return await _save_addresses(user, _with_default(addresses, address_id))


@router.delete("/addresses/{address_id}", response_model=list[SavedAddress])
async def delete_address(address_id: str, user: dict = Depends(get_current_user)):
    addresses = _addresses(user)
    _find(addresses, address_id)
    return await _save_addresses(user, _with_default([address for address in addresses if address.id != address_id], None))
