"""Deep analysis engine: statuses, quota, single IQR and partial results."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.mcp.analysis_events import AnalysisFailed, DeepAnalysisUnavailableError
from app.mcp.deep_analysis import (
    LLM_RELEVANCE_DISCARDED_WARNING,
    SMALL_SAMPLE_WARNING,
    UNAVAILABLE_DETAIL,
)
from app.mcp.llm_relevance import (
    LLM_RELEVANCE_EMPTY,
    LLM_RELEVANCE_TIMEOUT,
    LLM_RELEVANCE_UNAVAILABLE,
    LlmRelevanceUnavailableError,
)
from tests.deep_analysis_support import (
    FakeBrowser,
    FakeRelevance,
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


async def test_accessories_only_is_a_503_when_deepseek_rejects_everything(
    tmp_path: Path,
) -> None:
    sources = {
        "ebay": FakeSource("ebay", [10], titles=["Funda de silla"]),
        "wallapop": FakeSource("wallapop", [12], titles=["Cable de silla"]),
        "milanuncios": FakeSource("milanuncios", [11], titles=["Caja vacía silla"]),
    }
    analyzer = make_analyzer(
        tmp_path, sources, relevance=FakeRelevance(accept=lambda listing: False)
    )

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(make_analysis_request())

    assert exc_info.value.detail == LLM_RELEVANCE_EMPTY
    assert exc_info.value.sources == {
        "ebay": "ok",
        "wallapop": "ok",
        "milanuncios": "ok",
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


async def test_every_sanitised_listing_reaches_deepseek_without_a_prefilter(
    tmp_path: Path,
) -> None:
    titles = ["Silla de madera", "Funda de silla", "Silla rota", "Cable de silla"]
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40, 45], titles=titles),
        "wallapop": FakeSource("wallapop", [32, 38, 42, 47], titles=titles),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41, 46], titles=titles),
    }
    relevance = FakeRelevance(accept=lambda listing: listing.title == "Silla de madera")
    analyzer = make_analyzer(tmp_path, sources, relevance=relevance)

    result = await analyzer.analyze(make_analysis_request())

    received = [listing.title for listing in relevance.received]
    assert sorted(set(received)) == sorted(titles)
    assert len(received) == 12
    assert result.valuation.sample_size == 3
    assert {listing.title for listing in result.comparable_listings} == {"Silla de madera"}


async def test_deepseek_discards_are_reported_and_never_priced(tmp_path: Path) -> None:
    titles = ["Silla de madera", "Bicicleta", "Funda de silla"]
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], titles=titles),
        "wallapop": FakeSource("wallapop", [32, 38, 42], titles=titles),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41], titles=titles),
    }
    relevance = FakeRelevance(accept=lambda listing: listing.title == "Silla de madera")
    analyzer = make_analyzer(tmp_path, sources, relevance=relevance)

    result = await analyzer.analyze(make_analysis_request())

    assert result.valuation.sample_size == 3
    assert [listing.price for listing in result.comparable_listings] == [30, 31, 32]
    expected = LLM_RELEVANCE_DISCARDED_WARNING.format(count=6)
    assert expected in result.warnings


async def test_only_the_exact_listings_feed_the_price_triplet(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [100, 130], titles=["AirPods Pro 2", "AirPods 2"]),
        "wallapop": FakeSource("wallapop", [110, 140], titles=["AirPods Pro 2", "Funda AirPods"]),
        "milanuncios": FakeSource("milanuncios", [120, 150], titles=["AirPods Pro 2", "AirPods Pro"]),
    }
    relevance = FakeRelevance(accept=lambda listing: listing.title == "AirPods Pro 2")
    analyzer = make_analyzer(
        tmp_path,
        sources,
        relevance=relevance,
        market_min_sample_size=3,
    )

    result = await analyzer.analyze(
        make_analysis_request(name="Apple AirPods Pro 2", brand="Apple", model="AirPods Pro 2")
    )

    assert result.valuation.sample_size == 3
    assert result.valuation.platforms == ["ebay", "wallapop", "milanuncios"]
    assert [listing.price for listing in result.comparable_listings] == [100, 110, 120]
    assert result.valuation.price_min < result.valuation.price_avg < result.valuation.price_max


@pytest.mark.parametrize("code", [LLM_RELEVANCE_UNAVAILABLE, LLM_RELEVANCE_TIMEOUT])
async def test_llm_relevance_failures_are_503_and_never_price_the_full_sample(
    tmp_path: Path, code: str
) -> None:
    sources = three_sources()
    analyzer = make_analyzer(
        tmp_path,
        sources,
        relevance=FakeRelevance(error=LlmRelevanceUnavailableError(code)),
    )

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(make_analysis_request())

    assert exc_info.value.detail == code
    assert exc_info.value.sources == {
        "ebay": "ok",
        "wallapop": "ok",
        "milanuncios": "ok",
    }


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
