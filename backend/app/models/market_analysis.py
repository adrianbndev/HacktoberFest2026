"""Contracts for the Phase 2 deep market analysis (additive to `sdd.py`).

`POST /api/market/valuate` and `MarketValuationResult` are frozen; these models
describe the new browser-backed `POST /api/market/analyze` endpoint only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.models.sdd import (
    CamelModel,
    ConditionLabel,
    MarketListingSample,
    MarketPlatform,
    ValuationRecommendation,
)

DEFAULT_ANALYSIS_SOURCES: tuple[MarketPlatform, ...] = ("ebay", "wallapop", "milanuncios")
MAX_SOURCE_LISTINGS = 40
MAX_ANALYSIS_LISTINGS = 12

MarketSourceStatus = Literal["ok", "blocked", "timeout", "no_listings", "error"]


class MarketAnalysisLocation(CamelModel):
    """Optional coordinates used only for future locality hints (never PII)."""

    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)


class MarketAnalysisRequest(CamelModel):
    """Input payload for `POST /api/market/analyze` (brief §5.1)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(..., min_length=1, max_length=120)
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    condition_score: int = Field(..., ge=0, le=100)
    condition_label: ConditionLabel
    location: MarketAnalysisLocation | None = None
    sources: list[MarketPlatform] = Field(
        default_factory=lambda: list(DEFAULT_ANALYSIS_SOURCES), max_length=4
    )
    include_recommendation: bool = True

    @field_validator("name", "category")
    @classmethod
    def _require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("sources")
    @classmethod
    def _dedupe_sources(cls, value: list[MarketPlatform]) -> list[MarketPlatform]:
        unique = list(dict.fromkeys(value))
        if not unique:
            raise ValueError("at least one source is required")
        return unique


class MarketSourceResult(CamelModel):
    """Per-source outcome, emitted as soon as that source finishes."""

    source: MarketPlatform
    status: MarketSourceStatus
    sample_size: int = Field(..., ge=0)
    listings: list[MarketListingSample] = Field(
        default_factory=list, max_length=MAX_SOURCE_LISTINGS
    )
    latency_ms: int = Field(..., ge=0)
    error: str | None = None

    @field_validator("error")
    @classmethod
    def _sanitize_error(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())[:300]
        return cleaned or None

    @model_validator(mode="after")
    def _check_status_consistency(self) -> MarketSourceResult:
        if self.status == "ok" and self.sample_size <= 0:
            raise ValueError("status 'ok' requires at least one usable listing")
        if self.status == "no_listings" and self.sample_size != 0:
            raise ValueError("status 'no_listings' cannot carry a sample")
        return self


class MarketAnalysisValuation(CamelModel):
    """The three mandatory prices plus the deep-analysis confidence."""

    price_min: int = Field(..., ge=1)
    price_avg: int = Field(..., ge=1)
    price_max: int = Field(..., ge=1)
    sample_size: int = Field(..., ge=1)
    platforms: list[MarketPlatform] = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_invariants(self) -> MarketAnalysisValuation:
        if not 0 < self.price_min < self.price_avg < self.price_max:
            raise ValueError(
                "price triplet must satisfy 0 < priceMin < priceAvg < priceMax "
                f"(got {self.price_min}, {self.price_avg}, {self.price_max})"
            )
        if len(set(self.platforms)) != len(self.platforms):
            raise ValueError("platforms must not contain duplicates")
        return self


class MarketAnalysisResult(CamelModel):
    """Response for `POST /api/market/analyze` (brief §5.1)."""

    query: str = Field(..., min_length=2, max_length=200)
    sources: list[MarketSourceResult] = Field(..., min_length=1)
    valuation: MarketAnalysisValuation
    recommendation: ValuationRecommendation | None = None
    warnings: list[str] = Field(default_factory=list)
    cached: bool = False
    analyzed_at: str

    @field_validator("analyzed_at")
    @classmethod
    def _check_timestamp(cls, value: str) -> str:
        _parse_iso_timestamp(value)
        return value

    @model_validator(mode="after")
    def _check_platform_coherence(self) -> MarketAnalysisResult:
        declared = {source.source for source in self.sources}
        missing = set(self.valuation.platforms) - declared
        if missing:
            raise ValueError(f"valuation platforms not declared as sources: {sorted(missing)}")
        return self


def _parse_iso_timestamp(value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO 8601 string") from exc
