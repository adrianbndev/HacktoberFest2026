"""Deep analysis: parallel engine and hybrid Milanuncios transport."""

from __future__ import annotations

import time
from pathlib import Path

from app.mcp.analysis_events import AnalysisDone, SourceFinished
from app.mcp.deep_milanuncios import MilanunciosHybridRunner
from tests.deep_analysis_support import (
    FakeBrowser,
    FakeSource,
    make_analysis_request,
    make_analyzer,
)
from tests.support import make_settings
from tests.test_deep_milanuncios import FakeConnector


async def test_sources_run_concurrently(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], delay_sec=0.15),
        "wallapop": FakeSource("wallapop", [32, 38, 42], delay_sec=0.15),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41], delay_sec=0.15),
    }
    analyzer = make_analyzer(tmp_path, sources)

    started = time.monotonic()
    result = await analyzer.analyze(make_analysis_request())

    assert time.monotonic() - started < 0.35
    assert all(source.status == "ok" for source in result.sources)


async def test_concurrency_one_keeps_sequential_latency(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], delay_sec=0.08),
        "wallapop": FakeSource("wallapop", [32, 38, 42], delay_sec=0.08),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41], delay_sec=0.08),
    }
    analyzer = make_analyzer(tmp_path, sources, market_source_concurrency=1)

    started = time.monotonic()
    await analyzer.analyze(make_analysis_request())

    assert time.monotonic() - started >= 0.2


async def test_completion_order_differs_from_the_response_order(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], delay_sec=0.12),
        "wallapop": FakeSource("wallapop", [32, 38, 42], delay_sec=0.04),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41], delay_sec=0.0),
    }
    analyzer = make_analyzer(tmp_path, sources)

    events = [event async for event in analyzer.stream(make_analysis_request())]

    finished = [
        event.result.source for event in events if isinstance(event, SourceFinished)
    ]
    assert finished == ["milanuncios", "wallapop", "ebay"]
    done = events[-1]
    assert isinstance(done, AnalysisDone)
    assert [source.source for source in done.result.sources] == [
        "ebay",
        "wallapop",
        "milanuncios",
    ]


async def test_http_milanuncios_runs_without_a_browser_slot(tmp_path: Path) -> None:
    settings = make_settings(market_milanuncios_transport="auto")
    browser_milanuncios = FakeSource("milanuncios", list(range(30, 40)))
    http = FakeConnector(list(range(50, 60)))
    runner = MilanunciosHybridRunner(
        settings,
        FakeBrowser(),  # type: ignore[arg-type]
        browser_source=browser_milanuncios,
        http_connector=http,
    )
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40]),
        "wallapop": FakeSource("wallapop", [32, 38, 42]),
        "milanuncios": FakeSource("milanuncios", status="blocked"),
    }
    analyzer = make_analyzer(
        tmp_path,
        sources,
        milanuncios=runner,
        market_milanuncios_transport="auto",
    )

    result = await analyzer.analyze(make_analysis_request())

    milanuncios = next(source for source in result.sources if source.source == "milanuncios")
    assert milanuncios.status == "ok"
    assert milanuncios.sample_size == 10
    assert http.calls == 1
    assert browser_milanuncios.calls == 0
