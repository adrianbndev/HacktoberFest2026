"""Deep analysis engine: statuses, quota, single IQR, cache and events."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
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
from app.mcp.browser.session import BrowserUnavailableError
from app.mcp.browser.sources.base import SourceOutcome
from app.mcp.cache import MarketAnalysisCache
from app.mcp.deep_analysis import (
    RECOMMENDATION_SKIPPED_WARNING,
    RELEVANCE_SKIPPED_WARNING,
    SMALL_SAMPLE_WARNING,
    UNAVAILABLE_DETAIL,
    DeepMarketAnalyzer,
)
from app.mcp.deepseek import CLAMP_WARNING, RecommendationOutcome
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
            import asyncio

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


def _analyzer(
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


def _request(**overrides: object) -> MarketAnalysisRequest:
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


def _three_sources(**overrides: Any) -> dict[str, FakeSource]:
    defaults: dict[str, FakeSource] = {
        "ebay": FakeSource("ebay", [30, 35, 40]),
        "wallapop": FakeSource("wallapop", [32, 38, 42]),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41]),
    }
    for platform, source in overrides.items():
        source.platform = platform
        defaults[platform] = source
    return defaults


async def test_analyze_builds_the_frozen_contract(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path, _three_sources())

    result = await analyzer.analyze(_request())

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


async def test_per_platform_quota_caps_each_source_at_four(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [100, 101, 102, 103, 104, 105, 106, 107]),
        "wallapop": FakeSource("wallapop", [100, 101, 102, 103, 104, 105]),
        "milanuncios": FakeSource("milanuncios", [100, 101, 102, 103, 104, 105]),
    }
    analyzer = _analyzer(tmp_path, sources)

    result = await analyzer.analyze(_request())

    assert len(result.sources[0].listings) == 8
    assert len(result.valuation.platforms) == 3
    assert len(result.comparable_listings) == 12
    counts = {}
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
    analyzer = _analyzer(tmp_path, sources)

    result = await analyzer.analyze(_request())

    urls = [listing.url for listing in result.sources[0].listings]
    assert all(url and url.startswith("https://www.ebay.es/") for url in urls)


async def test_single_iqr_drops_outliers_without_running_iqr_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = _three_sources(
        ebay=FakeSource("ebay", [30, 32, 34, 36, 38, 9_000])
    )
    analyzer = _analyzer(tmp_path, sources)

    def _fail(*args: object, **kwargs: object) -> list[float]:
        raise AssertionError("IQR must run exactly once")

    monkeypatch.setattr("app.mcp.pricing_math.filter_outliers_iqr", _fail)

    result = await analyzer.analyze(_request())

    assert result.valuation.sample_size == 11
    assert result.valuation.price_max < 1_000


async def test_all_sources_blocked_never_returns_synthetic_data(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", status="blocked", error="blocked_or_antibot_page"),
        "wallapop": FakeSource("wallapop", status="blocked", error="blocked_or_antibot_page"),
        "milanuncios": FakeSource("milanuncios", status="blocked", error="captcha"),
    }
    analyzer = _analyzer(tmp_path, sources)

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(_request())

    assert exc_info.value.detail == UNAVAILABLE_DETAIL
    assert exc_info.value.sources == {
        "ebay": "blocked",
        "wallapop": "blocked",
        "milanuncios": "blocked",
    }


async def test_unavailable_browser_maps_to_the_exact_detail(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path, _three_sources(), browser=FakeBrowser(fail=True))

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(_request())

    assert exc_info.value.detail == "browser_unavailable"
    assert exc_info.value.sources == {}


async def test_partial_results_survive_blocked_and_timed_out_sources(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40]),
        "wallapop": FakeSource("wallapop", status="blocked"),
        "milanuncios": FakeSource("milanuncios", status="timeout"),
    }
    analyzer = _analyzer(tmp_path, sources)

    result = await analyzer.analyze(_request())

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
    analyzer = _analyzer(tmp_path, sources, market_source_timeout_sec=0.05)

    result = await analyzer.analyze(_request())

    assert result.sources[0].status == "timeout"
    assert result.valuation.platforms == ["wallapop", "milanuncios"]


async def test_accessories_only_is_a_503_not_a_fake_valuation(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [10], titles=["Funda de silla"]),
        "wallapop": FakeSource("wallapop", [12], titles=["Cable de silla"]),
        "milanuncios": FakeSource("milanuncios", [11], titles=["Caja vacía silla"]),
    }
    analyzer = _analyzer(tmp_path, sources)

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(_request())

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
    analyzer = _analyzer(tmp_path, sources, market_min_sample_size=4)

    result = await analyzer.analyze(_request())

    assert SMALL_SAMPLE_WARNING in result.warnings


async def test_relevance_fallback_adds_a_warning(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", [30, 35, 40], titles=["Bicicleta", "Monopatín", "Patinete"]),
        "wallapop": FakeSource("wallapop", [32, 38, 42], titles=["Bicicleta", "Monopatín", "Patinete"]),
        "milanuncios": FakeSource("milanuncios", [31, 36, 41], titles=["Bicicleta", "Monopatín", "Patinete"]),
    }
    analyzer = _analyzer(tmp_path, sources)

    result = await analyzer.analyze(_request())

    assert RELEVANCE_SKIPPED_WARNING in result.warnings
    assert result.valuation.sample_size == 9


async def test_recommendation_is_clamped_into_the_triplet(tmp_path: Path) -> None:
    recommender = FakeRecommender(suggested_price=9_999)
    analyzer = _analyzer(
        tmp_path,
        _three_sources(),
        recommender=recommender,
    )

    result = await analyzer.analyze(_request(includeRecommendation=True))

    assert recommender.calls == 1
    assert result.recommendation is not None
    assert result.recommendation.suggested_price == result.valuation.price_max
    assert CLAMP_WARNING in result.warnings


async def test_recommendation_failure_is_omitted_with_a_warning(tmp_path: Path) -> None:
    analyzer = _analyzer(
        tmp_path,
        _three_sources(),
        recommender=FakeRecommender(error=RuntimeError("llm down")),
    )

    result = await analyzer.analyze(_request(includeRecommendation=True))

    assert result.recommendation is None
    assert RECOMMENDATION_SKIPPED_WARNING in result.warnings
    assert result.valuation.sample_size == 9


async def test_include_recommendation_false_never_calls_the_llm(tmp_path: Path) -> None:
    recommender = FakeRecommender()
    analyzer = _analyzer(tmp_path, _three_sources(), recommender=recommender)

    result = await analyzer.analyze(_request(includeRecommendation=False))

    assert recommender.calls == 0
    assert result.recommendation is None


async def test_second_identical_request_is_a_cache_hit(tmp_path: Path) -> None:
    sources = _three_sources()
    analyzer = _analyzer(tmp_path, sources)
    first = await analyzer.analyze(_request())
    second = await analyzer.analyze(_request(description="Otra descripción distinta"))

    assert first.cached is False
    assert second.cached is True
    assert second.analyzed_at == first.analyzed_at
    assert sources["ebay"].calls == 1


async def test_cache_is_isolated_by_sources(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path, _three_sources())
    await analyzer.analyze(_request())

    other = await analyzer.analyze(_request(sources=["ebay", "wallapop"]))

    assert other.cached is False
    assert other.valuation.platforms == ["ebay", "wallapop"]


async def test_cache_hit_emits_started_and_done_only(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path, _three_sources())
    await analyzer.analyze(_request())

    events = [event async for event in analyzer.stream(_request())]

    assert [type(event) for event in events] == [AnalysisStarted, AnalysisDone]
    assert events[0].cached is True


async def test_event_order_matches_the_sse_contract(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path, _three_sources())

    events = [event async for event in analyzer.stream(_request())]

    assert isinstance(events[0], AnalysisStarted)
    assert isinstance(events[1], SourceStarted)
    assert isinstance(events[2], SourceFinished)
    assert isinstance(events[3], SourceStarted)
    finished = [
        index for index, event in enumerate(events) if isinstance(event, SourceFinished)
    ]
    assert len(finished) == 3
    assert isinstance(events[finished[-1] + 1], ValuationReady)
    assert isinstance(events[-1], AnalysisDone)


async def test_recommendation_event_is_emitted_when_present(tmp_path: Path) -> None:
    analyzer = _analyzer(
        tmp_path, _three_sources(), recommender=FakeRecommender()
    )

    events = [event async for event in analyzer.stream(_request(includeRecommendation=True))]

    assert any(isinstance(event, RecommendationReady) for event in events)
    assert isinstance(events[-1], AnalysisDone)


async def test_analysis_can_be_disabled(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path, _three_sources(), market_analysis_enabled=False)

    with pytest.raises(DeepAnalysisUnavailableError) as exc_info:
        await analyzer.analyze(_request())

    assert exc_info.value.detail == "analysis_disabled"


async def test_events_include_a_failure_before_done_when_all_is_blocked(tmp_path: Path) -> None:
    sources = {
        "ebay": FakeSource("ebay", status="blocked"),
        "wallapop": FakeSource("wallapop", status="blocked"),
        "milanuncios": FakeSource("milanuncios", status="blocked"),
    }
    analyzer = _analyzer(tmp_path, sources)

    events = [event async for event in analyzer.stream(_request())]

    assert isinstance(events[-1], AnalysisFailed)
    assert events[-1].sources == {
        "ebay": "blocked",
        "wallapop": "blocked",
        "milanuncios": "blocked",
    }
