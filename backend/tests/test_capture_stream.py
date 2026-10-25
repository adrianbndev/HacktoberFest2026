import asyncio
import json

from app.main import app
from app.models.domain import MobileCaptureSession
from app.routers.capture_stream import session_events
from app.store.repository import get_store
from fastapi.testclient import TestClient

SESSION = MobileCaptureSession(
    session_id="s1",
    user_id="uid-matias",
    status="photo_uploaded",
    photo_data_url="data:image/jpeg;base64,/9j/AA==",
    created_at="2026-10-24T18:00:00+00:00",
    updated_at="2026-10-24T18:00:01+00:00",
)


class SequencedStore:
    """Devuelve las sesiones de la lista y None cuando se agotan."""

    def __init__(self, sessions):
        self.sessions = list(sessions)

    def get_session(self, _session_id):
        return self.sessions.pop(0) if self.sessions else None


async def never_disconnected() -> bool:
    return False


def collect(store, *, heartbeat_sec: float = 15.0, max_events: int = 10):
    async def run() -> list[str]:
        stream = session_events(store, "s1", never_disconnected, poll_sec=0.001, heartbeat_sec=heartbeat_sec)
        frames = []
        async for frame in stream:
            frames.append(frame)
            if len(frames) >= max_events:
                break
        return frames

    return asyncio.run(run())


def test_emits_initial_state_then_expires() -> None:
    frames = collect(SequencedStore([SESSION]))
    assert frames[0].startswith("event: session\ndata: ")
    payload = json.loads(frames[0].split("data: ", 1)[1])
    assert payload["status"] == "photo_uploaded"
    assert payload["photoDataUrl"] == SESSION.photo_data_url
    assert frames[-1] == "event: expired\ndata: {}\n\n"


def test_heartbeat_while_unchanged() -> None:
    store = SequencedStore([SESSION, SESSION, SESSION])
    frames = collect(store, heartbeat_sec=0.002)
    assert frames[0].startswith("event: session")
    assert ": ping\n\n" in frames


def test_endpoint_returns_404_for_unknown_session() -> None:
    app.dependency_overrides[get_store] = lambda: SequencedStore([])
    try:
        assert TestClient(app).get("/api/capture-session/no-existe/stream").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_endpoint_streams_and_closes_when_session_disappears() -> None:
    app.dependency_overrides[get_store] = lambda: SequencedStore([SESSION, SESSION])
    try:
        with TestClient(app).stream("GET", "/api/capture-session/s1/stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = "".join(response.iter_text())
        assert "event: session" in body and "photo_uploaded" in body
        assert "event: expired" in body
    finally:
        app.dependency_overrides.clear()
