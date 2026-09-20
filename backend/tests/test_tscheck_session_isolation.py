"""Sessions are isolated and safe: cookie-only session, /auth/me null when signed out,
logout invalidates the server session, and a customer session cannot access admin routes."""
import uuid

from tests.conftest import rebind_session_cookie

CUSTOMER_EMAIL = "customer@safyra.co"
CUSTOMER_PASSWORD = "Safyra!Customer#2026"


def test_me_is_null_when_signed_out(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    assert resp.json() is None, "expected null user when no session cookie is present"


def test_logout_invalidates_server_session(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"tscheck-session-{suffix}@example.com"
    signup_resp = client.post(
        "/auth/signup",
        json={"name": "TS Check Session", "email": email, "password": "Tscheck!Pass901"},
    )
    assert signup_resp.status_code == 201, f"signup failed: {signup_resp.status_code} {signup_resp.text[:300]}"
    rebind_session_cookie(client, signup_resp)

    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json() is not None and me_resp.json()["email"] == email

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 204, f"logout expected 204, got {logout_resp.status_code}: {logout_resp.text[:300]}"

    me_after_logout = client.get("/auth/me")
    assert me_after_logout.status_code == 200
    assert me_after_logout.json() is None, "session should be invalidated server-side after logout"


def test_customer_session_cannot_access_admin_endpoints(client):
    login_resp = client.post("/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
    assert login_resp.status_code == 200, f"customer login failed: {login_resp.status_code} {login_resp.text[:300]}"
    rebind_session_cookie(client, login_resp)

    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "customer"

    # Customer session must be rejected by admin-only product mutation endpoint
    write_resp = client.post(
        "/products",
        json={
            "title": "tscheck-should-not-create",
            "slug": f"tscheck-should-not-create-{uuid.uuid4().hex[:6]}",
            "category": "Anarkali Sets",
            "collection": "Everyday Edit",
            "fabric": "Pure Kota Doria",
            "craft": "Handcrafted Chikankari",
            "price": 1000,
            "mrp": 1200,
            "stock": 1,
            "sizes": ["S"],
            "colors": ["Ivory"],
            "image_url": "https://example.com/x.jpg",
            "image_urls": ["https://example.com/x.jpg"],
            "description": "should be rejected",
            "fit": "",
            "measurements": "",
            "transparency": "",
            "lining": "",
            "care": "",
            "dispatch_days": "",
            "availability": "Made to order",
            "stock_by_size": {},
            "tags": [],
            "featured": False,
            "best_seller": False,
            "new_arrival": True,
        },
    )
    assert write_resp.status_code == 403, (
        f"customer session on admin-only route expected 403, got {write_resp.status_code}: {write_resp.text[:300]}"
    )
