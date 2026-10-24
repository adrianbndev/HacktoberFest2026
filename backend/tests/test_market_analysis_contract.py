"""Contract tests for the Phase 2 deep-analysis models (brief §5.1)."""

from __future__ import annotations

import pytest
from app.models.market_analysis import (
    MarketAnalysisRequest,
    MarketAnalysisResult,
    MarketAnalysisValuation,
    MarketSourceResult,
)
from app.models.sdd import MarketListingSample, ValuationRecommendation
from pydantic import ValidationError

VALID_REQUEST = {
    "name": "Silla de madera",
    "description": "Silla de madera en estado 'Como nuevo', con pequenas marcas.",
    "category": "Mobiliario",
    "brand": "Sin marca",
    "model": "Silla de madera",
    "conditionScore": 85,
    "conditionLabel": "Como nuevo",
    "location": {"lat": 40.4168, "lng": -3.7038},
}


def test_request_defaults_match_the_frozen_contract() -> None:
    request = MarketAnalysisRequest.model_validate(VALID_REQUEST)

    assert request.sources == ["ebay", "wallapop", "milanuncios"]
    assert request.include_recommendation is True
    assert request.condition_score == 85


def test_request_accepts_a_source_subset_and_dedupes_it() -> None:
    request = MarketAnalysisRequest.model_validate(
        {**VALID_REQUEST, "sources": ["wallapop", "ebay", "wallapop"]}
    )

    assert request.sources == ["wallapop", "ebay"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "x"),
        ("name", "   "),
        ("category", ""),
        ("conditionScore", -1),
        ("conditionScore", 101),
        ("conditionLabel", "Regular"),
        ("sources", []),
        ("sources", ["amazon"]),
        ("description", "x" * 2001),
        ("location", {"lat": 91, "lng": 0}),
    ],
)
def test_request_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        MarketAnalysisRequest.model_validate({**VALID_REQUEST, field: value})


def test_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        MarketAnalysisRequest.model_validate({**VALID_REQUEST, "userId": "uid-1"})


def test_response_serializes_camel_case_and_keeps_the_triplet() -> None:
    result = _result()
    payload = result.model_dump(by_alias=True, exclude_none=True)

    assert payload["query"] == "Silla madera"
    assert payload["sources"][0]["sampleSize"] == 3
    assert payload["sources"][0]["latencyMs"] == 8200
    assert payload["valuation"]["priceMin"] == 24
    assert payload["valuation"]["confidence"] == 0.74
    assert payload["cached"] is False
    assert payload["analyzedAt"] == "2026-10-24T15:00:00Z"
    assert "error" not in payload["sources"][0]


@pytest.mark.parametrize(
    ("price_min", "price_avg", "price_max"),
    [(0, 100, 120), (100, 100, 120), (100, 120, 120), (120, 100, 130)],
)
def test_valuation_rejects_invalid_triplet(
    price_min: int, price_avg: int, price_max: int
) -> None:
    with pytest.raises(ValidationError):
        MarketAnalysisValuation(
            price_min=price_min,
            price_avg=price_avg,
            price_max=price_max,
            sample_size=4,
            platforms=["wallapop"],
            confidence=0.5,
        )


def test_source_result_status_must_be_consistent_with_the_sample() -> None:
    with pytest.raises(ValidationError):
        MarketSourceResult(
            source="wallapop", status="ok", sample_size=0, latency_ms=100
        )
    with pytest.raises(ValidationError):
        MarketSourceResult(
            source="wallapop", status="no_listings", sample_size=3, latency_ms=100
        )


def test_result_rejects_a_platform_that_is_not_a_source() -> None:
    with pytest.raises(ValidationError):
        _result(platforms=["wallapop", "milanuncios"])


def test_result_requires_an_iso_timestamp() -> None:
    with pytest.raises(ValidationError):
        _result(analyzed_at="yesterday")


def test_recommendation_is_optional_and_uses_the_shared_shape() -> None:
    result = _result()

    assert result.recommendation is not None
    assert isinstance(result.recommendation, ValuationRecommendation)
    assert result.recommendation.suggested_price == 39


def _result(
    *, platforms: list[str] | None = None, analyzed_at: str = "2026-10-24T15:00:00Z"
) -> MarketAnalysisResult:
    return MarketAnalysisResult(
        query="Silla madera",
        sources=[
            MarketSourceResult(
                source="wallapop",
                status="ok",
                sample_size=3,
                listings=[
                    MarketListingSample(
                        title="Silla de madera",
                        price=35,
                        platform="wallapop",
                        condition="Buen estado",
                        url="https://es.wallapop.com/item/silla-madera",
                    )
                ],
                latency_ms=8200,
            )
        ],
        valuation=MarketAnalysisValuation(
            price_min=24,
            price_avg=38,
            price_max=52,
            sample_size=3,
            platforms=platforms or ["wallapop"],  # type: ignore[arg-type]
            confidence=0.74,
        ),
        recommendation=ValuationRecommendation(
            summary="Silla de madera en buen estado.",
            suggested_price=39,
            bullets=["Publica con fotos reales"],
            risks=["La demanda puede variar"],
            negotiation_margin_eur=5,
        ),
        analyzed_at=analyzed_at,
    )
