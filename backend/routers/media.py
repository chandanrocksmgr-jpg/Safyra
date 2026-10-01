from pathlib import Path
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lib.security import require_admin


router = APIRouter(prefix="/media", tags=["media"])
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_BYTES = 8 * 1024 * 1024


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
    filename = f"{uuid.uuid4()}{ALLOWED_TYPES[file.content_type]}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return MediaUploadResponse(
        url=f"/api/media/{filename}",
        filename=filename,
        content_type=file.content_type,
        size=len(content),
    )


@router.get("/{filename}")
async def get_image(filename: str):
    if not re.fullmatch(r"[0-9a-f-]+\.(jpg|png|webp)", filename):
        raise HTTPException(status_code=404, detail="Image not found")
    path = UPLOAD_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)