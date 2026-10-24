"""Lightweight, AI-free photo checks for admin uploads (warnings only, never blocking)."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps

MIN_SHORT_SIDE = 800  # px; below this, full-screen zoom on the product page looks soft
BLUR_THRESHOLD = 50.0  # Laplacian variance on a 1024 px greyscale copy
# Documents/screenshots: mostly paper-white with few mid-tones (text is black-on-white), little colour.
DOCUMENT_WHITE_SHARE = 0.5
DOCUMENT_MAX_MIDTONE_SHARE = 0.35
DOCUMENT_COLOURFULNESS = 35.0


def _laplacian_variance(grey: np.ndarray) -> float:
    centre = grey[1:-1, 1:-1]
    laplacian = grey[:-2, 1:-1] + grey[2:, 1:-1] + grey[1:-1, :-2] + grey[1:-1, 2:] - 4 * centre
    return float(laplacian.var())


def _colourfulness(rgb: np.ndarray) -> float:
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    rg = red - green
    yb = 0.5 * (red + green) - blue
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def analyse_image(content: bytes) -> dict:
    with Image.open(BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    width, height = image.size
    sample = image.copy()
    sample.thumbnail((1024, 1024))
    rgb = np.asarray(sample, dtype=np.float32)
    grey = np.asarray(sample.convert("L"), dtype=np.float32)
    sharpness = _laplacian_variance(grey)
    colourfulness = _colourfulness(rgb)
    white_share = float((grey > 235).mean())
    dark_share = float((grey < 70).mean())
    midtone_share = 1 - white_share - dark_share

    warnings: list[str] = []
    if min(width, height) < MIN_SHORT_SIDE:
        warnings.append(f"Low resolution ({width}×{height}px). Use at least {MIN_SHORT_SIDE}px on the shorter side so zoom stays sharp.")
    if sharpness < BLUR_THRESHOLD:
        warnings.append("This photo looks blurry or out of focus. Embroidery detail may not be visible.")
    if white_share > DOCUMENT_WHITE_SHARE and midtone_share < DOCUMENT_MAX_MIDTONE_SHARE and colourfulness < DOCUMENT_COLOURFULNESS:
        warnings.append("This looks like a document or screenshot rather than a garment photo.")
    if width > height * 1.15:
        warnings.append("Landscape photo. Product tiles are portrait (3:4), so the sides will be cropped.")
    return {
        "width": width,
        "height": height,
        "sharpness": round(sharpness, 1),
        "colourfulness": round(colourfulness, 1),
        "white_share": round(white_share, 3),
        "dark_share": round(dark_share, 3),
        "warnings": warnings,
    }
