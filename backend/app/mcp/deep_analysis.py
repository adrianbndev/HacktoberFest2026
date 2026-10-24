"""Deep browser-backed market analysis orchestrator (brief §5.1).

The fast `/valuate` path is untouched. This engine runs real browser sources
through `BrowserSessionPool`, emits progress events for SSE, computes the
price triplet from a single IQR pass and caches only real results.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Mapping
from time import monotonic

from app.config import Settings
from app.mcp.analysis_events import (
    AnalysisDone,
    AnalysisFailed,
    AnalysisStarted,
    DeepAnalysisEvent,
    DeepAnalysisUnavailableError,
    RecommendationReady,
    SourceFinished,
    SourceStarted,
    ValuationReady,
)
from app.mcp.analysis_query import build_analysis_query
from app.mcp.browser.pool import BrowserSessionPool
from app.mcp.browser.sources.base import BrowserSourceProtocol
from app.mcp.cache import MarketAnalysisCache, build_cache_key
from app.mcp.deep_cache import now_iso, read_cached, write_cached
from app.mcp.deep_milanuncios import MilanunciosHybridRunner
from app.mcp.deep_parallel import (
    RELEVANCE_SKIPPED_WARNING,
    SMALL_SAMPLE_WARNING,
    aggregate_results,
    run_sources,
)
from app.mcp.deep_recommend import RecommenderProtocol, recommend
from app.mcp.deep_sources import BrowserSourceRunner, default_sources
from app.mcp.deepseek import DeepSeekRecommender
from app.models.market_analysis import (
    MarketAnalysisRequest,
    MarketAnalysisResult,
    MarketSourceResult,
)
from app.models.sdd import MarketListingSample, MarketPlatform

logger = logging.getLogger(__name__)

__all__ = [
    "RELEVANCE_SKIPPED_WARNING",
    "SMALL_SAMPLE_WARNING",
    "DeepMarketAnalyzer",
    "reset_shared_analyzer",
    "shared_analyzer",
]

UNAVAILABLE_DETAIL = "Ninguna fuente de mercado profunda devolvió anuncios utilizables."
BROWSER_UNAVAILABLE_DETAIL = "browser_unavailable"
ANALYSIS_DISABLED_DETAIL = "analysis_disabled"
ANALYSIS_FAILED_DETAIL = "analysis_failed"


class DeepMarketAnalyzer:
    """Single entry point for `/api/market/analyze` and its SSE variant."""

    def __init__(
        self,
        settings: Settings,
        *,
        browser: BrowserSessionPool | None = None,
        cache: MarketAnalysisCache | None = None,
        sources: Mapping[MarketPlatform, BrowserSourceProtocol] | None = None,
        recommender: RecommenderProtocol | None = None,
        milanuncios: MilanunciosHybridRunner | None = None,
    ) -> None:
        self._settings = settings
        self.browser = browser or BrowserSessionPool(settings)
        self.cache = cache or MarketAnalysisCache(
            path=settings.market_cache_path, ttl_sec=settings.market_cache_ttl_sec
        )
        self._runner = BrowserSourceRunner(
            settings,
            self.browser,
            sources if sources is not None else default_sources(settings),
            milanuncios=milanuncios,
        )
        self._recommender: RecommenderProtocol = recommender or DeepSeekRecommender(
            settings, allow_template=False
        )

    async def analyze(self, request: MarketAnalysisRequest) -> MarketAnalysisResult:
        async for event in self.stream(request):
            if isinstance(event, AnalysisFailed):
                raise DeepAnalysisUnavailableError(event.detail, event.sources)
            if isinstance(event, AnalysisDone):
                return event.result
        raise DeepAnalysisUnavailableError(ANALYSIS_FAILED_DETAIL)

    async def stream(
        self, request: MarketAnalysisRequest
    ) -> AsyncIterator[DeepAnalysisEvent]:
        if not self._settings.market_analysis_enabled:
            yield AnalysisFailed(ANALYSIS_DISABLED_DETAIL, {})
            return

        query = build_analysis_query(request.name)
        cache_key = build_cache_key(query, request.condition_score, list(request.sources))
        cached = await read_cached(self.cache, cache_key)
        if cached is not None:
            yield AnalysisStarted(query, tuple(request.sources), True)
            yield AnalysisDone(cached)
            return

        yield AnalysisStarted(query, tuple(request.sources), False)
        deadline = monotonic() + self._settings.market_analysis_deadline_sec
        for platform in request.sources:
            yield SourceStarted(platform)

        results_by_platform: dict[MarketPlatform, MarketSourceResult] = {}
        usable_by_source: dict[MarketPlatform, list[MarketListingSample]] = {}
        async for platform, outcome in run_sources(
            self._runner,
            request.sources,
            query,
            deadline,
            self._settings.market_source_concurrency,
        ):
            if outcome is None:
                yield AnalysisFailed(BROWSER_UNAVAILABLE_DETAIL, {})
                return
            source_result, usable = outcome
            results_by_platform[platform] = source_result
            if usable:
                usable_by_source[platform] = usable
            yield SourceFinished(source_result)

        results = [
            results_by_platform[platform]
            for platform in request.sources
            if platform in results_by_platform
        ]
        aggregation = aggregate_results(
            self._settings, request, query, results, usable_by_source
        )
        if aggregation.valuation is None:
            yield AnalysisFailed(UNAVAILABLE_DETAIL, aggregation.statuses)
            return
        valuation = aggregation.valuation
        warnings = aggregation.warnings
        comparables = aggregation.comparables
        yield ValuationReady(valuation)

        recommendation = await recommend(
            settings=self._settings,
            recommender=self._recommender,
            request=request,
            query=query,
            valuation=valuation,
            comparables=comparables,
            deadline=deadline,
            warnings=warnings,
        )
        if recommendation is not None:
            yield RecommendationReady(recommendation)

        analysis = MarketAnalysisResult(
            query=query,
            sources=results,
            valuation=valuation,
            comparable_listings=comparables,
            recommendation=recommendation,
            warnings=list(dict.fromkeys(warnings)),
            cached=False,
            analyzed_at=now_iso(),
        )
        await write_cached(self.cache, cache_key, analysis)
        yield AnalysisDone(analysis)


_SHARED: DeepMarketAnalyzer | None = None
_SHARED_SETTINGS: Settings | None = None


def shared_analyzer(settings: Settings) -> DeepMarketAnalyzer:
    """Process-wide analyzer so the browser pool and cache are reused."""
    global _SHARED, _SHARED_SETTINGS
    if _SHARED is None or _SHARED_SETTINGS is not settings:
        _SHARED = DeepMarketAnalyzer(settings)
        _SHARED_SETTINGS = settings
    return _SHARED


def reset_shared_analyzer() -> None:
    """Test helper: drop the process-wide analyzer."""
    global _SHARED, _SHARED_SETTINGS
    _SHARED = None
    _SHARED_SETTINGS = None
