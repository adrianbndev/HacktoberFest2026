"""Deep analysis cache, SSE event order and recommendation behaviour."""

from __future__ import annotations

from pathlib import Path

from app.mcp.analysis_events import (
    AnalysisDone,
    AnalysisStarted,
    RecommendationReady,
    SourceFinished,
    SourceStarted,
    ValuationReady,
)
from app.mcp.deep_recommend import RECOMMENDATION_SKIPPED_WARNING
from app.mcp.deepseek import CLAMP_WARNING
from tests.deep_analysis_support import (
    FakeRecommender,
    make_analysis_request,
    make_analyzer,
    three_sources,
)


async def test_recommendation_is_clamped_into_the_triplet(tmp_path: Path) -> None:
    recommender = FakeRecommender(suggested_price=9_999)
    analyzer = make_analyzer(tmp_path, three_sources(), recommender=recommender)

    result = await analyzer.analyze(make_analysis_request(includeRecommendation=True))

    assert recommender.calls == 1
    assert result.recommendation is not None
    assert result.recommendation.suggested_price == result.valuation.price_max
    assert CLAMP_WARNING in result.warnings


async def test_recommendation_failure_is_omitted_with_a_warning(tmp_path: Path) -> None:
    analyzer = make_analyzer(
        tmp_path,
        three_sources(),
        recommender=FakeRecommender(error=RuntimeError("llm down")),
    )

    result = await analyzer.analyze(make_analysis_request(includeRecommendation=True))

    assert result.recommendation is None
    assert RECOMMENDATION_SKIPPED_WARNING in result.warnings
    assert result.valuation.sample_size == 9


async def test_include_recommendation_false_never_calls_the_llm(tmp_path: Path) -> None:
    recommender = FakeRecommender()
    analyzer = make_analyzer(tmp_path, three_sources(), recommender=recommender)

    result = await analyzer.analyze(make_analysis_request(includeRecommendation=False))

    assert recommender.calls == 0
    assert result.recommendation is None


async def test_second_identical_request_is_a_cache_hit(tmp_path: Path) -> None:
    sources = three_sources()
    analyzer = make_analyzer(tmp_path, sources)
    first = await analyzer.analyze(make_analysis_request())
    second = await analyzer.analyze(
        make_analysis_request(description="Otra descripción distinta")
    )

    assert first.cached is False
    assert second.cached is True
    assert second.analyzed_at == first.analyzed_at
    assert sources["ebay"].calls == 1


async def test_cache_is_isolated_by_sources(tmp_path: Path) -> None:
    analyzer = make_analyzer(tmp_path, three_sources())
    await analyzer.analyze(make_analysis_request())

    other = await analyzer.analyze(make_analysis_request(sources=["ebay", "wallapop"]))

    assert other.cached is False
    assert other.valuation.platforms == ["ebay", "wallapop"]


async def test_cache_hit_emits_started_and_done_only(tmp_path: Path) -> None:
    analyzer = make_analyzer(tmp_path, three_sources())
    await analyzer.analyze(make_analysis_request())

    events = [event async for event in analyzer.stream(make_analysis_request())]

    assert [type(event) for event in events] == [AnalysisStarted, AnalysisDone]
    assert events[0].cached is True


async def test_event_order_matches_the_sse_contract(tmp_path: Path) -> None:
    analyzer = make_analyzer(tmp_path, three_sources())

    events = [event async for event in analyzer.stream(make_analysis_request())]

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
    analyzer = make_analyzer(tmp_path, three_sources(), recommender=FakeRecommender())

    events = [
        event
        async for event in analyzer.stream(
            make_analysis_request(includeRecommendation=True)
        )
    ]

    assert any(isinstance(event, RecommendationReady) for event in events)
    assert isinstance(events[-1], AnalysisDone)
