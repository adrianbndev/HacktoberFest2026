"""Deep analysis integration: DeepSeek-only relevance gates the price triplet."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.mcp.analysis_events import DeepAnalysisUnavailableError
from app.mcp.deep_analysis import LLM_RELEVANCE_DISCARDED_WARNING
from app.mcp.llm_relevance import (
    LLM_RELEVANCE_EMPTY,
    LLM_RELEVANCE_TIMEOUT,
    LLM_RELEVANCE_UNAVAILABLE,
    LlmRelevanceUnavailableError,
)
from tests.deep_analysis_support import (
    FakeRelevance,
    FakeSource,
    make_analysis_request,
    make_analyzer,
    three_sources,
)


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
