"""Product image uploads accept large, high-quality photos: the per-image limit was raised from
8 MB to 40 MB. A ~10-15 MB noisy JPEG (well above the old 8 MB ceiling) is accepted with 201 and
real width/height; a file above the new 40 MB ceiling is still rejected with 413."""
import io
import os
import random

import pytest
from PIL import Image


def _noisy_jpeg_bytes(width: int, height: int, quality: int = 95) -> bytes:
    """Builds a genuinely large JPEG by encoding random noise (compresses poorly, unlike a
    solid color), so the byte size actually lands in the target MB range."""
    random.seed(42)
    img = Image.effect_noise((width, height), 60).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


@pytest.fixture(scope="module")
def big_jpeg_bytes() -> bytes:
    data = _noisy_jpeg_bytes(3000, 2600, quality=98)
    assert len(data) > 8 * 1024 * 1024, f"fixture JPEG must exceed the old 8MB ceiling, got {len(data) / 1024 / 1024:.1f}MB"
    assert len(data) < 40 * 1024 * 1024, f"fixture JPEG must stay under the 40MB ceiling, got {len(data) / 1024 / 1024:.1f}MB"
    return data


def test_upload_above_old_8mb_limit_is_accepted(admin_client, big_jpeg_bytes):
    files = {"file": ("tscheck-large-upload.jpg", big_jpeg_bytes, "image/jpeg")}
    resp = admin_client.post("/media/upload", files=files)
    assert resp.status_code == 201, f"upload > 8MB expected 201, got {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body["url"].startswith("/api/media/"), f"expected a /api/media/... url, got {body.get('url')}"
    assert body["width"] == 3000 and body["height"] == 2600, f"expected real dimensions 3000x2600, got {body.get('width')}x{body.get('height')}"


def test_upload_above_40mb_limit_is_rejected(admin_client):
    oversized = os.urandom(41 * 1024 * 1024)
    files = {"file": ("tscheck-oversized-upload.jpg", oversized, "image/jpeg")}
    resp = admin_client.post("/media/upload", files=files)
    assert resp.status_code == 413, f"upload > 40MB expected 413, got {resp.status_code}: {resp.text[:300]}"
