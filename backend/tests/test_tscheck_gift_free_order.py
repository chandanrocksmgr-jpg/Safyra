"""A qualifying first order (subtotal >= gift threshold) for a freshly-signed-up registered
customer gets the live gift product added automatically at price 0 through POST
/payments/create, without changing the order total: total == non-gift subtotal + shipping."""
import os
import uuid

import pytest

from tests.conftest import signup_customer

QUALIFYING_SLUG = "aira-pure-kota-doria-angrakha"


@pytest.fixture
def qualifying_product(client):
    products = client.get("/products").json()
    product = next(p for p in products if p.get("slug") == QUALIFYING_SLUG)
    assert "M" in product["sizes"] and "Blush petal" in product["colors"]
    return product


def test_first_qualifying_order_gets_free_gift_item(client, qualifying_product):
    suffix = uuid.uuid4().hex[:8]
    email = f"tscheck-gift-{suffix}@resend.dev"
    signup_resp = signup_customer(client, f"tscheck gift {suffix}", email, "Tscheck!Gift#2026")
    assert signup_resp.status_code == 201, f"signup failed: {signup_resp.status_code} {signup_resp.text[:300]}"

    settings = client.get("/gift-offer/settings")
    # settings endpoint is admin-only; use the public gift-offer doc + eligibility instead.
    elig = client.get("/gift-offer/eligibility", params={"subtotal": qualifying_product["price"]})
    assert elig.status_code == 200
    elig_body = elig.json()
    assert elig_body["eligible"] is True, f"expected eligible subtotal, got {elig_body}"
    gift_product_id = elig_body["product"]["id"]

    payload = {
        "name": f"tscheck-gift-order-{suffix}", "email": email, "phone": "9876543210",
        "address": "1 MG Road", "city": "Lucknow", "state_region": "Uttar Pradesh",
        "postal_code": "226003", "country": "India", "country_code": "IN", "shipping": "india",
        "items": [{"product_id": qualifying_product["id"], "size": "M", "color": "Blush petal", "quantity": 1}],
    }
    create_resp = client.post("/payments/create", json=payload)
    assert create_resp.status_code == 201, f"payments/create expected 201, got {create_resp.status_code}: {create_resp.text[:300]}"
    quote = create_resp.json()
    txn_id = quote["transaction_id"]

    from pymongo import MongoClient
    mongo_client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = mongo_client[os.environ.get("DB_NAME", "app")]
    try:
        doc = db.order_requests.find_one({"payment_transaction_id": txn_id}, {"_id": 0})
        assert doc, "order request should exist right after payments/create"
        gift_items = [item for item in doc["items"] if item.get("product_id") == gift_product_id]
        assert gift_items, f"expected the gift product {gift_product_id} among order items, got {[i.get('product_id') for i in doc['items']]}"
        assert gift_items[0]["price"] == 0, f"gift item should be priced 0, got {gift_items[0]['price']}"
        non_gift_subtotal = sum(item["price"] * item["quantity"] for item in doc["items"] if item.get("product_id") != gift_product_id)
        assert doc["total"] == non_gift_subtotal + doc["shipping_amount"], f"total {doc['total']} should equal non-gift subtotal {non_gift_subtotal} + shipping {doc['shipping_amount']}"
    finally:
        mongo_client.close()
