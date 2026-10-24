"""In-panel new-order alerts: the admin polls for unacknowledged paid orders and acknowledges them."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from lib.admin_alerts import alert_recipient
from lib.db import get_db
from lib.security import require_admin

router = APIRouter(prefix="/admin/order-alerts", tags=["admin-alerts"])


class AdminOrderAlert(BaseModel):
    id: str
    request_id: str
    request_number: str
    customer_name: str
    customer_mobile: str = ""
    total: int = 0
    item_count: int = 0
    payment_provider: str = ""
    created_at: datetime
    email_status: str = ""


class AdminOrderAlertList(BaseModel):
    alerts: list[AdminOrderAlert]
    alert_email: str = ""


class AdminOrderAlertAck(BaseModel):
    alert_ids: list[str] = Field(default_factory=list, max_length=100)


class AdminOrderAlertAckResult(BaseModel):
    acknowledged: int


@router.get("", response_model=AdminOrderAlertList)
async def list_order_alerts(_: dict = Depends(require_admin)):
    cursor = get_db().admin_order_alerts.find({"acknowledged_at": None}).sort("created_at", -1).limit(20)
    return AdminOrderAlertList(alerts=[AdminOrderAlert(**document) async for document in cursor], alert_email=alert_recipient())


@router.post("/ack", response_model=AdminOrderAlertAckResult)
async def acknowledge_order_alerts(input: AdminOrderAlertAck, admin: dict = Depends(require_admin)):
    """Empty alert_ids clears every pending alert (the 'dismiss all' action)."""
    query: dict = {"acknowledged_at": None}
    if input.alert_ids:
        query["id"] = {"$in": input.alert_ids}
    result = await get_db().admin_order_alerts.update_many(
        query, {"$set": {"acknowledged_at": datetime.now(timezone.utc), "acknowledged_by": admin["id"]}}
    )
    return AdminOrderAlertAckResult(acknowledged=result.modified_count)
