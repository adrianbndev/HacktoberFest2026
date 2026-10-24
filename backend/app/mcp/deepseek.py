"""DeepSeek query parsing, relevance scoring and grounded recommendations (MOD-04 §6).

Every capability has a deterministic fallback: a valuation never fails because
the model is slow, unavailable or returns invalid JSON.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.config import Settings
from app.mcp.deepseek_client import CompletionCallable, DeepSeekChat
from app.models.sdd import (
    MarketListingSample,
    MarketValuationResult,
    ValuationRecommendation,
    ValuationRequest,
)

FALLBACK_WARNING = "Recomendación generada con la plantilla determinista (LLM no disponible)."
CLAMP_WARNING = "El precio sugerido por la IA se ajustó al rango de mercado."
MAX_BULLETS = 5
MAX_RISKS = 4
RELEVANCE_THRESHOLD = 0.34
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
_CAPACITY_RE = re.compile(r"^\d+(?:gb|tb|mb)$")
_STOPWORDS = frozenset(
    {"caja", "como", "con", "desde", "esta", "este", "para", "pero", "solo", "todo", "viene"}
)


class ParsedQuery(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    query: str = Field(min_length=2, max_length=200)
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    keywords: list[str] = Field(default_factory=list, max_length=8)


class _LlmRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    summary: str = Field(min_length=1, max_length=600)
    suggested_price: int = Field(
        validation_alias=AliasChoices("suggestedPrice", "suggested_price")
    )
    bullets: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    negotiation_margin_eur: int = Field(
        validation_alias=AliasChoices("negotiationMarginEur", "negotiation_margin_eur")
    )

    @model_validator(mode="after")
    def _require_a_bullet(self) -> _LlmRecommendation:
        if not any(bullet.strip() for bullet in self.bullets):
            raise ValueError("recommendation must include at least one bullet")
        return self


@dataclass(frozen=True, slots=True)
class RecommendationOutcome:
    recommendation: ValuationRecommendation
    warnings: tuple[str, ...] = ()


class DeepSeekRecommender:
    """Domain-facing helper over the DeepSeek JSON transport."""

    def __init__(
        self, settings: Settings, *, completion: CompletionCallable | None = None
    ) -> None:
        self._chat = DeepSeekChat(settings, completion=completion)

    async def parse_query(self, raw_query: str, *, budget_sec: float | None = None) -> ParsedQuery:
        system = (
            "Extrae los datos de un anuncio de segunda mano. Responde solo con json válido: "
            '{"query": str, "brand": str, "model": str, "category": str, "keywords": [str]}.'
        )
        parsed = await self._chat.request_json(
            system=system,
            user=f"Anuncio: {raw_query}",
            validator=_validate_parsed_query,
            budget_sec=budget_sec,
        )
        return parsed if parsed is not None else _deterministic_parsed_query(raw_query)

    def score_relevance(
        self, query: str, listings: Sequence[MarketListingSample]
    ) -> list[MarketListingSample]:
        """Lexical relevance filter used in the hot path (no extra LLM latency)."""
        query_tokens = _tokens(query)
        if not query_tokens:
            return list(listings)
        query_models = _model_tokens(query_tokens)
        scored: list[tuple[float, MarketListingSample]] = []
        for listing in listings:
            title_tokens = _tokens(listing.title)
            if query_models:
                title_models = _model_tokens(title_tokens)
                if not query_models & title_models:
                    continue
                overlap = len(query_models & title_models) / len(query_models)
            else:
                overlap = len(query_tokens & title_tokens) / len(query_tokens)
            if overlap >= RELEVANCE_THRESHOLD:
                scored.append((overlap, listing))
        scored.sort(key=lambda pair: (-pair[0], pair[1].price))
        return [listing for _, listing in scored]

    async def recommend(
        self,
        *,
        request: ValuationRequest,
        valuation: MarketValuationResult,
        budget_sec: float | None = None,
    ) -> RecommendationOutcome:
        system = (
            "Eres un tasador experto de segunda mano en España. Responde solo con json válido: "
            '{"summary": str, "suggestedPrice": int, "bullets": [str], "risks": [str], '
            '"negotiationMarginEur": int}. Usa únicamente los datos aportados; no inventes '
            "anuncios ni precios."
        )
        payload = await self._chat.request_json(
            system=system,
            user=_recommendation_prompt(request, valuation),
            validator=_validate_recommendation,
            budget_sec=budget_sec,
        )
        if payload is None:
            return _template_outcome(request, valuation)
        return _clamp_outcome(payload, valuation)


def _validate_recommendation(payload: dict[str, object]) -> _LlmRecommendation | None:
    try:
        return _LlmRecommendation.model_validate(payload)
    except ValidationError:
        return None


def _validate_parsed_query(payload: dict[str, object]) -> ParsedQuery | None:
    try:
        return ParsedQuery.model_validate(payload)
    except ValidationError:
        return None


def _clamp_outcome(
    payload: _LlmRecommendation, valuation: MarketValuationResult
) -> RecommendationOutcome:
    warnings: list[str] = []
    suggested = max(valuation.price_min, min(valuation.price_max, payload.suggested_price))
    if suggested != payload.suggested_price:
        warnings.append(CLAMP_WARNING)
    margin = max(0, min(payload.negotiation_margin_eur, valuation.price_max - valuation.price_min))
    return RecommendationOutcome(
        recommendation=ValuationRecommendation(
            summary=payload.summary,
            suggested_price=suggested,
            bullets=[item.strip() for item in payload.bullets if item.strip()][:MAX_BULLETS],
            risks=[item.strip() for item in payload.risks if item.strip()][:MAX_RISKS],
            negotiation_margin_eur=margin,
        ),
        warnings=tuple(warnings),
    )


def _template_outcome(
    request: ValuationRequest, valuation: MarketValuationResult
) -> RecommendationOutcome:
    keywords = _keywords(request.description or "")
    detail = f" Destaca: {', '.join(keywords)}." if keywords else ""
    bullets = [
        f"Estado {request.condition_label} ({request.condition_score}/100): "
        f"valor de mercado ajustado a {valuation.price_avg} €.",
        f"Publica en {', '.join(valuation.platforms)} con un rango de "
        f"{valuation.price_min}-{valuation.price_max} €.",
        f"Tasación basada en {valuation.sample_size} anuncios comparables.{detail}",
    ]
    risks = ["El precio final puede variar según la demanda local y la urgencia de la venta."]
    if request.condition_score < 60:
        risks.append("El desgaste reduce el margen de negociación.")
    if valuation.sample_size < 5:
        risks.append("Muestra de mercado pequeña: revisa el rango antes de publicar.")
    margin = max(
        1, min(round(valuation.price_avg * 0.05), valuation.price_max - valuation.price_min)
    )
    return RecommendationOutcome(
        recommendation=ValuationRecommendation(
            summary=(
                f"{request.query}: valor medio de {valuation.price_avg} € "
                f"en un rango de {valuation.price_min}-{valuation.price_max} €."
            ),
            suggested_price=valuation.price_avg,
            bullets=bullets,
            risks=risks,
            negotiation_margin_eur=margin,
        ),
        warnings=(FALLBACK_WARNING,),
    )


def _recommendation_prompt(request: ValuationRequest, valuation: MarketValuationResult) -> str:
    listings = "\n".join(
        f"- {item.title} | {item.price} € | {item.platform}"
        for item in valuation.comparable_listings[:6]
    )
    return (
        f"Producto: {request.query}\nCategoría: {request.category}\n"
        f"Estado: {request.condition_label} ({request.condition_score}/100)\n"
        f"Descripción: {request.description or 'sin descripción'}\n"
        f"Precios: min={valuation.price_min} €, avg={valuation.price_avg} €, "
        f"max={valuation.price_max} €\nComparables:\n{listings or '- sin comparables'}"
    )


def _deterministic_parsed_query(raw_query: str) -> ParsedQuery:
    query = " ".join([word for word in raw_query.split() if word][:5])[:200]
    return ParsedQuery(query=query if len(query) >= 2 else "producto")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(_strip_accents(text.lower())))


def _model_tokens(tokens: set[str]) -> set[str]:
    """Digit-bearing tokens identify a model (13, s23, ps5); capacities do not."""
    return {
        token
        for token in tokens
        if any(char.isdigit() for char in token) and not _CAPACITY_RE.match(token)
    }


def _keywords(text: str, limit: int = 3) -> list[str]:
    tokens = _TOKEN_RE.findall(_strip_accents(text.lower()))
    return [token for token in dict.fromkeys(tokens) if token not in _STOPWORDS][:limit]


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
