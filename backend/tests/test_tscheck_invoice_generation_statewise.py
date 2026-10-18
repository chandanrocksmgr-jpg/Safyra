"""Paid-order invoice generation and account access, exercised against isolated temporary
GST settings and temporary paid orders: a PDF invoice is generated exactly once (idempotent),
with CGST+SGST when the buyer's state matches the seller's registered state and IGST for any
other state, it is linked into the owning customer's My Account, and an unrelated customer
cannot fetch someone else's invoice. All temporary settings/orders/users are restored/removed."""
import uuid

from tests.conftest import login_customer, signup_customer
from tests.helpers_order import create_order_request


def _mark_paid_and_confirm(admin_client, request_number: str) -> None:
    verify = admin_client.patch(f"/order-requests/{request_number}", json={"payment_status": "Paid", "payment_verified": True})
    assert verify.status_code == 200, f"mark paid failed: {verify.status_code} {verify.text[:300]}"
    confirm = admin_client.patch(f"/order-requests/{request_number}", json={"fulfilment_status": "Confirmed"})
    assert confirm.status_code == 200, f"confirm fulfilment failed: {confirm.status_code} {confirm.text[:300]}"


def _convert(admin_client, request_number: str) -> dict:
    resp = admin_client.post(f"/order-requests/{request_number}/convert")
    assert resp.status_code == 200, f"convert failed: {resp.status_code} {resp.text[:300]}"
    return resp.json()


def test_invoice_tax_split_intra_vs_inter_state_and_idempotent(client, admin_client, mongo_db, temp_complete_gst_settings):
    suffix = uuid.uuid4().hex[:8]

    intra = create_order_request(client, suffix=f"intra-{suffix}", state_region="Uttar Pradesh")
    inter = create_order_request(client, suffix=f"inter-{suffix}", state_region="Maharashtra")
    for request_number in (intra["request_number"], inter["request_number"]):
        _mark_paid_and_confirm(admin_client, request_number)

    intra_conversion = _convert(admin_client, intra["request_number"])
    inter_conversion = _convert(admin_client, inter["request_number"])

    intra_order = mongo_db.orders.find_one({"id": intra_conversion["order_id"]}, {"_id": 0})
    inter_order = mongo_db.orders.find_one({"id": inter_conversion["order_id"]}, {"_id": 0})
    assert intra_order["invoice_status"] == "issued", "same-state paid order should have an issued invoice"
    assert inter_order["invoice_status"] == "issued", "other-state paid order should have an issued invoice"

    intra_invoice = mongo_db.invoices.find_one({"order_id": intra_order["id"], "document_type": "invoice"}, {"_id": 0})
    inter_invoice = mongo_db.invoices.find_one({"order_id": inter_order["id"], "document_type": "invoice"}, {"_id": 0})
    assert intra_invoice and inter_invoice, "both orders should have exactly one invoice document"

    assert intra_invoice["cgst"] > 0 and intra_invoice["sgst"] > 0 and intra_invoice["igst"] == 0, f"same-state invoice should split CGST+SGST, got {intra_invoice}"
    assert intra_invoice["cgst"] == intra_invoice["sgst"], "CGST and SGST should be equal halves"
    assert inter_invoice["igst"] > 0 and inter_invoice["cgst"] == 0 and inter_invoice["sgst"] == 0, f"other-state invoice should use IGST only, got {inter_invoice}"
    assert intra_invoice["number"].startswith(temp_complete_gst_settings["invoice_prefix"] + "/")

    # Idempotency: re-converting (and running the bulk generator again) must not create a
    # second invoice or re-bump the sequence number for either order.
    repeat_conversion = _convert(admin_client, intra["request_number"])
    assert repeat_conversion["order_id"] == intra_conversion["order_id"]
    generate_resp = admin_client.post("/store-settings/generate-pending-invoices")
    assert generate_resp.status_code == 200
    assert mongo_db.invoices.count_documents({"order_id": intra_order["id"], "document_type": "invoice"}) == 1
    assert mongo_db.invoices.count_documents({"order_id": inter_order["id"], "document_type": "invoice"}) == 1

    # The PDF is downloadable by an admin.
    pdf_resp = admin_client.get(f"/invoices/{intra_invoice['id']}/pdf")
    assert pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF")

    # Cleanup the disposable order/invoice rows this test created (settings are restored by the fixture).
    for order in (intra_order, inter_order):
        mongo_db.orders.delete_one({"id": order["id"]})
        mongo_db.order_requests.delete_one({"id": order["source_request_id"]})
        mongo_db.invoices.delete_many({"order_id": order["id"]})


def test_invoice_pdf_is_protected_from_unrelated_customers(client, admin_client, mongo_db, temp_complete_gst_settings):
    suffix = uuid.uuid4().hex[:8]
    owner_email = f"tscheck-invoice-owner-{suffix}@example.com"
    other_email = f"tscheck-invoice-other-{suffix}@example.com"

    signup_owner = signup_customer(client, f"tscheck owner {suffix}", owner_email, "Tscheck!Pass123")
    signup_other = signup_customer(client, f"tscheck other {suffix}", other_email, "Tscheck!Pass123")
    assert signup_owner.status_code == 201, f"owner signup failed: {signup_owner.status_code} {signup_owner.text[:300]}"
    assert signup_other.status_code == 201, f"other signup failed: {signup_other.status_code} {signup_other.text[:300]}"
    owner_id = signup_owner.json()["user"]["id"]
    other_id = signup_other.json()["user"]["id"]

    order = create_order_request(client, suffix=f"protected-{suffix}", email=owner_email, state_region="Uttar Pradesh")
    _mark_paid_and_confirm(admin_client, order["request_number"])
    conversion = _convert(admin_client, order["request_number"])
    # Simulate a verified-email claim by directly linking the resulting order/invoice to the owner.
    mongo_db.orders.update_one({"id": conversion["order_id"]}, {"$set": {"customer_id": owner_id}})
    invoice = mongo_db.invoices.find_one({"order_id": conversion["order_id"], "document_type": "invoice"}, {"_id": 0})
    assert invoice, "paid order should have an issued invoice under complete temp settings"
    mongo_db.invoices.update_one({"id": invoice["id"]}, {"$set": {"customer_id": owner_id}})

    with_other = client.post("/auth/login", json={"email": other_email, "password": "Tscheck!Pass123"})
    assert with_other.status_code == 200
    client.cookies.set("safyra_session", with_other.cookies.get("safyra_session"))
    denied = client.get(f"/invoices/{invoice['id']}/pdf")
    assert denied.status_code == 404, f"an unrelated customer must not fetch another customer's invoice, got {denied.status_code}"
    client.cookies.clear()

    with_owner = client.post("/auth/login", json={"email": owner_email, "password": "Tscheck!Pass123"})
    assert with_owner.status_code == 200
    client.cookies.set("safyra_session", with_owner.cookies.get("safyra_session"))
    allowed = client.get(f"/invoices/{invoice['id']}/pdf")
    assert allowed.status_code == 200 and allowed.content.startswith(b"%PDF"), f"the owning customer must be able to fetch their own invoice, got {allowed.status_code}"
    client.cookies.clear()

    # Cleanup.
    mongo_db.orders.delete_one({"id": conversion["order_id"]})
    mongo_db.order_requests.delete_one({"request_number": order["request_number"]})
    mongo_db.invoices.delete_many({"order_id": conversion["order_id"]})
    mongo_db.users.delete_many({"id": {"$in": [owner_id, other_id]}})
