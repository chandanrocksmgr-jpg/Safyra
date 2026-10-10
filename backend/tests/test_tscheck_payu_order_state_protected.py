"""PayU order state is server protected: a created PayU order stays Payment pending until a
verified gateway response; unknown transaction ids return 404; a non-India payment quote
request returns 422; and Admin cannot manually flip a PayU order to Paid."""
import uuid

PRODUCT_ITEM_PAYLOAD = {
    "name": "Tscheck PayU Buyer",
    "phone": "9876501234",
    "address": "1 Test Lane",
    "city": "Lucknow",
    "state_region": "Uttar Pradesh",
    "postal_code": "226001",
}


def _india_approved_product(client) -> dict:
    products = client.get("/products").json()
    return next(p for p in products if p.get("sizes") and p.get("colors") and p.get("availability") != "Currently unavailable")


def _payment_payload(client, suffix: str, country_code: str = "IN", country: str = "India", shipping: str = "india") -> dict:
    product = _india_approved_product(client)
    return {
        **PRODUCT_ITEM_PAYLOAD,
        "email": f"tscheck-payu-{suffix}@example.com",
        "country": country,
        "country_code": country_code,
        "shipping": shipping,
        "note": "",
        "items": [{
            "product_id": product["id"], "set_type": None,
            "size": product["sizes"][0], "color": product["colors"][0], "quantity": 1,
        }],
    }


def test_created_payu_order_pending_until_verified_and_admin_cannot_force_paid(client, admin_client):
    suffix = uuid.uuid4().hex[:8]
    payload = _payment_payload(client, suffix)

    create_resp = client.post("/payments/create", json=payload)
    assert create_resp.status_code == 201, f"PayU create expected 201, got {create_resp.status_code}: {create_resp.text[:300]}"
    body = create_resp.json()
    assert body["action"] == "https://secure.payu.in/_payment" or "payu.in" in body["action"]
    txn_id = body["transaction_id"]
    request_number = body["request_number"]

    status_resp = client.get(f"/payments/{txn_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending", "newly created PayU order must remain pending without a verified callback"

    # Admin cannot manually mark a PayU order Paid.
    admin_attempt = admin_client.patch(f"/order-requests/{request_number}", json={"payment_status": "Paid", "payment_verified": True})
    assert admin_attempt.status_code == 409, f"manual PayU Paid override expected 409, got {admin_attempt.status_code}: {admin_attempt.text[:300]}"

    # Still pending after the rejected admin attempt.
    still_pending = client.get(f"/payments/{txn_id}")
    assert still_pending.json()["status"] == "pending"


def test_unknown_transaction_id_returns_404(client):
    resp = client.get(f"/payments/tscheck-unknown-txn-{uuid.uuid4().hex[:10]}")
    assert resp.status_code == 404, f"unknown transaction id expected 404, got {resp.status_code}: {resp.text[:300]}"


def test_non_india_payment_quote_returns_422(client):
    suffix = uuid.uuid4().hex[:8]
    payload = _payment_payload(client, suffix, country_code="US", country="United States", shipping="international")

    resp = client.post("/payments/quote", json=payload)
    assert resp.status_code == 422, f"non-India PayU quote expected 422, got {resp.status_code}: {resp.text[:300]}"
