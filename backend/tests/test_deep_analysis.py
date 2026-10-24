"""Deep analysis engine: statuses, quota, single IQR and partial results."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.mcp.analysis_events import AnalysisFailed, DeepAnalysisUnavailableError
from app.mcp.deep_analysis import (
    RELEVANCE_SKIPPED_WARNING,
    SMALL_SAMPLE_WARNING,
    UNAVAILABLE_DETAIL,
)
from tests.deep_analysis_support import (
    FakeBrowser,
    FakeSource,
    make_analysis_request,
    make_analyzer,
    three_sources,
)


async def test_analyze_builds_the_frozen_contract(tmp_path: Path) -> None:
    analyzer = make_analyzer(tmp_path, three_sources())

    result = await analyzer.analyze(make_analysis_request())

    assert result.query == "Silla madera"
    assert [source.source for source in result.sources] == [
        "ebay",
        "wallapop",
        "milanuncios",
    ]
    assert all(source.status == "ok" for source in result.sources)
    assert result.valuation.sample_size == 9
    assert result.valuation.platforms == ["ebay", "wallapop", "milanuncios"]
    assert 0 < result.valuation.price_min < result.valuation.price_avg < result.valuation.price_max
    assert 0 <= result.valuation.confidence <= 1
    assert result.recommendation is None
    assert result.cached is False
    assert len(result.sources[0].listings) == 3


async def test_per_platform_quota_caps_each_source_and_fills_twelve(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [100, 101, 102, 103, 104, 105, 106, 107]),
        "wallapop": FakeSource("wallapop", [100, 101, 102, 103, 104, 105]),
        "milanuncios": FakeSource("milanuncios", [100, 101, 102, 103, 104, 105]),
    }
    analyzer = make_analyzer(tmp_path, sources)

    result = await analyzer.analyze(make_analysis_request())

    assert len(result.sources[0].listings) == 8
    assert len(result.valuation.platforms) == 3
    assert len(result.comparable_listings) == 12
    counts: dict[str, int] = {}
    for listing in result.comparable_listings:
        counts[listing.platform] = counts.get(listing.platform, 0) + 1
    assert counts == {"ebay": 4, "wallapop": 4, "milanuncios": 4}


async def test_source_listing_urls_fall_back_to_functional_deep_links(
    tmp_path: Path,
) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], with_urls=False),
        "wallapop": FakeSource("wallapop", [32, 38, 42]),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41]),
    }
    analyzer = make_analyzer(tmp_path, sources)

    result = await analyzer.analyze(make_analysis_request())

    urls = [listing.url for listing in result.sources[0].listings]
    assert all(url and url.startswith("https://www.ebay.es/") for url in urls)


async def test_single_iqr_drops_outliers_without_running_iqr_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = three_sources(ebay=FakeSource("ebay", [30, 32, 34, 36, 38, 9_000]))
    analyzer = make_analyzer(tmp_path, sources)

    def _fail(*args: object, **kwargs: object) -> list[float]:
        raise AssertionError("IQR must run exactly once")

    monkeypatch.setattr("app.mcp.pricing_math.filter_outliers_iqr", _fail)

    result = await analyzer.analyze(make_analysis_request())

    assert result.valuation.sample_size == 11
    assert result.valuation.price_max < 1_000


async def test_all_sources_blocked_never_returns_synthetic_data(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", status="blocked", error="blocked_or_antibot_page"),
        "wallapop": FakeSource("wallapop", status="blocked", error="blocked_or_antibot_page"),
        "milanuncios": FakeSource("milanuncios", status="blocked", error="captcha"),
    }
    analyzer = make_analyzer(tmp_path, sources)

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(make_analysis_request())

    assert exc_info.value.detail == UNAVAILABLE_DETAIL
    assert exc_info.value.sources == {
        "ebay": "blocked",
        "wallapop": "blocked",
        "milanuncios": "blocked",
    }


async def test_unavailable_browser_maps_to_the_exact_detail(tmp_path: Path) -> None:
    analyzer = make_analyzer(
        tmp_path, three_sources(), browser=FakeBrowser(fail=True)
    )

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(make_analysis_request())

    assert exc_info.value.detail == "browser_unavailable"
    assert exc_info.value.sources == {}


async def test_partial_results_survive_blocked_and_timed_out_sources(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40]),
        "wallapop": FakeSource("wallapop", status="blocked"),
        "milanuncios": FakeSource("milanuncios", status="timeout"),
    }
    analyzer = make_analyzer(tmp_path, sources)

    result = await analyzer.analyze(make_analysis_request())

    assert [source.status for source in result.sources] == ["ok", "blocked", "timeout"]
    assert result.valuation.platforms == ["ebay"]
    assert any("wallapop" in warning for warning in result.warnings)
    assert any("milanuncios" in warning for warning in result.warnings)


async def test_source_timeout_does_not_abort_the_analysis(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], delay_sec=0.2),
        "wallapop": FakeSource("wallapop", [32, 38, 42]),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41]),
    }
    analyzer = make_analyzer(tmp_path, sources, market_source_timeout_sec=0.05)

    result = await analyzer.analyze(make_analysis_request())

    assert result.sources[0].status == "timeout"
    assert result.valuation.platforms == ["wallapop", "milanuncios"]


async def test_accessories_only_is_a_503_not_a_fake_valuation(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [10], titles=["Funda de silla"]),
        "wallapop": FakeSource("wallapop", [12], titles=["Cable de silla"]),
        "milanuncios": FakeSource("milanuncios", [11], titles=["Caja vacía silla"]),
    }
    analyzer = make_analyzer(tmp_path, sources)

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(make_analysis_request())

    assert exc_info.value.sources == {
        "ebay": "no_listings",
        "wallapop": "no_listings",
        "milanuncios": "no_listings",
    }


async def test_small_sample_adds_a_warning(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30]),
        "wallapop": FakeSource("wallapop", [32]),
        "milanuncios": FakeSource("milanuncios", [31]),
    }
    analyzer = make_analyzer(tmp_path, sources, market_min_sample_size=4)

    result = await analyzer.analyze(make_analysis_request())

    assert SMALL_SAMPLE_WARNING in result.warnings


async def test_relevance_fallback_adds_a_warning(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], titles=["Bicicleta", "Monopatín", "Patinete"]),
        "wallapop": FakeSource("wallapop", [32, 38, 42], titles=["Bicicleta", "Monopatín", "Patinete"]),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41], titles=["Bicicleta", "Monopatín", "Patinete"]),
    }
    analyzer = make_analyzer(tmp_path, sources)

    result = await analyzer.analyze(make_analysis_request())

    assert RELEVANCE_SKIPPED_WARNING in result.warnings
    assert result.valuation.sample_size == 9


async def test_analysis_can_be_disabled(tmp_path: Path) -> None:
    analyzer = make_analyzer(
        tmp_path, three_sources(), market_analysis_enabled=False
    )

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(make_analysis_request())

    assert exc_info.value.detail == "analysis_disabled"


async def test_events_include_a_failure_before_done_when_all_is_blocked(
    tmp_path: Path,
) -> None:
    sources = {
        "ebay": FakeSource("ebay", status="blocked"),
        "wallapop": FakeSource("wallapop", status="blocked"),
        "milanuncios": FakeSource("milanuncios", status="blocked"),
    }
    analyzer = make_analyzer(tmp_path, sources)

    events = [event async for event in analyzer.stream(make_analysis_request())]

    assert isinstance(events[-1], AnalysisFailed)
    assert events[-1].sources == {
        "ebay": "blocked",
        "wallapop": "blocked",
        "milanuncios": "blocked",
    }
