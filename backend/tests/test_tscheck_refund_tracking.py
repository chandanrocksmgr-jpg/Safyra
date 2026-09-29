"""Exceptional refund tracking: only paid orders can enter refund processing; reason and a
positive amount are required; Refunded requires explicit completion confirmation and cannot be
reversed; a reference is stored when provided."""
from tests.helpers_order import create_order_request


def test_unpaid_order_cannot_enter_refund_processing(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    resp = admin_client.patch(f"/order-requests/{number}", json={"refund_status": "Processing", "refund_reason": "tscheck reason", "refund_amount": 100})
    assert resp.status_code == 409, f"unpaid refund expected 409, got {resp.status_code}: {resp.text[:300]}"


def test_refund_requires_reason_and_positive_amount(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]
    admin_client.patch(f"/order-requests/{number}", json={"payment_status": "Paid", "payment_verified": True})

    missing_reason = admin_client.patch(f"/order-requests/{number}", json={"refund_status": "Processing", "refund_amount": 100})
    assert missing_reason.status_code == 422, f"missing reason expected 422, got {missing_reason.status_code}: {missing_reason.text[:300]}"

    zero_amount = admin_client.patch(f"/order-requests/{number}", json={"refund_status": "Processing", "refund_reason": "tscheck reason", "refund_amount": 0})
    assert zero_amount.status_code == 422, f"zero amount expected 422, got {zero_amount.status_code}: {zero_amount.text[:300]}"


def test_refunded_requires_confirmation_and_cannot_reverse(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]
    admin_client.patch(f"/order-requests/{number}", json={"payment_status": "Paid", "payment_verified": True})

    processing = admin_client.patch(f"/order-requests/{number}", json={
        "refund_status": "Processing", "refund_reason": "tscheck damaged item", "refund_amount": 500,
    })
    assert processing.status_code == 200, f"processing failed: {processing.status_code} {processing.text[:300]}"

    no_confirm = admin_client.patch(f"/order-requests/{number}", json={"refund_status": "Refunded"})
    assert no_confirm.status_code == 422, f"refunded without confirmation expected 422, got {no_confirm.status_code}: {no_confirm.text[:300]}"

    confirmed = admin_client.patch(f"/order-requests/{number}", json={
        "refund_status": "Refunded", "refund_confirmed": True, "refund_reference": "tscheck-ref-9001",
    })
    assert confirmed.status_code == 200, f"confirmed refund failed: {confirmed.status_code} {confirmed.text[:300]}"
    body = confirmed.json()
    assert body["refund_status"] == "Refunded"
    assert body["refund_confirmed_at"]
    assert body["refund_reference"] == "tscheck-ref-9001"

    reversal = admin_client.patch(f"/order-requests/{number}", json={"refund_status": "Processing"})
    assert reversal.status_code == 409, f"reversing Refunded expected 409, got {reversal.status_code}: {reversal.text[:300]}"
