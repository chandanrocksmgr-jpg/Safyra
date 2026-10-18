"""GST invoice per-item rules on a real production-shaped PayU order: a signed PayU `success`
webhook callback is simulated server-side (using the server's own PAYU_SALT secret to compute
the response hash exactly as our own webhook verifier requires) so the order genuinely transits
Payment pending -> Paid -> Confirmed through the production code path (_mark_paid ->
generate_invoice_for_order) -- never calling the real PayU gateway and never authorising any
charge. Verifies: same-state orders split CGST+SGST (equal halves) and other-state orders use
IGST; the per-item GST rate follows actual selling price (<=2500 -> 5%, >2500 -> 18%); and the
customer's own paid order/invoice is visible while a different customer cannot see it.
"""
import hashlib
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

from tests.conftest import rebind_session_cookie, signup_customer

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
PAYU_KEY = os.environ["PAYU_KEY"]
PAYU_SALT = os.environ["PAYU_SALT"]


def _sha512(value: str) -> str:
    return hashlib.sha512(value.encode("utf-8")).hexdigest()


def _response_hash(payload: dict) -> str:
    values = [
        PAYU_SALT, payload.get("status", ""), "", "", "", "", "",
        payload.get("udf5", ""), payload.get("udf4", ""), payload.get("udf3", ""),
        payload.get("udf2", ""), payload.get("udf1", ""), payload.get("email", ""),
        payload.get("firstname", ""), payload.get("productinfo", ""), payload.get("amount", ""),
        payload.get("txnid", ""), payload.get("key", ""),
    ]
    return _sha512("|".join(values))


def _india_payload(suffix: str, email: str, product: dict, state_region: str) -> dict:
    return {
        "name": f"tscheck-gst-{suffix}", "email": email, "phone": "9876543210",
        "address": "1 MG Road", "city": "Lucknow", "state_region": state_region,
        "postal_code": "226003", "country": "India", "country_code": "IN", "shipping": "india",
        "items": [{"product_id": product["id"], "size": product["sizes"][0], "color": product["colors"][0], "quantity": 1}],
    }


def _create_and_pay_india_order(client, admin_client, mongo_db, suffix: str, email: str, product: dict, state_region: str) -> dict:
    payload = _india_payload(suffix, email, product, state_region)
    create_resp = client.post("/payments/create", json=payload)
    assert create_resp.status_code == 201, f"PayU create expected 201, got {create_resp.status_code}: {create_resp.text[:300]}"
    body = create_resp.json()
    txn_id = body["transaction_id"]
    doc = mongo_db.order_requests.find_one({"payment_transaction_id": txn_id}, {"_id": 0})
    assert doc, "PayU order request should exist right after creation"

    webhook_payload = {
        "key": PAYU_KEY, "txnid": txn_id, "amount": f"{doc['total']:.2f}",
        "productinfo": doc["payu_productinfo"], "firstname": doc["name"], "email": doc["email"],
        "udf1": doc["id"], "udf2": "", "udf3": "", "udf4": "", "udf5": "",
        "status": "success", "mihpayid": f"tscheck-mihpay-{suffix}",
    }
    webhook_payload["hash"] = _response_hash(webhook_payload)
    webhook_resp = client.post("/payu/webhook", data=webhook_payload)
    assert webhook_resp.status_code == 200, f"simulated signed webhook expected 200, got {webhook_resp.status_code}: {webhook_resp.text[:300]}"

    final = mongo_db.order_requests.find_one({"payment_transaction_id": txn_id}, {"_id": 0})
    assert final["payment_status"] == "Paid", f"webhook should have marked the order Paid, got {final['payment_status']}"
    order = mongo_db.orders.find_one({"source_request_id": final["id"]}, {"_id": 0})
    assert order, "a Paid PayU order should be auto-converted to a real order"
    return {"request": final, "order": order, "product": product, "txn_id": txn_id}


