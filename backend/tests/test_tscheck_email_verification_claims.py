"""Verified email safely claims eligible guest orders: email verification tokens are stored
hashed, expire after 24 hours and are single-use; confirming the exact matching email links
only eligible paid guest orders (and their invoices) to that account. Tokens are seeded
directly into the real DB with a known plaintext (mirroring exactly what POST /email-
verification/send would create) so this test can exercise /confirm without ever triggering
the real outbound verification email."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
import uuid

from tests.conftest import signup_customer
from tests.helpers_order import create_order_request


def _insert_token(mongo_db, user_id: str, email: str, *, expires_delta: timedelta, used_at=None) -> str:
    token = secrets.token_urlsafe(40)
    now = datetime.now(timezone.utc)
    mongo_db.email_verification_tokens.insert_one({
        "token_hash": sha256(token.encode()).hexdigest(), "user_id": user_id, "email": email,
        "created_at": now, "expires_at": now + expires_delta, "used_at": used_at,
    })
    return token


def test_verification_claims_eligible_paid_guest_order_and_token_is_hashed_single_use(client, admin_client, mongo_db):
    suffix = uuid.uuid4().hex[:8]
    email = f"tscheck-verify-{suffix}@example.com"

    # A guest places and pays for an order with no account yet.
    guest_order = create_order_request(client, suffix=f"verify-{suffix}", email=email)
    paid = admin_client.patch(f"/order-requests/{guest_order['request_number']}", json={"payment_status": "Paid", "payment_verified": True})
    assert paid.status_code == 200, f"mark paid failed: {paid.status_code} {paid.text[:300]}"

    signup = signup_customer(client, f"tscheck verify {suffix}", email, "Tscheck!Pass123")
    assert signup.status_code == 201, f"signup failed: {signup.status_code} {signup.text[:300]}"
    user_id = signup.json()["user"]["id"]
    assert signup.json()["user"]["email_verified"] is False

    try:
        # The real token is never persisted in plaintext.
        token = _insert_token(mongo_db, user_id, email, expires_delta=timedelta(hours=24))
        stored = mongo_db.email_verification_tokens.find_one({"user_id": user_id, "used_at": None})
        assert stored["token_hash"] == sha256(token.encode()).hexdigest()
        assert token not in str(stored), "the plaintext token must never be stored alongside its hash"

        confirm = client.post("/email-verification/confirm", json={"token": token})
        assert confirm.status_code == 200, f"confirm failed: {confirm.status_code} {confirm.text[:300]}"
        body = confirm.json()
        assert body["verified"] is True
        assert body["claimed_orders"] == 1, f"exactly the one eligible paid guest order should be claimed, got {body}"

        claimed_order = mongo_db.order_requests.find_one({"request_number": guest_order["request_number"]}, {"_id": 0})
        assert claimed_order["customer_id"] == user_id, "the paid guest order should now be linked to the verified account"

        # Single-use: replaying the same (now-used) token is rejected.
        replay = client.post("/email-verification/confirm", json={"token": token})
        assert replay.status_code == 400, f"a used verification token must be rejected on replay, got {replay.status_code}"

        # Expired tokens are rejected even though otherwise valid.
        expired_token = _insert_token(mongo_db, user_id, email, expires_delta=timedelta(hours=-1))
        expired_resp = client.post("/email-verification/confirm", json={"token": expired_token})
        assert expired_resp.status_code == 400, f"an expired verification token must be rejected, got {expired_resp.status_code}"

        # An unrelated/garbage token is rejected too.
        garbage_resp = client.post("/email-verification/confirm", json={"token": secrets.token_urlsafe(40)})
        assert garbage_resp.status_code == 400
    finally:
        mongo_db.email_verification_tokens.delete_many({"user_id": user_id})
        mongo_db.users.delete_one({"id": user_id})
        mongo_db.order_requests.delete_one({"request_number": guest_order["request_number"]})
