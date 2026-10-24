"""Orchestration acceptance tests for /valuate (brief §7.5)."""

from __future__ import annotations

import time

import pytest
from app.mcp.market_analysis import (
    RECOMMENDATION_SKIPPED_WARNING,
    SMALL_SAMPLE_WARNING,
    UNAVAILABLE_DETAIL,
    MarketAnalyzer,
    MarketUnavailableError,
)
from tests.support import (
    FakeConnector,
    FakeRecommender,
    default_connectors,
    failing_connectors,
    make_request,
    make_settings,
)


async def test_live_valuation_returns_the_exact_contract() -> None:
    analyzer = MarketAnalyzer(make_settings(), connectors=default_connectors())

    result = await analyzer.valuate(make_request())

    assert result.source == "live_mcp"
    assert 0 < result.price_min < result.price_avg < result.price_max
    assert result.sample_size == 12
    assert 1 <= len(result.comparable_listings) <= 12
    assert set(result.platforms) == {
        listing.platform for listing in result.comparable_listings
    }
    assert all(
        listing.url and listing.url.startswith("https://")
        for listing in result.comparable_listings
    )
    assert result.recommendation is None


async def test_all_sources_failed_uses_the_deterministic_fallback() -> None:
    analyzer = MarketAnalyzer(make_settings(), connectors=failing_connectors())

    result = await analyzer.valuate(make_request())

    assert result.source == "stealth_fallback"
    assert result.sample_size == 11
    assert set(result.platforms) == {"wallapop", "milanuncios", "ebay"}
    assert any("catálogo curado" in warning for warning in result.warnings)
    assert all("network_error" in warning for warning in result.warnings[:3])


async def test_all_sources_failed_with_fallback_disabled_raises_typed_error() -> None:
    analyzer = MarketAnalyzer(
        make_settings(market_allow_fallback=False), connectors=failing_connectors()
    )

    with pytest.raises(MarketUnavailableError) as error:
        await analyzer.valuate(make_request())

    assert error.value.detail == UNAVAILABLE_DETAIL
    assert error.value.sources == {
        "wallapop": "network_error",
        "milanuncios": "network_error",
        "ebay": "network_error",
    }


async def test_partial_failure_keeps_live_source_and_warns() -> None:
    connectors: list[FakeConnector] = [
        FakeConnector("wallapop", [300, 320, 340, 360]),
        FakeConnector("milanuncios", [310, 330, 350, 370]),
        FakeConnector("ebay", failure_reason="blocked_http_403"),
    ]

    result = await MarketAnalyzer(make_settings(), connectors=connectors).valuate(make_request())

    assert result.source == "live_mcp"
    assert "ebay" not in result.platforms
    assert any("ebay" in warning and "blocked_http_403" in warning for warning in result.warnings)


async def test_slow_connectors_are_cut_off_by_the_per_source_timeout() -> None:
    connectors: list[FakeConnector] = [
        FakeConnector("wallapop", [300, 320, 340, 360]),
        FakeConnector("milanuncios", [310, 330, 350, 370], delay=1.0),
        FakeConnector("ebay", [290, 315, 345, 355]),
    ]
    settings = make_settings(
        market_connector_timeout_sec=0.05,
        market_jitter_min_sec=0.0,
        market_jitter_max_sec=0.0,
    )

    started = time.monotonic()
    result = await MarketAnalyzer(settings, connectors=connectors).valuate(make_request())
    elapsed = time.monotonic() - started

    assert result.source == "live_mcp"
    assert elapsed < 1.0
    assert any("milanuncios" in warning and "timeout" in warning for warning in result.warnings)


async def test_missing_listing_urls_are_filled_with_deep_links() -> None:
    connectors = [FakeConnector("wallapop", [300, 320, 340, 360], with_urls=False)]

    result = await MarketAnalyzer(make_settings(), connectors=connectors).valuate(make_request())

    assert result.comparable_listings
    assert all(
        listing.url and "es.wallapop.com/app/search" in listing.url
        for listing in result.comparable_listings
    )


