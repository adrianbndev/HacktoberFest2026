"""Settings loading tests (root .env + test isolation)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import get_settings
from pydantic import ValidationError


def test_get_settings_reads_the_configured_env_file(
    tmp_path: Path, monkeypatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DEEPSEEK_API_KEY=sk-from-file\nMARKET_ALLOW_FALLBACK=false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LIFEOS_ENV_FILE", str(env_file))
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.deepseek_api_key == "sk-from-file"
    assert settings.market_allow_fallback is False


def test_blank_deepseek_key_is_treated_as_missing(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
    get_settings.cache_clear()

    assert get_settings().deepseek_api_key is None


def test_deep_analysis_defaults_are_safe_and_additive() -> None:
    settings = get_settings()

    assert settings.market_analysis_enabled is True
    assert settings.market_analysis_deadline_sec == 60.0
    assert settings.market_source_timeout_sec == 25.0
    assert settings.market_browser_timeout_sec == 45.0
    assert settings.market_platform_quota == 4
    assert settings.market_cache_path == "/app/data/market_cache.sqlite"
    assert settings.market_cache_ttl_sec == 900
    assert settings.cdp_url == "http://market-browser:9222"


def test_deep_analysis_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_ANALYSIS_ENABLED", "false")
    monkeypatch.setenv("MARKET_CACHE_PATH", "/tmp/custom.sqlite")
    monkeypatch.setenv("MARKET_CACHE_TTL_SEC", "60")
    monkeypatch.setenv("CDP_URL", "http://127.0.0.1:9222")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.market_analysis_enabled is False
    assert settings.market_cache_path == "/tmp/custom.sqlite"
    assert settings.market_cache_ttl_sec == 60
    assert settings.cdp_url == "http://127.0.0.1:9222"


def test_deep_analysis_deadline_must_exceed_the_source_timeout(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_ANALYSIS_DEADLINE_SEC", "5")
    monkeypatch.setenv("MARKET_SOURCE_TIMEOUT_SEC", "10")
    get_settings.cache_clear()

    with pytest.raises(ValidationError):
        get_settings()
