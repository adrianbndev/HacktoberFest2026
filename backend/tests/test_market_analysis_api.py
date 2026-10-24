"""HTTP contract tests for /api/market/analyze (brief §5.1)."""

from __future__ import annotations

from app.mcp.analysis_events import DeepAnalysisUnavailableError
from tests.market_analysis_support import BODY, FakeAnalyzer, make_client


def test_analyze_returns_the_camel_case_contract() -> None:
    with make_client(FakeAnalyzer()) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {
        "query",
        "sources",
        "valuation",
        "comparableListings",
        "recommendation",
        "warnings",
        "cached",
        "analyzedAt",
    }
    assert body["sources"][0]["sampleSize"] == 3
    assert body["sources"][0]["latencyMs"] == 8200
    assert body["valuation"]["priceMin"] == 24
    assert body["valuation"]["confidence"] == 0.74
    assert body["comparableListings"][0]["url"].startswith("https://")
    assert body["cached"] is False


def test_analyze_returns_503_with_sources_when_all_sources_fail() -> None:
    analyzer = FakeAnalyzer(
        error=DeepAnalysisUnavailableError("no data", {"wallapop": "blocked"})
    )

    with make_client(analyzer) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "no data", "sources": {"wallapop": "blocked"}}


def test_analyze_returns_503_browser_unavailable_and_never_500() -> None:
    analyzer = FakeAnalyzer(
        error=DeepAnalysisUnavailableError("browser_unavailable", {})
    )

    with make_client(analyzer) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "browser_unavailable", "sources": {}}


def test_analyze_wraps_unexpected_errors_in_a_503() -> None:
    with make_client(FakeAnalyzer(error=RuntimeError("boom"))) as client:
        response = client.post("/api/market/analyze", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "analysis_failed", "sources": {}}


def test_analyze_validates_the_frozen_request_contract() -> None:
    with make_client(FakeAnalyzer()) as client:
        unknown = client.post("/api/market/analyze", json={**BODY, "userId": "u1"})
        no_sources = client.post("/api/market/analyze", json={**BODY, "sources": []})
        bad_name = client.post("/api/market/analyze", json={**BODY, "name": "x"})

    assert unknown.status_code == 422
    assert no_sources.status_code == 422
    assert bad_name.status_code == 422


def test_health_includes_browser_cache_and_analysis_fields() -> None:
    analyzer = FakeAnalyzer()

    with make_client(analyzer) as client:
        body = client.get("/api/market/health").json()

    assert body["browser"] == {
        "connected": False,
        "url": "http://market-browser:9222",
        "lastError": None,
    }
    assert body["cache"]["ttlSeconds"] == 900
    assert body["cache"]["path"]
    assert body["analysisEnabled"] is True
