"""Test/demo account cleanup criterion: the former demo customer customer@safyra.co can no
longer log in, while the seeded admin@safyra.co account remains fully functional.

Read-only: only POST /auth/login (rejected) and POST /auth/admin/login (accepted, via the
admin_client fixture) are exercised. No account, session or user record is created or mutated.
"""
import httpx


def test_demo_customer_login_is_rejected(client):
    resp = client.post("/auth/login", json={"email": "customer@safyra.co", "password": "Safyra!Customer#2026"})
    assert resp.status_code in (401, 400, 404), (
        f"former demo customer account should no longer authenticate, got {resp.status_code}: {resp.text[:300]}"
    )
    assert "safyra_session" not in resp.cookies, "demo customer must not receive a session cookie"


def test_admin_account_still_logs_in(admin_client):
    # admin_client fixture already performed the login and asserted 200; confirm the session works end to end
    resp = admin_client.get("/auth/me")
    assert resp.status_code == 200, f"admin session should be valid: {resp.status_code}: {resp.text[:300]}"
    me = resp.json()
    assert me.get("email") == "admin@safyra.co"
    assert me.get("role") == "admin"
