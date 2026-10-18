"""My Account covers wishlist, past orders, invoices and tracking: a signed-in customer's
GET /account exposes their wishlist id list, and a paid order linked to that account shows the
Confirmed -> In production -> Quality check -> Shipped -> Delivered milestone trail plus an
issued invoice once GST settings are complete, alongside verified courier/tracking details."""
import uuid

from tests.conftest import signup_customer
from tests.helpers_order import create_order_request


def test_account_shows_wishlist_and_paid_order_with_tracking_and_invoice(client, admin_client, mongo_db, temp_complete_gst_settings):
    suffix = uuid.uuid4().hex[:8]
    email = f"tscheck-account-{suffix}@example.com"

    signup = signup_customer(client, f"tscheck account {suffix}", email, "Tscheck!Pass123")
    assert signup.status_code == 201, f"signup failed: {signup.status_code} {signup.text[:300]}"
    user_id = signup.json()["user"]["id"]

    products = admin_client.get("/products").json()
    wishlist_product = next(p for p in products if p.get("sizes"))
    state_resp = client.put("/account/state", json={"wishlist_ids": [wishlist_product["id"]], "cart": []})
    assert state_resp.status_code == 204, f"wishlist save failed: {state_resp.status_code} {state_resp.text[:300]}"

    order = create_order_request(client, suffix=f"account-{suffix}", email=email, state_region="Uttar Pradesh")
    paid = admin_client.patch(f"/order-requests/{order['request_number']}", json={"payment_status": "Paid", "payment_verified": True})
    assert paid.status_code == 200
    confirm = admin_client.patch(f"/order-requests/{order['request_number']}", json={"fulfilment_status": "Confirmed"})
    assert confirm.status_code == 200
    courier = admin_client.patch(f"/order-requests/{order['request_number']}", json={"courier_name": "tscheck Courier", "tracking_number": "TSCHK123456", "tracking_link": "https://track.example.com/TSCHK123456"})
    assert courier.status_code == 200
    shipped = admin_client.patch(f"/order-requests/{order['request_number']}", json={"fulfilment_status": "Shipped"})
    assert shipped.status_code == 200

    convert_resp = admin_client.post(f"/order-requests/{order['request_number']}/convert")
    assert convert_resp.status_code == 200
    order_id = convert_resp.json()["order_id"]
    mongo_db.orders.update_one({"id": order_id}, {"$set": {"customer_id": user_id}})
    invoice = mongo_db.invoices.find_one({"order_id": order_id, "document_type": "invoice"}, {"_id": 0})
    assert invoice, "a complete-GST paid order should have an issued invoice"
    mongo_db.invoices.update_one({"id": invoice["id"]}, {"$set": {"customer_id": user_id}})
    # Re-sync the customer's embedded order snapshot now that customer_id was backfilled directly.
    sync_resp = admin_client.patch(f"/order-requests/{order['request_number']}", json={"internal_notes": "tscheck resync"})
    assert sync_resp.status_code == 200

    try:
        account = client.get("/account")
        assert account.status_code == 200, f"GET /account failed: {account.status_code} {account.text[:300]}"
        body = account.json()
        assert wishlist_product["id"] in body["wishlist_ids"], "wishlist should be exposed on the account"

        account_order = next((o for o in body["orders"] if o["id"] == order_id), None)
        assert account_order, f"the paid order should appear in account order history, got ids {[o['id'] for o in body['orders']]}"
        assert account_order["invoice_id"] == invoice["id"]
        assert account_order["invoice_status"] == "issued"
        assert account_order["courier_name"] == "tscheck Courier"
        assert account_order["tracking_number"] == "TSCHK123456"

        labels = [step["label"] for step in account_order["tracking"]]
        assert labels == ["Order confirmed", "In production", "Quality check", "Shipped", "Delivered"]
        completed = {step["label"]: step["completed"] for step in account_order["tracking"]}
        assert completed["Order confirmed"] is True
        assert completed["Shipped"] is True
        assert completed["Delivered"] is False, "a Shipped-but-not-yet-Delivered order should not show Delivered as complete"
    finally:
        mongo_db.orders.delete_one({"id": order_id})
        mongo_db.order_requests.delete_one({"request_number": order["request_number"]})
        mongo_db.invoices.delete_many({"order_id": order_id})
        mongo_db.users.delete_one({"id": user_id})
