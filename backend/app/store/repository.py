"""Persistencia compartida por los 3 Tracks: Firestore (plan gratuito Spark, sin facturación).

El resto del backend solo conoce `StoreRepository`; la estructura de colecciones y documentos está en
firestore_repository.py. El backend necesita la clave de servicio de Firebase (nunca va al repo).
"""
from functools import lru_cache
from typing import Protocol

from fastapi import HTTPException

from app.firebase import SERVICE_ACCOUNT_PATH, firebase_app, has_service_account
from app.models.domain import InventoryItem, MobileCaptureSession, UserProfile
from app.store.firestore_repository import FirestoreStoreRepository


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


@lru_cache
def get_store() -> StoreRepository:
    """Instancia única del proceso. En los routers se usa con Depends(get_store) para poder sustituirla en tests."""
    if not has_service_account():
        raise HTTPException(
            status_code=503,
            detail=f"Falta la clave de servicio de Firebase ({SERVICE_ACCOUNT_PATH.name}): "
            "guárdala en la raíz del repo y reinicia el backend",
        )
    return FirestoreStoreRepository(firebase_app())
