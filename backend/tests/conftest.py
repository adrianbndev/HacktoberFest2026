"""Shared pytest fixtures.

Tests must be hermetic: no network, no developer ``.env`` and no ambient
``MARKET_*`` / ``DEEPSEEK_*`` environment variables.
"""

from __future__ import annotations

import os

import pytest
from app.config import get_settings

ISOLATED_ENV_KEYS = ("MARKET_", "DEEPSEEK_")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIFEOS_ENV_FILE", os.devnull)
    for key in list(os.environ):
        if key.upper().startswith(ISOLATED_ENV_KEYS):
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
