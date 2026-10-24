"""Sesión de captura móvil <-> PC (MOD-02): el móvil sube la foto y el PC la recoge con polling."""
import socket
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.models.sdd import CaptureSessionCreated, CaptureSessionRequest, CaptureSessionUpdate, MobileCaptureSession
from app.store.repository import StoreRepository, get_store

router = APIRouter()
Store = Annotated[StoreRepository, Depends(get_store)]
WEB_PORT = 3000  # el móvil entra por la web (Next.js) y el proxy /api lo trae hasta aquí


def lan_ips() -> list[str]:
    """IPs de este equipo en la red local, para que el QR no apunte a localhost."""
    ips: set[str] = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))  # UDP: no envía nada, solo elige la interfaz de salida
            ips.add(probe.getsockname()[0])
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@router.post("/capture-session", response_model=CaptureSessionCreated)
def create_session(body: CaptureSessionRequest, store: Store) -> CaptureSessionCreated:
    session_id = uuid.uuid4().hex[:12]
    with store.transaction() as state:
        state.capture_sessions[session_id] = MobileCaptureSession(
            session_id=session_id, user_id=body.user_id, status="waiting_for_mobile", created_at=_now(), updated_at=_now()
        )
    ips = lan_ips()
    host = ips[0] if ips else "localhost"
    return CaptureSessionCreated(
        session_id=session_id, mobile_url=f"http://{host}:{WEB_PORT}/mobile-capture/{session_id}", lan_ips=ips
    )


@router.get("/capture-session/{session_id}", response_model=MobileCaptureSession, response_model_exclude_none=True)
def get_session(session_id: str, store: Store) -> MobileCaptureSession:
    session = store.snapshot().capture_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="La sesión de captura no existe")
    return session


@router.put("/capture-session/{session_id}", response_model=MobileCaptureSession, response_model_exclude_none=True)
def update_session(session_id: str, body: CaptureSessionUpdate, store: Store) -> MobileCaptureSession:
    with store.transaction() as state:
        session = state.capture_sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="La sesión de captura no existe")
        session.status = body.status
        if body.photo_data_url:
            session.photo_data_url = body.photo_data_url
        session.updated_at = _now()
        return session
