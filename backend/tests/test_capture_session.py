from fastapi.testclient import TestClient

from app.main import app
from app.store.repository import AppStoreRepository, get_store

PHOTO = "data:image/jpeg;base64,/9j/AA=="


def test_flujo_movil_pc(tmp_path) -> None:
    repo = AppStoreRepository(tmp_path / "store.json")
    app.dependency_overrides[get_store] = lambda: repo
    client = TestClient(app)
    try:
        created = client.post("/api/capture-session", json={"userId": "ales"}).json()
        session_url = f"/api/capture-session/{created['sessionId']}"
        assert created["mobileUrl"].endswith(f":3000/mobile-capture/{created['sessionId']}")
        assert client.get(session_url).json()["status"] == "waiting_for_mobile"

        assert client.put(session_url, json={"status": "mobile_connected"}).status_code == 200
        client.put(session_url, json={"status": "photo_uploaded", "photoDataUrl": PHOTO})
        session = client.get(session_url).json()
        assert session["status"] == "photo_uploaded" and session["photoDataUrl"] == PHOTO

        assert client.put(session_url, json={"status": "photo_uploaded", "photoDataUrl": "<script>"}).status_code == 422
        assert client.get("/api/capture-session/no-existe").status_code == 404
    finally:
        app.dependency_overrides.clear()
