"""Usuario autenticado: el navegador inicia sesión con Firebase Auth (Google) y envía su ID token."""
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from firebase_admin import auth as firebase_auth

from app.firebase import firebase_app


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    name: str
    email: str | None
    picture: str | None


def current_user(authorization: Annotated[str | None, Header()] = None) -> AuthenticatedUser:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar")
    try:
        claims = firebase_auth.verify_id_token(token, app=firebase_app())
    except firebase_auth.CertificateFetchError as error:
        raise HTTPException(status_code=503, detail="No se pudo verificar la sesión con Google") from error
    except (ValueError, firebase_auth.InvalidIdTokenError) as error:
        raise HTTPException(status_code=401, detail="La sesión no es válida o ha caducado") from error
    email = claims.get("email")
    name = claims.get("name") or (email or "Usuario").split("@")[0]
    return AuthenticatedUser(uid=claims["uid"], name=name, email=email, picture=claims.get("picture"))


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]
