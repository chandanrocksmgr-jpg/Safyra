"""Shared helper for tests that need a disposable order request created against a real
approved catalog product.

NOTE: India deliveries must now go through the PayU-hosted checkout (POST /payments/create)
and start life as "Payment pending" -- direct POST /order-requests for India now correctly
returns 422 ("India orders must use secure PayU checkout"). Tests that only need a plain,
immediately-unpaid OrderRequest (not specifically exercising PayU) use an international
(non-India) destination here, which still goes through the assisted /order-requests path."""
import uuid


def create_order_request(client, suffix: str | None = None, *, email: str | None = None, state_region: str | None = None, discount_code: str | None = None) -> dict:
    suffix = suffix or uuid.uuid4().hex[:8]
    products = client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors") and p.get("availability") != "Currently unavailable")
    payload = {
        "name": f"tscheck-order-{suffix}",
        "email": email or f"tscheck-order-{suffix}@example.com",
        "phone": "12025550123",
        "address": "500 Market Street, Suite 12",
        "city": "Los Angeles",
        "state_region": state_region or "California",
        "postal_code": "90001",
        "country": "United States",
        "country_code": "US",
        "shipping": "international",
        "note": f"tscheck note {suffix}",
        "items": [{
            "product_id": product["id"],
            "size": product["sizes"][0],
            "color": product["colors"][0],
            "quantity": 1,
        }],
    }
    if discount_code:
        payload["discount_code"] = discount_code
    resp = client.post("/order-requests", json=payload)
    assert resp.status_code == 201, f"order request create failed: {resp.status_code} {resp.text[:300]}"
    return {"request_number": resp.json()["request_number"], "payload": payload, "product": product}
