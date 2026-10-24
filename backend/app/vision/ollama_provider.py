"""Local/LAN VLM Adapter targeting Ollama on Matías's 16GB Mac (zero paid APIs)."""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Literal
from PIL import Image
from pydantic import BaseModel, Field

from app.models.sdd import (
    VisionAnalysisResult,
    VisionDynamicField,
    clamp_condition_score,
    map_score_to_condition_label,
)
from app.vision.dynamic_fields import ensure_dotenv_loaded, normalize_vlm_dynamic_fields
from app.vision.protocol import (
    ImageVisualMetrics,
    build_seo_description,
    build_seo_title,
)

PREFERRED_MAC_VISION_MODELS: tuple[str, ...] = (
    "qwen2.5vl:7b",
    "qwen2.5vl",
    "gemma3:12b",
    "minicpm-v:8b",
    "minicpm-v",
    "llava:13b",
    "llava:7b",
    "llava",
    "moondream",
)


class _VLMDynamicFieldItem(BaseModel):
    key: str = Field(..., description="Identificador camelCase del atributo propio de este artículo (ej: connectivity, color, material, format, accessories)")
    label: str = Field(..., description="Nombre del atributo en español propio y exclusivo del objeto fotografiado")
    value: str = Field(..., description="Valor observado en la imagen o propio del modelo identificado")
    field_type: Literal["select", "text", "number"] = Field(default="select", description="'select' si tiene opciones cerradas frecuentes, 'text' o 'number' si es dato abierto")
    options: list[str] = Field(default_factory=list, description="Si field_type es 'select', 3 a 5 opciones reales en español para este mismo atributo (incluyendo 'value')")


class _VLMFormExtractionSchema(BaseModel):
    name: str = Field(..., description="Nombre comercial completo en español")
    category: str = Field(..., description="Categoría precisa del objeto (ej: Audio y Sonido, Periféricos · Ratones, Periféricos · Teclados, Móviles y Telefonía, Informática y Portátiles, Consolas y Videojuegos, Motor y Vehículos, Mobiliario y Decoración)")
    brand: str = Field(..., description="Marca comercial")
    model: str = Field(..., description="Modelo específico o referencia")
    condition_score: int = Field(..., ge=0, le=100, description="Salud visual 0 a 100")
    condition_reasoning: str = Field(..., description="Explicación breve en español")
    seo_title: str = Field(..., description="Título atractivo <= 65 caracteres para Wallapop")
    seo_description: str = Field(..., description="Descripción persuasiva de venta")
    dynamic_fields: list[_VLMDynamicFieldItem] = Field(
        default_factory=list,
        description="Entre 4 y 6 campos técnicos o físicos EXCLUSIVOS del objeto concreto de la foto. PROHIBIDO mezclar atributos de otros aparatos.",
    )


