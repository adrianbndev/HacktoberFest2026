"""Settings loading tests (root .env + test isolation)."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings


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
