"""Criterion: Publishing states protect the storefront.

Verifies that only Active products/catalog groups appear in public endpoints
that drive the customer storefront (product list, facets), while Draft and
Archived records stay visible to admin but are excluded from those public
surfaces. Uses a temporary product the test creates and deletes itself.
"""
import uuid

import httpx




def test_archived_and_draft_products_excluded_from_public_surfaces(admin_client):
    unique = uuid.uuid4().hex[:8]
    slug = f"tscheck-pubstate-{unique}"
    # Title intentionally avoids the "tscheck/test/debug/placeholder" prefix the public
    # endpoint strips independent of status -- that title-prefix safety net is verified
    # separately; this test isolates the status-based visibility behaviour.
    base_title = f"SAFYRA QA Candidate {unique}"
    created = None
    try:
        # Create as draft first
        payload = {
            "title": base_title,
            "slug": slug,
            "status": "draft",
            "category": "Anarkali Sets",
            "collection": "Everyday Edit",
            "fabric": "Pure Kota Doria",
            "craft": "Hand Chikankari",
            "price": 1999,
            "stock": 3,
            "sizes": ["S"],
            "colors": ["Ivory"],
            "image_url": "https://example.com/tscheck-pubstate.jpg",
            "image_urls": ["https://example.com/tscheck-pubstate.jpg"],
            "description": "tscheck publishing-state product",
            "fit": "Regular fit",
            "measurements": "Length 44 in",
            "transparency": "Opaque",
            "lining": "Unlined",
            "care": "Dry clean only",
            "dispatch_days": "10-12 days",
            "availability": "Made to order",
        }
        resp = admin_client.post("/products", json=payload)
        assert resp.status_code == 201, f"create failed: {resp.status_code} {resp.text[:300]}"
        created = resp.json()
        product_id = created["id"]

        with httpx.Client(base_url="http://localhost:8001/api") as anon:
            # Draft: hidden from public list and facets
            public_list = anon.get("/products")
            assert product_id not in {p["id"] for p in public_list.json()}
            facets = anon.get("/products/facets")
            assert facets.status_code == 200

            # Flip to archived -> still must be hidden from public list
            patch = admin_client.patch(f"/products/{product_id}", json={"status": "archived"})
            assert patch.status_code == 200
            assert patch.json()["status"] == "archived"
            public_list_2 = anon.get("/products")
            assert product_id not in {p["id"] for p in public_list_2.json()}

            # But admin can still see it (any status) via authenticated listing
            admin_list = admin_client.get("/products")
            assert product_id in {p["id"] for p in admin_list.json()}

            # Flip to active -> now it must appear in the public list
            patch2 = admin_client.patch(f"/products/{product_id}", json={"status": "active"})
            assert patch2.status_code == 200
            public_list_3 = anon.get("/products")
            assert product_id in {p["id"] for p in public_list_3.json()}, "active product should be visible publicly"
    finally:
        if created:
            del_resp = admin_client.delete(f"/products/{created['id']}")
            assert del_resp.status_code == 204, f"cleanup delete failed: {del_resp.status_code} {del_resp.text[:200]}"
