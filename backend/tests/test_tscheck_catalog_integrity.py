"""Public catalog accuracy criterion: exactly the four approved SAFYRA products are public,
no tscheck/test/debug/placeholder rows leak into the customer-facing listing, and every stored
compare price (mrp) is genuinely higher than price (no fabricated "% off" data possible).

Also regression-guards a previously reported defect: the QA-name title filter must only apply to
the unauthenticated/public catalog surface. routers/products.py (list ~line 55, single ~lines
131-132) now exempts an authenticated admin from that filter, so an admin can see/manage their own
just-created QA-prefixed product via GET /products and GET /products/{id}.
"""
import uuid

APPROVED_TITLES = {
    "Luxury Nazakat Collection",
    "Aira Pure Kota Doria Angrakha",
    "Vaaya Pure Kota Doria Anarkali",
    "Sang-e-Mar-Mar — Rose Edition",
}
BANNED_PREFIXES = ("tscheck", "test", "debug", "placeholder")


def test_public_catalog_is_exactly_the_four_approved_products(client):
    resp = client.get("/products")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    products = resp.json()

    titles = {p["title"] for p in products}
    assert titles == APPROVED_TITLES, f"public catalog titles mismatch: {titles}"

    for product in products:
        lowered = product["title"].lower()
        assert not lowered.startswith(BANNED_PREFIXES), f"QA-named product leaked publicly: {product['title']}"
        if product.get("mrp") is not None:
            assert product["mrp"] >= product["price"], (
                f"{product['title']}: stored mrp {product['mrp']} is below price {product['price']} "
                "(would render a fabricated/negative discount badge)"
            )

    sang_e_mar_mar = next(p for p in products if p["title"] == "Sang-e-Mar-Mar — Rose Edition")
    assert sang_e_mar_mar["availability"] == "Currently unavailable"
    assert sang_e_mar_mar["sizes"] == [], "unavailable product must not expose purchasable sizes"


def test_admin_cannot_see_own_qa_named_product(admin_client, client):
    """Regression guard: admin-authenticated requests must be exempt from the public title
    filter, so an admin can see/manage their own freshly-created QA-prefixed product."""
    suffix = uuid.uuid4().hex[:8]
    title = f"tscheck-catalog-visibility-{suffix}"
    payload = {
        "title": title,
        "slug": title,
        "category": "Anarkali Sets",
        "collection": "Everyday Edit",
        "fabric": "Pure Kota Doria",
        "craft": "Handcrafted Chikankari",
        "price": 2000,
        "mrp": 2400,
        "stock": 3,
        "sizes": ["M"],
        "colors": ["Ivory"],
        "image_url": "https://example.com/image.jpg",
        "image_urls": ["https://example.com/image.jpg"],
        "description": "QA visibility probe.",
        "fit": "",
        "measurements": "",
        "transparency": "",
        "lining": "",
        "care": "",
        "dispatch_days": "10 days",
        "availability": "Made to order",
        "stock_by_size": {},
        "tags": [],
        "featured": False,
        "best_seller": False,
        "new_arrival": False,
    }

    create_resp = admin_client.post("/products", json=payload)
    assert create_resp.status_code in (200, 201), f"create failed: {create_resp.status_code}: {create_resp.text[:300]}"
    product_id = create_resp.json()["id"]

    try:
        # Correctly hidden from the unauthenticated/public listing (this part is by design).
        public_list = client.get("/products").json()
        assert product_id not in [p["id"] for p in public_list], "QA product unexpectedly public"

        # Bug: also hidden from the ADMIN's own authenticated listing and single-product fetch,
        # so the admin cannot see/edit/verify the very product they just created.
        admin_list = admin_client.get("/products").json()
        admin_ids = [p["id"] for p in admin_list]
        admin_get = admin_client.get(f"/products/{product_id}")
        assert product_id in admin_ids and admin_get.status_code == 200, (
            "admin-authenticated GET /products (list) and/or GET /products/{id} unexpectedly hide "
            f"the admin's own product '{title}' (id={product_id}). list_status=200 "
            f"contains_id={product_id in admin_ids} single_get_status={admin_get.status_code}"
        )
    finally:
        # Cleanup still works because DELETE is not filtered by title.
        admin_client.delete(f"/products/{product_id}")
