"""Admin sales trends (/analytics/sales) are built from verified commerce data: paid revenue,
paid orders, AOV, units, checkout-session-to-paid conversion, abandoned checkouts, a daily
trend, top products, discount performance and 7/30/90-day comparison controls -- and the
endpoint is admin-only."""


def test_sales_analytics_shape_and_comparison_windows(admin_client):
    for days in (7, 30, 90):
        resp = admin_client.get(f"/analytics/sales?days={days}")
        assert resp.status_code == 200, f"GET /analytics/sales?days={days} -> {resp.status_code}: {resp.text[:300]}"
        body = resp.json()
        assert body["days"] == days
        for metrics_key in ("current", "previous"):
            metrics = body[metrics_key]
            for field in ("revenue", "paid_orders", "average_order_value", "units_sold", "checkout_sessions", "conversion_rate", "abandoned_checkouts"):
                assert field in metrics, f"{metrics_key}.{field} missing from sales analytics response"
        assert "revenue_change" in body and "order_change" in body
        assert isinstance(body["trend"], list) and len(body["trend"]) == days
        assert all({"date", "revenue", "orders"} <= set(point) for point in body["trend"])
        assert isinstance(body["top_products"], list)
        assert isinstance(body["discounts"], list)
        if body["top_products"]:
            assert {"title", "units", "revenue"} <= set(body["top_products"][0])
        if body["discounts"]:
            assert {"name", "uses", "savings"} <= set(body["discounts"][0])


def test_sales_analytics_requires_admin(client):
    resp = client.get("/analytics/sales?days=30")
    assert resp.status_code in (401, 403), f"anonymous analytics access expected 401/403, got {resp.status_code}: {resp.text[:300]}"
