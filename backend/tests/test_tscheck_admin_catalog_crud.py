"""Admin catalog product maintenance (create/update/delete) and admin password/recovery controls.

Both groups of tests authenticate as the single seeded admin account and rotate its session/
password, so they are kept in one module: pytest-xdist's configured `--dist loadscope` schedules
an entire module onto a single worker, guaranteeing these run sequentially with no cross-worker
race on the shared admin account (a plain `xdist_group` marker does not override loadscope).
"""
import uuid

from tests.conftest import rebind_session_cookie

ADMIN_EMAIL = "admin@safyra.co"
ADMIN_SEED_PASSWORD = "Safyra!Admin#2026"
RECOVERY_ANSWER = "zardozi 1947"
TEMP_PASSWORD = "Tscheck!Temp#901"


def _fixture_payload(suffix: str) -> dict:
    return {
        "title": f"tscheck-admin-product-{suffix}",
        "slug": f"tscheck-admin-product-{suffix}",
        "category": "Anarkali Sets",
        "collection": "Everyday Edit",
        "fabric": "Pure Kota Doria",
        "craft": "Handcrafted Chikankari",
        "price": 2500,
        "mrp": 3000,
        "stock": 5,
        "sizes": ["S", "M", "L"],
        "colors": ["Ivory"],
        "image_url": "https://example.com/image.jpg",
        "image_urls": ["https://example.com/image.jpg"],
        "description": "A test product created by tscheck admin catalog CRUD test.",
        "fit": "Regular fit",
        "measurements": "",
        "transparency": "",
        "lining": "",
        "care": "Dry clean only",
        "dispatch_days": "12-15 business days",
        "availability": "Made to order",
        "stock_by_size": {},
        "tags": [],
        "featured": False,
        "best_seller": False,
        "new_arrival": True,
    }


