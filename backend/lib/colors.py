"""Colour options: name + approximate swatch + the photos manually assigned to that colour.

`products.colors` (list of names) stays the source of truth used by variants, carts and filters.
`products.color_options` carries the presentation data for those same names, in the same order.
"""

import hashlib

# Keyword → approximate swatch. First match on the colour name wins; order matters (most specific first).
SWATCH_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("ivory", "vanilla", "off white", "offwhite", "cream", "pearl"), "#EFE6D4"),
    (("white", "chalk"), "#F6F3EC"),
    (("blush", "rose", "pink", "petal"), "#D9A3A5"),
    (("peach", "coral", "apricot"), "#E7B49A"),
    (("red", "scarlet", "crimson", "maroon", "wine"), "#9B2F2A"),
    (("mustard", "butter", "yellow", "gold", "haldi"), "#DFBB55"),
    (("orange", "rust", "terracotta"), "#C2693C"),
    (("mint", "sage", "olive", "green", "pista", "emerald"), "#6F8166"),
    (("teal", "turquoise", "aqua"), "#4E8A8B"),
    (("sky", "aster", "powder blue", "blue", "indigo", "denim"), "#8CA7BF"),
    (("navy", "midnight", "ink"), "#2B3449"),
    (("lilac", "lavender", "mauve", "purple", "violet"), "#B4A3C4"),
    (("beige", "sand", "nude", "biscuit", "oat"), "#D9C7AC"),
    (("brown", "coffee", "chocolate", "mocha", "tan"), "#7B5A42"),
    (("grey", "gray", "silver", "steel"), "#9A9A96"),
    (("black", "onyx", "charcoal"), "#2A2724"),
]


def swatch_for(name: str) -> str:
    """Approximate hex for a colour name: keyword match first, then a stable muted fallback."""
    text = (name or "").strip().lower()
    if not text:
        return "#E9DFC9"
    for keywords, hex_value in SWATCH_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return hex_value
    # Stable per-name fallback kept inside a soft, premium range (never neon).
    digest = hashlib.sha256(text.encode()).digest()
    return "#%02X%02X%02X" % tuple(110 + digest[index] % 90 for index in range(3))


def _clean_hex(value: str | None, name: str) -> str:
    text = (value or "").strip()
    if len(text) == 7 and text.startswith("#"):
        try:
            int(text[1:], 16)
            return text.upper()
        except ValueError:
            pass
    return swatch_for(name)


def normalize_color_options(colors: list[str], options: list[dict] | None, gallery: list[str] | None = None) -> tuple[list[str], list[dict]]:
    """Align colour names and their presentation rows.

    Returns (colors, color_options) where both lists hold the same names in the same order. Photos that
    are no longer in the product gallery are dropped so a colour can never point at a deleted image.
    """
    by_name = {str(item.get("name", "")).strip().casefold(): item for item in (options or []) if str(item.get("name", "")).strip()}
    names: list[str] = []
    for name in [str(value).strip() for value in (colors or []) if str(value).strip()]:
        if name.casefold() not in {existing.casefold() for existing in names}:
            names.append(name)
    allowed = set(gallery or [])
    aligned = []
    for name in names:
        source = by_name.get(name.casefold(), {})
        images = [url for url in (source.get("image_urls") or []) if isinstance(url, str) and (not allowed or url in allowed)]
        aligned.append({"name": name, "swatch": _clean_hex(source.get("swatch"), name), "image_urls": images})
    return names, aligned


async def migrate_color_options() -> None:
    """Idempotent backfill: give every product with colours its `color_options` rows once (auto swatches, no photos assigned)."""
    import logging

    from lib.db import get_db

    products = get_db().products
    migrated = 0
    async for product in products.find({"color_options": {"$exists": False}}):
        _, options = normalize_color_options(product.get("colors") or [], [], product.get("image_urls") or [])
        result = await products.update_one({"id": product["id"], "color_options": {"$exists": False}}, {"$set": {"color_options": options}})
        migrated += result.modified_count
    if migrated:
        logging.getLogger(__name__).info("Created colour options for %d products", migrated)
