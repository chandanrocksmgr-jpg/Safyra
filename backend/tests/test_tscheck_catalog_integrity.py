"""Public catalog accuracy criterion: exactly the four approved SAFYRA products are public,
no tscheck/test/debug/placeholder rows leak into the customer-facing listing, and every stored
compare price (mrp) is genuinely higher than price (no fabricated "% off" data possible).

Also documents a real defect found while probing this behaviour: the same title filter that
correctly hides QA-named products from the PUBLIC catalog is applied unconditionally in
routers/products.py, so it also hides an admin's own just-created QA product from the
admin-authenticated GET /products list and GET /products/{id} - the admin cannot see or manage
(edit/verify) a product they just created through the UI if its title starts with one of the
banned prefixes, even though DELETE by id still works.
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
    """Bug report: admin-authenticated requests are filtered by the same public title regex."""
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
            "BUG: admin-authenticated GET /products (list) and/or GET /products/{id} hide the "
            f"admin's own product '{title}' (id={product_id}) because its title matches the "
            f"public QA-name filter. list_status=200 contains_id={product_id in admin_ids} "
            f"single_get_status={admin_get.status_code}"
        )
    finally:
        # Cleanup still works because DELETE is not filtered by title.
        admin_client.delete(f"/products/{product_id}")
