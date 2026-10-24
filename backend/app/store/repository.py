"""Persistencia compartida por los 3 Tracks (.agent/rules/hackathon-guardrails.md §3).

Con la clave de servicio de Firebase se usa Firestore; sin ella, un JSON local atómico con la misma interfaz
(para desarrollar sin conexión ni credenciales). El resto del backend solo conoce `StoreRepository`.
"""
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.firebase import firebase_app, has_service_account
from app.models.domain import AppStoreState, InventoryItem, MobileCaptureSession, UserProfile

DEFAULT_STORE_PATH = Path(__file__).resolve().parents[3] / "data" / "store.json"


class StoreRepository(Protocol):
    """Lo único que el resto del backend usa del almacenamiento."""

    def get_profile(self, uid: str) -> UserProfile | None: ...
    def save_profile(self, profile: UserProfile) -> None: ...
    def list_items(self, uid: str) -> list[InventoryItem]: ...
    def save_item(self, item: InventoryItem) -> None: ...
    def delete_item(self, uid: str, item_id: str) -> bool: ...
    def replace_items(self, uid: str, items: list[InventoryItem]) -> None: ...
    def get_session(self, session_id: str) -> MobileCaptureSession | None: ...
    def save_session(self, session: MobileCaptureSession) -> None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonStoreRepository:
    """Estado en memoria protegido por un RLock; cada cambio se escribe en .tmp y se renombra (os.replace)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._state = self._load()

    def get_profile(self, uid: str) -> UserProfile | None:
        with self._lock:
            profile = self._state.profiles.get(uid)
            return profile.model_copy(deep=True) if profile else None

    def save_profile(self, profile: UserProfile) -> None:
        with self._mutate() as state:
            state.profiles[profile.id] = profile

    def list_items(self, uid: str) -> list[InventoryItem]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._state.inventory if item.user_id == uid]

    def save_item(self, item: InventoryItem) -> None:
        with self._mutate() as state:
            state.inventory = [i for i in state.inventory if (i.user_id, i.id) != (item.user_id, item.id)] + [item]

    def delete_item(self, uid: str, item_id: str) -> bool:
        with self._mutate() as state:
            kept = [item for item in state.inventory if (item.user_id, item.id) != (uid, item_id)]
            deleted = len(kept) < len(state.inventory)
            state.inventory = kept
        return deleted

    def replace_items(self, uid: str, items: list[InventoryItem]) -> None:
        with self._mutate() as state:
            state.inventory = [item for item in state.inventory if item.user_id != uid] + items

    def get_session(self, session_id: str) -> MobileCaptureSession | None:
        with self._lock:
            session = self._state.capture_sessions.get(session_id)
            return session.model_copy(deep=True) if session else None

    def save_session(self, session: MobileCaptureSession) -> None:
        with self._mutate() as state:
            state.capture_sessions[session.session_id] = session

    @contextmanager
    def _mutate(self) -> Iterator[AppStoreState]:
        """Modifica un borrador bajo el lock y lo persiste al salir. Si el bloque lanza, no se guarda nada."""
        with self._lock:
            draft = self._state.model_copy(deep=True)
            yield draft
            draft.last_updated_at = _now()
            self._persist(draft)
            self._state = draft

    def _load(self) -> AppStoreState:
        try:
            return AppStoreState.model_validate_json(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except ValueError:  # JSON roto o que ya no cumple el contrato: se aparta, nunca se borra
            os.replace(self._path, self._path.with_suffix(".json.corrupt"))
        state = AppStoreState(
            profiles={}, inventory=[], capture_sessions={}, notifications=[], calendar_events=[], last_updated_at=_now()
        )
        self._persist(state)
        return state

    def _persist(self, state: AppStoreState) -> None:
        text = state.model_dump_json(indent=2, exclude_none=True)
        AppStoreState.model_validate_json(text)  # nunca escribir un archivo que luego no se pueda leer
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".json.tmp")
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, self._path)


@lru_cache
def get_store() -> StoreRepository:
    """Instancia única del proceso. En los routers se usa con Depends(get_store) para poder sustituirla en tests."""
    if has_service_account():
        from app.store.firestore_repository import FirestoreStoreRepository

        return FirestoreStoreRepository(firebase_app())
    return JsonStoreRepository(Path(os.getenv("STORE_FILE_PATH") or DEFAULT_STORE_PATH))
