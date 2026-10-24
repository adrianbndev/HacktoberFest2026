"""Progress events emitted by the deep analysis engine (SSE wire source)."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.market_analysis import (
    MarketAnalysisResult,
    MarketAnalysisValuation,
    MarketSourceResult,
)
from app.models.sdd import MarketPlatform, ValuationRecommendation


@dataclass(frozen=True, slots=True)
class AnalysisStarted:
    query: str
    sources: tuple[MarketPlatform, ...]
    cached: bool


@dataclass(frozen=True, slots=True)
class SourceStarted:
    source: MarketPlatform


@dataclass(frozen=True, slots=True)
class SourceFinished:
    result: MarketSourceResult


@dataclass(frozen=True, slots=True)
class ValuationReady:
    valuation: MarketAnalysisValuation


@dataclass(frozen=True, slots=True)
class RecommendationReady:
    recommendation: ValuationRecommendation


@dataclass(frozen=True, slots=True)
class AnalysisDone:
    result: MarketAnalysisResult


@dataclass(frozen=True, slots=True)
class AnalysisFailed:
    detail: str
    sources: dict[str, str]


DeepAnalysisEvent = (
    AnalysisStarted
    | SourceStarted
    | SourceFinished
    | ValuationReady
    | RecommendationReady
    | AnalysisDone
    | AnalysisFailed
)


class DeepAnalysisUnavailableError(Exception):
    """No real browser data could produce a valuation (never synthetic data)."""

    def __init__(self, detail: str, sources: dict[str, str] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.sources = sources or {}
