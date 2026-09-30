"""Submission availability boundary criterion: a POST /order-requests attempt for the existing
'Currently unavailable' approved product (Sang-e-Mar-Mar) must be rejected before any row is
inserted. This test intentionally uses a request that is expected to FAIL server-side validation
-- it must never succeed, and must never be retried with a fix that would let it succeed.
"""
import uuid

UNAVAILABLE_TITLE = "Sang-e-Mar-Mar — Rose Edition"


def _unavailable_product(client):
    products = client.get("/products").json()
    product = next((p for p in products if p["title"] == UNAVAILABLE_TITLE), None)
    assert product is not None, "expected seeded unavailable product not found in /products"
    assert product["availability"] == "Currently unavailable"
    return product


def test_order_request_for_unavailable_product_is_rejected_without_insertion(client, admin_client):
    product = _unavailable_product(client)
    suffix = uuid.uuid4().hex[:8]
    request_name = f"tscheck-unavailable-{suffix}"
    # Unavailable products expose no purchasable sizes/colors publicly; probe with a plausible
    # size/colour value so the rejection is proven to come from the availability rule itself.
    payload = {
        "name": request_name,
        "email": f"tscheck-unavailable-{suffix}@example.com",
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
            "size": "M",
            "color": "Ivory",
            "quantity": 1,
        }],
    }

    resp = client.post("/order-requests", json=payload)
    assert resp.status_code in (400, 409, 422), (
        f"expected order-request submission for unavailable product to be rejected, "
        f"got {resp.status_code}: {resp.text[:300]}"
    )

    # Confirm no row was inserted under this fixture name (admin search by name substring, if
    # the search endpoint supports it) -- and definitely no request_number was ever returned.
    assert "request_number" not in resp.json() if resp.headers.get("content-type", "").startswith("application/json") else True

    search_resp = admin_client.get("/order-requests", params={"q": request_name})
    assert search_resp.status_code == 200
    rows = search_resp.json()
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    matching = [r for r in rows if r.get("name") == request_name or request_name in str(r)]
    assert not matching, f"unavailable-product order request must not be inserted, found: {matching}"
