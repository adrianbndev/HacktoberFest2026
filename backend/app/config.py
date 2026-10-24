"""Runtime configuration for the market valuation backend.

Only the settings required by MOD-04 are defined here. Full MOD-00 settings
(auth, store, vision providers) belong to their own phase.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NO_ENV_FILE = os.devnull
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Environment-backed settings.

    Environment variable names are the upper-case field names, e.g.
    ``MARKET_ALLOW_FALLBACK=false`` or ``DEEPSEEK_API_KEY=...``.
    """

    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LifeOS ReCommerce Market API"
    app_version: str = "0.1.0"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # Live valuation budget (spec: total <= 2.8 s in interactive mode).
    market_allow_fallback: bool = True
    market_jitter_min_sec: float = Field(default=0.2, ge=0.0, le=5.0)
    market_jitter_max_sec: float = Field(default=0.6, ge=0.0, le=5.0)
    market_connector_timeout_sec: float = Field(default=1.6, gt=0.0, le=10.0)
    market_deadline_sec: float = Field(default=2.8, gt=0.0, le=30.0)
    market_max_comparable_listings: int = Field(default=12, ge=1, le=12)
    market_min_sample_size: int = Field(default=3, ge=1, le=50)
    market_max_listing_price_eur: int = Field(default=100_000, ge=1)

    # DeepSeek (OpenAI-compatible API).
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_reasoning_model: str = "deepseek-v4-pro"
    deepseek_fast_model: str = "deepseek-flash"
    deepseek_timeout_sec: float = Field(default=4.0, gt=0.0, le=60.0)
    deepseek_recommendation_budget_sec: float = Field(default=1.2, gt=0.0, le=10.0)

    @field_validator("deepseek_api_key")
    @classmethod
    def _empty_key_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _check_latency_budget(self) -> Settings:
        if self.market_jitter_max_sec < self.market_jitter_min_sec:
            raise ValueError("market_jitter_max_sec must be >= market_jitter_min_sec")
        if self.market_deadline_sec <= self.market_connector_timeout_sec:
            raise ValueError(
                "market_deadline_sec must be greater than market_connector_timeout_sec"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance.

    By default it reads the repository-root ``.env`` (shared with Docker
    Compose). ``LIFEOS_ENV_FILE`` lets tests point the loader at an empty file
    so a developer's real key can never leak into the test suite.
    """
    return Settings(
        _env_file=os.environ.get("LIFEOS_ENV_FILE", str(DEFAULT_ENV_FILE))
    )
