from html import escape
import logging
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from lib.db import db
from lib.email_service import send_email
from lib.security import get_current_user, require_super_admin
from lib.store_credit import balances_for, credit_summary, issue_credit
from models.store_credit import AdminCustomerDetail, AdminCustomerRow, StoreCreditIssue, StoreCreditSummary

router = APIRouter()
logger = logging.getLogger(__name__)
CUSTOMER_FIELDS = {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1, "created_at": 1}


@router.get("/account/store-credit", response_model=StoreCreditSummary)
async def my_store_credit(user: dict = Depends(get_current_user)):
    return await credit_summary(user["id"])


def _customer_query(q: str) -> dict:
    query: dict = {"role": "customer"}
    term = q.strip()
    if not term:
        return query
    digits = re.sub(r"\D", "", term)
    conditions: list[dict] = [{"email": {"$regex": re.escape(term), "$options": "i"}}, {"name": {"$regex": re.escape(term), "$options": "i"}}]
    if len(digits) >= 4:
        # Phones may be stored with spaces or a +91 prefix; match the digits in order with optional separators.
        conditions.append({"phone": {"$regex": r"[\s\-]*".join(re.escape(digit) for digit in digits[-10:])}})
    query["$or"] = conditions
    return query


@router.get("/admin/customers", response_model=list[AdminCustomerRow])
async def search_customers(q: str = Query(default="", max_length=120), _: dict = Depends(require_super_admin)):
    users = await db.users.find(_customer_query(q), CUSTOMER_FIELDS).sort("created_at", -1).to_list(50)
    balances = await balances_for([user["id"] for user in users])
    return [AdminCustomerRow(**user, credit_balance=balances.get(user["id"], 0)) for user in users]


async def _detail(customer: dict) -> AdminCustomerDetail:
    credits = await credit_summary(customer["id"])
    orders = await db.orders.find(
        {"customer_id": customer["id"]},
        {"_id": 0, "request_number": 1, "total": 1, "credit_applied": 1, "payment_status": 1, "fulfilment_status": 1, "converted_at": 1, "received_at": 1},
    ).sort("received_at", -1).to_list(20)
    shaped = [{**order, "created_at": order.get("received_at") or order.get("converted_at"), "total": int(order.get("total") or 0)} for order in orders]
    return AdminCustomerDetail(**customer, credit_balance=credits["balance"], credits=credits, orders=shaped)


async def _customer(customer_id: str) -> dict:
    customer = await db.users.find_one({"id": customer_id, "role": "customer"}, CUSTOMER_FIELDS)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/admin/customers/{customer_id}", response_model=AdminCustomerDetail)
async def customer_detail(customer_id: str, _: dict = Depends(require_super_admin)):
    return await _detail(await _customer(customer_id))


@router.post("/admin/customers/{customer_id}/store-credit", response_model=AdminCustomerDetail, status_code=201)
async def issue_store_credit(customer_id: str, input: StoreCreditIssue, background_tasks: BackgroundTasks, admin: dict = Depends(require_super_admin)):
    customer = await _customer(customer_id)
    grant = await issue_credit(customer["id"], input.amount, admin.get("id"))
    background_tasks.add_task(_email_customer, customer, grant)
    return await _detail(customer)


async def _email_customer(customer: dict, grant: dict) -> None:
    if not customer.get("email"):
        return
    amount = f"₹{grant['amount']:,}"
    expires = grant["expires_at"].strftime("%d %B %Y")
    html = (
        '<table role="presentation" width="100%"><tr><td style="padding:28px;font-family:Arial,sans-serif;color:#261c19">'
        f'<p>Hi {escape(customer.get("name") or "there")},</p>'
        f'<h1 style="font:30px Georgia,serif;margin:0 0 12px">{escape(amount)} SAFYRA Credit has been added to your account.</h1>'
        f'<p>You can use it on your next order at checkout: just tick “Use my SAFYRA Credit”. It is valid until <strong>{escape(expires)}</strong>.</p>'
        '<p>Sign in to your SAFYRA account to see your balance at any time.</p></td></tr></table>'
    )
    try:
        await send_email(to=str(customer["email"]), subject=f"{amount} SAFYRA Credit added to your account", html=html)
    except Exception as exc:  # the credit is issued either way
        logger.error("Store credit email failed for %s: %s", customer["id"], exc)
