"""Shared helper for tests that need a disposable order request created against a real
approved catalog product."""
import uuid


def create_order_request(client, suffix: str | None = None) -> dict:
    suffix = suffix or uuid.uuid4().hex[:8]
    products = client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors") and p.get("availability") != "Currently unavailable")
    payload = {
        "name": f"tscheck-order-{suffix}",
        "email": f"tscheck-order-{suffix}@example.com",
        "phone": "9876543210",
        "address": "221B Baker Street, near Hazratganj",
        "city": "Lucknow",
        "state_region": "Uttar Pradesh",
        "postal_code": "226001",
        "country": "India",
        "country_code": "IN",
        "shipping": "india",
        "note": f"tscheck note {suffix}",
        "items": [{
            "product_id": product["id"],
            "size": product["sizes"][0],
            "color": product["colors"][0],
            "quantity": 1,
        }],
    }
    resp = client.post("/order-requests", json=payload)
    assert resp.status_code == 201, f"order request create failed: {resp.status_code} {resp.text[:300]}"
    return {"request_number": resp.json()["request_number"], "payload": payload}
