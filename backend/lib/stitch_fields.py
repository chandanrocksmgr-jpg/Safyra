"""Derives size/size-guide behaviour from a product's stitch type.

Only "stitched" products ask a customer for a size or show the SAFYRA size guide — this is fully automatic
(never admin-managed) so every stitched product always carries the one canonical chart, and every
semi-stitched/unstitched/other product never shows a size picker.
"""

import logging

from lib.db import db

logger = logging.getLogger(__name__)

# Hosted on Emergent's asset CDN (not this deployment's own GridFS) so the same URL resolves in every
# environment — preview, any future redeploy, etc. — with nothing to re-upload per environment.
DEFAULT_SIZE_GUIDE_IMAGE = "https://customer-assets-agu9un31.emergentagent.net/job_lucknowi-craft/artifacts/2fdac9826d8b71d6_IMG-20261029-WA0001.jpg"


def stitch_fields(product: dict) -> dict:
    stitched = product.get("stitch_type", "stitched") == "stitched"
    fields = {"size_required": stitched, "size_guide_image": DEFAULT_SIZE_GUIDE_IMAGE if stitched else ""}
    if not stitched:
        fields["sizes"] = []
    return fields


async def migrate_stitch_types() -> None:
    """Backfills stitch_type on legacy products (inferred from their existing sizing) and realigns
    size_required/size_guide_image/sizes to match — self-heals every environment on next startup,
    including one where the size guide image was previously stored as a per-environment GridFS id."""
    updated = 0
    async for product in db.products.find({}, {"id": 1, "stitch_type": 1, "sizes": 1, "size_required": 1, "size_guide_image": 1}):
        stitch_type = product.get("stitch_type") or ("stitched" if product.get("sizes") or product.get("size_required") else "unstitched")
        fields = stitch_fields({**product, "stitch_type": stitch_type})
        fields["stitch_type"] = stitch_type
        if any(product.get(key) != value for key, value in fields.items()):
            await db.products.update_one({"id": product["id"]}, {"$set": fields})
            updated += 1
    if updated:
        logger.info("Stitch-type migration realigned %d products", updated)
