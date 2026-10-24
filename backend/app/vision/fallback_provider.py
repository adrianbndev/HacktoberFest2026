"""Liskov-compliant deterministic Vision fallback using Pillow visual inspection."""

from __future__ import annotations

from PIL import Image

from app.models.sdd import (
    ConditionLabel,
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.catalog_data import (
    CATALOG_TEMPLATES,
    CatalogItemTemplate,
    synthesize_template_from_hint,
)
from app.vision.protocol import (
    ImageVisualMetrics,
    build_seo_description,
    build_seo_title,
)


def _compute_visual_health_adjustment(metrics: ImageVisualMetrics) -> int:
    """Computes a deterministic score adjustment (-12 to +7) from Pillow image metrics."""
    delta = 0
    if metrics.sharpness >= 18.0:
        delta += 4
    elif metrics.sharpness < 7.0:
        delta -= 6

    if 85.0 <= metrics.brightness <= 215.0:
        delta += 3
    elif metrics.brightness < 45.0:
        delta -= 5

    if metrics.contrast < 20.0:
        delta -= 4
    return delta


def _matches_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    low = text.lower()
    tokens = set(low.replace("-", " ").replace("/", " ").replace("_", " ").split())
    for kw in keywords:
        k = kw.lower()
        if " " in k:
            if k in low:
                return True
        elif k in tokens:
            return True
    return False


def _select_template(metrics: ImageVisualMetrics, user_hint: str | None) -> CatalogItemTemplate:
    if user_hint and user_hint.strip():
        for item in CATALOG_TEMPLATES:
            if _matches_keywords(user_hint, item.keywords):
                return item
        return synthesize_template_from_hint(user_hint)

    r, g, b = metrics.dominant_rgb
    idx = (r + g * 2 + b * 3 + metrics.width) % len(CATALOG_TEMPLATES)
    return CATALOG_TEMPLATES[idx]


def _format_health_reasoning(label: ConditionLabel, color: str, metrics: ImageVisualMetrics) -> str:
    descriptions: dict[ConditionLabel, str] = {
        "Nuevo": f"Artículo en acabado {color} sin marcas de uso ni arañazos; conservación impoluta.",
        "Como nuevo": f"Superficie y acabados en tono {color} muy limpios, conservación excelente.",
        "Buen estado": f"Ligeras marcas de uso normal en bordes ({color}), plenamente funcional.",
        "Desgaste visible": f"Marcas evidentes de uso continuado o roces estéticos en el acabado {color}.",
        "Para piezas": f"Deterioro visible o marcas pronunciadas en la carcasa ({color}); apto para repuestos.",
    }
    desc = descriptions.get(label, f"Estado físico evaluado en color {color}.")
    return f"{desc} (Inspección visual: nitidez {metrics.sharpness:.1f}, luminancia {metrics.brightness:.0f}/255)."


class DeterministicVisionProvider:
    """Offline Liskov fallback that inspects image via Pillow in <20ms."""

    provider_id: str = "deterministic_fallback"

    async def analyze(
        self,
        image: Image.Image,
        metrics: ImageVisualMetrics,
        photo_data_url: str,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        del image, photo_data_url
        template = _select_template(metrics, user_hint)
        adj = _compute_visual_health_adjustment(metrics)
        score = clamp_condition_score(template.base_score + adj)
        label = map_score_to_condition_label(score)

        product_name = (
            f"{template.name} ({metrics.color_name_es})"
            if metrics.color_name_es.lower() not in template.name.lower()
            else template.name
        )
        reasoning = _format_health_reasoning(label, metrics.color_name_es.lower(), metrics)

        return VisionAnalysisResult(
            name=product_name,
            category=template.category,
            brand=template.brand,
            model=template.model,
            condition_score=score,
            condition_label=label,
            condition_reasoning=reasoning,
            seo_title=build_seo_title(product_name, label, score),
            seo_description=build_seo_description(
                name=product_name,
                brand=template.brand,
                model=template.model,
                category=template.category,
                condition_score=score,
                condition_label=label,
                condition_reasoning=reasoning,
            ),
            source="deterministic_fallback",
            model_used="pillow-deterministic-v1",
        )
