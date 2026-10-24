"""Resilient Vision Orchestrator (Chain of Responsibility: Mac Ollama -> Pillow Fallback)."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Sequence

from app.models.sdd import (
    VisionAnalysisResult,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.fallback_provider import DeterministicVisionProvider
from app.vision.image_processor import decode_image_source, prepare_and_inspect_image
from app.vision.ollama_provider import OllamaVisionProvider
from app.vision.protocol import (
    VisionProviderProtocol,
    build_seo_description,
    build_seo_title,
)

DEFAULT_VISION_TIMEOUT_SEC = float(os.getenv("VISION_TIMEOUT_SEC", "6.0"))


class ResilientVisionOrchestrator:
    """Executes Pillow pre-processing + primary VLM (Matías's Mac) + deterministic fallback."""

    def __init__(
        self,
        providers: Sequence[VisionProviderProtocol] | None = None,
        timeout_sec: float = DEFAULT_VISION_TIMEOUT_SEC,
    ) -> None:
        self.timeout_sec = timeout_sec
        self.fallback_provider = DeterministicVisionProvider()
        if providers is not None:
            self.providers = list(providers)
        else:
            mode = os.getenv("VISION_PROVIDER", "auto").lower()
            if mode == "fallback":
                self.providers = [self.fallback_provider]
            else:
                self.providers = [
                    OllamaVisionProvider(request_timeout_sec=timeout_sec),
                    self.fallback_provider,
                ]

    async def analyze_photo(
        self,
        photo_source: str | bytes | Path,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        """Full pipeline: decode -> Pillow optimize & metrics -> VLM provider -> normalize."""
        start_ts = time.perf_counter()
        raw_image = decode_image_source(photo_source)
        enhanced_image, metrics = prepare_and_inspect_image(raw_image)
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
                return self._normalize_result(result, start_ts)
            except Exception:
                continue

        # Guaranteed last-resort fallback so the user's form never fails
        fallback_res = await self.fallback_provider.analyze(
            image=enhanced_image,
            metrics=metrics,
            photo_data_url=data_url_ref,
            user_hint=user_hint,
        )
        return self._normalize_result(fallback_res, start_ts)

    @staticmethod
    def _normalize_result(result: VisionAnalysisResult, start_ts: float) -> VisionAnalysisResult:
        score = clamp_condition_score(result.condition_score)
        label = map_score_to_condition_label(score)
        elapsed_ms = max(1, int(round((time.perf_counter() - start_ts) * 1000)))

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
            source=result.source,
            latency_ms=elapsed_ms,
            model_used=result.model_used,
        )
