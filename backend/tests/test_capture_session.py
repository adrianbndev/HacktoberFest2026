from app.auth import AuthenticatedUser, current_user
from app.main import app
from app.store.repository import get_store
from fastapi.testclient import TestClient

PHOTO = "data:image/jpeg;base64,/9j/AA=="


def test_flujo_movil_pc(memory_store) -> None:
    app.dependency_overrides[get_store] = lambda: memory_store
    client = TestClient(app)
    try:
        assert client.post("/api/capture-session").status_code == 401  # solo el PC con sesión iniciada

        app.dependency_overrides[current_user] = lambda: AuthenticatedUser("uid-matias", "Matías", None, None)
        created = client.post("/api/capture-session").json()
        assert len(created["sessionId"]) == 32
        session_url = f"/api/capture-session/{created['sessionId']}"
        assert created["mobileUrl"].endswith(f":3000/mobile-capture/{created['sessionId']}")

        app.dependency_overrides.pop(current_user)  # el móvil no inicia sesión
        assert client.get(session_url).json()["userId"] == "uid-matias"
        assert client.put(session_url, json={"status": "mobile_connected"}).status_code == 200
        client.put(session_url, json={"status": "photo_uploaded", "photoDataUrl": PHOTO})
        session = client.get(session_url).json()
        assert session["status"] == "photo_uploaded" and session["photoDataUrl"] == PHOTO

        assert client.put(session_url, json={"status": "photo_uploaded", "photoDataUrl": "<script>"}).status_code == 422
        assert client.get("/api/capture-session/no-existe").status_code == 404

        # Si el PC está ocupado revisando el producto anterior o editando uno, el móvil recibe 409 con el motivo.
        busy_msg = "Se está revisando el producto anterior en el portátil."
        assert client.put(session_url, json={"status": "mobile_connected", "busyReason": busy_msg}).status_code == 200
        assert client.get(session_url).json()["busyReason"] == busy_msg
        blocked = client.put(session_url, json={"status": "photo_uploaded", "photoDataUrl": PHOTO})
        assert blocked.status_code == 409 and busy_msg in blocked.json()["detail"]

        # Al guardar el producto y volver a la Home en el PC, busyReason se limpia y el móvil puede subir otra foto.
        assert client.put(session_url, json={"status": "completed", "busyReason": None}).status_code == 200
        assert "busyReason" not in client.get(session_url).json()
        assert client.put(session_url, json={"status": "photo_uploaded", "photoDataUrl": PHOTO}).status_code == 200

        # Si ambos dispositivos recargan la página, el PC recupera el mismo sessionId sin perder el vínculo.
        app.dependency_overrides[current_user] = lambda: AuthenticatedUser("uid-matias", "Matías", None, None)
        reloaded = client.post("/api/capture-session").json()
        assert reloaded["sessionId"] == created["sessionId"]
    finally:
        app.dependency_overrides.clear()
