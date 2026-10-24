"""Conexión con Firebase (proyecto lifeos-recommerce-hf26, plan gratuito Spark: sin facturación, sin gastos)."""
import os
from functools import lru_cache
from pathlib import Path

import firebase_admin
import google.auth.credentials
from firebase_admin import credentials

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "lifeos-recommerce-hf26")
# Clave privada de la cuenta de servicio (Consola > Configuración > Cuentas de servicio). Nunca va al repo.
SERVICE_ACCOUNT_PATH = Path(
    os.getenv("FIREBASE_SERVICE_ACCOUNT") or Path(__file__).resolve().parents[2] / "firebase-service-account.json"
)


def has_service_account() -> bool:
    return SERVICE_ACCOUNT_PATH.is_file()


class _AnonymousCredential(credentials.Base):
    """Sin clave de servicio: basta para verificar tokens de login (solo usa los certificados públicos de Google)."""

    def get_credential(self) -> google.auth.credentials.Credentials:
        return google.auth.credentials.AnonymousCredentials()


@lru_cache
def firebase_app() -> firebase_admin.App:
    """Sin clave basta para verificar los tokens de login; con la clave además se usa Firestore."""
    credential = credentials.Certificate(SERVICE_ACCOUNT_PATH) if has_service_account() else _AnonymousCredential()
    return firebase_admin.initialize_app(credential, {"projectId": FIREBASE_PROJECT_ID})
