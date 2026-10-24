"""Shared fakes for the deep-analysis engine tests (no CDP, no network)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from app.mcp.browser.session import BrowserUnavailableError
from app.mcp.browser.sources.base import SourceOutcome
from app.mcp.cache import MarketAnalysisCache
from app.mcp.deep_analysis import DeepMarketAnalyzer
from app.mcp.deepseek import RecommendationOutcome
from app.models.market_analysis import MarketAnalysisRequest
from app.models.sdd import (
    MarketListingSample,
    MarketValuationResult,
    ValuationRecommendation,
    ValuationRequest,
)
from tests.support import make_settings


class FakeBrowser:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sessions = 0

    @asynccontextmanager
    async def session(self) -> Any:
        if self.fail:
            raise BrowserUnavailableError("no cdp")
        self.sessions += 1
        yield object()


class FakeSource:
    platform = "ebay"

    def __init__(
        self,
        platform: str,
        prices: list[int] | None = None,
        *,
        status: str = "ok",
        delay_sec: float = 0.0,
        error: str | None = None,
        titles: list[str] | None = None,
        with_urls: bool = True,
    ) -> None:
        self.platform = platform  # type: ignore[assignment]
        self.prices = prices or []
        self.status = status
        self.delay_sec = delay_sec
        self.error = error
        self.titles = titles
        self.with_urls = with_urls
        self.calls = 0

    async def collect(self, page: Any, query: str) -> SourceOutcome:
        self.calls += 1
        if self.delay_sec:
            await asyncio.sleep(self.delay_sec)
        listings = tuple(
            MarketListingSample(
                title=(
                    self.titles[index]
                    if self.titles and index < len(self.titles)
                    else f"{query} unidad {index}"
                ),
                price=price,
                platform=self.platform,  # type: ignore[arg-type]
                condition="Buen estado",
                url=(
                    f"https://example.com/{self.platform}/{index}"
                    if self.with_urls
                    else None
                ),
            )
            for index, price in enumerate(self.prices)
        )
        status = self.status if listings or self.status != "ok" else "no_listings"
        return SourceOutcome(
            source=self.platform,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            listings=listings,
            latency_ms=5,
            error=self.error,
        )


class FakeRecommender:
    def __init__(self, *, suggested_price: int = 0, error: Exception | None = None) -> None:
        self.suggested_price = suggested_price
        self.error = error
        self.calls = 0

    async def recommend(
        self,
        *,
        request: ValuationRequest,
        valuation: MarketValuationResult,
        budget_sec: float | None = None,
    ) -> RecommendationOutcome:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return RecommendationOutcome(
            recommendation=ValuationRecommendation(
                summary="Recomendación de prueba",
                suggested_price=self.suggested_price or valuation.price_avg,
                bullets=["Publica con fotos reales"],
                risks=["La demanda puede variar"],
                negotiation_margin_eur=5,
            )
        )


def make_analyzer(
    tmp_path: Path,
    sources: dict[str, FakeSource],
    *,
    browser: FakeBrowser | None = None,
    recommender: FakeRecommender | None = None,
    **settings_overrides: object,
) -> DeepMarketAnalyzer:
    settings = make_settings(
        market_cache_path=str(tmp_path / "cache.sqlite"),
        **settings_overrides,
    )
    return DeepMarketAnalyzer(
        settings,
        browser=browser or FakeBrowser(),  # type: ignore[arg-type]
        cache=MarketAnalysisCache(path=settings.market_cache_path, ttl_sec=900),
        sources=sources,  # type: ignore[arg-type]
        recommender=recommender or FakeRecommender(),
    )


def make_analysis_request(**overrides: object) -> MarketAnalysisRequest:
    body: dict[str, object] = {
        "name": "Silla de madera",
        "description": "Silla de madera en buen estado",
        "category": "Mobiliario",
        "brand": "Sin marca",
        "model": "Silla de madera",
        "conditionScore": 85,
        "conditionLabel": "Como nuevo",
        "sources": ["ebay", "wallapop", "milanuncios"],
        "includeRecommendation": False,
    }
    body.update(overrides)
    return MarketAnalysisRequest.model_validate(body)


def three_sources(**overrides: Any) -> dict[str, FakeSource]:
    defaults: dict[str, FakeSource] = {
        "ebay": FakeSource("ebay", [30, 35, 40]),
        "wallapop": FakeSource("wallapop", [32, 38, 42]),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41]),
    }
    for platform, source in overrides.items():
        source.platform = platform
        defaults[platform] = source
    return defaults
