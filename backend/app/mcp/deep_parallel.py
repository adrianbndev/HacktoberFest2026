"""Parallel source scheduling and aggregation for the deep engine (Phase 3)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.config import Settings
from app.mcp.deep_support import (
    select_comparables,
    single_iqr_filter,
    source_warnings,
)
from app.mcp.pricing_math import compute_price_triplet_from_clean, confidence_score
from app.models.market_analysis import (
    MarketAnalysisRequest,
    MarketAnalysisValuation,
    MarketSourceResult,
)
from app.models.sdd import MarketListingSample, MarketPlatform

SMALL_SAMPLE_WARNING = "Muestra de mercado pequeña: interpreta el rango con cautela."

SourceOutcomePair = tuple[MarketSourceResult, list[MarketListingSample]]


class SourceRunnerProtocol(Protocol):
    async def run(
        self, platform: MarketPlatform, query: str, deadline: float
    ) -> SourceOutcomePair | None: ...


@dataclass(frozen=True, slots=True)
class AggregationOutcome:
    valuation: MarketAnalysisValuation | None
    comparables: list[MarketListingSample]
    warnings: list[str]
    statuses: dict[str, str]


async def run_sources(
    runner: SourceRunnerProtocol,
    platforms: Sequence[MarketPlatform],
    query: str,
    deadline: float,
    concurrency: int,
) -> AsyncIterator[tuple[MarketPlatform, SourceOutcomePair | None]]:
    """Run sources concurrently and yield `(platform, outcome)` in completion order.

    `None` means the browser/pool is unavailable and the caller must fail the
    whole analysis. Cancelling this generator cancels every in-flight source and
    releases its pool slot.
    """
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def run_one(
        platform: MarketPlatform,
    ) -> tuple[MarketPlatform, SourceOutcomePair | None]:
        async with semaphore:
            outcome = await runner.run(platform, query, deadline)
            return platform, outcome

    tasks = [asyncio.create_task(run_one(platform)) for platform in platforms]
    try:
        for future in asyncio.as_completed(tasks):
            yield await future
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def aggregate_results(
    settings: Settings,
    request: MarketAnalysisRequest,
    query: str,
    results: Sequence[MarketSourceResult],
    accepted: Sequence[MarketListingSample],
) -> AggregationOutcome:
    """One IQR pass over the LLM-`exact` listings, quota and confidence.

    `accepted` is already the DeepSeek-selected sample; there is no lexical
    relevance pass and no fallback to the full source sample.
    """
    statuses: dict[str, str] = {
        str(result.source): result.status for result in results
    }
    warnings = source_warnings(statuses)
    clean = single_iqr_filter(accepted)
    if not clean:
        return AggregationOutcome(None, [], warnings, statuses)

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
    if len(clean) < settings.market_min_sample_size:
        warnings.append(SMALL_SAMPLE_WARNING)
    comparables = select_comparables(
        clean,
        query,
        triplet.price_avg,
        limit=settings.market_max_comparable_listings,
        quota=settings.market_platform_quota,
    )
    return AggregationOutcome(valuation, comparables, warnings, statuses)
