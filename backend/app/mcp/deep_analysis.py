"""Deep browser-backed market analysis orchestrator (brief §5.1).

The fast `/valuate` path is untouched. This engine runs real browser sources
through `BrowserSessionManager`, emits progress events for SSE, computes the
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
from app.mcp.analysis_query import build_analysis_query, build_relevance_query
from app.mcp.browser.session import BrowserSessionManager
from app.mcp.browser.sources.base import BrowserSourceProtocol
from app.mcp.cache import MarketAnalysisCache, build_cache_key
from app.mcp.deep_cache import now_iso, read_cached, write_cached
from app.mcp.deep_recommend import RecommenderProtocol, recommend
from app.mcp.deep_sources import BrowserSourceRunner, default_sources
from app.mcp.deep_support import select_comparables, single_iqr_filter, source_warnings
from app.mcp.deepseek import DeepSeekRecommender
from app.mcp.pricing_math import compute_price_triplet_from_clean, confidence_score
from app.mcp.relevance import score_relevance
from app.models.market_analysis import (
    MarketAnalysisRequest,
    MarketAnalysisResult,
    MarketAnalysisValuation,
    MarketSourceResult,
)
from app.models.sdd import MarketListingSample, MarketPlatform

logger = logging.getLogger(__name__)

UNAVAILABLE_DETAIL = "Ninguna fuente de mercado profunda devolvió anuncios utilizables."
BROWSER_UNAVAILABLE_DETAIL = "browser_unavailable"
ANALYSIS_DISABLED_DETAIL = "analysis_disabled"
ANALYSIS_FAILED_DETAIL = "analysis_failed"
SMALL_SAMPLE_WARNING = "Muestra de mercado pequeña: interpreta el rango con cautela."
RELEVANCE_SKIPPED_WARNING = (
    "No se pudo aplicar el filtro de relevancia; se usa la muestra completa."
)


class DeepMarketAnalyzer:
    """Single entry point for `/api/market/analyze` and its SSE variant."""

    def __init__(
        self,
        settings: Settings,
        *,
        browser: BrowserSessionManager | None = None,
        cache: MarketAnalysisCache | None = None,
        sources: Mapping[MarketPlatform, BrowserSourceProtocol] | None = None,
        recommender: RecommenderProtocol | None = None,
    ) -> None:
        self._settings = settings
        self.browser = browser or BrowserSessionManager(settings)
        self.cache = cache or MarketAnalysisCache(
            path=settings.market_cache_path, ttl_sec=settings.market_cache_ttl_sec
        )
        self._runner = BrowserSourceRunner(
            settings,
            self.browser,
            sources if sources is not None else default_sources(settings),
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
        relevance_query = build_relevance_query(request.name, request.brand, request.model)
        cache_key = build_cache_key(query, request.condition_score, list(request.sources))
        cached = await read_cached(self.cache, cache_key)
        if cached is not None:
            yield AnalysisStarted(query, tuple(request.sources), True)
            yield AnalysisDone(cached)
            return

        yield AnalysisStarted(query, tuple(request.sources), False)
        deadline = monotonic() + self._settings.market_analysis_deadline_sec
        results: list[MarketSourceResult] = []
        usable_by_source: dict[MarketPlatform, list[MarketListingSample]] = {}
        for platform in request.sources:
            yield SourceStarted(platform)
            outcome = await self._runner.run(platform, query, deadline)
            if outcome is None:
                yield AnalysisFailed(BROWSER_UNAVAILABLE_DETAIL, {})
                return
            source_result, usable = outcome
            results.append(source_result)
            if usable:
                usable_by_source[platform] = usable
            yield SourceFinished(source_result)

        statuses: dict[str, str] = {
            str(source_result.source): source_result.status
            for source_result in results
        }
        if not usable_by_source:
            yield AnalysisFailed(UNAVAILABLE_DETAIL, statuses)
            return

        warnings = source_warnings(statuses)
        all_usable = [
            listing
            for platform in request.sources
            for listing in usable_by_source.get(platform, ())
        ]
        relevant = score_relevance(relevance_query, all_usable)
        if not relevant:
            relevant = all_usable
            warnings.append(RELEVANCE_SKIPPED_WARNING)
        clean = single_iqr_filter(relevant)
        if not clean:
            yield AnalysisFailed(UNAVAILABLE_DETAIL, statuses)
            return

        triplet = compute_price_triplet_from_clean(
            [listing.price for listing in clean], request.condition_score
        )
        platforms = [
            platform
            for platform in request.sources
            if any(listing.platform == platform for listing in clean)
        ]
        valuation = MarketAnalysisValuation(
            price_min=triplet.price_min,
            price_avg=triplet.price_avg,
            price_max=triplet.price_max,
            sample_size=len(clean),
            platforms=platforms,
            confidence=confidence_score(
                [listing.price for listing in clean],
                platform_count=len(platforms),
                ok_sources=sum(1 for result in results if result.status == "ok"),
                requested_sources=len(request.sources),
            ),
        )
        if len(clean) < self._settings.market_min_sample_size:
            warnings.append(SMALL_SAMPLE_WARNING)
        comparables = select_comparables(
            clean,
            query,
            triplet.price_avg,
            limit=self._settings.market_max_comparable_listings,
            quota=self._settings.market_platform_quota,
        )
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
    """Process-wide analyzer so the browser lock/client and cache are reused."""
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
