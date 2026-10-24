"""Official Pydantic v2 Contracts (backend/app/models/sdd.py).

Mirrors src/types/sdd.ts 1:1 using camelCase serialization aliases.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_camel(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


class CamelModel(BaseModel):
    """Base Pydantic model with automatic camelCase alias mapping."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="ignore",
    )


TeamMemberId = Literal["ales", "adri", "matias"]

ConditionLabel = Literal[
    "Nuevo",
    "Como nuevo",
    "Buen estado",
    "Desgaste visible",
    "Para piezas",
]

CONDITION_LABELS: tuple[ConditionLabel, ...] = (
    "Nuevo",
    "Como nuevo",
    "Buen estado",
    "Desgaste visible",
    "Para piezas",
)

MarketPlatform = Literal["wallapop", "vinted", "milanuncios", "ebay"]

VisionProviderSource = Literal[
    "ollama_local",
    "gemini",
    "openai",
    "deterministic_fallback",
]

SEO_TITLE_MAX_LENGTH = 65


def clamp_condition_score(score: int | float) -> int:
    """Clamps a numeric condition score strictly to the [0, 100] interval."""
    numeric = int(round(float(score)))
    return max(0, min(100, numeric))


def map_score_to_condition_label(score: int | float) -> ConditionLabel:
    """Pure deterministic rubric mapping conditionScore (0-100) to ConditionLabel.

    - 90..100 -> 'Nuevo'
    - 80..89  -> 'Como nuevo'
    - 65..79  -> 'Buen estado'
    - 40..64  -> 'Desgaste visible'
    - 0..39   -> 'Para piezas'
    """
    clamped = clamp_condition_score(score)
    if clamped >= 90:
        return "Nuevo"
    if clamped >= 80:
        return "Como nuevo"
    if clamped >= 65:
        return "Buen estado"
    if clamped >= 40:
        return "Desgaste visible"
    return "Para piezas"


class VisionAnalyzeRequest(CamelModel):
    """Input payload for POST /api/vision/analyze."""

    photo_data_url: str = Field(..., min_length=10)
    user_hint: str | None = Field(default=None)


class VisionAnalysisResult(CamelModel):
    """Structured output returned by Vision AI to pre-fill the user's product form."""

    name: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    condition_score: int = Field(..., ge=0, le=100)
    condition_label: ConditionLabel
    condition_reasoning: str = Field(..., min_length=5)
    seo_title: str = Field(..., min_length=5, max_length=SEO_TITLE_MAX_LENGTH)
    seo_description: str = Field(..., min_length=15)
    source: VisionProviderSource = Field(default="ollama_local")
    latency_ms: int | None = Field(default=None)
    model_used: str | None = Field(default=None)

    @field_validator("condition_score", mode="before")
    @classmethod
    def _validate_and_clamp_score(cls, value: int | float) -> int:
        return clamp_condition_score(value)

    @field_validator("seo_title", mode="before")
    @classmethod
    def _truncate_seo_title(cls, value: str) -> str:
        cleaned = " ".join(str(value).strip().split())
        if len(cleaned) <= SEO_TITLE_MAX_LENGTH:
            return cleaned
        return cleaned[: SEO_TITLE_MAX_LENGTH - 1].rstrip(" -|,.") + "…"

    @model_validator(mode="after")
    def _enforce_rubric_label(self) -> VisionAnalysisResult:
        self.condition_label = map_score_to_condition_label(self.condition_score)
        return self


MAX_COMPARABLE_LISTINGS = 12
ValuationSource = Literal["live_mcp", "stealth_fallback"]


class ValuationRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(..., min_length=2, max_length=200)
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    category: str = Field(..., min_length=1, max_length=120)
    condition_score: int = Field(..., ge=0, le=100)
    condition_label: ConditionLabel
    description: str | None = Field(default=None, max_length=2000)
    include_recommendation: bool = False

    @field_validator("query", "category")
    @classmethod
    def _require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


MarketValuationRequest = ValuationRequest


class PricePoint(CamelModel):
    timestamp: str = Field(..., min_length=10, max_length=64)
    price_min: int = Field(..., ge=1)
    price_avg: int = Field(..., ge=1)
    price_max: int = Field(..., ge=1)
    sample_size: int = Field(..., ge=1)
    platforms: list[MarketPlatform] = Field(..., min_length=1)

    @field_validator("timestamp")
    @classmethod
    def _check_timestamp(cls, value: str) -> str:
        _parse_iso_timestamp(value)
        return value

    @model_validator(mode="after")
    def _check_triplet(self) -> PricePoint:
        _assert_strict_triplet(self.price_min, self.price_avg, self.price_max)
        return self


class MarketListingSample(CamelModel):
    title: str = Field(..., min_length=1, max_length=300)
    price: float = Field(..., ge=1, le=1_000_000)
    platform: MarketPlatform
    condition: str = Field(..., min_length=1, max_length=80)
    url: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("url must be an absolute http(s) URL")
        return value


class ValuationRecommendation(CamelModel):
    summary: str = Field(..., min_length=1, max_length=600)
    suggested_price: int = Field(..., ge=1)
    bullets: list[str] = Field(default_factory=list, max_length=8)
    risks: list[str] = Field(default_factory=list, max_length=8)
    negotiation_margin_eur: int = Field(..., ge=0)


class MarketValuationResult(CamelModel):
    price_min: int = Field(..., ge=1)
    price_avg: int = Field(..., ge=1)
    price_max: int = Field(..., ge=1)
    sample_size: int = Field(..., ge=1)
    platforms: list[MarketPlatform] = Field(..., min_length=1)
    comparable_listings: list[MarketListingSample] = Field(
        default_factory=list, max_length=MAX_COMPARABLE_LISTINGS
    )
    source: ValuationSource
    recommendation: ValuationRecommendation | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_response_invariants(self) -> MarketValuationResult:
        _assert_strict_triplet(self.price_min, self.price_avg, self.price_max)
        if len(set(self.platforms)) != len(self.platforms):
            raise ValueError("platforms must not contain duplicates")
        missing = {listing.platform for listing in self.comparable_listings} - set(self.platforms)
        if missing:
            raise ValueError(f"comparable listings use undeclared platforms: {sorted(missing)}")
        return self


class MarketHealthResponse(CamelModel):
    status: Literal["ok"]
    service: str
    version: str
    fallback_enabled: bool
    jitter_enabled: bool
    recommendation_enabled: bool
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def _check_timestamp(cls, value: str) -> str:
        _parse_iso_timestamp(value)
        return value


def _parse_iso_timestamp(value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO 8601 string") from exc


def _assert_strict_triplet(price_min: int, price_avg: int, price_max: int) -> None:
    if not 0 < price_min < price_avg < price_max:
        raise ValueError(
            "price triplet must satisfy 0 < priceMin < priceAvg < priceMax "
            f"(got {price_min}, {price_avg}, {price_max})"
        )
