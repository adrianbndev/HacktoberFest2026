"""Shared HTTP fakes for `/api/market/analyze` tests."""

from __future__ import annotations

import json
from typing import Any

from app.main import create_app
from app.mcp.analysis_events import (
    AnalysisDone,
    AnalysisStarted,
    RecommendationReady,
    SourceFinished,
    SourceStarted,
    ValuationReady,
)
from app.models.market_analysis import (
    MarketAnalysisRequest,
    MarketAnalysisResult,
    MarketAnalysisValuation,
    MarketSourceResult,
)
from app.models.sdd import MarketListingSample, ValuationRecommendation
from app.routers.market_analysis import get_deep_analyzer
from fastapi.testclient import TestClient

BODY: dict[str, Any] = {
    "name": "Silla de madera",
    "description": "Silla de madera en estado 'Como nuevo'",
    "category": "Mobiliario",
    "brand": "Sin marca",
    "model": "Silla de madera",
    "conditionScore": 85,
    "conditionLabel": "Como nuevo",
    "sources": ["wallapop"],
}


def listing() -> MarketListingSample:
    return MarketListingSample(
        title="Silla de madera",
        price=35,
        platform="wallapop",
        condition="Buen estado",
        url="https://es.wallapop.com/item/silla-madera",
    )


def make_result(*, cached: bool = False) -> MarketAnalysisResult:
    return MarketAnalysisResult(
        query="Silla madera",
        sources=[
            MarketSourceResult(
                source="wallapop",
                status="ok",
                sample_size=3,
                listings=[listing()],
                latency_ms=8200,
            )
        ],
        valuation=MarketAnalysisValuation(
            price_min=24,
            price_avg=38,
            price_max=52,
            sample_size=3,
            platforms=["wallapop"],
            confidence=0.74,
        ),
        comparable_listings=[listing()],
        recommendation=ValuationRecommendation(
            summary="Silla de madera en buen estado.",
            suggested_price=39,
            bullets=["Publica con fotos reales"],
            risks=["La demanda puede variar"],
            negotiation_margin_eur=5,
        ),
        analyzed_at="2026-10-24T15:00:00Z",
        cached=cached,
    )


def make_events(result: MarketAnalysisResult) -> list[Any]:
    return [
        AnalysisStarted("Silla madera", ("wallapop",), False),
        SourceStarted("wallapop"),
        SourceFinished(result.sources[0]),
        ValuationReady(result.valuation),
        RecommendationReady(result.recommendation),  # type: ignore[arg-type]
        AnalysisDone(result),
    ]


class FakeBrowser:
    def __init__(self, connected: bool = False) -> None:
        self.connected = connected

    async def health(self) -> Any:
        from app.mcp.browser.session import BrowserHealth

        return BrowserHealth(
            connected=self.connected,
            url="http://market-browser:9222",
            last_error=None,
        )


class FakeAnalyzer:
    def __init__(
        self,
        *,
        result: MarketAnalysisResult | None = None,
        error: Exception | None = None,
        events: list[Any] | None = None,
    ) -> None:
        self.result = result or make_result()
        self.error = error
        self.events = events if events is not None else make_events(self.result)
        self.browser = FakeBrowser()

    async def analyze(self, request: MarketAnalysisRequest) -> MarketAnalysisResult:
        if self.error is not None:
            raise self.error
        return self.result

    async def stream(self, request: MarketAnalysisRequest) -> Any:
        for event in self.events:
            yield event


def make_client(analyzer: FakeAnalyzer) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_deep_analyzer] = lambda: analyzer
    return TestClient(app)


def parse_sse(text: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for frame in text.split("\n\n"):
        if not frame.strip() or frame.lstrip().startswith(":"):
            continue
        name = ""
        data = ""
        for line in frame.splitlines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = line.removeprefix("data: ")
        if name:
            events.append((name, json.loads(data)))
    return events
