"""Pure helpers for the deep analysis: selection, warnings and clamping."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.mcp.analysis_query import (
    build_platform_search_url,
    clean_brand,
    clean_model,
)
from app.mcp.pricing_math import iqr_fences
from app.models.market_analysis import (
    MarketAnalysisRequest,
    MarketAnalysisValuation,
)
from app.models.sdd import (
    MarketListingSample,
    MarketPlatform,
    MarketValuationResult,
    ValuationRecommendation,
    ValuationRequest,
)


def select_comparables(
    listings: Sequence[MarketListingSample],
    query: str,
    price_avg: int,
    *,
    limit: int,
    quota: int,
) -> list[MarketListingSample]:
    """Up to `quota` per platform, then fill to `limit` by price proximity."""
    ordered = [
        listing.model_copy(
            update={
                "url": listing.url or build_platform_search_url(listing.platform, query)
            }
        )
        for listing in listings
    ]
    ordered.sort(key=lambda listing: (abs(listing.price - price_avg), listing.price))
    by_platform: dict[MarketPlatform, list[int]] = {}
    for index, listing in enumerate(ordered):
        by_platform.setdefault(listing.platform, []).append(index)
    chosen: list[MarketListingSample] = []
    chosen_indexes: set[int] = set()
    for indexes in by_platform.values():
        for index in indexes[:quota]:
            if len(chosen) >= limit:
                break
            chosen_indexes.add(index)
            chosen.append(ordered[index])
    if len(chosen) < limit:
        for index, listing in enumerate(ordered):
            if len(chosen) >= limit:
                break
            if index not in chosen_indexes:
                chosen.append(listing)
    chosen.sort(key=lambda listing: listing.price)
    return chosen


def single_iqr_filter(
    listings: Sequence[MarketListingSample],
) -> list[MarketListingSample]:
    """Filter listings with one set of IQR fences (never re-run IQR later)."""
    lower, upper = iqr_fences([listing.price for listing in listings])
    return [listing for listing in listings if lower <= listing.price <= upper]


def source_warnings(statuses: Mapping[str, str]) -> list[str]:
    return [
        f"Fuente {platform} no disponible ({status})."
        for platform, status in statuses.items()
        if status != "ok"
    ]


def valuation_request(request: MarketAnalysisRequest, query: str) -> ValuationRequest:
    return ValuationRequest(
        query=query,
        brand=clean_brand(request.brand),
        model=clean_model(request.model, name=request.name),
        category=request.category,
        condition_score=request.condition_score,
        condition_label=request.condition_label,
        description=request.description,
        include_recommendation=True,
    )


def market_valuation(
    valuation: MarketAnalysisValuation,
    comparables: Sequence[MarketListingSample],
) -> MarketValuationResult:
    return MarketValuationResult(
        price_min=valuation.price_min,
        price_avg=valuation.price_avg,
        price_max=valuation.price_max,
        sample_size=valuation.sample_size,
        platforms=valuation.platforms,
        comparable_listings=list(comparables),
        source="live_mcp",
    )


def clamp_recommendation(
    recommendation: ValuationRecommendation, valuation: MarketAnalysisValuation
) -> tuple[ValuationRecommendation, bool]:
    suggested = max(valuation.price_min, min(valuation.price_max, recommendation.suggested_price))
    margin = max(
        0,
        min(
            recommendation.negotiation_margin_eur,
            valuation.price_max - valuation.price_min,
        ),
    )
    if (
        suggested == recommendation.suggested_price
        and margin == recommendation.negotiation_margin_eur
    ):
        return recommendation, False
    return (
        recommendation.model_copy(
            update={"suggested_price": suggested, "negotiation_margin_eur": margin}
        ),
        True,
    )
