"""Optional OpenAI Vision Adapter using gpt-4o-mini with structured outputs."""

from __future__ import annotations

import os

from PIL import Image
from pydantic import BaseModel, Field

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


class _OpenAIExtractionSchema(BaseModel):
    name: str = Field(..., description="Nombre comercial completo en español")
    category: str = Field(..., description="Categoría de mercado en español")
    brand: str = Field(..., description="Marca comercial")
    model: str = Field(..., description="Modelo específico o referencia")
    condition_score: int = Field(..., ge=0, le=100, description="Salud visual 0 a 100")
    condition_reasoning: str = Field(..., description="Diagnóstico visual breve")
    seo_title: str = Field(..., description="Título Wallapop <= 65 caracteres")
    seo_description: str = Field(..., description="Descripción persuasiva de venta")


class OpenAIVisionProvider:
    """Interchangeable provider using OpenAI gpt-4o-mini when OPENAI_API_KEY is present."""

    provider_id: str = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("VISION_OPENAI_MODEL", "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def analyze(
        self,
        image: Image.Image,
        metrics: ImageVisualMetrics,
        photo_data_url: str,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        del image, photo_data_url
        if not self.is_available():
            raise RuntimeError("OPENAI_API_KEY is not configured")

        from openai import AsyncOpenAI  # Deferred import to preserve fast boot

        client = AsyncOpenAI(api_key=self.api_key)
        hint_text = f" Pista del usuario: '{user_hint}'." if user_hint else ""
        system_prompt = (
            "Eres un tasador experto de segunda mano en España (Wallapop, Vinted). "
            "Extrae nombre, marca, modelo, categoría y diagnóstico de salud física (0-100)."
        )

        image_data_uri = f"data:image/jpeg;base64,{metrics.optimized_jpeg_b64}"
        user_prompt = (
            f"Analiza este producto ({metrics.color_name_es}, {metrics.width}x{metrics.height}).{hint_text}"
        )

        response = await client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_data_uri, "detail": "low"}},
                    ],
                },
            ],
            response_format=_OpenAIExtractionSchema,
        )

        parsed = response.choices[0].message.parsed
        if not parsed:
            raise ValueError("OpenAI response did not return parsed structured data")

        score = clamp_condition_score(parsed.condition_score)
        label = map_score_to_condition_label(score)

        return VisionAnalysisResult(
            name=parsed.name.strip(),
            category=parsed.category.strip(),
            brand=parsed.brand.strip(),
            model=parsed.model.strip(),
            condition_score=score,
            condition_label=label,
            condition_reasoning=parsed.condition_reasoning.strip(),
            seo_title=build_seo_title(parsed.name, label, score, parsed.seo_title),
            seo_description=build_seo_description(
                name=parsed.name,
                brand=parsed.brand,
                model=parsed.model,
                category=parsed.category,
                condition_score=score,
                condition_label=label,
                condition_reasoning=parsed.condition_reasoning,
                candidate_description=parsed.seo_description,
            ),
            source="openai",
            model_used=self.model,
        )
