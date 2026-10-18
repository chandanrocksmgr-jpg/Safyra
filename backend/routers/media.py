from io import BytesIO
from pathlib import Path
import re
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from lib.db import db
from lib.security import require_admin


router = APIRouter(prefix="/media", tags=["media"])
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_BYTES = 8 * 1024 * 1024
FORMAT_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
Image.MAX_IMAGE_PIXELS = 40_000_000
media_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="product_media")


class MediaUploadResponse(BaseModel):
    url: str
    filename: str
    content_type: str
    size: int


@router.post("/upload", response_model=MediaUploadResponse, status_code=201)
async def upload_image(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG or WebP image")
    content = await file.read(MAX_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded image is empty")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Images must be 8 MB or smaller")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = image.format or ""
            width, height = image.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=415, detail="The file is not a valid JPG, PNG or WebP image") from exc
    detected_type = FORMAT_TYPES.get(image_format)
    if not detected_type or detected_type != file.content_type:
        raise HTTPException(status_code=415, detail="The image format does not match its file type")
    filename = f"{uuid.uuid4()}{ALLOWED_TYPES[file.content_type]}"
    media_id = await media_bucket.upload_from_stream(
        filename,
        content,
        metadata={"content_type": detected_type, "size": len(content), "width": width, "height": height},
    )
    return MediaUploadResponse(
        url=f"/api/media/{media_id}",
        filename=filename,
        content_type=detected_type,
        size=len(content),
    )


@router.get("/{media_id}")
async def get_image(media_id: str):
    if ObjectId.is_valid(media_id):
        try:
            media = await media_bucket.open_download_stream(ObjectId(media_id))
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