"""Shipping and internal management: admin-saved courier/shipping/tracking values persist,
and internal admin notes are never exposed via the customer-facing account/order snapshot."""
from tests.helpers_order import create_order_request


def test_shipping_fields_persist(client, admin_client):
    created = create_order_request(client)
    number = created["request_number"]

    save = admin_client.patch(f"/order-requests/{number}", json={
        "courier_name": "tscheck-courier",
        "shipping_details": "tscheck shipping details box",
        "tracking_number": "TSCHECKTRACK123",
        "tracking_link": "https://track.example.com/TSCHECKTRACK123",
        "internal_notes": "tscheck internal note, not for customers",
    })
    assert save.status_code == 200, f"save failed: {save.status_code} {save.text[:300]}"

    reread = admin_client.get(f"/order-requests/{number}")
    assert reread.status_code == 200
    body = reread.json()
    assert body["courier_name"] == "tscheck-courier"
    assert body["tracking_number"] == "TSCHECKTRACK123"
    assert body["tracking_link"] == "https://track.example.com/TSCHECKTRACK123"
    assert body["internal_notes"] == "tscheck internal note, not for customers"


def test_internal_notes_not_exposed_to_customer(client, admin_client, customer_client):
    me = customer_client.get("/auth/me").json()
    products = client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors"))
    payload = {
        "name": "tscheck privacy customer",
        "email": me["email"],
        "phone": "9876500000",
        "address": "1 Privacy Lane",
        "city": "Lucknow",
        "state_region": "Uttar Pradesh",
        "postal_code": "226001",
        "country": "India",
        "country_code": "IN",
        "shipping": "india",
        "note": "tscheck privacy note",
        "items": [{"product_id": product["id"], "size": product["sizes"][0], "color": product["colors"][0], "quantity": 1}],
    }
    create_resp = customer_client.post("/order-requests", json=payload)
    assert create_resp.status_code == 201, f"create failed: {create_resp.status_code} {create_resp.text[:300]}"
    number = create_resp.json()["request_number"]

    secret_note = "tscheck-secret-internal-note-should-not-leak"
    admin_client.patch(f"/order-requests/{number}", json={
        "payment_status": "Paid", "payment_verified": True, "internal_notes": secret_note,
    })
    admin_client.patch(f"/order-requests/{number}", json={"fulfilment_status": "Confirmed"})
    convert = admin_client.post(f"/order-requests/{number}/convert", json={})
    assert convert.status_code == 200, f"convert failed: {convert.status_code} {convert.text[:300]}"

    orders = customer_client.get("/account/orders")
    assert orders.status_code == 200
    matching = [o for o in orders.json() if o["order_number"] == number]
    assert matching, f"converted order snapshot missing from customer account: {orders.json()}"
    snapshot_text = str(matching[0])
    assert secret_note not in snapshot_text, "internal admin notes leaked into customer-facing order snapshot"
    assert "internal_notes" not in matching[0], "internal_notes field must not be present in customer order snapshot"
