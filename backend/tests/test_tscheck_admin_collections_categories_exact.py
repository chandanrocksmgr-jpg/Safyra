"""Admin Collections & Categories criterion: exactly eight active genuine categories and
three genuine collections are present, in the approved order, with no test-named groups.

Read-only: only GET /catalog-groups is exercised, no mutation of any group record.
"""

EXPECTED_CATEGORIES_IN_ORDER = [
    "Anarkali Sets",
    "Angrakha Suits",
    "Straight Kurtis",
    "Stitched Sets",
    "Sarees",
    "Dupattas",
    "Chikankari Bottoms",
    "Unstitched Sets",
]
EXPECTED_COLLECTIONS = {"Safyra Luxury", "Everyday Edit", "Vaaya Kota Doria"}
BANNED_PREFIXES = ("tscheck", "test", "debug", "placeholder", "qa")


def test_admin_sees_exactly_eight_categories_and_three_collections(admin_client):
    resp = admin_client.get("/catalog-groups")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    groups = resp.json()

    categories = [g for g in groups if g["group_type"] == "category"]
    collections = [g for g in groups if g["group_type"] == "collection"]

    assert len(categories) == 8, f"expected 8 categories, got {len(categories)}: {[c['name'] for c in categories]}"
    assert len(collections) == 3, f"expected 3 collections, got {len(collections)}: {[c['name'] for c in collections]}"

    for group in categories + collections:
        assert group["status"] == "active", f"{group['name']} is not active: {group['status']}"
        lowered = group["name"].lower()
        assert not lowered.startswith(BANNED_PREFIXES), f"test-named group leaked into admin: {group['name']}"

    category_names_sorted = sorted(c["name"] for c in categories)
    assert category_names_sorted == sorted(EXPECTED_CATEGORIES_IN_ORDER), (
        f"category set mismatch: {category_names_sorted}"
    )

    collection_names = {c["name"] for c in collections}
    assert collection_names == EXPECTED_COLLECTIONS, f"collection set mismatch: {collection_names}"

    # Navigation contract order: categories sorted by sort_order must follow the approved sequence
    ordered_by_sort = [c["name"] for c in sorted(categories, key=lambda c: c["sort_order"])]
    assert ordered_by_sort == EXPECTED_CATEGORIES_IN_ORDER, f"category sort_order sequence mismatch: {ordered_by_sort}"
