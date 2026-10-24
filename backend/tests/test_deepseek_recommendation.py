"""DeepSeek recommendation tests (brief §7.6)."""

from __future__ import annotations

import asyncio
import json

from app.config import Settings
from app.mcp.deepseek import (
    CLAMP_WARNING,
    FALLBACK_WARNING,
    DeepSeekRecommender,
)
from app.mcp.deepseek_client import CompletionResult, ModelUnavailableError
from tests.deepseek_support import (
    FakeCompletion,
    make_request,
    make_settings,
    make_valuation,
    recommendation_json,
)


async def test_recommendation_uses_reasoning_model_and_validates_json() -> None:
    completion = FakeCompletion([recommendation_json()])

    outcome = await DeepSeekRecommender(make_settings(), completion=completion).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert outcome.warnings == ()
    assert outcome.recommendation.suggested_price == 130
    assert outcome.recommendation.negotiation_margin_eur == 10
    call = completion.calls[0]
    assert call["model"] == "deepseek-v4-pro"
    assert call["reasoning_effort"] == "max"
    assert call["extra_body"] == {"thinking": {"type": "enabled"}}
    assert call["response_format"] == {"type": "json_object"}
    assert "json" in str(call["messages"]).lower()


async def test_suggested_price_and_margin_are_clamped_to_the_triplet() -> None:
    completion = FakeCompletion(
        [recommendation_json(suggestedPrice=9999, negotiationMarginEur=9999)]
    )

    outcome = await DeepSeekRecommender(make_settings(), completion=completion).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert outcome.recommendation.suggested_price == 150
    assert outcome.recommendation.negotiation_margin_eur == 50
    assert outcome.warnings == (CLAMP_WARNING,)


async def test_snake_case_keys_are_accepted() -> None:
    payload = recommendation_json()
    body = json.loads(payload.content or "{}")
    body["suggested_price"] = body.pop("suggestedPrice")
    body["negotiation_margin_eur"] = body.pop("negotiationMarginEur")

    outcome = await DeepSeekRecommender(
        make_settings(), completion=FakeCompletion([CompletionResult(json.dumps(body))])
    ).recommend(request=make_request(), valuation=make_valuation(), budget_sec=1.0)

    assert outcome.recommendation.suggested_price == 130


async def test_empty_content_is_retried_once() -> None:
    completion = FakeCompletion([CompletionResult(None), recommendation_json()])

    outcome = await DeepSeekRecommender(make_settings(), completion=completion).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert len(completion.calls) == 2
    assert outcome.warnings == ()
    assert outcome.recommendation.suggested_price == 130


async def test_invalid_json_falls_back_to_the_deterministic_template() -> None:
    completion = FakeCompletion(
        [
            CompletionResult("not json"),
            CompletionResult("{}"),
            CompletionResult(""),
            CompletionResult('{"summary": "incomplete"}'),
        ]
    )

    outcome = await DeepSeekRecommender(make_settings(), completion=completion).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert len(completion.calls) == 4
    assert outcome.warnings == (FALLBACK_WARNING,)
    assert outcome.recommendation.suggested_price == 120
    joined = " ".join(outcome.recommendation.bullets).lower()
    assert "bateria" in joined
    assert "120" in joined


async def test_model_not_found_switches_to_the_fast_model() -> None:
    completion = FakeCompletion([ModelUnavailableError("model_not_found"), recommendation_json()])

    outcome = await DeepSeekRecommender(make_settings(), completion=completion).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert [call["model"] for call in completion.calls] == [
        "deepseek-v4-pro",
        "deepseek-flash",
    ]
    assert completion.calls[1]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "reasoning_effort" not in completion.calls[1]
    assert outcome.recommendation.suggested_price == 130


async def test_transport_errors_fall_back_without_raising() -> None:
    completion = FakeCompletion([RuntimeError("network down")])

    outcome = await DeepSeekRecommender(make_settings(), completion=completion).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert len(completion.calls) == 1
    assert outcome.warnings == (FALLBACK_WARNING,)


async def test_budget_timeout_falls_back_to_the_template() -> None:
    class SlowCompletion:
        async def __call__(self, **kwargs: object) -> CompletionResult:
            await asyncio.sleep(0.5)
            return recommendation_json()

    outcome = await DeepSeekRecommender(make_settings(), completion=SlowCompletion()).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=0.01
    )

    assert outcome.warnings == (FALLBACK_WARNING,)
    assert outcome.recommendation.suggested_price == 120


async def test_missing_api_key_uses_the_template_without_network() -> None:
    outcome = await DeepSeekRecommender(Settings(_env_file=None)).recommend(
        request=make_request(), valuation=make_valuation(), budget_sec=1.0
    )

    assert outcome.warnings == (FALLBACK_WARNING,)
    assert outcome.recommendation.bullets
