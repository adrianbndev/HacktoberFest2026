"""Persistencia compartida por los 3 Tracks (.agent/rules/hackathon-guardrails.md §3).

Local: JSON atómico en disco. Para pasar a cloud (Postgres, Supabase...), implementa `StoreRepository`
y devuélvelo desde `get_store()`: el resto del código no cambia (.agent/architecture.md §5).
"""
import os
import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.models.domain import AppStoreState
from app.store.seed_data import build_seed_state

DEFAULT_STORE_PATH = Path(__file__).resolve().parents[3] / "data" / "store.json"


class StoreRepository(Protocol):
    """Lo único que el resto del backend usa del almacenamiento."""

    def snapshot(self) -> AppStoreState: ...
    def transaction(self) -> AbstractContextManager[AppStoreState]: ...
    def reset_to_seed(self) -> AppStoreState: ...


class AppStoreRepository:
    """Estado en memoria protegido por un RLock; cada cambio se escribe en .tmp y se renombra (os.replace)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._state = self._load()

    def snapshot(self) -> AppStoreState:
        """Copia del estado actual: mutarla no afecta al store."""
        with self._lock:
            return self._state.model_copy(deep=True)

    @contextmanager
    def transaction(self) -> Iterator[AppStoreState]:
        """Modifica un borrador bajo el lock y lo persiste al salir. Si el bloque lanza, no se guarda nada."""
        with self._lock:
            draft = self._state.model_copy(deep=True)
            yield draft
            draft.last_updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._persist(draft)
            self._state = draft

    def reset_to_seed(self) -> AppStoreState:
        with self._lock:
            self._state = build_seed_state()
            self._persist(self._state)
            return self.snapshot()

    def _load(self) -> AppStoreState:
        try:
            return AppStoreState.model_validate_json(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except ValueError:  # JSON roto o que ya no cumple el contrato: se aparta, nunca se borra
            os.replace(self._path, self._path.with_suffix(".json.corrupt"))
        state = build_seed_state()
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
    return AppStoreRepository(Path(os.getenv("STORE_FILE_PATH") or DEFAULT_STORE_PATH))
