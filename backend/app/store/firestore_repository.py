"""Persistencia en Firestore (plan gratuito Spark).

Estructura: users/{uid} (perfil), users/{uid}/items/{itemId} (producto con su foto comprimida, < 1 MiB)
y captureSessions/{sessionId}. Las reglas de seguridad bloquean el acceso directo desde el navegador.
"""
import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore import CollectionReference, DocumentReference

from app.models.domain import InventoryItem, MobileCaptureSession, UserProfile

FIRESTORE_TIMEOUT_SEC = 5.0  # ninguna llamada externa sin timeout (guardrails §2)


class FirestoreStoreRepository:
    def __init__(self, app: firebase_admin.App) -> None:
        self._db = firestore.client(app)

    def _user(self, uid: str) -> DocumentReference:
        return self._db.collection("users").document(uid)

    def _items(self, uid: str) -> CollectionReference:
        return self._user(uid).collection("items")

    def _session(self, session_id: str) -> DocumentReference:
        return self._db.collection("captureSessions").document(session_id)

    def get_profile(self, uid: str) -> UserProfile | None:
        snapshot = self._user(uid).get(timeout=FIRESTORE_TIMEOUT_SEC)
        return UserProfile.model_validate(snapshot.to_dict()) if snapshot.exists else None

    def save_profile(self, profile: UserProfile) -> None:
        self._user(profile.id).set(profile.model_dump(exclude_none=True), timeout=FIRESTORE_TIMEOUT_SEC)

    def list_items(self, uid: str) -> list[InventoryItem]:
        documents = self._items(uid).stream(timeout=FIRESTORE_TIMEOUT_SEC)
        return [InventoryItem.model_validate(document.to_dict()) for document in documents]

    def save_item(self, item: InventoryItem) -> None:
        document = self._items(item.user_id).document(item.id)
        document.set(item.model_dump(exclude_none=True), timeout=FIRESTORE_TIMEOUT_SEC)

    def delete_item(self, uid: str, item_id: str) -> bool:
        document = self._items(uid).document(item_id)
        if not document.get(timeout=FIRESTORE_TIMEOUT_SEC).exists:
            return False
        document.delete(timeout=FIRESTORE_TIMEOUT_SEC)
        return True

    def replace_items(self, uid: str, items: list[InventoryItem]) -> None:
        batch = self._db.batch()
        for document in self._items(uid).list_documents(timeout=FIRESTORE_TIMEOUT_SEC):
            batch.delete(document)
        for item in items:
            batch.set(self._items(uid).document(item.id), item.model_dump(exclude_none=True))
        batch.commit(timeout=FIRESTORE_TIMEOUT_SEC)

    def get_session(self, session_id: str) -> MobileCaptureSession | None:
        snapshot = self._session(session_id).get(timeout=FIRESTORE_TIMEOUT_SEC)
        return MobileCaptureSession.model_validate(snapshot.to_dict()) if snapshot.exists else None

    def save_session(self, session: MobileCaptureSession) -> None:
        self._session(session.session_id).set(session.model_dump(exclude_none=True), timeout=FIRESTORE_TIMEOUT_SEC)
