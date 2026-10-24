"""Shared fakes for market orchestration and API tests."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.config import Settings
from app.mcp.connectors import ConnectorResult
from app.mcp.deepseek import RecommendationOutcome
from app.models.sdd import (
    MarketListingSample,
    MarketPlatform,
    MarketValuationResult,
    ValuationRecommendation,
    ValuationRequest,
)


class FakeConnector:
    def __init__(
        self,
        platform: MarketPlatform,
        prices: Sequence[int] = (),
        *,
        failure_reason: str | None = None,
        delay: float = 0.0,
        with_urls: bool = True,
    ) -> None:
        self.platform = platform
        self._prices = tuple(prices)
        self._failure_reason = failure_reason
        self._delay = delay
        self._with_urls = with_urls
        self.queries: list[str] = []

    async def search(self, query: str) -> ConnectorResult:
        self.queries.append(query)
        if self._delay:
            await asyncio.sleep(self._delay)
        listings = tuple(
            MarketListingSample(
                title=f"{query} unidad {price}",
                price=price,
                platform=self.platform,
                condition="Buen estado",
                url=(
                    f"https://example.com/{self.platform}/{price}"
                    if self._with_urls
                    else None
                ),
            )
            for price in self._prices
        )
        return ConnectorResult(self.platform, listings, self._failure_reason)


class FakeRecommender:
    def __init__(
        self,
        *,
        outcome: RecommendationOutcome | None = None,
        error: Exception | None = None,
    ) -> None:
        self._outcome = outcome
        self._error = error
        self.calls = 0
        self.last_budget: float | None = None

    def score_relevance(
        self, query: str, listings: Sequence[MarketListingSample]
    ) -> list[MarketListingSample]:
        return list(listings)

    async def recommend(
        self,
        *,
        request: ValuationRequest,
        valuation: MarketValuationResult,
        budget_sec: float | None = None,
    ) -> RecommendationOutcome:
        self.calls += 1
        self.last_budget = budget_sec
        if self._error is not None:
            raise self._error
        if self._outcome is not None:
            return self._outcome
        return RecommendationOutcome(
            recommendation=ValuationRecommendation(
                summary="Recomendación de prueba",
                suggested_price=valuation.price_avg,
                bullets=["Publica el anuncio con fotos reales"],
                risks=["La demanda puede variar"],
                negotiation_margin_eur=5,
            )
        )


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "market_allow_fallback": True,
        "market_jitter_min_sec": 0.0,
        "market_jitter_max_sec": 0.0,
        "market_connector_timeout_sec": 0.2,
        "market_deadline_sec": 2.8,
        "market_min_sample_size": 3,
        "market_max_comparable_listings": 12,
        "deepseek_api_key": None,
        "_env_file": None,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def make_request(*, include_recommendation: bool = False) -> ValuationRequest:
    return ValuationRequest(
        query="iPhone 13 128GB",
        category="Móviles",
        condition_score=80,
        condition_label="Como nuevo",
        description="Caja original, batería 89%, sin arañazos",
        include_recommendation=include_recommendation,
    )


def default_connectors() -> list[FakeConnector]:
    return [
        FakeConnector("wallapop", [300, 320, 340, 360]),
        FakeConnector("milanuncios", [310, 330, 350, 370]),
        FakeConnector("ebay", [290, 315, 345, 355]),
    ]


def failing_connectors(reason: str = "network_error") -> list[FakeConnector]:
    return [
        FakeConnector("wallapop", failure_reason=reason),
        FakeConnector("milanuncios", failure_reason=reason),
        FakeConnector("ebay", failure_reason=reason),
    ]
