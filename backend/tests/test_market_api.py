"""HTTP contract tests for POST /api/market/valuate."""

from __future__ import annotations

from app.main import create_app
from app.mcp.market_analysis import UNAVAILABLE_DETAIL, MarketAnalyzer
from app.routers.market import get_market_analyzer
from fastapi.testclient import TestClient
from tests.support import (
    FakeRecommender,
    default_connectors,
    failing_connectors,
    make_settings,
)

REQUEST_BODY = {
    "query": "iPhone 13 128GB",
    "category": "Móviles",
    "conditionScore": 80,
    "conditionLabel": "Como nuevo",
    "brand": "Apple",
    "model": "iPhone 13",
    "description": "Caja original, batería 89%, sin arañazos",
}


def _client(analyzer: MarketAnalyzer) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_market_analyzer] = lambda: analyzer
    return TestClient(app)


def test_valuate_returns_camel_case_contract_without_recommendation() -> None:
    analyzer = MarketAnalyzer(make_settings(), connectors=default_connectors())

    with _client(analyzer) as client:
        response = client.post("/api/market/valuate", json=REQUEST_BODY)

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {
        "priceMin",
        "priceAvg",
        "priceMax",
        "sampleSize",
        "platforms",
        "comparableListings",
        "source",
        "warnings",
    }
    assert "recommendation" not in body
    assert body["source"] == "live_mcp"
    assert 0 < body["priceMin"] < body["priceAvg"] < body["priceMax"]
    assert body["comparableListings"][0]["url"].startswith("https://")


def test_valuate_includes_recommendation_when_requested() -> None:
    analyzer = MarketAnalyzer(
        make_settings(), connectors=default_connectors(), recommender=FakeRecommender()
    )

    with _client(analyzer) as client:
        response = client.post(
            "/api/market/valuate", json={**REQUEST_BODY, "includeRecommendation": True}
        )

    assert response.status_code == 200
    recommendation = response.json()["recommendation"]
    assert recommendation["suggestedPrice"] > 0
    assert recommendation["bullets"]


def test_valuate_uses_fallback_when_sources_fail() -> None:
    analyzer = MarketAnalyzer(make_settings(), connectors=failing_connectors())

    with _client(analyzer) as client:
        response = client.post("/api/market/valuate", json=REQUEST_BODY)

    assert response.status_code == 200
    assert response.json()["source"] == "stealth_fallback"


def test_valuate_returns_structured_503_when_fallback_is_disabled() -> None:
    analyzer = MarketAnalyzer(
        make_settings(market_allow_fallback=False), connectors=failing_connectors()
    )

    with _client(analyzer) as client:
        response = client.post("/api/market/valuate", json=REQUEST_BODY)

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"detail", "sources"}
    assert body["detail"] == UNAVAILABLE_DETAIL
    assert body["sources"] == {
        "wallapop": "network_error",
        "milanuncios": "network_error",
        "ebay": "network_error",
    }


def test_valuation_request_validation_is_enforced() -> None:
    analyzer = MarketAnalyzer(make_settings(), connectors=default_connectors())
    without_category = {
        key: value for key, value in REQUEST_BODY.items() if key != "category"
    }

    with _client(analyzer) as client:
        invalid_score = client.post(
            "/api/market/valuate", json={**REQUEST_BODY, "conditionScore": 101}
        )
        invalid_label = client.post(
            "/api/market/valuate", json={**REQUEST_BODY, "conditionLabel": "Regular"}
        )
        missing_category = client.post("/api/market/valuate", json=without_category)

    assert invalid_score.status_code == 422
    assert invalid_label.status_code == 422
    assert missing_category.status_code == 422


def test_openapi_documents_the_valuate_route() -> None:
    with _client(MarketAnalyzer(make_settings(), connectors=default_connectors())) as client:
        schema = client.get("/openapi.json").json()

    assert "/api/market/valuate" in schema["paths"]
    assert "post" in schema["paths"]["/api/market/valuate"]
