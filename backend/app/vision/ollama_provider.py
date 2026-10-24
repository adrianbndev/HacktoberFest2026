"""Local/LAN VLM Adapter targeting Ollama on Matías's 16GB Mac (zero paid APIs)."""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any
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

PREFERRED_MAC_VISION_MODELS: tuple[str, ...] = (
    "llama3.2-vision:11b",
    "llama3.2-vision",
    "minicpm-v:8b",
    "minicpm-v",
    "llava:13b",
    "llava:7b",
    "llava",
    "moondream",
)


class _VLMFormExtractionSchema(BaseModel):
    name: str = Field(..., description="Nombre comercial completo en español")
    category: str = Field(..., description="Categoría de mercado")
    brand: str = Field(..., description="Marca comercial")
    model: str = Field(..., description="Modelo específico o referencia")
    condition_score: int = Field(..., ge=0, le=100, description="Salud visual 0 a 100")
    condition_reasoning: str = Field(..., description="Explicación breve en español")
    seo_title: str = Field(..., description="Título atractivo <= 65 caracteres para Wallapop")
    seo_description: str = Field(..., description="Descripción persuasiva de venta")


SYSTEM_PROMPT_ES = (
    "Eres un tasador experto de productos de segunda mano en España (Wallapop, Vinted, Milanuncios, eBay). "
    "Analiza la fotografía del objeto y extrae con máxima precisión los datos para rellenar el formulario: "
    "nombre comercial exacto (incluyendo color visible), marca, modelo, categoría y diagnóstico de estado físico "
    "(condition_score de 0 a 100: 90-100 Nuevo, 80-89 Como nuevo, 65-79 Buen estado, 40-64 Desgaste visible, 0-39 Para piezas). "
    "Responde SIEMPRE en JSON válido."
)


def _http_json_request(url: str, payload: dict[str, Any] | None = None, timeout: float = 2.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaVisionProvider:
    """Connects over LAN/localhost to Ollama (Matías's 16GB Mac) with structured outputs & circuit breaker."""

    provider_id: str = "ollama_local"
    CIRCUIT_BREAKER_TTL_SEC: float = 12.0

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        request_timeout_sec: float = 2.5,
    ) -> None:
        raw_url = (
            base_url
            or os.getenv("VISION_OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.base_url = raw_url if raw_url.startswith("http") else f"http://{raw_url}"
        self.configured_model = model_name or os.getenv("VISION_OLLAMA_MODEL") or "llama3.2-vision"
        self.request_timeout_sec = request_timeout_sec
        self._resolved_model: str | None = None
        self._last_check_ts: float = 0.0
        self._cached_health: dict[str, Any] | None = None

    def reset_circuit_breaker(self) -> None:
        self._last_check_ts = 0.0
        self._cached_health = None
        self._resolved_model = None

    async def check_node_health(self, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._cached_health and (now - self._last_check_ts) < self.CIRCUIT_BREAKER_TTL_SEC:
            return self._cached_health

        try:
            tags_data = await asyncio.to_thread(_http_json_request, f"{self.base_url}/api/tags", None, 1.2)
            models = [m.get("name", "") for m in tags_data.get("models", [])]
            res = {
                "reachable": True,
                "baseUrl": self.base_url,
                "configuredModel": self.configured_model,
                "selectedModel": self._pick_best_installed_model(models),
                "installedModels": models,
            }
        except Exception as exc:
            res = {
                "reachable": False,
                "baseUrl": self.base_url,
                "configuredModel": self.configured_model,
                "error": str(exc),
            }

        self._last_check_ts = now
        self._cached_health = res
        return res

    def _pick_best_installed_model(self, installed: list[str]) -> str:
        if not installed or self.configured_model in installed:
            return self.configured_model
        for cand in PREFERRED_MAC_VISION_MODELS:
            for inst in installed:
                if inst == cand or inst.startswith(cand):
                    return inst
        for cand in PREFERRED_MAC_VISION_MODELS:
            family = cand.split(":")[0]
            for inst in installed:
                if inst.startswith(family):
                    return inst
        return installed[0]

    async def _resolve_model(self) -> str:
        if self._resolved_model:
            return self._resolved_model
        health = await self.check_node_health()
        if not health.get("reachable"):
            raise ConnectionError(f"Ollama node unreachable at {self.base_url}: {health.get('error')}")
        self._resolved_model = str(health.get("selectedModel") or self.configured_model)
        return self._resolved_model

    async def analyze(
        self,
        image: Image.Image,
        metrics: ImageVisualMetrics,
        photo_data_url: str,
        user_hint: str | None = None,
    ) -> VisionAnalysisResult:
        del image, photo_data_url
        model_to_use = await self._resolve_model()
        hint_clause = f"\nPista adicional del usuario: '{user_hint}'." if user_hint else ""
        context = (
            f"Color dominante en el centro: {metrics.color_name_es}. "
            f"Resolución original: {metrics.width}x{metrics.height}.{hint_clause}"
        )

        payload: dict[str, Any] = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_ES},
                {
                    "role": "user",
                    "content": f"Identifica este producto para pre-rellenar el formulario. {context}",
                    "images": [metrics.optimized_jpeg_b64],
                },
            ],
            "format": _VLMFormExtractionSchema.model_json_schema(),
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.1, "num_predict": 320},
        }

        raw = await asyncio.to_thread(
            _http_json_request, f"{self.base_url}/api/chat", payload, self.request_timeout_sec
        )
        extracted = _VLMFormExtractionSchema.model_validate_json(raw.get("message", {}).get("content", "{}"))
        score = clamp_condition_score(extracted.condition_score)
        label = map_score_to_condition_label(score)

        return VisionAnalysisResult(
            name=extracted.name.strip(),
            category=extracted.category.strip(),
            brand=extracted.brand.strip(),
            model=extracted.model.strip(),
            condition_score=score,
            condition_label=label,
            condition_reasoning=extracted.condition_reasoning.strip(),
            seo_title=build_seo_title(extracted.name, label, score, extracted.seo_title),
            seo_description=build_seo_description(
                name=extracted.name,
                brand=extracted.brand,
                model=extracted.model,
                category=extracted.category,
                condition_score=score,
                condition_label=label,
                condition_reasoning=extracted.condition_reasoning,
                candidate_description=extracted.seo_description,
            ),
            source="ollama_local",
            model_used=model_to_use,
        )