SYSTEM_PROMPT_ES = (
    "Eres un tasador experto de productos de segunda mano en España. "
    "Analiza la fotografía e identifica el OBJETO EXACTO (nombre comercial, marca, modelo, categoría específica y salud física 0-100). "
    "En 'dynamic_fields', genera entre 4 y 6 campos técnicos EXCLUSIVOS del objeto concreto que ves en la foto. "
    "REGLA ESTRICTA DE NO CONTAMINACIÓN: NUNCA pongas atributos de otro tipo de aparato (jamás pongas Sensor/DPI o Número de botones a unos auriculares/altavoces; jamás pongas RAM, SSD o Tamaño de pantalla a un ratón, teclado o auricular).\n"
    "- Si es Audio (auriculares, cascos, AirPods, altavoz): Formato de audio (Diadema Over-Ear, In-Ear True Wireless, Altavoz portátil), Conectividad (Bluetooth inalámbrico, Bluetooth + Cable Jack, Solo cable), Cancelación de ruido ANC (Sí ANC activa, Aislamiento pasivo, No), Estuche y cables, Color.\n"
    "- Si es un Ratón: Conectividad, Sensor / Precisión DPI, Número de botones, Ergonomía / Mano, Alimentación, Color.\n"
    "- Si es un Teclado: Tipo de interruptores (Switches), Formato / Tamaño (75%, TKL, 100%, 60%), Distribución de idioma (Español ISO Ñ, ANSI), Conectividad, Iluminación, Color.\n"
    "- Si es un Móvil o Portátil: Almacenamiento, Memoria RAM, Procesador o Salud de batería (%), Tamaño/Estado de pantalla, Color.\n"
    "- Si es un Coche/Vehículo: Tipo de combustible, Cambio/Transmisión, Carrocería, Año, Kilometraje (km), Etiqueta DGT, Color.\n"
    "- Para cualquier otro objeto (consola, monitor, cámara, bici, mueble, ropa, calzado, reloj, electrodoméstico), genera únicamente los 4-6 atributos reales que definen ese artículo concreto. "
    "Para cada campo con 'field_type': 'select', incluye de 3 a 5 'options' reales en español que contengan el 'value'. "
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
        request_timeout_sec: float | None = None,
    ) -> None:
        ensure_dotenv_loaded()
        raw_url = (
            base_url
            or os.getenv("VISION_OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.base_url = raw_url if raw_url.startswith("http") else f"http://{raw_url}"
        self.configured_model = model_name or os.getenv("VISION_OLLAMA_MODEL") or "qwen2.5vl:7b"
        self.request_timeout_sec = request_timeout_sec or float(os.getenv("VISION_TIMEOUT_SEC", "35.0"))
        self._resolved_model: str | None = None
        self._last_check_ts: float = 0.0
        self._cached_health: dict[str, Any] | None = None
        self.last_error: str | None = None

    def reset_circuit_breaker(self) -> None:
        self._last_check_ts = 0.0
        self._cached_health = None
        self._resolved_model = None

    async def check_node_health(self, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._cached_health and (now - self._last_check_ts) < self.CIRCUIT_BREAKER_TTL_SEC:
            return self._cached_health

        is_local = "127.0.0.1" in self.base_url or "localhost" in self.base_url
        ping_timeout = 1.0 if is_local else 3.5
        try:
            tags_data = await asyncio.to_thread(_http_json_request, f"{self.base_url}/api/tags", None, ping_timeout)
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
                if inst == cand or inst.startswith(cand.split(":")[0]):
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
        context = f"Color dominante: {metrics.color_name_es}. Resolución: {metrics.width}x{metrics.height}.{hint_clause}"

        payload: dict[str, Any] = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_ES},
                {
                    "role": "user",
                    "content": (
                        f"Identifica el objeto exacto de esta imagen y genera en 'dynamic_fields' los campos específicos "
                        f"exclusivos de este tipo de artículo (no uses campos de otros aparatos). {context}"
                    ),
                    "images": [metrics.optimized_jpeg_b64],
                },
            ],
            "format": _VLMFormExtractionSchema.model_json_schema(),
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.1, "num_predict": 650},
        }

        try:
            raw = await asyncio.to_thread(
                _http_json_request, f"{self.base_url}/api/chat", payload, self.request_timeout_sec
            )
            self.last_error = None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            self.last_error = f"HTTP {exc.code} from Ollama ({model_to_use}): {body}"
            raise RuntimeError(self.last_error) from exc
        except Exception as exc:
            self.last_error = f"Ollama error ({model_to_use}): {exc}"
            raise

        extracted = _VLMFormExtractionSchema.model_validate_json(raw.get("message", {}).get("content", "{}"))
        score = clamp_condition_score(extracted.condition_score)
        label = map_score_to_condition_label(score)
        raw_vlm_fields = [
            VisionDynamicField(
                key=f.key, label=f.label, value=f.value, field_type=f.field_type, options=f.options,
            )
            for f in extracted.dynamic_fields
        ]

        normalized_fields = normalize_vlm_dynamic_fields(
            vlm_fields=raw_vlm_fields, category=extracted.category, name=extracted.name,
            brand=extracted.brand, model=extracted.model, color_name_es=metrics.color_name_es,
        )

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
                name=extracted.name, brand=extracted.brand, model=extracted.model,
                category=extracted.category, condition_score=score, condition_label=label,
                condition_reasoning=extracted.condition_reasoning, candidate_description=extracted.seo_description,
                dynamic_fields=normalized_fields,
            ),
            dynamic_fields=normalized_fields,
            source="ollama_local",
            model_used=model_to_use,
        )
