"""Admin-only cancellation: requires a reason of at least five characters, is unavailable to
customers, is recorded in history, blocks further management updates, and cannot cancel a
delivered order."""
from tests.helpers_order import create_order_request


def test_cancellation_requires_min_length_reason(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    short = admin_client.post(f"/order-requests/{number}/cancel", json={"reason": "bad"})
    assert short.status_code == 422, f"short reason expected 422, got {short.status_code}: {short.text[:300]}"


def test_customer_cannot_cancel(client, customer_client):
    created = create_order_request(client)
    number = created["request_number"]

    resp = customer_client.post(f"/order-requests/{number}/cancel", json={"reason": "tscheck customer attempt"})
    assert resp.status_code == 403, f"customer cancel expected 403, got {resp.status_code}: {resp.text[:300]}"


def test_cancellation_recorded_and_blocks_further_updates(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    cancel = admin_client.post(f"/order-requests/{number}/cancel", json={"reason": "tscheck valid reason text"})
    assert cancel.status_code == 200, f"cancel failed: {cancel.status_code} {cancel.text[:300]}"
    body = cancel.json()
    assert body["cancelled"] is True
    assert body["cancellation_reason"] == "tscheck valid reason text"
    assert any(e["event"] == "cancelled" for e in body["history"]), "cancellation not recorded in history"

    blocked_update = admin_client.patch(f"/order-requests/{number}", json={"courier_name": "tscheck-should-fail"})
    assert blocked_update.status_code == 409, f"update after cancel expected 409, got {blocked_update.status_code}: {blocked_update.text[:300]}"


def test_cannot_cancel_delivered_order(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    admin_client.patch(f"/order-requests/{number}", json={"payment_status": "Paid", "payment_verified": True})
    for status in ["Confirmed", "Processing", "Ready to ship", "Shipped", "Delivered"]:
        step = admin_client.patch(f"/order-requests/{number}", json={"fulfilment_status": status})
        assert step.status_code == 200, f"advancing to {status} failed: {step.status_code} {step.text[:300]}"

    cancel = admin_client.post(f"/order-requests/{number}/cancel", json={"reason": "tscheck delivered attempt"})
    assert cancel.status_code == 409, f"cancelling delivered order expected 409, got {cancel.status_code}: {cancel.text[:300]}"
