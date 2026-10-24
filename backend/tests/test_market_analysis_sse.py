"""SSE contract tests for /api/market/analyze/stream (brief §5.2)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.mcp.analysis_events import (
    AnalysisDone,
    AnalysisFailed,
    AnalysisStarted,
)
from app.mcp.sse import stream_analysis
from app.models.market_analysis import MarketAnalysisRequest, MarketAnalysisResult
from tests.market_analysis_support import (
    BODY,
    FakeAnalyzer,
    make_client,
    make_result,
    parse_sse,
)


def test_sse_stream_has_headers_and_the_expected_event_order() -> None:
    with make_client(FakeAnalyzer()) as client, client.stream("POST", "/api/market/analyze/stream", json=BODY) as response:
        text = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    events = parse_sse(text)
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
    result = make_result(cached=True)
    analyzer = FakeAnalyzer(
        result=result,
        events=[
            AnalysisStarted("Silla madera", ("wallapop",), True),
            AnalysisDone(result),
        ],
    )

    with make_client(analyzer) as client:
        started = time.monotonic()
        with client.stream("POST", "/api/market/analyze/stream", json=BODY) as response:
            events = parse_sse("".join(response.iter_text()))
        elapsed = time.monotonic() - started

    assert [name for name, _ in events] == ["analysis_started", "done"]
    assert events[0][1]["cached"] is True
    assert elapsed < 1.0


def test_sse_emits_an_error_event_on_failure() -> None:
    analyzer = FakeAnalyzer(
        events=[AnalysisFailed("no data", {"wallapop": "blocked"})]
    )

    with make_client(analyzer) as client:
        response = client.post("/api/market/analyze/stream", json=BODY)

    events = parse_sse(response.text)
    assert events == [
        ("error", {"detail": "no data", "sources": {"wallapop": "blocked"}})
    ]


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
    analyzer = SlowStreamAnalyzer(make_result(), delay_sec=0.06)
    request = MarketAnalysisRequest.model_validate(BODY)

    frames = [
        frame
        async for frame in stream_analysis(analyzer, request, heartbeat_sec=0.02)
    ]

    assert ": ping\n\n" in frames
    assert any(frame.startswith("event: analysis_started") for frame in frames)


async def test_disconnect_stops_the_browser_and_closes_pages() -> None:
    analyzer = SlowStreamAnalyzer(make_result())
    request = MarketAnalysisRequest.model_validate(BODY)
    stopped = False

    async def _cleanup() -> None:
        nonlocal stopped
        stopped = True

    generator = stream_analysis(
        analyzer, request, heartbeat_sec=10, on_disconnect=_cleanup
    )
    await generator.__anext__()
    await generator.aclose()

    assert stopped is True


async def test_disconnect_cancels_the_analysis_stream() -> None:
    analyzer = SlowStreamAnalyzer(make_result())
    request = MarketAnalysisRequest.model_validate(BODY)

    generator = stream_analysis(analyzer, request, heartbeat_sec=10)
    first = await generator.__anext__()
    await generator.aclose()

    assert first.startswith("event: analysis_started")
    assert analyzer.cancelled is True
