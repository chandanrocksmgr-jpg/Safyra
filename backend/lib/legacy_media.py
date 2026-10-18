"""Recover legacy Shopify product imagery into durable GridFS storage.

After the domain moved off Shopify, ``safyra.co/cdn/shop/files/...`` paths hit
this app instead of Shopify's CDN. The original files still live at the
store's ``cdn.shopify.com`` path, so each one is fetched once, stored in the
``product_media`` GridFS bucket and served from ``/api/media/shopify/<path>``.
"""

import logging
import re
from io import BytesIO

import httpx
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from PIL import Image, UnidentifiedImageError

from lib.db import get_db

logger = logging.getLogger(__name__)

SHOPIFY_FILES_BASE = "https://cdn.shopify.com/s/files/1/0853/1325/7781/files/"
LEGACY_URL = re.compile(
    r"https?://(?:www\.)?safyra\.co/cdn/shop/files/([A-Za-z0-9._/-]+)(?:\?[^\s\"'<>]*)?"
    r"|https://cdn\.shopify\.com/s/files/1/0853/1325/7781/files/([A-Za-z0-9._/-]+)(?:\?[^\s\"'<>]*)?"
)
MIGRATED_URL = re.compile(r"/api/media/shopify/([A-Za-z0-9._/-]+)")
SAFE_PATH = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._/-]{0,200}\.(?:jpe?g|png|webp)", re.IGNORECASE)
FORMAT_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MIGRATED_COLLECTIONS = ["products", "site_content", "catalog_groups", "order_requests", "checkout_sessions", "orders"]
VALID_IMAGE_PREFIXES = ("https://", "http://", "/api/media/")


def is_safe_legacy_path(path: str) -> bool:
    return bool(SAFE_PATH.fullmatch(path)) and ".." not in path


def legacy_media_url(path: str) -> str:
    return f"/api/media/shopify/{path}"


def _rewrite(value, paths: set[str]):
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            path = match.group(1) or match.group(2)
            if not is_safe_legacy_path(path):
                return match.group(0)
            paths.add(path)
            return legacy_media_url(path)

        rewritten = LEGACY_URL.sub(replace, value)
        paths.update(path for path in MIGRATED_URL.findall(rewritten) if is_safe_legacy_path(path))
        return rewritten
    if isinstance(value, list):
        return [_rewrite(item, paths) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite(item, paths) for key, item in value.items()}
    return value


def _clean_product_images(document: dict) -> dict:
    """Drop device-only links (blob:, data:, file:) that can never render for shoppers."""
    images = []
    for image in document.get("image_urls") or []:
        if isinstance(image, str) and image.strip().startswith(VALID_IMAGE_PREFIXES) and image not in images:
            images.append(image.strip())
    primary = document.get("image_url") or ""
    if not primary.startswith(VALID_IMAGE_PREFIXES):
        primary = images[0] if images else ""
    return {**document, "image_url": primary, "image_urls": images}


async def get_legacy_image(path: str) -> tuple[bytes, str] | None:
    database = get_db()
    bucket = AsyncIOMotorGridFSBucket(database, bucket_name="product_media")
    existing = await database["product_media.files"].find_one({"metadata.legacy_path": path}, sort=[("uploadDate", -1)])
    if existing:
        stream = await bucket.open_download_stream(existing["_id"])
        return await stream.read(), (existing.get("metadata") or {}).get("content_type", "image/jpeg")
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        response = await client.get(SHOPIFY_FILES_BASE + path, params={"width": 1600})
    if response.status_code != 200:
        logger.warning("Legacy image %s unavailable on Shopify CDN (%s)", path, response.status_code)
        return None
    content = response.content
    try:
        with Image.open(BytesIO(content)) as image:
            content_type = FORMAT_TYPES.get(image.format or "")
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        logger.warning("Legacy image %s is not a valid image: %s", path, exc)
        return None
    if not content_type:
        return None
    await bucket.upload_from_stream(
        path.rsplit("/", 1)[-1],
        content,
        metadata={"content_type": content_type, "size": len(content), "width": width, "height": height, "legacy_path": path, "source": "shopify"},
    )
    return content, content_type


async def migrate_legacy_media() -> None:
    """Idempotent: rewrites legacy URLs to /api/media/shopify/... and pre-caches every referenced file."""
    database = get_db()
    paths: set[str] = set()
    for name in MIGRATED_COLLECTIONS:
        async for document in database[name].find({}):
            updated = _rewrite(document, paths)
            if name == "products":
                updated = _clean_product_images(updated)
            changes = {key: value for key, value in updated.items() if key != "_id" and value != document.get(key)}
            if changes:
                await database[name].update_one({"_id": document["_id"]}, {"$set": changes})
                logger.info("Rewrote legacy media in %s %s: %s", name, document.get("id", document["_id"]), sorted(changes))
    for path in sorted(paths):
        try:
            await get_legacy_image(path)
        except Exception as exc:  # one bad file must not stop the rest
            logger.error("Could not cache legacy image %s: %s", path, exc)
    logger.info("Legacy media migration complete (%d files referenced)", len(paths))
