"""Official Pydantic v2 Contracts (backend/app/models/sdd.py).

Mirrors src/types/sdd.ts 1:1 using camelCase serialization aliases.
"""

from __future__ import annotations

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


TeamMemberId = Literal["ales", "adri", "matias", "jurado"]

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
    def _enforce_rubric_label(self) -> "VisionAnalysisResult":
        self.condition_label = map_score_to_condition_label(self.condition_score)
        return self


class ValuationRequest(CamelModel):
    """Input payload for POST /api/market/valuate."""

    query: str
    brand: str | None = None
    model: str | None = None
    category: str
    condition_score: int = Field(..., ge=0, le=100)
    condition_label: ConditionLabel


class MarketListingSample(CamelModel):
    """Comparable secondhand listing sample."""

    title: str
    price: float
    platform: MarketPlatform
    condition: str
    url: str | None = None


class MarketValuationResult(CamelModel):
    """Output payload for POST /api/market/valuate."""

    price_min: float
    price_avg: float
    price_max: float
    sample_size: int
    platforms: list[MarketPlatform]
    comparable_listings: list[MarketListingSample]
    source: Literal["live_mcp", "stealth_fallback"]
