"""DeepSeek-only product relevance for the deep market analysis.

`/analyze` has no deterministic product prefilter: every sanitised listing is
classified by `deepseek-flash` in small JSON batches. Only listings labelled
`exact` feed the price triplet. A missing key, transport error, timeout or
invalid payload fails the analysis with a typed error (never a silent subset
and never the full sample as a fallback).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from time import monotonic
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.config import Settings
from app.mcp.deepseek_client import DeepSeekChat
from app.models.market_analysis import MarketAnalysisRequest
from app.models.sdd import MarketListingSample

logger = logging.getLogger(__name__)

EXACT = "exact"
LABELS = frozenset(
    {
        "exact",
        "different_model",
        "accessory",
        "single_item",
        "broken",
        "unrelated",
        "bundle",
    }
)
UNKNOWN_LABEL = "unrelated"

LLM_RELEVANCE_UNAVAILABLE = "llm_relevance_unavailable"
LLM_RELEVANCE_TIMEOUT = "llm_relevance_timeout"
LLM_RELEVANCE_DISABLED = "llm_relevance_disabled"
LLM_RELEVANCE_EMPTY = "llm_relevance_empty"

SYSTEM_PROMPT = """Eres un clasificador estricto de anuncios de segunda mano.
Recibes un producto objetivo y una lista de anuncios. Decide si cada anuncio es
exactamente ese producto. Devuelve solo JSON válido con esta forma:
{"listings": [{"id": <id entero recibido>, "label": "<etiqueta>"}]}
Etiquetas permitidas: exact, different_model, accessory, single_item, broken,
unrelated, bundle.
Incluye una entrada por cada id recibido. No inventes ids ni anuncios.

Reglas:
- exact: mismo producto completo, misma generación y modelo, funciona y es una
  unidad.
- different_model: otro modelo, otra generación o cualquier duda razonable.
- accessory: funda, estuche, caja, cable, cargador, recambio o accesorio.
- single_item: una sola pieza o un solo lado del producto (p. ej. un auricular).
- broken: roto, averiado, no funciona o para piezas.
- bundle: pack o lote de varios productos o unidades.
- unrelated: no tiene relación con el producto objetivo.
- "con estuche" o "con caja" puede ser exact si el producto está completo; el
  accesorio por separado nunca es exact.
- Si dudas entre exact y otro modelo, usa different_model.

Ejemplos para el objetivo "Apple AirPods Pro 2":
- "AirPods Pro 2" -> exact
- "Apple AirPods Pro 2" -> exact
- "AirPods Pro 2nd generation" -> exact
- "AirPods Pro 2 con estuche" -> exact
- "AirPods 2" -> different_model
- "AirPods Pro" -> different_model
- "AirPods Pro 3" -> different_model
- "AirPods Pro 2 solo izquierdo" -> single_item
- "AirPods Pro 2 rotos" -> broken
- "Funda para AirPods Pro 2" -> accessory
- "Estuche AirPods Pro 2" -> accessory
- "AirPods Pro 2 para piezas" -> broken
- "Lote 2x AirPods Pro 2" -> bundle
"""


class LlmRelevanceUnavailableError(Exception):
    """The LLM could not decide relevance; the caller must return a 503."""

    def __init__(self, code: str = LLM_RELEVANCE_UNAVAILABLE) -> None:
        super().__init__(code)
        self.code = code


class RelevanceClassifierProtocol(Protocol):
    async def classify(
        self,
        request: MarketAnalysisRequest,
        listings: Sequence[MarketListingSample],
        deadline: float,
    ) -> list[MarketListingSample]: ...


class _LabeledListing(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    label: str = UNKNOWN_LABEL

    @field_validator("label")
    @classmethod
    def _normalise_label(cls, value: str) -> str:
        normalised = value.strip().lower()
        return normalised if normalised in LABELS else UNKNOWN_LABEL


class _RelevanceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    listings: list[_LabeledListing] = Field(default_factory=list)


def _validate_response(payload: dict[str, object]) -> _RelevanceResponse | None:
    try:
        return _RelevanceResponse.model_validate(payload)
    except ValidationError:
        return None


def _id_key(value: int | str | None) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    text = str(value).strip()
    return text or None


class LlmRelevanceFilter:
    """Batch classifier over the shared DeepSeek JSON transport."""

    def __init__(self, settings: Settings, *, chat: DeepSeekChat | None = None) -> None:
        self._settings = settings
        self._chat = chat or DeepSeekChat(settings)

    async def classify(
        self,
        request: MarketAnalysisRequest,
        listings: Sequence[MarketListingSample],
        deadline: float,
    ) -> list[MarketListingSample]:
        if not self._settings.market_llm_relevance_enabled:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_DISABLED)
        indexed = list(enumerate(listings))
        if not indexed:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_EMPTY)

        remaining = min(
            self._settings.market_llm_relevance_budget_sec, deadline - monotonic()
        )
        if remaining <= 0:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_TIMEOUT)
        local_deadline = monotonic() + remaining
        batches = [
            indexed[start : start + self._settings.market_llm_relevance_batch_size]
            for start in range(0, len(indexed), self._settings.market_llm_relevance_batch_size)
        ]
        try:
            outcomes = await asyncio.wait_for(
                asyncio.gather(
                    *(
                        self._classify_batch(request, batch, remaining)
                        for batch in batches
                    )
                ),
                timeout=remaining + 0.5,
            )
        except TimeoutError as exc:
            raise LlmRelevanceUnavailableError(LLM_RELEVANCE_TIMEOUT) from exc

        accepted_ids: set[str] = set()
        for outcome in outcomes:
            if outcome is None:
                code = (
                    LLM_RELEVANCE_TIMEOUT
                    if monotonic() >= local_deadline
                    else LLM_RELEVANCE_UNAVAILABLE
                )
                raise LlmRelevanceUnavailableError(code)
            accepted_ids |= outcome

        return [
            listing for index, listing in indexed if str(index) in accepted_ids
        ]

    async def _classify_batch(
        self,
        request: MarketAnalysisRequest,
        batch: Sequence[tuple[int, MarketListingSample]],
        budget_sec: float,
    ) -> set[str] | None:
        response = await self._chat.request_json(
            system=SYSTEM_PROMPT,
            user=_user_prompt(request, batch),
            validator=_validate_response,
            budget_sec=budget_sec,
            model=self._settings.llm_relevance_model,
        )
        if response is None:
            logger.warning("LLM relevance batch failed")
            return None
        batch_ids = {str(index) for index, _ in batch}
        return {
            key
            for entry in response.listings
            if entry.label == EXACT
            if (key := _id_key(entry.id)) is not None and key in batch_ids
        }


def _user_prompt(
    request: MarketAnalysisRequest, batch: Sequence[tuple[int, MarketListingSample]]
) -> str:
    payload = {
        "target": {
            "name": request.name,
            "brand": request.brand,
            "model": request.model,
            "category": request.category,
            "description": request.description,
            "conditionLabel": request.condition_label,
            "conditionScore": request.condition_score,
        },
        "listings": [
            {
                "id": index,
                "title": listing.title,
                "price": listing.price,
                "condition": listing.condition,
            }
            for index, listing in batch
        ],
    }
    return json.dumps(payload, ensure_ascii=False)
