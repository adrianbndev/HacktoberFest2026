"""Acceptance tests for the minimal backend foundation (brief §7.1)."""

from __future__ import annotations

from app.main import create_app
from fastapi.testclient import TestClient


def test_market_health_returns_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/market/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert body["version"]
    assert body["fallbackEnabled"] is True
    assert body["jitterEnabled"] is True
    assert body["recommendationEnabled"] is False
    assert "timestamp" in body


def test_openapi_and_docs_are_served() -> None:
    with TestClient(create_app()) as client:
        docs = client.get("/docs")
        schema = client.get("/openapi.json")

    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    assert schema.status_code == 200
    assert "/api/market/health" in schema.json()["paths"]


def test_health_reflects_fallback_flag(monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("MARKET_ALLOW_FALLBACK", "false")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        body = client.get("/api/market/health").json()

    assert body["fallbackEnabled"] is False


def test_health_reports_recommendation_when_the_key_is_configured(monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-only")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        body = client.get("/api/market/health").json()

    assert body["recommendationEnabled"] is True
