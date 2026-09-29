"""Protected Admin order-request workspace: unauthenticated and customer access to the
order-requests admin APIs is denied; an authenticated admin can list/search/filter requests
and see full customer, address, item, quantity and note details."""
from tests.helpers_order import create_order_request


def test_unauthenticated_and_customer_access_denied(client, customer_client):
    resp = client.get("/order-requests")
    assert resp.status_code in (401, 403), f"unauthenticated list expected 401/403, got {resp.status_code}: {resp.text[:200]}"

    resp2 = customer_client.get("/order-requests")
    assert resp2.status_code == 403, f"customer list expected 403, got {resp2.status_code}: {resp2.text[:200]}"


def test_admin_can_search_filter_and_see_full_details(client, admin_client):
    created = create_order_request(client)
    request_number = created["request_number"]
    payload = created["payload"]

    search_resp = admin_client.get("/order-requests", params={"q": request_number})
    assert search_resp.status_code == 200, f"search failed: {search_resp.status_code} {search_resp.text[:300]}"
    rows = search_resp.json()
    assert any(r["request_number"] == request_number for r in rows), f"created request not found via search: {rows}"

    filter_resp = admin_client.get("/order-requests", params={"payment_status": "Unpaid"})
    assert filter_resp.status_code == 200
    assert any(r["request_number"] == request_number for r in filter_resp.json())

    detail_resp = admin_client.get(f"/order-requests/{request_number}")
    assert detail_resp.status_code == 200, f"detail fetch failed: {detail_resp.status_code} {detail_resp.text[:300]}"
    detail = detail_resp.json()
    assert detail["name"] == payload["name"]
    assert detail["address"] == payload["address"]
    assert detail["note"] == payload["note"]
    assert detail["items"][0]["product_id"] == payload["items"][0]["product_id"]
    assert detail["items"][0]["quantity"] == payload["items"][0]["quantity"]
