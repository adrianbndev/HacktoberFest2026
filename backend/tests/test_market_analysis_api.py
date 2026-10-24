"""HTTP/SSE contract tests for /api/market/analyze (brief §5.1-5.2)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.main import create_app
from app.mcp.analysis_events import (
    AnalysisDone,
    AnalysisFailed,
    AnalysisStarted,
    DeepAnalysisUnavailableError,
    RecommendationReady,
    SourceFinished,
    SourceStarted,
    ValuationReady,
)
from app.mcp.sse import stream_analysis
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


def _listing() -> MarketListingSample:
    return MarketListingSample(
        title="Silla de madera",
        price=35,
        platform="wallapop",
        condition="Buen estado",
        url="https://es.wallapop.com/item/silla-madera",
    )


def _result(*, cached: bool = False) -> MarketAnalysisResult:
    return MarketAnalysisResult(
        query="Silla madera",
        sources=[
            MarketSourceResult(
                source="wallapop",
                status="ok",
                sample_size=3,
                listings=[_listing()],
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
        comparable_listings=[_listing()],
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


def _events(result: MarketAnalysisResult) -> list[Any]:
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
        self.result = result or _result()
        self.error = error
        self.events = events if events is not None else _events(self.result)
        self.browser = FakeBrowser()

    async def analyze(self, request: MarketAnalysisRequest) -> MarketAnalysisResult:
        if self.error is not None:
            raise self.error
        return self.result

    async def stream(self, request: MarketAnalysisRequest) -> Any:
        for event in self.events:
            yield event


def _client(analyzer: FakeAnalyzer) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_deep_analyzer] = lambda: analyzer
    return TestClient(app)


def _parse_sse(text: str) -> list[tuple[str, dict[str, Any]]]:
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


def test_analyze_returns_the_camel_case_contract() -> None:
    with _client(FakeAnalyzer()) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {
        "query",
        "sources",
        "valuation",
        "comparableListings",
        "recommendation",
        "warnings",
        "cached",
        "analyzedAt",
    }
    assert body["sources"][0]["sampleSize"] == 3
    assert body["sources"][0]["latencyMs"] == 8200
    assert body["valuation"]["priceMin"] == 24
    assert body["valuation"]["confidence"] == 0.74
    assert body["comparableListings"][0]["url"].startswith("https://")
    assert body["cached"] is False


def test_analyze_returns_503_with_sources_when_all_sources_fail() -> None:
    analyzer = FakeAnalyzer(
        error=DeepAnalysisUnavailableError("no data", {"wallapop": "blocked"})
    )

    with _client(analyzer) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "no data", "sources": {"wallapop": "blocked"}}


def test_analyze_returns_503_browser_unavailable_and_never_500() -> None:
    analyzer = FakeAnalyzer(
        error=DeepAnalysisUnavailableError("browser_unavailable", {})
    )

    with _client(analyzer) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "browser_unavailable", "sources": {}}


def test_analyze_wraps_unexpected_errors_in_a_503() -> None:
    with _client(FakeAnalyzer(error=RuntimeError("boom"))) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "analysis_failed", "sources": {}}


def test_analyze_validates_the_frozen_request_contract() -> None:
    with _client(FakeAnalyzer()) as client:
        unknown = client.post("/api/market/analyze", json={**BODY, "userId": "u1"})
        no_sources = client.post("/api/market/analyze", json={**BODY, "sources": []})
        bad_name = client.post("/api/market/analyze", json={**BODY, "name": "x"})

    assert unknown.status_code == 422
    assert no_sources.status_code == 422
    assert bad_name.status_code == 422


def test_sse_stream_has_headers_and_the_expected_event_order() -> None:
    analyzer = FakeAnalyzer()

    with _client(analyzer) as client, client.stream("POST", "/api/market/analyze/stream", json=BODY) as response:
        text = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    events = _parse_sse(text)
    assert [name for name, _ in events] == [
        "analysis_started",
        "source_started",
        "source_result",
        "valuation",
        "recommendation",
        "done",
    ]
    assert events[0][1] == {
        "query": "Silla madera",
        "sources": ["wallapop"],
        "cached": False,
    }
    assert events[2][1]["sampleSize"] == 3
    assert events[-1][1]["cached"] is False


def test_sse_cache_hit_emits_started_and_done_quickly() -> None:
    result = _result(cached=True)
    analyzer = FakeAnalyzer(
        result=result,
        events=[
            AnalysisStarted("Silla madera", ("wallapop",), True),
            AnalysisDone(result),
        ],
    )

    with _client(analyzer) as client:
        started = time.monotonic()
        with client.stream("POST", "/api/market/analyze/stream", json=BODY) as response:
            events = _parse_sse("".join(response.iter_text()))
        elapsed = time.monotonic() - started

    assert [name for name, _ in events] == ["analysis_started", "done"]
    assert events[0][1]["cached"] is True
    assert elapsed < 1.0


def test_sse_emits_an_error_event_on_failure() -> None:
    analyzer = FakeAnalyzer(
        events=[AnalysisFailed("no data", {"wallapop": "blocked"})]
    )

    with _client(analyzer) as client:
        response = client.post("/api/market/analyze/stream", json=BODY)

    events = _parse_sse(response.text)
    assert events == [("error", {"detail": "no data", "sources": {"wallapop": "blocked"}})]


def test_health_includes_browser_cache_and_analysis_fields() -> None:
    analyzer = FakeAnalyzer()

    with _client(analyzer) as client:
        body = client.get("/api/market/health").json()

    assert body["browser"] == {
        "connected": False,
        "url": "http://market-browser:9222",
        "lastError": None,
    }
    assert body["cache"]["ttlSeconds"] == 900
    assert body["cache"]["path"]
    assert body["analysisEnabled"] is True


class SlowStreamAnalyzer:
    def __init__(self, result: MarketAnalysisResult, *, delay_sec: float = 10.0) -> None:
        self.result = result
        self.delay_sec = delay_sec
        self.cancelled = False

    async def stream(self, request: MarketAnalysisRequest) -> Any:
        try:
            yield AnalysisStarted("Silla madera", ("wallapop",), False)
            await asyncio.sleep(self.delay_sec)
            yield AnalysisDone(self.result)
        finally:
            self.cancelled = True


async def test_stream_emits_heartbeats_while_a_source_is_slow() -> None:
    analyzer = SlowStreamAnalyzer(_result(), delay_sec=0.06)
    request = MarketAnalysisRequest.model_validate(BODY)

    frames = [
        frame
        async for frame in stream_analysis(analyzer, request, heartbeat_sec=0.02)
    ]

    assert ": ping\n\n" in frames
    assert any(frame.startswith("event: analysis_started") for frame in frames)


async def test_disconnect_cancels_the_analysis_stream() -> None:
    analyzer = SlowStreamAnalyzer(_result())
    request = MarketAnalysisRequest.model_validate(BODY)

    generator = stream_analysis(analyzer, request, heartbeat_sec=10)
    first = await generator.__anext__()
    await generator.aclose()

    assert first.startswith("event: analysis_started")
    assert analyzer.cancelled is True