def test_signed_webhook_marks_paid_and_issues_statewise_invoice(client, admin_client, mongo_db):
    suffix = uuid.uuid4().hex[:8]
    products = admin_client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors") and p.get("availability") != "Currently unavailable")

    # Tampered/unsigned webhook must be rejected (400) before we trust any state transition.
    bad_payload = {"key": PAYU_KEY, "txnid": "tscheck-no-such-txn", "amount": "1.00", "status": "success", "hash": "deadbeef"}
    bad_resp = client.post("/payu/webhook", data=bad_payload)
    assert bad_resp.status_code in (400, 404), f"unsigned/invalid webhook expected 400/404, got {bad_resp.status_code}: {bad_resp.text[:300]}"

    intra = _create_and_pay_india_order(client, admin_client, mongo_db, f"intra-{suffix}", f"tscheck-gst-intra-{suffix}@example.com", product, "Uttar Pradesh")
    inter = _create_and_pay_india_order(client, admin_client, mongo_db, f"inter-{suffix}", f"tscheck-gst-inter-{suffix}@example.com", product, "Maharashtra")

    assert intra["order"]["invoice_status"] == "issued", f"same-state paid order should have an issued invoice, got {intra['order'].get('invoice_status')}"
    assert inter["order"]["invoice_status"] == "issued", f"other-state paid order should have an issued invoice, got {inter['order'].get('invoice_status')}"

    intra_invoice = mongo_db.invoices.find_one({"order_id": intra["order"]["id"], "document_type": "invoice"}, {"_id": 0})
    inter_invoice = mongo_db.invoices.find_one({"order_id": inter["order"]["id"], "document_type": "invoice"}, {"_id": 0})
    assert intra_invoice and inter_invoice, "both paid orders should have exactly one invoice document"

    assert intra_invoice["cgst"] > 0 and intra_invoice["sgst"] > 0 and intra_invoice["igst"] == 0, f"same-state invoice should split CGST+SGST only, got {intra_invoice}"
    assert abs(intra_invoice["cgst"] - intra_invoice["sgst"]) <= 1, f"CGST and SGST should be (near-)equal halves, got {intra_invoice}"
    assert inter_invoice["igst"] > 0 and inter_invoice["cgst"] == 0 and inter_invoice["sgst"] == 0, f"other-state invoice should use IGST only, got {inter_invoice}"

    # Per-item GST rate follows actual selling price (<=2500 -> 5%, >2500 -> 18%).
    item = intra_invoice["items"][0]
    expected_rate = 5 if item["price"] <= 2500 else 18
    assert item["gst_rate"] == expected_rate, f"item at price {item['price']} should use {expected_rate}% GST, got {item['gst_rate']}%"
    assert item.get("hsn_code"), "invoice line item should carry an HSN code"


def test_customer_sees_own_invoice_other_customer_cannot(client, admin_client, mongo_db):
    suffix = uuid.uuid4().hex[:8]
    products = admin_client.get("/products").json()
    product = next(p for p in products if p.get("sizes") and p.get("colors") and p.get("availability") != "Currently unavailable")

    owner_email = f"tscheck-gst-owner-{suffix}@example.com"
    other_email = f"tscheck-gst-other-{suffix}@example.com"
    owner_signup = signup_customer(client, f"tscheck gst owner {suffix}", owner_email, "Tscheck!Pass123")
    assert owner_signup.status_code == 201, f"owner signup failed: {owner_signup.status_code} {owner_signup.text[:300]}"

    result = _create_and_pay_india_order(client, admin_client, mongo_db, suffix, owner_email, product, "Uttar Pradesh")
    order_id = result["order"]["id"]
    owner_id = owner_signup.json()["user"]["id"]
    mongo_db.orders.update_one({"id": order_id}, {"$set": {"customer_id": owner_id}})
    mongo_db.invoices.update_one({"order_id": order_id, "document_type": "invoice"}, {"$set": {"customer_id": owner_id}})
    invoice = mongo_db.invoices.find_one({"order_id": order_id, "document_type": "invoice"}, {"_id": 0})
    assert invoice, "paid order should have an issued invoice"

    login = client.post("/auth/login", json={"email": owner_email, "password": "Tscheck!Pass123"})
    assert login.status_code == 200
    rebind_session_cookie(client, login)
    owner_pdf = client.get(f"/invoices/{invoice['id']}/pdf")
    assert owner_pdf.status_code == 200, f"owner should be able to fetch their own invoice PDF, got {owner_pdf.status_code}: {owner_pdf.text[:300]}"
    assert owner_pdf.headers["content-type"] == "application/pdf"

    other_signup = signup_customer(client, f"tscheck gst other {suffix}", other_email, "Tscheck!Pass123")
    assert other_signup.status_code == 201
    other_pdf = client.get(f"/invoices/{invoice['id']}/pdf")
    assert other_pdf.status_code in (403, 404), f"a different customer must not access someone else's invoice PDF, got {other_pdf.status_code}: {other_pdf.text[:300]}"
