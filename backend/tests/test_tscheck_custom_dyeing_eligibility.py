"""Custom-dyeing eligibility criterion: the customisation field is the sole eligibility
source for the 'Prefer another colour? / Ask about custom dyeing' product-page option.

Frontend derives eligibility purely from a case-insensitive regex match of dye/dyed/dyeing
against product.customisation (see frontend/src/pages/Product.tsx: supportsCustomDyeing).
This test asserts the underlying data contract the frontend relies on: approved eligible
products expose a customisation string mentioning dye/dyeing, approved ineligible products
do not, so the UI toggling on that field alone is correct behaviour, not an accident of data.
"""
import re

ELIGIBLE_TITLES = {"Aira Pure Kota Doria Angrakha", "Vaaya Pure Kota Doria Anarkali"}
INELIGIBLE_TITLES = {"Luxury Nazakat Collection", "Sang-e-Mar-Mar — Rose Edition"}

DYE_RE = re.compile(r"\bdye(?:d|ing)?\b", re.IGNORECASE)


def test_customisation_field_drives_custom_dyeing_eligibility(client):
    resp = client.get("/products")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:300]}"
    products = resp.json()

    by_title = {p["title"]: p for p in products}

    for title in ELIGIBLE_TITLES:
        assert title in by_title, f"expected approved eligible product missing: {title}"
        customisation = by_title[title].get("customisation") or ""
        assert DYE_RE.search(customisation), (
            f"{title}: customisation field does not mention dye/dyeing "
            f"(got {customisation!r}); frontend would incorrectly hide the custom-dyeing option"
        )

    for title in INELIGIBLE_TITLES:
        assert title in by_title, f"expected approved ineligible product missing: {title}"
        customisation = by_title[title].get("customisation") or ""
        assert not DYE_RE.search(customisation), (
            f"{title}: customisation field unexpectedly mentions dye/dyeing "
            f"(got {customisation!r}); frontend would incorrectly show the custom-dyeing option"
        )
