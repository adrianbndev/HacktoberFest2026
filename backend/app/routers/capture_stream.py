"""SSE de la sesión de captura (MOD-02): el PC recibe la foto en cuanto el móvil la sube."""
import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.store.repository import StoreRepository, get_store

router = APIRouter()
Store = Annotated[StoreRepository, Depends(get_store)]
POLL_SEC = 0.4  # lectura del store; el evento sale en cuanto cambia algo
HEARTBEAT_SEC = 15.0
Disconnected = Callable[[], Awaitable[bool]]


def session_frame(payload: str) -> str:
    """Formato SSE `event: session\\ndata: <json>\\n\\n`."""
    return f"event: session\ndata: {payload}\n\n"


async def session_events(
    store: StoreRepository,
    session_id: str,
    is_disconnected: Disconnected,
    *,
    poll_sec: float = POLL_SEC,
    heartbeat_sec: float = HEARTBEAT_SEC,
) -> AsyncIterator[str]:
    """Emite la sesión al conectar y en cada cambio; `: ping` si lleva un rato igual.

    El store (Firestore) es síncrono: se lee en un hilo para no bloquear el bucle.
    Si la sesión desaparece se cierra el stream con `expired` y el cliente vuelve al polling.
    """
    previous: str | None = None
    idle = 0.0
    while not await is_disconnected():
        session = await asyncio.to_thread(store.get_session, session_id)
        if session is None:
            yield "event: expired\ndata: {}\n\n"
            return
        payload = session.model_dump_json(by_alias=True, exclude_none=True)
        if payload != previous:
            previous, idle = payload, 0.0
            yield session_frame(payload)
        else:
            idle += poll_sec
            if idle >= heartbeat_sec:
                idle = 0.0
                yield ": ping\n\n"
        await asyncio.sleep(poll_sec)


@router.get("/capture-session/{session_id}/stream")
async def stream_session(session_id: str, request: Request, store: Store) -> StreamingResponse:
    # 404 antes de abrir el stream: un EventSource sobre una sesión inexistente no debe reconectar en bucle.
    if await asyncio.to_thread(store.get_session, session_id) is None:
        raise HTTPException(status_code=404, detail="La sesión de captura no existe")
    return StreamingResponse(
        session_events(store, session_id, request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
