"""Admin can run controlled offers: a coupon and an automatic discount can be scoped to a
product, and checkout-side pricing (lib.order_pricing.price_order_items, exercised through
POST /order-requests) validates a supplied code server-side and applies only the single best
eligible promotion -- never both stacked together."""
from datetime import datetime, timedelta, timezone

from tests.helpers_order import create_order_request


def _window():
    now = datetime.now(timezone.utc)
    return (now - timedelta(hours=1)).isoformat(), (now + timedelta(hours=2)).isoformat()


def test_admin_creates_coupon_and_automatic_offer_best_one_wins(client, admin_client, mongo_db):
    products = admin_client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors") and p.get("availability") != "Currently unavailable")
    starts_at, ends_at = _window()
    suffix = product["id"][:8]
    coupon_payload = {
        "name": f"tscheck offer coupon {suffix}", "promotion_type": "code", "code": f"TSCHK{suffix[:4].upper()}",
        "discount_type": "percentage", "value": 10, "minimum_subtotal": 0, "usage_limit": 5,
        "product_ids": [product["id"]], "collections": [], "starts_at": starts_at, "ends_at": ends_at, "status": "active",
    }
    automatic_payload = {**coupon_payload, "name": f"tscheck offer automatic {suffix}", "promotion_type": "automatic", "code": None, "value": 25}

    coupon_resp = admin_client.post("/discounts", json=coupon_payload)
    automatic_resp = admin_client.post("/discounts", json=automatic_payload)
    created_ids = []
    try:
        assert coupon_resp.status_code == 201, f"coupon create failed: {coupon_resp.status_code} {coupon_resp.text[:300]}"
        assert automatic_resp.status_code == 201, f"automatic create failed: {automatic_resp.status_code} {automatic_resp.text[:300]}"
        coupon = coupon_resp.json()
        automatic = automatic_resp.json()
        created_ids = [coupon["id"], automatic["id"]]
        assert coupon["effective_status"] == "active"
        assert automatic["effective_status"] == "active"

        # Non-admin cannot manage offers.
        anon_resp = client.get("/discounts")
        assert anon_resp.status_code in (401, 403), f"anonymous discount list expected 401/403, got {anon_resp.status_code}"

        # Pause/resume control works.
        pause_resp = admin_client.patch(f"/discounts/{coupon['id']}", json={"status": "paused"})
        assert pause_resp.status_code == 200 and pause_resp.json()["effective_status"] == "paused"
        resume_resp = admin_client.patch(f"/discounts/{coupon['id']}", json={"status": "active"})
        assert resume_resp.status_code == 200 and resume_resp.json()["effective_status"] == "active"

        # Checkout: supplying the coupon code applies only the single BEST eligible promotion
        # (the 25% automatic offer outranks the 10% coupon, even though the coupon was supplied).
        created = create_order_request(client, suffix=f"offers-{suffix}", discount_code=coupon["code"])
        request_number = created["request_number"]
        order = admin_client.get(f"/order-requests/{request_number}").json()
        assert len(order["discount_ids"]) == 1, f"expected exactly one applied promotion, got {order['discount_ids']}"
        assert order["discount_ids"][0] == automatic["id"], "the single best eligible promotion (25% automatic) should have been applied, not the 10% coupon"
        assert order["subtotal"] < order["regular_subtotal"], "a discount should have reduced the subtotal"
        expected_subtotal = order["regular_subtotal"] - round(order["regular_subtotal"] * 0.25)
        assert order["subtotal"] == expected_subtotal, f"expected 25% off subtotal {expected_subtotal}, got {order['subtotal']}"

        # An invalid/unknown coupon code is rejected server-side.
        bad_resp = client.post("/order-requests", json={**created["payload"], "email": f"tscheck-bad-{suffix}@example.com", "discount_code": "TSCHK-DOES-NOT-EXIST"})
        assert bad_resp.status_code == 422, f"invalid coupon code expected 422, got {bad_resp.status_code}: {bad_resp.text[:300]}"
    finally:
        # No DELETE endpoint exists for discounts; direct-DB cleanup removes the disposable rows.
        if created_ids:
            mongo_db.discounts.delete_many({"id": {"$in": created_ids}})
