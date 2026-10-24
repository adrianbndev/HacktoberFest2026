"""Almacén en memoria con la misma interfaz que Firestore, para probar la API sin red ni credenciales."""
import pytest

from app.models.domain import InventoryItem, MobileCaptureSession, UserProfile


class InMemoryStore:
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
