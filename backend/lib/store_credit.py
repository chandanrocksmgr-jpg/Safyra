"""SAFYRA Credit ledger.

Each admin issue creates a grant (`store_credits`) valid for one year. Checkout holds credit by decrementing
grants soonest-expiring first, with an atomic guard per grant; the exact allocations are stored on the order
request so a failed or expired payment restores precisely what was taken. Every movement is also written to
`store_credit_activity` for the customer's history.
"""

from datetime import datetime, timezone
import uuid

from lib.db import get_db


def one_year_after(moment: datetime) -> datetime:
    try:
        return moment.replace(year=moment.year + 1)
    except ValueError:  # 29 February -> 28 February next year
        return moment.replace(year=moment.year + 1, day=28)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _log(customer_id: str, kind: str, amount: int, request_number: str | None = None, expires_at: datetime | None = None) -> None:
    await get_db().store_credit_activity.insert_one({
        "id": str(uuid.uuid4()), "customer_id": customer_id, "type": kind, "amount": amount,
        "request_number": request_number, "expires_at": expires_at, "created_at": datetime.now(timezone.utc),
    })


async def issue_credit(customer_id: str, amount: int, issued_by: str | None) -> dict:
    now = datetime.now(timezone.utc)
    grant = {
        "id": str(uuid.uuid4()), "customer_id": customer_id, "amount": amount, "remaining": amount,
        "issued_at": now, "expires_at": one_year_after(now), "issued_by": issued_by,
    }
    await get_db().store_credits.insert_one(grant)
    await _log(customer_id, "issued", amount, expires_at=grant["expires_at"])
    return grant


async def credit_balance(customer_id: str) -> int:
    rows = await get_db().store_credits.aggregate([
        {"$match": {"customer_id": customer_id, "remaining": {"$gt": 0}, "expires_at": {"$gt": datetime.now(timezone.utc)}}},
        {"$group": {"_id": None, "balance": {"$sum": "$remaining"}}},
    ]).to_list(1)
    return int(rows[0]["balance"]) if rows else 0


async def balances_for(customer_ids: list[str]) -> dict[str, int]:
    rows = await get_db().store_credits.aggregate([
        {"$match": {"customer_id": {"$in": customer_ids}, "remaining": {"$gt": 0}, "expires_at": {"$gt": datetime.now(timezone.utc)}}},
        {"$group": {"_id": "$customer_id", "balance": {"$sum": "$remaining"}}},
    ]).to_list(len(customer_ids) or 1)
    return {row["_id"]: int(row["balance"]) for row in rows}


async def hold_credit(customer_id: str, amount: int, request_number: str) -> list[dict]:
    """Take `amount` from active grants, soonest expiry first. Raises ValueError (after rolling back) if short."""
    db = get_db()
    allocations: list[dict] = []
    needed = amount
    for _ in range(5):  # a concurrent checkout can win a grant between read and update; re-read and continue
        if needed <= 0:
            break
        grants = await db.store_credits.find(
            {"customer_id": customer_id, "remaining": {"$gt": 0}, "expires_at": {"$gt": datetime.now(timezone.utc)}},
        ).sort("expires_at", 1).to_list(200)
        if not grants:
            break
        for grant in grants:
            take = min(needed, int(grant["remaining"]))
            result = await db.store_credits.update_one(
                {"id": grant["id"], "remaining": {"$gte": take}, "expires_at": {"$gt": datetime.now(timezone.utc)}},
                {"$inc": {"remaining": -take}},
            )
            if result.modified_count:
                allocations.append({"credit_id": grant["id"], "amount": take})
                needed -= take
            if needed <= 0:
                break
    if needed > 0:
        await _return(allocations)
        raise ValueError("Your SAFYRA Credit balance changed. Please review your order again.")
    await _log(customer_id, "redeemed", amount, request_number)
    return allocations


async def _return(allocations: list[dict]) -> None:
    for allocation in allocations:
        await get_db().store_credits.update_one({"id": allocation["credit_id"]}, {"$inc": {"remaining": allocation["amount"]}})


async def restore_credit(customer_id: str, allocations: list[dict], request_number: str) -> None:
    if not allocations:
        return
    await _return(allocations)
    await _log(customer_id, "restored", sum(int(item["amount"]) for item in allocations), request_number)


async def credit_summary(customer_id: str) -> dict:
    db = get_db()
    now = datetime.now(timezone.utc)
    grants = await db.store_credits.find({"customer_id": customer_id}, {"_id": 0}).sort("issued_at", -1).to_list(200)
    activity = await db.store_credit_activity.find({"customer_id": customer_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    shaped = []
    for grant in grants:
        expired = _aware(grant["expires_at"]) <= now
        status = "Used" if grant["remaining"] <= 0 else "Expired" if expired else "Active"
        shaped.append({**grant, "status": status})
    active = sorted((grant for grant in shaped if grant["status"] == "Active"), key=lambda grant: _aware(grant["expires_at"]))
    return {
        "balance": sum(int(grant["remaining"]) for grant in active),
        "next_expiry": active[0]["expires_at"] if active else None,
        "next_expiry_amount": int(active[0]["remaining"]) if active else 0,
        "grants": shaped, "activity": activity,
    }
