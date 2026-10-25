"""DeepSeek-only product relevance: Hermetic fake-LLM tests (no API calls)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from time import monotonic

import pytest
from app.mcp.deepseek_client import CompletionResult, DeepSeekChat
from app.mcp.llm_relevance import (
    EXACT,
    LLM_RELEVANCE_DISABLED,
    LLM_RELEVANCE_TIMEOUT,
    LLM_RELEVANCE_UNAVAILABLE,
    SYSTEM_PROMPT,
    LlmRelevanceFilter,
    LlmRelevanceUnavailableError,
)
from app.models.market_analysis import MarketAnalysisRequest
from app.models.sdd import MarketListingSample
from tests.deepseek_support import FakeCompletion
from tests.support import make_settings

AIRPODS_TARGET = "AirPods Pro 2"
AIRPODS_MATRIX: tuple[tuple[str, str], ...] = (
    ("AirPods Pro 2", EXACT),
    ("Apple AirPods Pro 2", EXACT),
    ("AirPods Pro 2nd generation", EXACT),
    ("AirPods 2", "different_model"),
    ("AirPods Pro", "different_model"),
    ("AirPods Pro 3", "different_model"),
    ("AirPods Pro 2 solo izquierdo", "single_item"),
    ("AirPods Pro 2 rotos", "broken"),
    ("Funda para AirPods Pro 2", "accessory"),
    ("Estuche AirPods Pro 2", "accessory"),
    ("AirPods Pro 2 para piezas", "broken"),
    ("Lote 2x AirPods Pro 2", "bundle"),
)


class LabelingCompletion:
    """Fake transport that labels each received listing from a title mapping."""

    def __init__(self, label_for: Callable[[str], str]) -> None:
        self._label_for = label_for
        self.calls: list[dict[str, object]] = []
        self.sent_titles: list[str] = []

    async def __call__(self, **kwargs: object) -> CompletionResult:
        self.calls.append(kwargs)
        messages = kwargs["messages"]
        assert isinstance(messages, list)
        payload = json.loads(messages[1]["content"])
        listings = payload["listings"]
        self.sent_titles.extend(item["title"] for item in listings)
        labelled = [
            {"id": item["id"], "label": self._label_for(item["title"])}
            for item in listings
        ]
        return CompletionResult(json.dumps({"listings": labelled}))


def _request(*, name: str = "Apple AirPods Pro 2") -> MarketAnalysisRequest:
    return MarketAnalysisRequest.model_validate(
        {
            "name": name,
            "description": "Auriculares con estuche original",
            "category": "Audio",
            "brand": "Apple",
            "model": AIRPODS_TARGET,
            "conditionScore": 85,
            "conditionLabel": "Como nuevo",
            "sources": ["wallapop"],
            "includeRecommendation": False,
        }
    )


def _listings(titles: list[str]) -> list[MarketListingSample]:
    return [
        MarketListingSample(
            title=title,
            price=200 + index,
            platform="wallapop",
            condition="Buen estado",
            url=f"https://example.com/{index}",
        )
        for index, title in enumerate(titles)
    ]


def _chat(settings: object, completion: object) -> DeepSeekChat:
    return DeepSeekChat(settings, completion=completion)  # type: ignore[arg-type]


def _filter(**overrides: object) -> tuple[LlmRelevanceFilter, LabelingCompletion]:
    label_by_title = dict(AIRPODS_MATRIX)
    completion = LabelingCompletion(lambda title: label_by_title.get(title, "unrelated"))
    settings = make_settings(**overrides)
    return LlmRelevanceFilter(settings, chat=_chat(settings, completion)), completion


async def test_all_sanitised_listings_reach_the_llm_and_only_exact_is_accepted() -> None:
    relevance, completion = _filter()
    titles = [title for title, _ in AIRPODS_MATRIX]
    listings = _listings(titles)

    accepted = await relevance.classify(_request(), listings, monotonic() + 5)

    assert [listing.title for listing in accepted] == [
        "AirPods Pro 2",
        "Apple AirPods Pro 2",
        "AirPods Pro 2nd generation",
    ]
    assert completion.sent_titles == titles
    assert completion.calls[0]["model"] == "deepseek-flash"
    assert completion.calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}


async def test_prompt_carries_the_target_fields_and_the_airpods_rules() -> None:
    relevance, completion = _filter()
    listings = _listings(["AirPods Pro 2", "Funda para AirPods Pro 2"])

    await relevance.classify(_request(), listings, monotonic() + 5)

    messages = completion.calls[0]["messages"]
    payload = json.loads(messages[1]["content"])
    assert payload["target"] == {
        "name": "Apple AirPods Pro 2",
        "brand": "Apple",
        "model": "AirPods Pro 2",
        "category": "Audio",
        "description": "Auriculares con estuche original",
        "conditionLabel": "Como nuevo",
        "conditionScore": 85,
    }
    assert [item["title"] for item in payload["listings"]] == [
        "AirPods Pro 2",
        "Funda para AirPods Pro 2",
    ]
    for expected in AIRPODS_MATRIX:
        assert expected[0] in SYSTEM_PROMPT
    assert "solo izquierdo" in SYSTEM_PROMPT
    assert "para piezas" in SYSTEM_PROMPT


async def test_batches_use_the_configured_size_and_keep_input_order() -> None:
    relevance, completion = _filter(market_llm_relevance_batch_size=2)
    listings = _listings([title for title, _ in AIRPODS_MATRIX])

    accepted = await relevance.classify(_request(), listings, monotonic() + 5)

    assert len(completion.calls) == 6
    assert len(accepted) == 3
    assert [listing.price for listing in accepted] == [200, 201, 202]


async def test_missing_ids_unknown_labels_and_hallucinated_ids_are_not_exact() -> None:
    class PartialCompletion:
        async def __call__(self, **kwargs: object) -> CompletionResult:
            return CompletionResult(
                json.dumps(
                    {
                        "listings": [
                            {"id": 0, "label": "EXACT"},
                            {"label": "exact"},
                            {"id": 1, "label": "maybe_exact"},
                            {"id": 99, "label": "exact"},
                        ]
                    }
                )
            )

    settings = make_settings()
    relevance = LlmRelevanceFilter(
        settings, chat=_chat(settings, PartialCompletion())
    )

    accepted = await relevance.classify(
        _request(), _listings(["AirPods Pro 2", "AirPods Pro 2", "AirPods Pro 2"]), monotonic() + 5
    )

    assert [listing.price for listing in accepted] == [200]


async def test_invalid_json_fails_with_a_typed_error_not_a_subset() -> None:
    settings = make_settings()
    completion = FakeCompletion(
        [CompletionResult("not json"), CompletionResult("still not json")]
    )
    relevance = LlmRelevanceFilter(settings, chat=_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(_request(), _listings(["AirPods Pro 2"]), monotonic() + 5)

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
            first_id = payload["listings"][0]["id"]
            if first_id != 0:
                return CompletionResult("not json")
            labelled = [
                {"id": item["id"], "label": "exact"} for item in payload["listings"]
            ]
            return CompletionResult(json.dumps({"listings": labelled}))

    settings = make_settings(market_llm_relevance_batch_size=2)
    completion = FlakyCompletion()
    relevance = LlmRelevanceFilter(settings, chat=_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(
            _request(),
            _listings(["AirPods Pro 2", "AirPods Pro 2", "AirPods Pro 2"]),
            monotonic() + 5,
        )

    assert exc_info.value.code == LLM_RELEVANCE_UNAVAILABLE


async def test_missing_api_key_is_unavailable_without_network() -> None:
    relevance = LlmRelevanceFilter(make_settings())

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(_request(), _listings(["AirPods Pro 2"]), monotonic() + 5)

    assert exc_info.value.code == LLM_RELEVANCE_UNAVAILABLE


async def test_timeout_maps_to_the_timeout_code() -> None:
    class SlowCompletion:
        async def __call__(self, **kwargs: object) -> CompletionResult:
            await asyncio.sleep(0.5)
            return CompletionResult(json.dumps({"listings": []}))

    settings = make_settings(market_llm_relevance_budget_sec=0.01)
    relevance = LlmRelevanceFilter(settings, chat=_chat(settings, SlowCompletion()))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(_request(), _listings(["AirPods Pro 2"]), monotonic() + 5)

    assert exc_info.value.code == LLM_RELEVANCE_TIMEOUT


async def test_an_expired_deadline_never_calls_the_llm() -> None:
    completion = FakeCompletion([])
    settings = make_settings()
    relevance = LlmRelevanceFilter(settings, chat=_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(_request(), _listings(["AirPods Pro 2"]), monotonic() - 1)

    assert exc_info.value.code == LLM_RELEVANCE_TIMEOUT
    assert completion.calls == []


async def test_disabled_llm_relevance_is_an_explicit_error() -> None:
    completion = FakeCompletion([])
    settings = make_settings(market_llm_relevance_enabled=False)
    relevance = LlmRelevanceFilter(settings, chat=_chat(settings, completion))

    with pytest.raises(LlmRelevanceUnavailableError) as exc_info:
        await relevance.classify(_request(), _listings(["AirPods Pro 2"]), monotonic() + 5)

    assert exc_info.value.code == LLM_RELEVANCE_DISABLED
    assert completion.calls == []
