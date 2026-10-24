"""Valuation orchestrator: connectors -> normalisation -> pricing -> recommendation."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from time import monotonic
from typing import Protocol

from app.config import Settings
from app.mcp.catalog_fallback import build_deep_link, build_fallback_result
from app.mcp.connectors import (
    ConnectorResult,
    EbayConnector,
    MarketConnectorProtocol,
    MilanunciosConnector,
    WallapopConnector,
)
from app.mcp.deepseek import DeepSeekRecommender, RecommendationOutcome
from app.mcp.normalize import dedupe_listings, filter_usable_listings, normalize_query
from app.mcp.pricing_math import (
    compute_price_triplet,
    filter_outliers_iqr,
)
from app.mcp.stealth_http import human_jitter
from app.models.sdd import (
    MarketListingSample,
    MarketPlatform,
    MarketValuationResult,
    ValuationRequest,
)

UNAVAILABLE_DETAIL = (
    "Ninguna fuente de mercado devolvió anuncios utilizables y el fallback está desactivado."
)
SMALL_SAMPLE_WARNING = "Muestra de mercado pequeña: interpreta el rango con cautela."
RECOMMENDATION_SKIPPED_WARNING = "No se pudo generar la recomendación; se omite."


class MarketUnavailableError(Exception):
    """All live sources failed and the deterministic fallback is disabled."""

    def __init__(self, detail: str, sources: dict[MarketPlatform, str]) -> None:
        super().__init__(detail)
        self.detail = detail
        self.sources = sources


class RecommenderProtocol(Protocol):
    def score_relevance(
        self, query: str, listings: Sequence[MarketListingSample]
    ) -> list[MarketListingSample]: ...

    async def recommend(
        self,
        *,
        request: ValuationRequest,
        valuation: MarketValuationResult,
        budget_sec: float | None = None,
    ) -> RecommendationOutcome: ...


class MarketAnalyzer:
    """Coordinate the fast valuation pipeline within the response deadline."""

    def __init__(
        self,
        settings: Settings,
        *,
        connectors: Sequence[MarketConnectorProtocol] | None = None,
        recommender: RecommenderProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._connectors = tuple(connectors) if connectors is not None else _default_connectors(
            settings
        )
        self._recommender: RecommenderProtocol = recommender or DeepSeekRecommender(settings)

    async def valuate(self, request: ValuationRequest) -> MarketValuationResult:
        started = monotonic()
        deadline = started + self._settings.market_deadline_sec
        query = normalize_query(request.query, brand=request.brand, model=request.model)

        await human_jitter(
            self._settings.market_jitter_min_sec, self._settings.market_jitter_max_sec
        )

        outcomes = await self._gather(query, deadline)
        sources = {outcome.platform: outcome.failure_reason or "ok" for outcome in outcomes}
        live = [
            listing for outcome in outcomes if outcome.ok for listing in outcome.listings
        ]
        live = filter_usable_listings(
            dedupe_listings(self._recommender.score_relevance(query, live)),
            max_price_eur=self._settings.market_max_listing_price_eur,
        )

        if not live:
            return await self._fallback_or_raise(request, query, sources)
        return await self._build_live(request, query, live, sources)

    async def _gather(self, query: str, deadline: float) -> list[ConnectorResult]:
        remaining = max(0.0, deadline - monotonic())
        per_source = min(self._settings.market_connector_timeout_sec, remaining)
        if per_source <= 0:
            return [
                ConnectorResult(connector.platform, failure_reason="deadline_exceeded")
                for connector in self._connectors
            ]
        searches = [
            asyncio.wait_for(connector.search(query), timeout=per_source)
            for connector in self._connectors
        ]
        raw = await asyncio.gather(*searches, return_exceptions=True)
        results: list[ConnectorResult] = []
        for connector, outcome in zip(self._connectors, raw, strict=True):
            if isinstance(outcome, ConnectorResult):
                results.append(outcome)
            elif isinstance(outcome, TimeoutError):
                results.append(ConnectorResult(connector.platform, failure_reason="timeout"))
            else:
                results.append(
                    ConnectorResult(connector.platform, failure_reason="unexpected_error")
                )
        return results

    async def _build_live(
        self,
        request: ValuationRequest,
        query: str,
        live: list[MarketListingSample],
        sources: dict[MarketPlatform, str],
    ) -> MarketValuationResult:
        cleaned = filter_outliers_iqr([listing.price for listing in live])
        triplet = compute_price_triplet(cleaned, request.condition_score)
        warnings = _source_warnings(sources)
        if len(cleaned) < self._settings.market_min_sample_size:
            warnings.append(SMALL_SAMPLE_WARNING)
        listings = _select_comparables(
            live,
            query,
            triplet.price_avg,
            self._settings.market_max_comparable_listings,
        )
        result = MarketValuationResult(
            price_min=triplet.price_min,
            price_avg=triplet.price_avg,
            price_max=triplet.price_max,
            sample_size=len(cleaned),
            platforms=list(dict.fromkeys(listing.platform for listing in listings)),
            comparable_listings=listings,
            source="live_mcp",
            warnings=warnings,
        )
        return await self._maybe_recommend(request, result)

    async def _fallback_or_raise(
        self,
        request: ValuationRequest,
        query: str,
        sources: dict[MarketPlatform, str],
    ) -> MarketValuationResult:
        if not self._settings.market_allow_fallback:
            raise MarketUnavailableError(UNAVAILABLE_DETAIL, sources)
        fallback = build_fallback_result(
            query=query,
            category=request.category,
            condition_score=request.condition_score,
            max_listings=self._settings.market_max_comparable_listings,
        )
        result = fallback.model_copy(
            update={"warnings": [*_source_warnings(sources), *fallback.warnings]}
        )
        return await self._maybe_recommend(request, result)

    async def _maybe_recommend(
        self, request: ValuationRequest, result: MarketValuationResult
    ) -> MarketValuationResult:
        if not request.include_recommendation:
            return result
        budget = self._settings.deepseek_recommendation_budget_sec
        if budget <= 0:
            return _with_warnings(result, (RECOMMENDATION_SKIPPED_WARNING,))
        try:
            outcome = await self._recommender.recommend(
                request=request, valuation=result, budget_sec=budget
            )
        except Exception:
            return _with_warnings(result, (RECOMMENDATION_SKIPPED_WARNING,))
        return result.model_copy(
            update={
                "recommendation": outcome.recommendation,
                "warnings": [*result.warnings, *outcome.warnings],
            }
        )


def _default_connectors(settings: Settings) -> tuple[MarketConnectorProtocol, ...]:
    timeout = settings.market_connector_timeout_sec
    return (
        WallapopConnector(timeout_sec=timeout),
        MilanunciosConnector(timeout_sec=timeout),
        EbayConnector(timeout_sec=timeout),
    )


def _select_comparables(
    live: Sequence[MarketListingSample], query: str, price_avg: int, limit: int
) -> list[MarketListingSample]:
    candidates: list[MarketListingSample] = []
    for listing in live:
        link = listing.url or build_deep_link(listing.platform, query)
        if link:
            candidates.append(listing.model_copy(update={"url": link}))
    candidates.sort(key=lambda listing: (abs(listing.price - price_avg), listing.price))
    selected = candidates[:limit]
    selected.sort(key=lambda listing: listing.price)
    return selected


def _source_warnings(sources: dict[MarketPlatform, str]) -> list[str]:
    return [
        f"Fuente {platform} no disponible ({reason})."
        for platform, reason in sorted(sources.items())
        if reason != "ok"
    ]


def _with_warnings(
    result: MarketValuationResult, warnings: tuple[str, ...]
) -> MarketValuationResult:
    return result.model_copy(update={"warnings": [*result.warnings, *warnings]})
