"""Resilient Vision Orchestrator (Chain of Responsibility: Ollama -> OpenAI -> Pillow Fallback)."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Sequence
from pathlib import Path

from app.models.sdd import (
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.dynamic_fields import build_dynamic_fields, ensure_dotenv_loaded
from app.vision.fallback_provider import DeterministicVisionProvider
from app.vision.image_processor import decode_image_source, prepare_and_inspect_image
from app.vision.ollama_provider import OllamaVisionProvider
from app.vision.openai_provider import OpenAIVisionProvider
from app.vision.protocol import (
    VisionProviderProtocol,
    build_seo_description,
    build_seo_title,
)

ensure_dotenv_loaded()
DEFAULT_VISION_TIMEOUT_SEC = float(os.getenv("VISION_TIMEOUT_SEC", "35.0"))


class ResilientVisionOrchestrator:
    """Executes non-blocking Pillow inspection + primary VLM + optional OpenAI + deterministic fallback."""

    def __init__(
        self,
        providers: Sequence[VisionProviderProtocol] | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        ensure_dotenv_loaded()
        self.timeout_sec = timeout_sec if timeout_sec is not None else float(os.getenv("VISION_TIMEOUT_SEC", str(DEFAULT_VISION_TIMEOUT_SEC)))
        self.fallback_provider = DeterministicVisionProvider()
        if providers is not None:
            self.providers = list(providers)
        else:
            mode = os.getenv("VISION_PROVIDER", "auto").lower()
            if mode == "fallback":
                self.providers = [self.fallback_provider]
            else:
                active: list[VisionProviderProtocol] = [
                    OllamaVisionProvider(request_timeout_sec=self.timeout_sec),
                ]
                openai_prov = OpenAIVisionProvider()
                if openai_prov.is_available():
                    active.append(openai_prov)
                active.append(self.fallback_provider)
                self.providers = active

    def get_provider_ids(self) -> list[str]:
        return [p.provider_id for p in self.providers]

    async def analyze_photo(
        self,
        photo_source: str | bytes | Path,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        """Full pipeline: non-blocking decode & Pillow metrics -> VLM chain -> normalize."""
        start_ts = time.perf_counter()
        raw_image = await asyncio.to_thread(decode_image_source, photo_source)
        enhanced_image, metrics = await asyncio.to_thread(prepare_and_inspect_image, raw_image)
        data_url_ref = photo_source if isinstance(photo_source, str) else "binary://image"

        for provider in self.providers:
            try:
                result = await asyncio.wait_for(
                    provider.analyze(
                        image=enhanced_image,
                        metrics=metrics,
                        photo_data_url=data_url_ref,
                        user_hint=user_hint,
                    ),
                    timeout=self.timeout_sec,
                )
                return self._normalize_result(result, start_ts, metrics.color_name_es)
            except Exception:
                continue

        fallback_res = await self.fallback_provider.analyze(
            image=enhanced_image,
            metrics=metrics,
            photo_data_url=data_url_ref,
            user_hint=user_hint,
        )
        return self._normalize_result(fallback_res, start_ts, metrics.color_name_es)

    @staticmethod
    def _normalize_result(
        result: VisionAnalysisResult,
        start_ts: float,
        color_name_es: str = "Negro",
    ) -> VisionAnalysisResult:
        score = clamp_condition_score(result.condition_score)
        label = map_score_to_condition_label(score)
        elapsed_ms = max(1, int(round((time.perf_counter() - start_ts) * 1000)))
        dynamic_fields = result.dynamic_fields or build_dynamic_fields(
            category=result.category,
            name=result.name,
            brand=result.brand,
            model=result.model,
            color_name_es=color_name_es,
        )

        return VisionAnalysisResult(
            name=result.name.strip(),
            category=result.category.strip(),
            brand=result.brand.strip(),
            model=result.model.strip(),
            condition_score=score,
            condition_label=label,
            condition_reasoning=result.condition_reasoning.strip(),
            seo_title=build_seo_title(result.name, label, score, result.seo_title),
            seo_description=build_seo_description(
                name=result.name,
                brand=result.brand,
                model=result.model,
                category=result.category,
                condition_score=score,
                condition_label=label,
                condition_reasoning=result.condition_reasoning,
                candidate_description=result.seo_description,
            ),
            dynamic_fields=dynamic_fields,
            source=result.source,
            latency_ms=elapsed_ms,
            model_used=result.model_used,
        )
