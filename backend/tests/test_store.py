import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store.repository import AppStoreRepository, get_store
from app.store.seed_data import build_seed_state


def test_seed_cumple_invariantes() -> None:
    state = build_seed_state()
    assert set(state.profiles) == {"ales", "adri", "matias"}
    for user in state.profiles:
        items = [item for item in state.inventory if item.user_id == user]
        assert len(items) >= 3
        for item in items:
            assert 0 < item.price_min < item.price_avg < item.price_max
            assert len(item.price_history) == 3 and item.price_history[-1].price_avg == item.price_avg
            assert all(0 < p.price_min < p.price_avg < p.price_max for p in item.price_history)
            assert all(listing.url for listing in item.comparable_listings)
    assert len({item.id for item in state.inventory}) == len(state.inventory)


def test_persiste_en_disco_y_sobrevive_a_un_reinicio(tmp_path) -> None:
    path = tmp_path / "store.json"
    with AppStoreRepository(path).transaction() as state:
        state.active_user_id = "adri"
    assert AppStoreRepository(path).snapshot().active_user_id == "adri"
    assert not path.with_suffix(".json.tmp").exists()


def test_transaccion_fallida_no_guarda_nada(tmp_path) -> None:
    repo = AppStoreRepository(tmp_path / "store.json")
    with pytest.raises(RuntimeError), repo.transaction() as state:
        state.inventory.clear()
        raise RuntimeError
    assert len(repo.snapshot().inventory) == len(build_seed_state().inventory)


def test_archivo_corrupto_se_aparta_y_arranca_la_semilla(tmp_path) -> None:
    path = tmp_path / "store.json"
    path.write_text("{roto", encoding="utf-8")
    repo = AppStoreRepository(path)
    assert path.with_suffix(".json.corrupt").read_text(encoding="utf-8") == "{roto"
    assert len(repo.snapshot().profiles) == 3


def test_api_de_punta_a_punta(tmp_path) -> None:
    repo = AppStoreRepository(tmp_path / "store.json")
    app.dependency_overrides[get_store] = lambda: repo
    client = TestClient(app)
    try:
        assert client.post("/api/auth", json={"userId": "ales"}).json()["id"] == "ales"
        inventory = client.get("/api/inventory", params={"userId": "ales"}).json()
        assert inventory["totals"]["itemCount"] == 3

        new_item = inventory["items"][0] | {"id": "nuevo", "status": "listed"}
        assert client.post("/api/inventory", json=new_item).status_code == 200
        assert client.get("/api/inventory", params={"userId": "ales"}).json()["totals"]["itemCount"] == 4
        assert client.post("/api/inventory", json=new_item | {"priceMin": 9999}).status_code == 422
        assert client.delete("/api/inventory", params={"id": "nuevo"}).status_code == 204
        assert client.delete("/api/inventory", params={"id": "nuevo"}).status_code == 404

        valuation = client.post("/api/market/valuate", json={
            "query": "Nintendo Switch OLED", "category": "Consolas y Videojuegos",
            "conditionScore": 88, "conditionLabel": "Como nuevo",
        }).json()
        assert 0 < valuation["priceMin"] < valuation["priceAvg"] < valuation["priceMax"]

        assert client.post("/api/store/reset").status_code == 200
        assert client.get("/api/inventory", params={"userId": "ales"}).json()["totals"]["itemCount"] == 3
    finally:
        app.dependency_overrides.clear()
