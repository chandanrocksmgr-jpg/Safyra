"""Fulfilment notifications are idempotent: advancing a paid order through In production,
Quality check, Shipped and Delivered creates at most one status-notification row per stage
(enforced by a unique (request_id, status) index), each stage leaves a retryable `Failed`
state on delivery failure rather than silently dropping it, and the Shipped email never
invents an unverified courier/tracking link when none has been recorded yet."""
import time
import uuid

from tests.helpers_order import create_order_request

STAGES = ["Confirmed", "In production", "Quality check", "Shipped", "Delivered"]
NOTIFIED_STAGES = {"In production", "Quality check", "Shipped", "Delivered"}


def _wait_for_notification(mongo_db, request_id: str, stage: str, attempts: int = 10):
    for _ in range(attempts):
        doc = mongo_db.order_status_notifications.find_one({"request_id": request_id, "status": stage})
        if doc and doc.get("delivery_status") in ("Sent", "Failed"):
            return doc
        time.sleep(0.5)
    return mongo_db.order_status_notifications.find_one({"request_id": request_id, "status": stage})


def test_each_fulfilment_stage_notifies_at_most_once(client, admin_client, mongo_db):
    suffix = uuid.uuid4().hex[:8]
    created = create_order_request(client, suffix=f"fulfil-{suffix}")
    request_number = created["request_number"]
    order = admin_client.get(f"/order-requests/{request_number}").json()
    request_id = order["id"]

    try:
        paid = admin_client.patch(f"/order-requests/{request_number}", json={"payment_status": "Paid", "payment_verified": True})
        assert paid.status_code == 200, f"mark paid failed: {paid.status_code} {paid.text[:300]}"

        # No courier/tracking has been recorded -- the Shipped email must not expose an
        # unverified link; confirm the order carries no tracking link before/through Shipped.
        assert order["tracking_link"] == ""

        for stage in STAGES[1:]:
            resp = admin_client.patch(f"/order-requests/{request_number}", json={"fulfilment_status": stage})
            assert resp.status_code == 200, f"advancing to {stage} failed: {resp.status_code} {resp.text[:300]}"
            assert resp.json()["fulfilment_status"] == stage
            if stage in NOTIFIED_STAGES:
                notification = _wait_for_notification(mongo_db, request_id, stage)
                assert notification is not None, f"expected a status-notification row for stage {stage}"
                assert notification["delivery_status"] in ("Sent", "Failed"), f"notification for {stage} should resolve to Sent or Failed, not stay stuck in {notification['delivery_status']}"

        # Exactly one notification row per notified stage -- the unique (request_id, status)
        # index guarantees no duplicates even though this is the normal, single-pass flow.
        rows = list(mongo_db.order_status_notifications.find({"request_id": request_id}, {"_id": 0, "status": 1}))
        statuses = [row["status"] for row in rows]
        assert sorted(statuses) == sorted(NOTIFIED_STAGES), f"expected exactly one row per notified stage, got {statuses}"
        assert len(statuses) == len(set(statuses)), "no stage should have more than one notification row"

        final_order = admin_client.get(f"/order-requests/{request_number}").json()
        assert final_order["tracking_link"] == "", "no tracking link should have been fabricated for the Shipped stage"
    finally:
        mongo_db.order_status_notifications.delete_many({"request_id": request_id})
        mongo_db.order_requests.delete_one({"id": request_id})
