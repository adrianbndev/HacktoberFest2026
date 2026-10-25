"""Shared pytest fixtures: in-memory store (main) and hermetic settings (phase)."""

from __future__ import annotations

import os

import pytest
from app.config import Settings, get_settings
from app.models.domain import InventoryItem, MobileCaptureSession, UserProfile

ISOLATED_ENV_KEYS = ("MARKET_", "DEEPSEEK_", "VISION_")
# Variables del entorno local que no forman parte de los defaults bajo test.
EXTRA_ISOLATED_ENV_KEYS = ("CDP_URL",)


class InMemoryStore:
    """Almacén en memoria con la misma interfaz que Firestore, sin red ni credenciales."""

    def __init__(self) -> None:
        self.profiles: dict[str, UserProfile] = {}
        self.items: dict[tuple[str, str], InventoryItem] = {}
        self.sessions: dict[str, MobileCaptureSession] = {}

    def get_profile(self, uid: str) -> UserProfile | None:
        return self.profiles.get(uid)

    def save_profile(self, profile: UserProfile) -> None:
        self.profiles[profile.id] = profile

    def list_items(self, uid: str) -> list[InventoryItem]:
        return [item for (owner, _), item in self.items.items() if owner == uid]

    def save_item(self, item: InventoryItem) -> None:
        self.items[(item.user_id, item.id)] = item

    def delete_item(self, uid: str, item_id: str) -> bool:
        return self.items.pop((uid, item_id), None) is not None

    def replace_items(self, uid: str, items: list[InventoryItem]) -> None:
        kept = {key: item for key, item in self.items.items() if key[0] != uid}
        self.items = kept | {(uid, item.id): item for item in items}

    def get_session(self, session_id: str) -> MobileCaptureSession | None:
        return self.sessions.get(session_id)

    def save_session(self, session: MobileCaptureSession) -> None:
        self.sessions[session.session_id] = session


@pytest.fixture
def memory_store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIFEOS_ENV_FILE", os.devnull)
    # Un `.env` real del desarrollador (clave de DeepSeek, CDP_URL local) no debe cambiar los defaults que
    # afirman los tests: se corta también el env_file que `Settings` lee por defecto.
    monkeypatch.setitem(Settings.model_config, "env_file", os.devnull)
    for key in list(os.environ):
        if key.upper().startswith(ISOLATED_ENV_KEYS) or key.upper() in EXTRA_ISOLATED_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
