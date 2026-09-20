"""Admin catalog product maintenance: create, update, delete a product via /api/products."""
import uuid


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


def test_admin_can_create_update_and_delete_product(client):
    suffix = uuid.uuid4().hex[:8]
    payload = _fixture_payload(suffix)

    # Create
    create_resp = client.post("/products", json=payload)
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

    # Update (edit)
    patch_resp = client.patch(f"/products/{product_id}", json={"stock": 12, "description": "Updated description tscheck"})
    assert patch_resp.status_code == 200, f"PATCH /products/{{id}} expected 200, got {patch_resp.status_code}: {patch_resp.text[:300]}"
    updated = patch_resp.json()
    assert updated["stock"] == 12
    assert updated["description"] == "Updated description tscheck"

    # Confirm update persisted via GET single product
    get_resp = client.get(f"/products/{product_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["stock"] == 12

    # Delete
    delete_resp = client.delete(f"/products/{product_id}")
    assert delete_resp.status_code in (200, 204), f"DELETE /products/{{id}} expected 200/204, got {delete_resp.status_code}: {delete_resp.text[:300]}"

    # Confirm deletion
    list_resp_after = client.get("/products")
    ids_after = [p["id"] for p in list_resp_after.json()]
    assert product_id not in ids_after, "deleted product still present in GET /products"