def test_admin_can_create_update_and_delete_product(admin_client, client):
    suffix = uuid.uuid4().hex[:8]
    payload = _fixture_payload(suffix)

    # Unauthenticated write is rejected
    unauth_resp = client.post("/products", json=payload)
    assert unauth_resp.status_code == 401, (
        f"unauthenticated POST /products expected 401, got {unauth_resp.status_code}: {unauth_resp.text[:300]}"
    )

    # Create (as admin)
    create_resp = admin_client.post("/products", json=payload)
    assert create_resp.status_code in (200, 201), (
        f"POST /products expected 200/201, got {create_resp.status_code}: {create_resp.text[:300]}"
    )
    created = create_resp.json()
    product_id = created["id"]
    assert created["title"] == payload["title"]
    assert created["stock"] == 5

    # Verify it persists through GET /products
    list_resp = client.get("/products")
    assert list_resp.status_code == 200
    ids = [p["id"] for p in list_resp.json()]
    assert product_id in ids, "created product missing from GET /products"

    # Customer-authenticated write is rejected (403, role enforced)
    customer_login = client.post("/auth/login", json={"email": "customer@safyra.co", "password": "Safyra!Customer#2026"})
    assert customer_login.status_code == 200
    rebind_session_cookie(client, customer_login)
    customer_patch = client.patch(f"/products/{product_id}", json={"stock": 99})
    assert customer_patch.status_code == 403, (
        f"customer PATCH /products/{{id}} expected 403, got {customer_patch.status_code}: {customer_patch.text[:300]}"
    )

    # Update (edit) as admin
    patch_resp = admin_client.patch(f"/products/{product_id}", json={"stock": 12, "description": "Updated description tscheck"})
    assert patch_resp.status_code == 200, f"PATCH /products/{{id}} expected 200, got {patch_resp.status_code}: {patch_resp.text[:300]}"
    updated = patch_resp.json()
    assert updated["stock"] == 12
    assert updated["description"] == "Updated description tscheck"

    # Confirm update persisted via GET single product
    get_resp = client.get(f"/products/{product_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["stock"] == 12

    # Delete as admin
    delete_resp = admin_client.delete(f"/products/{product_id}")
    assert delete_resp.status_code in (200, 204), f"DELETE /products/{{id}} expected 200/204, got {delete_resp.status_code}: {delete_resp.text[:300]}"

    # Confirm deletion
    list_resp_after = client.get("/products")
    ids_after = [p["id"] for p in list_resp_after.json()]
    assert product_id not in ids_after, "deleted product still present in GET /products"


def test_admin_recovery_question_and_verified_reset_roundtrip(client):
    # Recovery question is available for the admin email
    question_resp = client.get("/auth/admin/recovery-question", params={"email": ADMIN_EMAIL})
    assert question_resp.status_code == 200, f"expected 200, got {question_resp.status_code}: {question_resp.text[:300]}"
    assert question_resp.json().get("question"), "recovery question should be non-empty"

    # Wrong answer is rejected
    wrong_resp = client.post(
        "/auth/admin/recover",
        json={"email": ADMIN_EMAIL, "answer": "definitely not the answer", "new_password": TEMP_PASSWORD},
    )
    assert wrong_resp.status_code == 400, f"expected 400 for wrong answer, got {wrong_resp.status_code}: {wrong_resp.text[:300]}"

    # Correct answer resets the password (policy-compliant new password)
    reset_resp = client.post(
        "/auth/admin/recover",
        json={"email": ADMIN_EMAIL, "answer": RECOVERY_ANSWER, "new_password": TEMP_PASSWORD},
    )
    assert reset_resp.status_code == 204, f"expected 204 for correct answer, got {reset_resp.status_code}: {reset_resp.text[:300]}"

    # New (temp) password now works
    login_temp = client.post("/auth/admin/login", json={"email": ADMIN_EMAIL, "password": TEMP_PASSWORD})
    assert login_temp.status_code == 200, f"login with reset password failed: {login_temp.status_code} {login_temp.text[:300]}"
    rebind_session_cookie(client, login_temp)

    # Restore the documented seed password via the authenticated change-password flow
    restore_resp = client.put(
        "/auth/password",
        json={"current_password": TEMP_PASSWORD, "new_password": ADMIN_SEED_PASSWORD},
    )
    assert restore_resp.status_code == 204, f"password restore failed: {restore_resp.status_code} {restore_resp.text[:300]}"

    # Seed password logs in again, confirming the restore
    login_seed = client.post("/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_SEED_PASSWORD})
    assert login_seed.status_code == 200, f"seed password no longer works after restore: {login_seed.status_code} {login_seed.text[:300]}"


def test_admin_current_password_change_flow(admin_client):
    # Authenticated admin can change the password and is signed out server-side
    change_resp = admin_client.put(
        "/auth/password",
        json={"current_password": ADMIN_SEED_PASSWORD, "new_password": TEMP_PASSWORD},
    )
    assert change_resp.status_code == 204, f"expected 204, got {change_resp.status_code}: {change_resp.text[:300]}"

    # Old session cookie is invalidated after password change
    me_after_change = admin_client.get("/auth/me")
    assert me_after_change.status_code == 200
    assert me_after_change.json() is None, "session should be invalidated after password change"

    # Restore the seed password so the fixture is reusable
    login_temp = admin_client.post("/auth/admin/login", json={"email": ADMIN_EMAIL, "password": TEMP_PASSWORD})
    assert login_temp.status_code == 200
    rebind_session_cookie(admin_client, login_temp)
    restore_resp = admin_client.put(
        "/auth/password",
        json={"current_password": TEMP_PASSWORD, "new_password": ADMIN_SEED_PASSWORD},
    )
    assert restore_resp.status_code == 204

    login_seed = admin_client.post("/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_SEED_PASSWORD})
    assert login_seed.status_code == 200


def test_admin_recovery_rate_limits_repeated_failures(client):
    synthetic_email = f"tscheck-recovery-{uuid.uuid4().hex[:8]}@example.com"
    last_status = None
    for _ in range(6):
        resp = client.post(
            "/auth/admin/recover",
            json={"email": synthetic_email, "answer": "wrong", "new_password": TEMP_PASSWORD},
        )
        last_status = resp.status_code
    assert last_status == 429, f"6th attempt within the window expected 429, got {last_status}"
