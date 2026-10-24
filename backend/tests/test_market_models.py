"""Contract tests for the market Pydantic models (frozen + additive fields)."""

from __future__ import annotations

import pytest
from app.models.sdd import (
    MarketHealthResponse,
    MarketListingSample,
    MarketValuationResult,
    PricePoint,
    ValuationRequest,
)
from pydantic import ValidationError

VALID_REQUEST = {
    "query": "iPhone 13 128GB",
    "category": "Móviles",
    "conditionScore": 80,
    "conditionLabel": "Como nuevo",
}


def test_request_accepts_contract_and_additive_fields() -> None:
    request = ValuationRequest.model_validate(
        {
            **VALID_REQUEST,
            "brand": "Apple",
            "model": "iPhone 13",
            "description": "Caja original, batería 89%, sin arañazos",
            "includeRecommendation": True,
        }
    )

    assert request.query == "iPhone 13 128GB"
    assert request.condition_score == 80
    assert request.include_recommendation is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("query", "x"),
        ("query", "   "),
        ("category", ""),
        ("conditionScore", -1),
        ("conditionScore", 101),
        ("conditionLabel", "Regular"),
    ],
)
def test_request_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        ValuationRequest.model_validate({**VALID_REQUEST, field: value})


def test_request_rejects_unknown_fields_and_long_description() -> None:
    with pytest.raises(ValidationError):
        ValuationRequest.model_validate({**VALID_REQUEST, "priceMin": 10})

    with pytest.raises(ValidationError):
        ValuationRequest.model_validate({**VALID_REQUEST, "description": "x" * 2001})


@pytest.mark.parametrize(
    ("price_min", "price_avg", "price_max"),
    [(0, 100, 120), (100, 100, 120), (100, 120, 120), (120, 100, 130)],
)
def test_result_rejects_invalid_triplet(price_min: int, price_avg: int, price_max: int) -> None:
    with pytest.raises(ValidationError):
        _result(price_min=price_min, price_avg=price_avg, price_max=price_max)


def test_result_serializes_camel_case_and_declares_platforms() -> None:
    result = _result()
    payload = result.model_dump(by_alias=True, exclude_none=True)

    assert payload["priceMin"] == 100
    assert payload["priceAvg"] == 120
    assert payload["priceMax"] == 150
    assert payload["sampleSize"] == 4
    assert payload["comparableListings"][0]["title"] == "iPhone 13"
    assert "recommendation" not in payload
    assert payload["warnings"] == []


def test_result_rejects_listing_from_undeclared_platform() -> None:
    with pytest.raises(ValidationError):
        MarketValuationResult(
            price_min=100,
            price_avg=120,
            price_max=150,
            sample_size=1,
            platforms=["wallapop"],
            comparable_listings=[
                MarketListingSample(
                    title="iPhone 13",
                    price=120,
                    platform="ebay",
                    condition="Buen estado",
                    url="https://www.ebay.es/sch/i.html?_nkw=iPhone+13",
                )
            ],
            source="live_mcp",
        )


def test_comparable_listing_requires_http_url() -> None:
    with pytest.raises(ValidationError):
        MarketListingSample(
            title="iPhone 13",
            price=120,
            platform="wallapop",
            condition="Buen estado",
            url="javascript:alert(1)",
        )


def test_price_point_enforces_triplet_and_iso_timestamp() -> None:
    point = PricePoint(
        timestamp="2026-10-24T10:00:00+00:00",
        price_min=100,
        price_avg=120,
        price_max=150,
        sample_size=10,
        platforms=["wallapop", "ebay"],
    )
    assert point.sample_size == 10

    with pytest.raises(ValidationError):
        PricePoint(
            timestamp="not-a-date",
            price_min=100,
            price_avg=120,
            price_max=150,
            sample_size=10,
            platforms=["wallapop"],
        )


def test_health_response_requires_iso_timestamp() -> None:
    response = MarketHealthResponse(
        status="ok",
        service="test",
        version="0.1.0",
        fallback_enabled=True,
        jitter_enabled=True,
        recommendation_enabled=False,
        timestamp="2026-10-24T10:00:00+00:00",
    )
    assert response.status == "ok"


def _result(
    price_min: int = 100, price_avg: int = 120, price_max: int = 150
) -> MarketValuationResult:
    return MarketValuationResult(
        price_min=price_min,
        price_avg=price_avg,
        price_max=price_max,
        sample_size=4,
        platforms=["wallapop", "ebay"],
        comparable_listings=[
            MarketListingSample(
                title="iPhone 13",
                price=120,
                platform="wallapop",
                condition="Buen estado",
                url="https://es.wallapop.com/app/search?keywords=iPhone%2013",
            )
        ],
        source="live_mcp",
    )
