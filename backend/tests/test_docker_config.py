"""Static checks for the Docker/Compose deliverables (brief §7.8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]


def _compose() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_backend_service_is_healthy_and_exposed() -> None:
    service = _compose()["services"]["lifeos-backend"]

    assert service["ports"] == ["8000:8000"]
    assert service["build"]["context"] == "./backend"
    assert "healthcheck" in service
    assert (ROOT / "backend" / "Dockerfile").exists()


def test_browser_service_is_optional_and_hardened() -> None:
    compose = _compose()
    service = compose["services"]["market-browser"]

    assert service["profiles"] == ["browser"]
    assert service["shm_size"] == "2g"
    assert "chrome-profile:/chrome-profile" in service["volumes"]
    assert "chrome-profile" in compose["volumes"]
    assert (ROOT / "backend" / "Dockerfile.browser").exists()
    assert (ROOT / "backend" / "docker" / "browser-entrypoint.sh").exists()
    assert (ROOT / "backend" / "docker" / "cdp_proxy.py").exists()


def test_browser_container_never_uses_headless_or_automation_flags() -> None:
    entrypoint = (ROOT / "backend" / "docker" / "browser-entrypoint.sh").read_text(
        encoding="utf-8"
    )

    active = "\n".join(
        line for line in entrypoint.splitlines() if not line.lstrip().startswith("#")
    )
    assert "--headless" not in active
    assert "--enable-automation" not in active
    assert "--remote-debugging-port=" in active
    assert "CHROME_PORT" in active
    assert "cdp_proxy.py" in active
    assert "--user-data-dir=/chrome-profile" in active


def test_env_example_documents_the_required_flags() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    for key in (
        "MARKET_ALLOW_FALLBACK",
        "MARKET_JITTER_MIN_SEC",
        "MARKET_JITTER_MAX_SEC",
        "MARKET_CONNECTOR_TIMEOUT_SEC",
        "MARKET_DEADLINE_SEC",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
    ):
        assert key in env_example
