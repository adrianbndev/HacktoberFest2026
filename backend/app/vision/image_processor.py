"""Local image decoding, smart framing/sharpening, and visual metrics via Pillow."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat

from app.vision.protocol import ImageVisualMetrics

DEFAULT_MAX_INFERENCE_PX = int(os.getenv("VISION_MAX_IMAGE_PX", "896"))
DEFAULT_JPEG_QUALITY = 84


def _classify_color_es(r: int, g: int, b: int) -> str:
    """Maps an RGB triplet to a concise Spanish commercial color label."""
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    spread = max(r, g, b) - min(r, g, b)
    if spread < 22:
        if lum > 205:
            return "Blanco"
        if lum > 135:
            return "Gris plata"
        if lum > 65:
            return "Gris espacial"
        return "Negro"
    if r >= g and r >= b:
        return "Rojo / Coral" if g < 110 else "Dorado / Naranja"
    if g >= r and g >= b:
        return "Verde"
    return "Azul"


def decode_image_source(source: str | bytes | Path) -> Image.Image:
    """Decodes a Data URL, raw Base64 string, bytes, or file path into a RGB PIL Image."""
    raw_bytes: bytes
    if isinstance(source, bytes):
        raw_bytes = source
    elif isinstance(source, Path):
        raw_bytes = source.read_bytes()
    elif isinstance(source, str):
        stripped = source.strip()
        if stripped.startswith("data:image/"):
            _, _, b64_part = stripped.partition(",")
            raw_bytes = base64.b64decode(b64_part)
        elif len(stripped) < 260 and Path(stripped).is_file():
            raw_bytes = Path(stripped).read_bytes()
        else:
            raw_bytes = base64.b64decode(stripped)
    else:
        raise ValueError("Unsupported image input type")

    try:
        with Image.open(io.BytesIO(raw_bytes)) as opened:
            transposed = ImageOps.exif_transpose(opened)
            return transposed.convert("RGB")
    except Exception as exc:
        raise ValueError(f"No se pudo decodificar la imagen: {exc}") from exc


def prepare_and_inspect_image(
    image: Image.Image,
    max_dimension_px: int = DEFAULT_MAX_INFERENCE_PX,
) -> tuple[Image.Image, ImageVisualMetrics]:
    """Optimizes image for fast VLM inference on Matías's Mac and extracts metrics."""
    orig_w, orig_h = image.size
    aspect_ratio = round(orig_w / max(1, orig_h), 3)

    # Resize preserving aspect ratio so VLM visual encoder processes optimal patches
    working = image.copy()
    if max(orig_w, orig_h) > max_dimension_px:
        working.thumbnail((max_dimension_px, max_dimension_px), Image.Resampling.LANCZOS)

    # Subtle unsharp mask helps VLMs read small model numbers and detect surface scratches
    enhanced = working.filter(
        ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3)
    )

    gray = working.convert("L")
    gray_stat = ImageStat.Stat(gray)
    brightness = round(float(gray_stat.mean[0]), 2)
    contrast = round(float(gray_stat.stddev[0]), 2)

    edges = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = round(float(ImageStat.Stat(edges).mean[0]), 2)

    # Sample center 60% of the frame to get the product's dominant color (ignoring borders)
    w, h = working.size
    center_crop = working.crop((int(w * 0.2), int(h * 0.2), int(w * 0.8), int(h * 0.8)))
    rgb_mean = ImageStat.Stat(center_crop).mean
    dom_rgb = (int(rgb_mean[0]), int(rgb_mean[1]), int(rgb_mean[2]))
    color_es = _classify_color_es(*dom_rgb)

    buffer = io.BytesIO()
    enhanced.save(buffer, format="JPEG", quality=DEFAULT_JPEG_QUALITY, optimize=True)
    jpeg_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    metrics = ImageVisualMetrics(
        width=orig_w,
        height=orig_h,
        aspect_ratio=aspect_ratio,
        brightness=brightness,
        contrast=contrast,
        sharpness=sharpness,
        dominant_rgb=dom_rgb,
        color_name_es=color_es,
        optimized_jpeg_b64=jpeg_b64,
    )
    return enhanced, metrics
