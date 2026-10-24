"""Vision domain protocol, visual metrics dataclass, and pure SEO copy functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from PIL import Image

from app.models.sdd import (
    SEO_TITLE_MAX_LENGTH,
    ConditionLabel,
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)


@dataclass(frozen=True)
class ImageVisualMetrics:
    """Objective visual metrics extracted locally via Pillow in <20ms."""

    width: int
    height: int
    aspect_ratio: float
    brightness: float          # 0.0 (black) to 255.0 (white)
    contrast: float            # Std-dev of luminance (0.0 to ~128.0)
    sharpness: float           # Mean edge gradient (0.0 to ~100.0)
    dominant_rgb: tuple[int, int, int]
    color_name_es: str
    optimized_jpeg_b64: str    # Compressed base64 JPEG for fast LAN transfer to Mac


class VisionProviderProtocol(Protocol):
    """SOLID Dependency Inversion port for interchangeable Vision providers."""

    provider_id: str

    async def analyze(
        self,
        image: Image.Image,
        metrics: ImageVisualMetrics,
        photo_data_url: str,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        """Analyzes a product image and returns structured form data + health + SEO."""
        ...


def build_seo_title(
    name: str,
    condition_label: ConditionLabel,
    condition_score: int,
    candidate_title: str | None = None,
) -> str:
    """Builds or normalizes a persuasive Wallapop SEO title (<= 65 chars)."""
    score = clamp_condition_score(condition_score)
    if candidate_title and len(candidate_title.strip()) >= 12:
        cleaned = " ".join(candidate_title.strip().split())
        if len(cleaned) <= SEO_TITLE_MAX_LENGTH:
            return cleaned

    base = f"{name.strip()} - {condition_label} ({score}%)"
    if len(base) <= SEO_TITLE_MAX_LENGTH:
        return base

    short_base = f"{name.strip()} | {condition_label}"
    if len(short_base) <= SEO_TITLE_MAX_LENGTH:
        return short_base

    return short_base[: SEO_TITLE_MAX_LENGTH - 1].rstrip(" -|,.") + "…"


def build_seo_description(
    name: str,
    brand: str,
    model: str,
    category: str,
    condition_score: int,
    condition_label: ConditionLabel,
    condition_reasoning: str,
    candidate_description: str | None = None,
) -> str:
    """Builds a structured 4-part persuasive Wallapop SEO description in Spanish."""
    score = clamp_condition_score(condition_score)
    label = map_score_to_condition_label(score)

    if candidate_description and len(candidate_description.strip()) >= 85:
        text = candidate_description.strip()
        if "#" in text:
            return text

    tags = [
        tag.lower().replace(" ", "")
        for tag in (brand, model.split()[0] if model else "", category.split()[0], "segundamano", "oportunidad")
        if tag and tag.lower() not in ("desconocida", "genérico", "n/a")
    ]
    hashtag_line = " ".join(f"#{t}" for t in dict.fromkeys(tags) if t)

    return (
        f"✨ Se vende {name} ({brand} {model}) en estado '{label}'.\n"
        f"🔍 Diagnóstico visual IA ({score}/100%): {condition_reasoning.strip()}\n"
        f"📦 Listo para entrega en mano o envío protegido por Wallapop/Vinted. "
        f"Se puede ver y probar sin compromiso.\n"
        f"🏷️ {hashtag_line}"
    )
