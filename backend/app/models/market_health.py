"""Health payload for `/api/market/health` (additive Phase 2 fields)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.models.sdd import CamelModel


class BrowserHealthStatus(CamelModel):
    connected: bool
    url: str
    last_error: str | None = None


class MarketCacheStatus(CamelModel):
    path: str
    ttl_seconds: int = Field(ge=0)


class MarketHealthResponse(CamelModel):
    status: Literal["ok"]
    service: str
    version: str
    fallback_enabled: bool
    jitter_enabled: bool
    recommendation_enabled: bool
    timestamp: str
    browser: BrowserHealthStatus = Field(
        default_factory=lambda: BrowserHealthStatus(connected=False, url="")
    )
    cache: MarketCacheStatus = Field(
        default_factory=lambda: MarketCacheStatus(path="", ttl_seconds=900)
    )
    analysis_enabled: bool = False

    @field_validator("timestamp")
    @classmethod
    def _check_timestamp(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be an ISO 8601 string") from exc
        return value
