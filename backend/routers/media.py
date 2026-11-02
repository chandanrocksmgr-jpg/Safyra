from io import BytesIO
from pathlib import Path
import asyncio
import re
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

import pillow_heif

from lib.db import get_db
from lib.image_quality import analyse_image
from lib.legacy_media import get_legacy_image, is_safe_legacy_path
from lib.security import require_admin

pillow_heif.register_heif_opener()  # lets Pillow.open() read iPhone HEIC/HEIF photos directly

router = APIRouter(prefix="/media", tags=["media"])
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
# iPhones shoot HEIC/HEIF by default; these are accepted and transcoded to JPEG below (browsers can't render HEIC).
HEIF_TYPES = {"image/heic", "image/heif"}
# Effectively no limit for photography: anything larger than this is almost certainly not a product photo.
MAX_BYTES = 200 * 1024 * 1024
# Studio originals are kept at up to this long edge (far beyond any screen, good for deep zoom) and
# re-encoded so pages stay fast. Anything smaller is stored byte-for-byte.
OPTIMISE_LONG_EDGE = 4000
OPTIMISE_OVER_BYTES = 6 * 1024 * 1024
FORMAT_TYPES = {"JPEG": "image/jpeg", "MPO": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}
MAX_VIDEO_BYTES = 40 * 1024 * 1024
# A decoded RGB buffer costs ~3 bytes/pixel in memory; this cap (covers any phone or studio camera in practical
# use) keeps a single decode well within the server's memory budget. Pillow raises DecompressionBombError above it.
Image.MAX_IMAGE_PIXELS = 60_000_000
# Decoding + re-encoding a large photo is CPU/memory heavy; this bounds how many run at once so a burst of
# uploads can't stack peak memory past the server's limit, and keeps it off the event loop (see run_in_threadpool
# below) so health checks never stall behind it.
_UPLOAD_SLOTS = asyncio.Semaphore(2)
_UPLOAD_SLOT_WAIT_SECONDS = 25


def _media_bucket() -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="product_media")


class MediaUploadResponse(BaseModel):
    url: str
    filename: str
    content_type: str
    size: int
    width: int
    height: int
    warnings: list[str] = Field(default_factory=list)


class MediaQualityRequest(BaseModel):
    urls: list[str] = Field(default_factory=list, max_length=60)


class MediaQualityItem(BaseModel):
    url: str
    width: int
    height: int
    warnings: list[str] = Field(default_factory=list)


class MediaQualityResponse(BaseModel):
    items: list[MediaQualityItem] = Field(default_factory=list)


def _decode_and_prepare_image(content: bytes) -> tuple[bytes, str, int, int, list[str]]:
    """All the CPU/memory-heavy Pillow decode/convert/optimise work for one upload.

    Runs inside run_in_threadpool (see caller) so it never blocks the event loop — that blocking was what
    stalled /health checks and triggered OOM-restart-driven 520s in production under concurrent uploads.
    """
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = image.format or ""
            width, height = image.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=415, detail="The file is not a valid JPG, PNG, WebP or HEIC/HEIF image") from exc
    optimise_note: list[str] = []
    if image_format == "HEIF":
        # iPhone photos shoot HEIC/HEIF by default; browsers can't render it, so transcode to JPEG once on upload.
        # Downscaling immediately (not waiting for the later size check) bounds peak memory for these often-huge originals.
        try:
            with Image.open(BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((OPTIMISE_LONG_EDGE, OPTIMISE_LONG_EDGE), Image.LANCZOS)
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=92, optimize=True, progressive=True)
                content = buffer.getvalue()
                width, height = image.size
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(status_code=415, detail="This HEIC/HEIF photo could not be converted") from exc
        detected_type = "image/jpeg"
        optimise_note = ["Converted from HEIC to JPEG so it displays on every device."]
    else:
        # PIL's own decoded format is the source of truth for storage/serving — a declared-vs-detected
        # mismatch (e.g. "image/jpg", or a browser mislabeling an MPO/JPEG) is not a reason to reject a valid photo.
        detected_type = FORMAT_TYPES.get(image_format)
        if not detected_type:
            raise HTTPException(status_code=415, detail="The image format does not match its file type")
    if len(content) > OPTIMISE_OVER_BYTES or max(width, height) > OPTIMISE_LONG_EDGE:
        content, width, height, detected_type, resize_note = _optimised(content, detected_type, width, height)
        optimise_note = [*optimise_note, *resize_note]
    return content, detected_type, width, height, optimise_note


