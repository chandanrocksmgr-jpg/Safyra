"""Criterion: Product editor supports complete safe draft management.

Creates a temporary Draft product with size-level inventory and merchandising
controls, confirms it is visible to the admin list but absent from the public
/api/products feed, then deletes it without touching any existing product.
"""
import uuid




def _make_title():
    return f"tscheck-draft-product-{uuid.uuid4().hex[:8]}"


def test_draft_product_hidden_from_public_catalog(admin_client):
    title = _make_title()
    slug = title
    payload = {
        "title": title,
        "slug": slug,
        "status": "draft",
        "category": "Anarkali Sets",
        "collection": "Everyday Edit",
        "fabric": "Pure Kota Doria",
        "craft": "Hand Chikankari",
        "price": 2999,
        "mrp": 4999,
        "stock": 5,
        "sizes": ["S", "M"],
        "colors": ["Ivory"],
        "stock_by_size": {"S": 2, "M": 3},
        "image_url": "https://example.com/tscheck-draft.jpg",
        "image_urls": ["https://example.com/tscheck-draft.jpg"],
        "description": "tscheck draft product",
        "fit": "Regular fit",
        "measurements": "Length 44 in",
        "transparency": "Opaque",
        "lining": "Unlined",
        "care": "Dry clean only",
        "dispatch_days": "10-12 days",
        "availability": "Made to order",
        "featured": True,
        "new_arrival": False,
        "best_seller": False,
    }
    created = None
    try:
        resp = admin_client.post("/products", json=payload)
        assert resp.status_code == 201, f"create draft product failed: {resp.status_code} {resp.text[:300]}"
        created = resp.json()
        product_id = created["id"]
        assert created["status"] == "draft"
        assert created["stock_by_size"] == {"S": 2, "M": 3}

        # Visible to admin (authenticated) listing
        admin_list = admin_client.get("/products")
        assert admin_list.status_code == 200
        admin_ids = {p["id"] for p in admin_list.json()}
        assert product_id in admin_ids, "draft product should be visible to admin /products listing"

        # Absent from the public (unauthenticated) listing
        import httpx
        with httpx.Client(base_url="http://localhost:8001/api") as anon:
            public_list = anon.get("/products")
        assert public_list.status_code == 200
        public_ids = {p["id"] for p in public_list.json()}
        assert product_id not in public_ids, "draft product leaked into public /api/products"
    finally:
        if created:
            del_resp = admin_client.delete(f"/products/{created['id']}")
            assert del_resp.status_code == 204, f"cleanup delete failed: {del_resp.status_code} {del_resp.text[:200]}"
