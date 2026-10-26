"""Super Admin / Junior Admin boundary for the gift offer management APIs: a Junior Admin
session must be refused on the two Super-Admin-only gift offer endpoints (settings write and
the gift-eligible products list), while a Super Admin succeeds on the same calls."""
import os

import httpx
import pytest

from tests.conftest import API_URL, rebind_session_cookie

JUNIOR_EMAIL = os.environ.get("TSCHECK_JUNIOR_EMAIL", "junior@safyra.co")
JUNIOR_PASSWORD = os.environ.get("TSCHECK_JUNIOR_PASSWORD", "Safyra!Junior#2026")


@pytest.fixture
def junior_client():
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.post("/auth/admin/login", json={"email": JUNIOR_EMAIL, "password": JUNIOR_PASSWORD})
        assert resp.status_code == 200, f"junior admin login failed: {resp.status_code} {resp.text[:300]}"
        rebind_session_cookie(c, resp)
        yield c


def test_junior_admin_forbidden_on_gift_offer_apis(junior_client, admin_client):
    settings_resp = junior_client.put("/gift-offer/settings", json={"enabled": True, "product_id": ""})
    assert settings_resp.status_code == 403, f"junior admin PUT settings expected 403, got {settings_resp.status_code}: {settings_resp.text[:300]}"

    products_resp = junior_client.get("/gift-offer/products")
    assert products_resp.status_code == 403, f"junior admin GET products expected 403, got {products_resp.status_code}: {products_resp.text[:300]}"

    # Sanity: the same endpoints work for the Super Admin.
    super_products_resp = admin_client.get("/gift-offer/products")
    assert super_products_resp.status_code == 200, f"super admin GET products expected 200, got {super_products_resp.status_code}: {super_products_resp.text[:300]}"