@router.post("/upload", response_model=MediaUploadResponse, status_code=201)
async def upload_image(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    # Some phones/apps send "image/jpg" (not a real MIME type) or label an iPhone HDR/Live-Photo JPEG as MPO —
    # both decode to a perfectly valid photo, so normalize instead of rejecting a clean image outright.
    declared_type = "image/jpeg" if file.content_type == "image/jpg" else file.content_type
    is_heif_upload = declared_type in HEIF_TYPES or (file.filename or "").lower().endswith((".heic", ".heif"))
    if declared_type not in ALLOWED_TYPES and not is_heif_upload:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, WebP or iPhone HEIC/HEIF image")
    content = await file.read(MAX_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded image is empty")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Images must be 200 MB or smaller")
    try:
        await asyncio.wait_for(_UPLOAD_SLOTS.acquire(), timeout=_UPLOAD_SLOT_WAIT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="The server is busy processing other photos — please try again in a few seconds")
    try:
        content, detected_type, width, height, optimise_note = await run_in_threadpool(_decode_and_prepare_image, content)
    finally:
        _UPLOAD_SLOTS.release()
    quality = await run_in_threadpool(_safe_analysis, content)
    filename = f"{uuid.uuid4()}{ALLOWED_TYPES[detected_type]}"
    media_id = await _media_bucket().upload_from_stream(
        filename,
        content,
        metadata={"content_type": detected_type, "size": len(content), "width": width, "height": height, "quality": quality},
    )
    return MediaUploadResponse(
        url=f"/api/media/{media_id}",
        filename=filename,
        content_type=detected_type,
        size=len(content),
        width=quality.get("width", width),
        height=quality.get("height", height),
        warnings=[*optimise_note, *quality.get("warnings", [])],
    )


class MediaVideoResponse(BaseModel):
    url: str
    content_type: str
    size: int


@router.post("/upload-video", response_model=MediaVideoResponse, status_code=201)
async def upload_video(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    """Short product films (max 2 per product), stored in the same GridFS bucket as photos."""
    if file.content_type not in VIDEO_TYPES:
        raise HTTPException(status_code=415, detail="Upload an MP4, WebM or MOV video")
    content = await file.read(MAX_VIDEO_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded video is empty")
    if len(content) > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="Videos must be 40 MB or smaller")
    media_id = await _media_bucket().upload_from_stream(
        f"{uuid.uuid4()}{VIDEO_TYPES[file.content_type]}",
        content,
        metadata={"content_type": file.content_type, "size": len(content), "kind": "video"},
    )
    return MediaVideoResponse(url=f"/api/media/{media_id}", content_type=file.content_type, size=len(content))


def _optimised(content: bytes, content_type: str, width: int, height: int) -> tuple[bytes, int, int, str, list[str]]:
    """Re-encode an oversized studio original: honour EXIF rotation, cap the long edge, keep near-lossless quality.

    JPEG decoding uses draft mode so a 100 MP original never has to be expanded in memory at full size.
    """
    original_mp = round((width * height) / 1_000_000)
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format == "JPEG":
                image.draft("RGB", (OPTIMISE_LONG_EDGE, OPTIMISE_LONG_EDGE))
            image = ImageOps.exif_transpose(image)
            image.thumbnail((OPTIMISE_LONG_EDGE, OPTIMISE_LONG_EDGE), Image.LANCZOS)
            buffer = BytesIO()
            if content_type == "image/png" and image.mode in {"RGBA", "LA", "P"}:
                image.save(buffer, format="PNG", optimize=True)
                new_type = "image/png"
            elif content_type == "image/webp":
                image.save(buffer, format="WEBP", quality=92, method=5)
                new_type = "image/webp"
            else:
                image.convert("RGB").save(buffer, format="JPEG", quality=92, optimize=True, progressive=True)
                new_type = "image/jpeg"
            optimised = buffer.getvalue()
            new_width, new_height = image.size
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return content, width, height, content_type, []
    if len(optimised) >= len(content):
        return content, width, height, content_type, []
    note = f"Optimised from {original_mp} MP for fast loading; stored at {new_width}×{new_height}."
    return optimised, new_width, new_height, new_type, [note]


def _safe_analysis(content: bytes) -> dict:
    try:
        return analyse_image(content)
    except Exception:  # quality hints are advisory; never fail an upload over them
        return {"warnings": []}


@router.post("/quality", response_model=MediaQualityResponse)
async def check_media_quality(input: MediaQualityRequest, _: dict = Depends(require_admin)):
    """Advisory photo checks for images already stored in SAFYRA media (external links are skipped)."""
    files = get_db()["product_media.files"]
    items: list[MediaQualityItem] = []
    for url in dict.fromkeys(input.urls):
        if url.startswith("/api/media/shopify/"):
            path = url.removeprefix("/api/media/shopify/")
            if not is_safe_legacy_path(path):
                continue
            record = await files.find_one({"metadata.legacy_path": path}, sort=[("uploadDate", -1)])
            if not record and await get_legacy_image(path):
                record = await files.find_one({"metadata.legacy_path": path}, sort=[("uploadDate", -1)])
        elif url.startswith("/api/media/") and ObjectId.is_valid(url.removeprefix("/api/media/")):
            record = await files.find_one({"_id": ObjectId(url.removeprefix("/api/media/"))})
        else:
            continue
        if not record:
            continue
        quality = (record.get("metadata") or {}).get("quality")
        if not quality or "width" not in quality:
            stream = await _media_bucket().open_download_stream(record["_id"])
            quality = _safe_analysis(await stream.read())
            await files.update_one({"_id": record["_id"]}, {"$set": {"metadata.quality": quality}})
        if "width" in quality:
            items.append(MediaQualityItem(url=url, width=quality["width"], height=quality["height"], warnings=quality.get("warnings", [])))
    return MediaQualityResponse(items=items)


@router.get("/shopify/{path:path}")
async def get_legacy_shopify_image(path: str):
    if not is_safe_legacy_path(path):
        raise HTTPException(status_code=404, detail="Image not found")
    media = await get_legacy_image(path)
    if not media:
        raise HTTPException(status_code=404, detail="Image not found")
    content, content_type = media
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"})


@router.get("/{media_id}")
async def get_image(media_id: str):
    if ObjectId.is_valid(media_id):
        try:
            media = await _media_bucket().open_download_stream(ObjectId(media_id))
            content = await media.read()
            return Response(
                content=content,
                media_type=(media.metadata or {}).get("content_type", "application/octet-stream"),
                headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"},
            )
        except NoFile as exc:
            raise HTTPException(status_code=404, detail="Image not found") from exc
    # Legacy local URLs remain readable during migration; all new uploads use GridFS.
    if re.fullmatch(r"[0-9a-f-]+\.(jpg|png|webp)", media_id):
        path = UPLOAD_DIR / media_id
        if path.is_file():
            return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"})
    raise HTTPException(status_code=404, detail="Image not found")