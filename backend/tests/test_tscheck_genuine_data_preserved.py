"""Genuine-data-preservation criterion: cleanup of test/QA data must not have touched the five
non-test order requests, the one non-test checkout session, or the four approved products.

Read-only: only GET /order-requests, GET /checkout-sessions and GET /products (admin-scoped)
are exercised. No order, checkout session or product is created, edited or deleted.
"""

APPROVED_TITLES = {
    "Luxury Nazakat Collection",
    "Aira Pure Kota Doria Angrakha",
    "Vaaya Pure Kota Doria Anarkali",
    "Sang-e-Mar-Mar — Rose Edition",
}
BANNED_PREFIXES = ("tscheck", "test", "debug", "placeholder", "qa")


def test_five_genuine_order_requests_remain(admin_client):
    resp = admin_client.get("/order-requests")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    orders = resp.json()

    assert len(orders) == 5, f"expected 5 genuine order requests, got {len(orders)}"
    for order in orders:
        email = (order.get("email") or order.get("customer_name") or "").lower()
        assert not email.startswith(BANNED_PREFIXES), f"test order leaked into admin: {order}"


def test_one_genuine_checkout_session_remains(admin_client):
    resp = admin_client.get("/checkout-sessions")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    payload = resp.json()
    sessions = payload["items"] if isinstance(payload, dict) and "items" in payload else payload

    assert len(sessions) == 1, f"expected exactly 1 genuine checkout session, got {len(sessions)}"
    session = sessions[0]
    email = (session.get("email") or "").lower()
    assert not email.startswith(BANNED_PREFIXES), f"test checkout session leaked: {session}"


def test_four_approved_products_unaltered_by_cleanup(admin_client):
    resp = admin_client.get("/products")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    products = resp.json()

    titles = {p["title"] for p in products}
    assert titles == APPROVED_TITLES, f"approved product set altered by cleanup: {titles}"
