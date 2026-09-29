"""Guarded payment and fulfilment states: unpaid requests cannot advance fulfilment beyond
Request received; Paid requires explicit payment_verified; paid requests can progress through
the fulfilment steps; a verified Paid status cannot be reversed."""
from tests.helpers_order import create_order_request


def test_unpaid_cannot_advance_fulfilment(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    resp = admin_client.patch(f"/order-requests/{number}", json={"fulfilment_status": "Confirmed"})
    assert resp.status_code == 409, f"unpaid fulfilment advance expected 409, got {resp.status_code}: {resp.text[:300]}"


def test_paid_requires_explicit_verification_then_allows_progress(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    no_verify = admin_client.patch(f"/order-requests/{number}", json={"payment_status": "Paid"})
    assert no_verify.status_code == 422, f"Paid without verification expected 422, got {no_verify.status_code}: {no_verify.text[:300]}"

    verify = admin_client.patch(
        f"/order-requests/{number}",
        json={"payment_status": "Paid", "payment_verified": True},
    )
    assert verify.status_code == 200, f"verified Paid expected 200, got {verify.status_code}: {verify.text[:300]}"
    body = verify.json()
    assert body["payment_status"] == "Paid"
    assert body["payment_verified_at"], "payment_verified_at should be set"

    advance = admin_client.patch(f"/order-requests/{number}", json={"fulfilment_status": "Confirmed"})
    assert advance.status_code == 200, f"paid fulfilment advance expected 200, got {advance.status_code}: {advance.text[:300]}"
    assert advance.json()["fulfilment_status"] == "Confirmed"

    advance2 = admin_client.patch(f"/order-requests/{number}", json={"fulfilment_status": "Shipped"})
    assert advance2.status_code == 200
    assert advance2.json()["fulfilment_status"] == "Shipped"

    reversal = admin_client.patch(f"/order-requests/{number}", json={"payment_status": "Unpaid"})
    assert reversal.status_code == 409, f"reversing verified Paid expected 409, got {reversal.status_code}: {reversal.text[:300]}"
