"""Duplicate-resistant order conversion: only a paid, confirmed, active (non-cancelled) request
converts; repeat conversion returns the same order id/reference and does not create a duplicate;
the original request reference is preserved and the conversion appears in internal history."""
from tests.helpers_order import create_order_request


def test_conversion_requires_paid_and_confirmed(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    blocked = admin_client.post(f"/order-requests/{number}/convert", json={})
    assert blocked.status_code == 409, f"unpaid/unconfirmed convert expected 409, got {blocked.status_code}: {blocked.text[:300]}"


def test_repeat_conversion_is_idempotent_and_preserves_reference(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    admin_client.patch(f"/order-requests/{number}", json={"payment_status": "Paid", "payment_verified": True})
    admin_client.patch(f"/order-requests/{number}", json={"fulfilment_status": "Confirmed"})

    first = admin_client.post(f"/order-requests/{number}/convert", json={})
    assert first.status_code == 200, f"first convert failed: {first.status_code} {first.text[:300]}"
    first_body = first.json()
    assert first_body["order_number"] == number, "original request reference must be preserved as order_number"

    second = admin_client.post(f"/order-requests/{number}/convert", json={})
    assert second.status_code == 200, f"second convert failed: {second.status_code} {second.text[:300]}"
    second_body = second.json()
    assert second_body["order_id"] == first_body["order_id"], "repeat conversion must return the same order id"
    assert second_body["order_number"] == first_body["order_number"]

    detail = admin_client.get(f"/order-requests/{number}").json()
    converted_events = [e for e in detail["history"] if e["event"] == "converted"]
    assert len(converted_events) == 1, f"expected exactly one conversion history entry, got {len(converted_events)}: {converted_events}"
    assert detail["converted_order_id"] == first_body["order_id"]