async def test_recommendation_is_only_generated_when_requested() -> None:
    recommender = FakeRecommender()
    settings = make_settings()

    without = await MarketAnalyzer(
        settings, connectors=default_connectors(), recommender=recommender
    ).valuate(make_request())
    with_recommendation = await MarketAnalyzer(
        settings, connectors=default_connectors(), recommender=recommender
    ).valuate(make_request(include_recommendation=True))

    assert without.recommendation is None
    assert recommender.calls == 1
    assert with_recommendation.recommendation is not None
    recommendation = with_recommendation.recommendation
    assert with_recommendation.price_min <= recommendation.suggested_price <= (
        with_recommendation.price_max
    )
    assert recommender.last_budget == settings.deepseek_recommendation_budget_sec


async def test_recommendation_failure_keeps_the_valuation() -> None:
    recommender = FakeRecommender(error=RuntimeError("deepseek down"))

    result = await MarketAnalyzer(
        make_settings(), connectors=default_connectors(), recommender=recommender
    ).valuate(make_request(include_recommendation=True))

    assert result.source == "live_mcp"
    assert result.recommendation is None
    assert RECOMMENDATION_SKIPPED_WARNING in result.warnings


async def test_fallback_can_include_a_recommendation() -> None:
    result = await MarketAnalyzer(
        make_settings(), connectors=failing_connectors(), recommender=FakeRecommender()
    ).valuate(make_request(include_recommendation=True))

    assert result.source == "stealth_fallback"
    assert result.recommendation is not None
    assert result.price_min <= result.recommendation.suggested_price <= result.price_max


async def test_small_samples_are_flagged() -> None:
    connectors = [FakeConnector("wallapop", [300]), FakeConnector("ebay", [310])]

    result = await MarketAnalyzer(make_settings(), connectors=connectors).valuate(make_request())

    assert result.sample_size == 2
    assert SMALL_SAMPLE_WARNING in result.warnings


async def test_live_valuation_with_mocks_is_well_under_the_2_8s_budget() -> None:
    connectors = [
        FakeConnector("wallapop", [300, 320, 340, 360], delay=0.02),
        FakeConnector("milanuncios", [310, 330, 350, 370], delay=0.02),
        FakeConnector("ebay", [290, 315, 345, 355], delay=0.02),
    ]

    started = time.monotonic()
    await MarketAnalyzer(make_settings(), connectors=connectors).valuate(make_request())

    assert time.monotonic() - started < 2.8


async def test_payload_has_no_null_nan_or_zero_prices() -> None:
    result = await MarketAnalyzer(
        make_settings(), connectors=default_connectors()
    ).valuate(make_request(include_recommendation=True))
    payload = result.model_dump(by_alias=True, exclude_none=True)

    for key in ("priceMin", "priceAvg", "priceMax", "sampleSize"):
        assert isinstance(payload[key], int)
        assert payload[key] > 0
    assert payload["recommendation"]["suggestedPrice"] > 0
    assert "null" not in str(payload).lower()


async def test_recommendation_budget_is_not_clipped_by_the_market_deadline() -> None:
    recommender = FakeRecommender()
    settings = make_settings(
        market_deadline_sec=0.3,
        market_connector_timeout_sec=0.1,
        deepseek_recommendation_budget_sec=25.0,
    )

    result = await MarketAnalyzer(
        settings, connectors=default_connectors(), recommender=recommender
    ).valuate(make_request(include_recommendation=True))

    assert result.recommendation is not None
    assert recommender.last_budget == 25.0


async def test_zero_recommendation_budget_skips_the_llm() -> None:
    recommender = FakeRecommender()
    settings = make_settings(deepseek_recommendation_budget_sec=0.0)

    result = await MarketAnalyzer(
        settings, connectors=default_connectors(), recommender=recommender
    ).valuate(make_request(include_recommendation=True))

    assert recommender.calls == 0
    assert result.recommendation is None
    assert RECOMMENDATION_SKIPPED_WARNING in result.warnings
