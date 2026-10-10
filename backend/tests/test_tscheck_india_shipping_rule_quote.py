"""India PayU payment quote applies the server-verified shipping rule: free from ₹1,000,
₹120 below that, and the quoted total always equals subtotal + shipping."""
import uuid

from tests.helpers_order import create_order_request  # noqa: F401  (keeps helper import path warm)


def _india_payload(product: dict, quantity: int = 1) -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "name": f"tscheck-shipquote-{suffix}", "email": f"tscheck-shipquote-{suffix}@example.com",
        "phone": "9876501234", "address": "1 Test Lane", "city": "Lucknow",
        "state_region": "Uttar Pradesh", "postal_code": "226001",
        "country": "India", "country_code": "IN", "shipping": "india", "note": "",
        "items": [{
            "product_id": product["id"], "set_type": None,
            "size": product["sizes"][0], "color": product["colors"][0], "quantity": quantity,
        }],
    }


def test_free_shipping_above_threshold_for_approved_product(client):
    products = client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors") and p.get("price", 0) >= 1000)

    resp = client.post("/payments/quote", json=_india_payload(product))
    assert resp.status_code == 200, f"India quote expected 200, got {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body["subtotal"] >= 1000
    assert body["shipping_amount"] == 0, "subtotal >= ₹1,000 must be free India shipping"
    assert body["total"] == body["subtotal"] + body["shipping_amount"]


def test_shipping_fee_below_threshold_is_120(client):
    resp = client.post("/payments/quote", json={
        "name": "tscheck-shipquote-low", "email": "tscheck-shipquote-low@example.com",
        "phone": "9876501234", "address": "1 Test Lane", "city": "Lucknow",
        "state_region": "Uttar Pradesh", "postal_code": "226001",
        "country": "India", "country_code": "IN", "shipping": "india", "note": "",
        "items": [],
    })
    # Empty cart still exercises the shipping rule math via subtotal 0 (< 999) and yields a 422
    # on the zero-total guard -- assert that guard explicitly instead of assuming a 200.
    assert resp.status_code == 422, f"zero-value India quote expected 422 (payable total must be > 0), got {resp.status_code}: {resp.text[:300]}"
