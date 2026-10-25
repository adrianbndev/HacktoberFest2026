"""DeepSeek-only product relevance: batching, validation and failure codes."""

from __future__ import annotations

import asyncio
import json
from time import monotonic

import pytest
from app.mcp.deepseek_client import CompletionResult
from app.mcp.llm_relevance import (
    LLM_RELEVANCE_DISABLED,
    LLM_RELEVANCE_TIMEOUT,
    LLM_RELEVANCE_UNAVAILABLE,
    LlmRelevanceFilter,
    LlmRelevanceUnavailableError,
)
from tests.deepseek_support import FakeCompletion
from tests.llm_relevance_support import (
    AIRPODS_MATRIX,
    make_airpods_request,
    make_chat,
    make_listings,
    make_relevance_filter,
)
from tests.support import make_settings


async def test_batches_use_the_configured_size_and_keep_input_order() -> None:
    relevance, completion = make_relevance_filter(
        market_llm_relevance_batch_size=2
    )
    listings = make_listings([title for title, _ in AIRPODS_MATRIX])

    accepted = await relevance.classify(
        make_airpods_request(), listings, monotonic() + 5
    )

    assert len(completion.calls) == 7
    assert len(accepted) == 4
    assert [listing.price for listing in accepted] == [200, 201, 202, 203]


class StaticCompletion:
    """Return the same payload for every attempt (transport retries included)."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls = 0

    async def __call__(self, **kwargs: object) -> CompletionResult:
        self.calls += 1
        return CompletionResult(json.dumps(self.payload))


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"listings": []}, id="empty-listings"),
        pytest.param(
            {"listings": [{"id": 0, "label": "exact"}]},
            id="missing-ids",
        ),
        pytest.param(
            {
                "listings": [
                    {"label": "exact"},
                    {"id": 1, "label": "exact"},
                    {"id": 2, "label": "exact"},
                ]
            },
            id="entry-without-id",
        ),
        pytest.param(
            {
                "listings": [
                    {"id": 0, "label": "maybe_exact"},
                    {"id": 1, "label": "exact"},
                    {"id": 2, "label": "exact"},
                ]
            },
            id="unknown-label",
        ),
        pytest.param(
            {
                "listings": [
                    {"id": 0, "label": "exact"},
                    {"id": 1, "label": "exact"},
                    {"id": 2, "label": "exact"},
                    {"id": 99, "label": "exact"},
                ]
            },
            id="hallucinated-id",
        ),
        pytest.param(
            {
                "listings": [
                    {"id": 0, "label": "exact"},
                    {"id": 0, "label": "exact"},
                    {"id": 2, "label": "exact"},
                ]
            },
            id="missing-id-with-duplicate",
        ),
    ],
)
async def test_incomplete_or_invalid_batch_coverage_is_a_503(
    payload: dict[str, object],
) -> None:
    settings = make_settings()
    completion = StaticCompletion(payload)
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(),
            make_listings(["AirPods Pro 2", "AirPods Pro 2", "AirPods Pro 2"]),
            monotonic() + 5,
        )

    assert exc_info.value.code == LLM_RELEVANCE_UNAVAILABLE


async def test_complete_coverage_without_exact_returns_an_empty_accepted_list() -> None:
    payload = {
        "listings": [
            {"id": 0, "label": "different_model"},
            {"id": 1, "label": "accessory"},
        ]
    }
    settings = make_settings()
    completion = StaticCompletion(payload)
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, completion))

    accepted = await relevance.classify(
        make_airpods_request(),
        make_listings(["AirPods 2", "Funda AirPods"]),
        monotonic() + 5,
    )

    assert accepted == []


async def test_invalid_json_fails_with_a_typed_error_not_a_subset() -> None:
    settings = make_settings()
    completion = FakeCompletion(
        [CompletionResult("not json"), CompletionResult("still not json")]
    )
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(), make_listings(["AirPods Pro 2"]), monotonic() + 5
        )

    assert exc_info.value.code == LLM_RELEVANCE_UNAVAILABLE
    assert len(completion.calls) == 2


async def test_one_failed_batch_does_not_return_a_silent_subset() -> None:
    class FlakyCompletion:
        def __init__(self) -> None:
            self.calls = 0

        async def __call__(self, **kwargs: object) -> CompletionResult:
            self.calls += 1
            messages = kwargs["messages"]
            payload = json.loads(messages[1]["content"])
            if payload["listings"][0]["id"] != 0:
                return CompletionResult("not json")
            labelled = [
                {"id": item["id"], "label": "exact"} for item in payload["listings"]
            ]
            return CompletionResult(json.dumps({"listings": labelled}))

    settings = make_settings(market_llm_relevance_batch_size=2)
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, FlakyCompletion()))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(),
            make_listings(["AirPods Pro 2", "AirPods Pro 2", "AirPods Pro 2"]),
            monotonic() + 5,
        )

    assert exc_info.value.code == LLM_RELEVANCE_UNAVAILABLE


async def test_missing_api_key_is_unavailable_without_network() -> None:
    relevance = LlmRelevanceFilter(make_settings())

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(), make_listings(["AirPods Pro 2"]), monotonic() + 5
        )

    assert exc_info.value.code == LLM_RELEVANCE_UNAVAILABLE


async def test_timeout_maps_to_the_timeout_code() -> None:
    class SlowCompletion:
        async def __call__(self, **kwargs: object) -> CompletionResult:
            await asyncio.sleep(0.5)
            return CompletionResult(json.dumps({"listings": []}))

    settings = make_settings(market_llm_relevance_budget_sec=0.01)
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, SlowCompletion()))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(), make_listings(["AirPods Pro 2"]), monotonic() + 5
        )

    assert exc_info.value.code == LLM_RELEVANCE_TIMEOUT


async def test_an_expired_deadline_never_calls_the_llm() -> None:
    completion = FakeCompletion([])
    settings = make_settings()
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(), make_listings(["AirPods Pro 2"]), monotonic() - 1
        )

    assert exc_info.value.code == LLM_RELEVANCE_TIMEOUT
    assert completion.calls == []


async def test_disabled_llm_relevance_is_an_explicit_error() -> None:
    completion = FakeCompletion([])
    settings = make_settings(market_llm_relevance_enabled=False)
    relevance = LlmRelevanceFilter(settings, chat=make_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            make_airpods_request(), make_listings(["AirPods Pro 2"]), monotonic() + 5
        )

    assert exc_info.value.code == LLM_RELEVANCE_DISABLED
    assert completion.calls == []
