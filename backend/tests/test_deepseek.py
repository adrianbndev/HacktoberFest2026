"""DeepSeek recommendation, parsing and relevance tests (brief §7.6)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from app.config import Settings
from app.mcp.deepseek import (
    CLAMP_WARNING,
    FALLBACK_WARNING,
    DeepSeekRecommender,
    ParsedQuery,
)
from app.mcp.deepseek_client import CompletionResult, ModelUnavailableError
from app.models.sdd import (
    MarketListingSample,
    MarketValuationResult,
    ValuationRequest,
)


class FakeCompletion:
    def __init__(self, responses: list[CompletionResult | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def __call__(self, **kwargs: object) -> CompletionResult:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _settings() -> Settings:
    return Settings(
        deepseek_api_key="test-key",
        deepseek_reasoning_model="deepseek-v4-pro",
        deepseek_fast_model="deepseek-flash",
        deepseek_timeout_sec=2.0,
        _env_file=None,
    )


def _request() -> ValuationRequest:
    return ValuationRequest(
        query="iPhone 13 128GB",
        category="Móviles",
        condition_score=80,
        condition_label="Como nuevo",
        description="Caja original, batería 89%, sin arañazos",
        include_recommendation=True,
    )


def _valuation(
    *, price_min: int = 100, price_avg: int = 120, price_max: int = 150
) -> MarketValuationResult:
    return MarketValuationResult(
        price_min=price_min,
        price_avg=price_avg,
        price_max=price_max,
        sample_size=12,
        platforms=["wallapop", "ebay"],
        comparable_listings=[
            MarketListingSample(
                title="iPhone 13 128GB",
                price=price_avg,
                platform="wallapop",
                condition="Buen estado",
                url="https://es.wallapop.com/app/search?keywords=iPhone%2013",
            )
        ],
        source="live_mcp",
    )


def _recommendation_json(**overrides: object) -> CompletionResult:
    payload: dict[str, object] = {
        "summary": "iPhone 13 en muy buen estado, con caja y batería al 89%.",
        "suggestedPrice": 130,
        "bullets": ["Menciona la caja original", "Destaca la batería al 89%"],
        "risks": ["La demanda puede variar"],
        "negotiationMarginEur": 10,
    }
    payload.update(overrides)
    return CompletionResult(json.dumps(payload))


async def test_recommendation_uses_reasoning_model_and_validates_json() -> None:
    completion = FakeCompletion([_recommendation_json()])

    outcome = await DeepSeekRecommender(_settings(), completion=completion).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
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
        [_recommendation_json(suggestedPrice=9999, negotiationMarginEur=9999)]
    )

    outcome = await DeepSeekRecommender(_settings(), completion=completion).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
    )

    assert outcome.recommendation.suggested_price == 150
    assert outcome.recommendation.negotiation_margin_eur == 50
    assert outcome.warnings == (CLAMP_WARNING,)


async def test_snake_case_keys_are_accepted() -> None:
    payload = _recommendation_json()
    body = json.loads(payload.content or "{}")
    body["suggested_price"] = body.pop("suggestedPrice")
    body["negotiation_margin_eur"] = body.pop("negotiationMarginEur")

    outcome = await DeepSeekRecommender(
        _settings(), completion=FakeCompletion([CompletionResult(json.dumps(body))])
    ).recommend(request=_request(), valuation=_valuation(), budget_sec=1.0)

    assert outcome.recommendation.suggested_price == 130


async def test_empty_content_is_retried_once() -> None:
    completion = FakeCompletion([CompletionResult(None), _recommendation_json()])

    outcome = await DeepSeekRecommender(_settings(), completion=completion).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
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

    outcome = await DeepSeekRecommender(_settings(), completion=completion).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
    )

    assert len(completion.calls) == 4
    assert outcome.warnings == (FALLBACK_WARNING,)
    assert outcome.recommendation.suggested_price == 120
    joined = " ".join(outcome.recommendation.bullets).lower()
    assert "bateria" in joined
    assert "120" in joined


async def test_model_not_found_switches_to_the_fast_model() -> None:
    completion = FakeCompletion([ModelUnavailableError("model_not_found"), _recommendation_json()])

    outcome = await DeepSeekRecommender(_settings(), completion=completion).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
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

    outcome = await DeepSeekRecommender(_settings(), completion=completion).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
    )

    assert len(completion.calls) == 1
    assert outcome.warnings == (FALLBACK_WARNING,)


async def test_budget_timeout_falls_back_to_the_template() -> None:
    class SlowCompletion:
        async def __call__(self, **kwargs: object) -> CompletionResult:
            await asyncio.sleep(0.5)
            return _recommendation_json()

    outcome = await DeepSeekRecommender(_settings(), completion=SlowCompletion()).recommend(
        request=_request(), valuation=_valuation(), budget_sec=0.01
    )

    assert outcome.warnings == (FALLBACK_WARNING,)
    assert outcome.recommendation.suggested_price == 120


async def test_missing_api_key_uses_the_template_without_network() -> None:
    outcome = await DeepSeekRecommender(Settings(_env_file=None)).recommend(
        request=_request(), valuation=_valuation(), budget_sec=1.0
    )

    assert outcome.warnings == (FALLBACK_WARNING,)
    assert outcome.recommendation.bullets


async def test_parse_query_extracts_structured_fields() -> None:
    body = CompletionResult(
        json.dumps(
            {
                "query": "Nintendo Switch OLED",
                "brand": "Nintendo",
                "model": "Switch OLED",
                "category": "Consolas",
                "keywords": ["oled", "64gb"],
            }
        )
    )

    parsed = await DeepSeekRecommender(
        _settings(), completion=FakeCompletion([body])
    ).parse_query("Consola Nintendo Switch OLED 64GB blanca", budget_sec=1.0)

    assert parsed == ParsedQuery(
        query="Nintendo Switch OLED",
        brand="Nintendo",
        model="Switch OLED",
        category="Consolas",
        keywords=["oled", "64gb"],
    )


async def test_parse_query_falls_back_deterministically() -> None:
    parsed = await DeepSeekRecommender(Settings(_env_file=None)).parse_query(
        "  Consola Nintendo Switch OLED 64GB blanca  "
    )

    assert parsed.query == "Consola Nintendo Switch OLED 64GB"
    assert parsed.brand is None


def test_relevance_filter_drops_unrelated_titles() -> None:
    recommender = DeepSeekRecommender(Settings(_env_file=None))
    listings = [
        MarketListingSample(
            title="Samsung Galaxy S23", price=380, platform="ebay", condition="Buen estado"
        ),
        MarketListingSample(
            title="iPhone 13 128GB", price=330, platform="wallapop", condition="Buen estado"
        ),
    ]

    ranked = recommender.score_relevance("iPhone 13", listings)

    assert [listing.title for listing in ranked] == ["iPhone 13 128GB"]


def test_legacy_reasoner_model_is_never_hard_coded() -> None:
    app_dir = Path(__file__).parents[1] / "app"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in app_dir.rglob("*.py"))

    assert "deepseek-reasoner" not in sources


@pytest.mark.parametrize("model", ["deepseek-v4-pro", "deepseek-flash"])
def test_default_models_are_the_approved_ones(model: str) -> None:
    settings = _settings()

    assert model in {settings.deepseek_reasoning_model, settings.deepseek_fast_model}
