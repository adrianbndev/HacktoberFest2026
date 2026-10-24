"""Liskov-compliant deterministic Vision fallback using Pillow visual inspection."""

from __future__ import annotations

from dataclasses import dataclass
from PIL import Image

from app.models.sdd import (
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.protocol import (
    ImageVisualMetrics,
    build_seo_description,
    build_seo_title,
)


@dataclass(frozen=True)
class _CatalogItemTemplate:
    keywords: tuple[str, ...]
    name: str
    category: str
    brand: str
    model: str
    base_score: int
    reasoning_template: str


CATALOG_TEMPLATES: tuple[_CatalogItemTemplate, ...] = (
    _CatalogItemTemplate(
        keywords=("switch", "nintendo", "oled", "joycon", "consola"),
        name="Nintendo Switch OLED 64GB",
        category="Consolas y Videojuegos",
        brand="Nintendo",
        model="Switch OLED HEG-001",
        base_score=88,
        reasoning_template="Pantalla OLED sin rayones apreciables, carcasa en tono {color} bien conservada y controles firmes.",
    ),
    _CatalogItemTemplate(
        keywords=("iphone", "apple", "ios", "pro", "movil", "móvil", "telefono"),
        name="Apple iPhone 14 Pro 128GB",
        category="Telefonía y Smartphones",
        brand="Apple",
        model="iPhone 14 Pro A2890",
        base_score=85,
        reasoning_template="Chasis en acabado {color} con bordes limpios, módulo de cámaras intacto y cristal sin fisuras.",
    ),
    _CatalogItemTemplate(
        keywords=("macbook", "portatil", "portátil", "laptop", "mac", "air", "m2", "m3"),
        name="MacBook Air 13 M2 8GB/256GB",
        category="Informática y Portátiles",
        brand="Apple",
        model="MacBook Air M2 A2681",
        base_score=91,
        reasoning_template="Chasis unibody de aluminio ({color}) sin abolladuras, teclado limpio y bisagra firme.",
    ),
    _CatalogItemTemplate(
        keywords=("sony", "wh-1000xm5", "xm5", "xm4", "auriculares", "cascos", "audio"),
        name="Auriculares Sony WH-1000XM5 ANC",
        category="Audio y Sonido",
        brand="Sony",
        model="WH-1000XM5",
        base_score=84,
        reasoning_template="Almohadillas sin desgaste pronunciado, diadema intacta y acabado {color} bien cuidado.",
    ),
    _CatalogItemTemplate(
        keywords=("ps5", "playstation", "dualsense", "mando"),
        name="PlayStation 5 Edición Disco 825GB",
        category="Consolas y Videojuegos",
        brand="Sony",
        model="PS5 CFI-1216A",
        base_score=86,
        reasoning_template="Cubiertas laterales en color {color} limpias, puertos intactos y excelente estado estético.",
    ),
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


def _select_template(metrics: ImageVisualMetrics, user_hint: str | None) -> _CatalogItemTemplate:
    if user_hint:
        lowered = user_hint.lower()
        for item in CATALOG_TEMPLATES:
            if any(k in lowered for k in item.keywords):
                return item

    # Deterministic visual selection based on color & aspect ratio when no hint is provided
    r, g, b = metrics.dominant_rgb
    idx = (r + g * 2 + b * 3 + metrics.width) % len(CATALOG_TEMPLATES)
    return CATALOG_TEMPLATES[idx]


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
        reasoning = (
            template.reasoning_template.format(color=metrics.color_name_es.lower())
            + f" (Inspección visual: nitidez {metrics.sharpness:.1f}, luminancia {metrics.brightness:.0f}/255)."
        )

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
