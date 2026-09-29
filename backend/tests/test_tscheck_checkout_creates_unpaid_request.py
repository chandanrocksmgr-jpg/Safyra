"""Existing checkout/catalog preserved: the customer checkout flow still creates an unpaid
'Request received' order request with a request_number reference, and the public catalogue
remains exactly the four approved products (also covered by test_tscheck_catalog_integrity.py)."""
from tests.helpers_order import create_order_request


def test_checkout_creates_unpaid_request_received_order(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]
    assert number.startswith("SAF-REQ-"), f"unexpected request_number format: {number}"

    detail = admin_client.get(f"/order-requests/{number}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["payment_status"] == "Unpaid"
    assert body["fulfilment_status"] == "Request received"
    assert body["cancelled"] is False


def test_public_catalog_has_four_products(client):
    resp = client.get("/products")
    assert resp.status_code == 200
    assert len(resp.json()) == 4, f"expected exactly four public products, got {len(resp.json())}"
