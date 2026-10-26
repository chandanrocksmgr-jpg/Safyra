"""Gift offer settings can be enabled without a chosen gift product (the reported production
bug was that this used to be rejected with 422). Verifies: enabling with an empty product_id is
accepted and reported back as enabled; GET /gift-offer/eligibility then explains the gift still
needs to be chosen; and a product_id that is not a marked gift product is still rejected with
422. Restores the real seeded settings (enabled, Chikankari Potli Pouch) in a finally block."""
import pytest

GIFT_PRODUCT_ID = "1325fb86-7c54-4b4a-9258-9d568e6102fc"


@pytest.fixture
def restore_gift_settings(admin_client):
    original = admin_client.get("/gift-offer/settings").json()
    try:
        yield original
    finally:
        restore_payload = {
            "enabled": original["enabled"], "product_id": original["product_id"],
            "threshold": original["threshold"], "low_stock_threshold": original["low_stock_threshold"],
            "headline": original["headline"], "subtext": original["subtext"], "terms": original["terms"],
        }
        resp = admin_client.put("/gift-offer/settings", json=restore_payload)
        assert resp.status_code == 200, f"restore failed: {resp.status_code} {resp.text[:300]}"
        assert resp.json()["product_id"] == GIFT_PRODUCT_ID


def test_enable_without_gift_is_accepted_and_reported_in_eligibility(client, admin_client, restore_gift_settings):
    original = restore_gift_settings
    payload = {
        "enabled": True, "product_id": "", "threshold": original["threshold"],
        "low_stock_threshold": original["low_stock_threshold"], "headline": original["headline"],
        "subtext": original["subtext"], "terms": original["terms"],
    }

    resp = admin_client.put("/gift-offer/settings", json=payload)
    assert resp.status_code == 200, f"enable without gift expected 200, got {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body["enabled"] is True
    assert body["product_id"] == "" or body["product_id"] is None

    elig = client.get("/gift-offer/eligibility", params={"subtotal": 9000})
    assert elig.status_code == 200, f"eligibility check failed: {elig.status_code} {elig.text[:300]}"
    elig_body = elig.json()
    assert elig_body["eligible"] is False, f"should not be eligible with no gift chosen, got {elig_body}"
    assert "chosen" in elig_body["reason"].lower() or "gift" in elig_body["reason"].lower(), f"reason should mention the gift needing to be chosen, got {elig_body['reason']}"
    assert not elig_body.get("product"), f"no product should be reported when none is chosen, got {elig_body.get('product')}"


def test_non_gift_product_id_still_rejected(admin_client, restore_gift_settings):
    original = restore_gift_settings
    products = admin_client.get("/products").json()
    non_gift_product = next(p for p in products if not p.get("is_gift"))

    payload = {
        "enabled": True, "product_id": non_gift_product["id"], "threshold": original["threshold"],
        "low_stock_threshold": original["low_stock_threshold"], "headline": original["headline"],
        "subtext": original["subtext"], "terms": original["terms"],
    }
    resp = admin_client.put("/gift-offer/settings", json=payload)
    assert resp.status_code == 422, f"non-gift product_id expected 422, got {resp.status_code}: {resp.text[:300]}"
