"""Pydantic v2 contracts for the market valuation module (MOD-04).

Field names mirror `.agent/architecture.md` and are serialized in camelCase.
Additive optional fields (recommendation, warnings, request hints) are
documented in ADR-002; existing contract fields must not change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ConditionLabel = Literal[
    "Nuevo",
    "Como nuevo",
    "Buen estado",
    "Desgaste visible",
    "Para piezas",
]

MarketPlatform = Literal["wallapop", "vinted", "milanuncios", "ebay"]

ValuationSource = Literal["live_mcp", "stealth_fallback"]

MAX_COMPARABLE_LISTINGS = 12


def to_camel(value: str) -> str:
    """Convert ``snake_case`` field names to the contract's ``camelCase``."""
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    """Base model with camelCase aliases and strict unknown-field handling."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class PricePoint(CamelModel):
    """Historical triplet (frozen contract, see architecture.md §2)."""

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
    """A comparable second-hand listing (frozen contract)."""

    title: str = Field(..., min_length=1, max_length=300)
    price: int = Field(..., ge=1, le=1_000_000)
    platform: MarketPlatform
    condition: str = Field(..., min_length=1, max_length=80)
    url: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("url must be an absolute http(s) URL")
        return value


class ValuationRequest(CamelModel):
    """`POST /api/market/valuate` body.

    ``query``, ``category``, ``conditionScore`` and ``conditionLabel`` are the
    frozen spec fields. ``brand``, ``model``, ``description`` and
    ``includeRecommendation`` are additive and optional.
    """

    query: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=1, max_length=120)
    condition_score: int = Field(..., ge=0, le=100)
    condition_label: ConditionLabel
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    include_recommendation: bool = False

    @field_validator("query", "category")
    @classmethod
    def _require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ValuationRecommendation(CamelModel):
    """LLM or deterministic recommendation (additive optional field)."""

    summary: str = Field(..., min_length=1, max_length=600)
    suggested_price: int = Field(..., ge=1)
    bullets: list[str] = Field(default_factory=list, max_length=8)
    risks: list[str] = Field(default_factory=list, max_length=8)
    negotiation_margin_eur: int = Field(..., ge=0)


class MarketValuationResult(CamelModel):
    """`POST /api/market/valuate` response (frozen fields + additive ones)."""

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
    """`GET /api/market/health` response."""

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
