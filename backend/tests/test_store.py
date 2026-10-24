import pytest
from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, current_user
from app.main import app
from app.store.repository import JsonStoreRepository, get_store
from app.store.seed_data import demo_items, new_profile

MATIAS = AuthenticatedUser(uid="uid-matias", name="Matías", email="matias@example.com", picture=None)
ALES = AuthenticatedUser(uid="uid-ales", name="Ales", email="ales@example.com", picture=None)


def test_productos_demo_cumplen_invariantes() -> None:
    items = demo_items("uid-x")
    assert len(items) == 3 and len({item.id for item in items}) == 3
    for item in items:
        assert item.user_id == "uid-x"
        assert 0 < item.price_min < item.price_avg < item.price_max
        assert len(item.price_history) == 3 and item.price_history[-1].price_avg == item.price_avg
        assert all(0 < p.price_min < p.price_avg < p.price_max for p in item.price_history)
        assert all(listing.url for listing in item.comparable_listings)
    assert {item.price_trend for item in items} == {"up", "down", "stable"}


def test_json_persiste_y_sobrevive_a_un_reinicio(tmp_path) -> None:
    path = tmp_path / "store.json"
    JsonStoreRepository(path).save_profile(new_profile("uid-1", "Adri", None, None))
    assert JsonStoreRepository(path).get_profile("uid-1").name == "Adri"
    assert not path.with_suffix(".json.tmp").exists()


def test_cambio_fallido_no_guarda_nada(tmp_path) -> None:
    repo = JsonStoreRepository(tmp_path / "store.json")
    repo.replace_items("uid-1", demo_items("uid-1"))
    with pytest.raises(RuntimeError), repo._mutate() as state:
        state.inventory.clear()
        raise RuntimeError
    assert len(repo.list_items("uid-1")) == 3


def test_archivo_corrupto_se_aparta_y_arranca_vacio(tmp_path) -> None:
    path = tmp_path / "store.json"
    path.write_text("{roto", encoding="utf-8")
    repo = JsonStoreRepository(path)
    assert path.with_suffix(".json.corrupt").read_text(encoding="utf-8") == "{roto"
    assert repo.get_profile("uid-1") is None


def test_api_de_punta_a_punta(tmp_path) -> None:
    repo = JsonStoreRepository(tmp_path / "store.json")
    app.dependency_overrides[get_store] = lambda: repo
    client = TestClient(app)
    try:
        assert client.get("/api/inventory").status_code == 401  # sin login de Firebase
        assert client.get("/api/inventory", headers={"Authorization": "Bearer no-es-un-token"}).status_code == 401

        app.dependency_overrides[current_user] = lambda: MATIAS
        assert client.post("/api/auth").json()["name"] == "Matías"
        inventory = client.get("/api/inventory").json()
        assert inventory["totals"]["itemCount"] == 3

        new_item = inventory["items"][0] | {"id": "nuevo", "userId": "otro-usuario", "details": "Con caja y 2 mandos"}
        saved = client.post("/api/inventory", json=new_item).json()
        assert saved["userId"] == MATIAS.uid and saved["details"] == "Con caja y 2 mandos"
        assert client.get("/api/inventory").json()["totals"]["itemCount"] == 4
        assert client.post("/api/inventory", json=new_item | {"priceMin": 9999}).status_code == 422

        app.dependency_overrides[current_user] = lambda: ALES  # cada usuario solo ve lo suyo
        client.post("/api/auth")
        assert client.get("/api/inventory").json()["totals"]["itemCount"] == 3
        assert client.delete("/api/inventory", params={"id": "nuevo"}).status_code == 404

        app.dependency_overrides[current_user] = lambda: MATIAS
        assert client.delete("/api/inventory", params={"id": "nuevo"}).status_code == 204
        valuation = client.post("/api/market/valuate", json={
            "query": "Nintendo Switch OLED", "category": "Consolas y Videojuegos",
            "conditionScore": 88, "conditionLabel": "Como nuevo",
        }).json()
        assert 0 < valuation["priceMin"] < valuation["priceAvg"] < valuation["priceMax"]

        client.delete("/api/inventory", params={"id": "demo-1"})
        assert client.post("/api/store/reset").json()["totals"]["itemCount"] == 3
    finally:
        app.dependency_overrides.clear()
