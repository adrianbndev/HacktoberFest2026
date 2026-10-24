"""Shared fixtures for the DeepSeek tests."""

from __future__ import annotations

import json

from app.config import Settings
from app.mcp.deepseek_client import CompletionResult
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


def make_settings() -> Settings:
    return Settings(
        deepseek_api_key="test-key",
        deepseek_reasoning_model="deepseek-v4-pro",
        deepseek_fast_model="deepseek-flash",
        deepseek_timeout_sec=2.0,
        _env_file=None,
    )


def make_request() -> ValuationRequest:
    return ValuationRequest(
        query="iPhone 13 128GB",
        category="Móviles",
        condition_score=80,
        condition_label="Como nuevo",
        description="Caja original, batería 89%, sin arañazos",
        include_recommendation=True,
    )


def make_valuation(
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


def recommendation_json(**overrides: object) -> CompletionResult:
    payload: dict[str, object] = {
        "summary": "iPhone 13 en muy buen estado, con caja y batería al 89%.",
        "suggestedPrice": 130,
        "bullets": ["Menciona la caja original", "Destaca la batería al 89%"],
        "risks": ["La demanda puede variar"],
        "negotiationMarginEur": 10,
    }
    payload.update(overrides)
    return CompletionResult(json.dumps(payload))
