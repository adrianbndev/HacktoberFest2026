"""Optional LLM recommendation for the deep analysis (template disabled)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from time import monotonic
from typing import Protocol

from app.config import Settings
from app.mcp.deep_support import clamp_recommendation, market_valuation, valuation_request
from app.mcp.deepseek import CLAMP_WARNING, RecommendationOutcome
from app.models.market_analysis import MarketAnalysisRequest, MarketAnalysisValuation
from app.models.sdd import (
    MarketListingSample,
    MarketValuationResult,
    ValuationRecommendation,
    ValuationRequest,
)

RECOMMENDATION_SKIPPED_WARNING = "No se pudo generar la recomendación; se omite."


class RecommenderProtocol(Protocol):
    async def recommend(
        self,
        *,
        request: ValuationRequest,
        valuation: MarketValuationResult,
        budget_sec: float | None = None,
    ) -> RecommendationOutcome: ...


async def recommend(
    *,
    settings: Settings,
    recommender: RecommenderProtocol,
    request: MarketAnalysisRequest,
    query: str,
    valuation: MarketAnalysisValuation,
    comparables: Sequence[MarketListingSample],
    deadline: float,
    warnings: list[str],
) -> ValuationRecommendation | None:
    """Return a clamped recommendation, or omit it with a warning."""
    if not request.include_recommendation:
        return None
    budget = min(
        settings.deepseek_recommendation_budget_sec,
        max(0.0, deadline - monotonic()),
    )
    if budget <= 0:
        warnings.append(RECOMMENDATION_SKIPPED_WARNING)
        return None
    try:
        outcome = await asyncio.wait_for(
            recommender.recommend(
                request=valuation_request(request, query),
                valuation=market_valuation(valuation, comparables),
                budget_sec=budget,
            ),
            timeout=budget + 1.0,
        )
    except Exception:
        warnings.append(RECOMMENDATION_SKIPPED_WARNING)
        return None
    recommendation, clamped = clamp_recommendation(outcome.recommendation, valuation)
    warnings.extend(outcome.warnings)
    if clamped:
        warnings.append(CLAMP_WARNING)
    return recommendation
