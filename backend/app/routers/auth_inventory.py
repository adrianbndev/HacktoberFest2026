"""Perfil del usuario de Firebase, CRUD de su inventario y reset de la demo (MOD-00 / MOD-01)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import CurrentUser
from app.models.domain import InventoryItem, InventoryResponse, InventoryTotals, UserProfile
from app.store.repository import StoreRepository, get_store
from app.store.seed_data import demo_items, new_profile

router = APIRouter()
Store = Annotated[StoreRepository, Depends(get_store)]


def inventory_totals(items: list[InventoryItem]) -> InventoryTotals:
    """Valoración acumulada de lo que aún tienes (los artículos vendidos no cuentan)."""
    owned = [item for item in items if item.status != "sold"]
    return InventoryTotals(
        total_min=sum(item.price_min for item in owned), total_avg=sum(item.price_avg for item in owned),
        total_max=sum(item.price_max for item in owned),
        daily_gain_eur=sum(item.price_delta_eur for item in owned if item.price_delta_eur > 0),
        item_count=len(owned),
    )


@router.post("/auth", response_model=UserProfile, response_model_exclude_none=True)
def login(user: CurrentUser, store: Store) -> UserProfile:
    """Primer acceso: crea el perfil desde la cuenta de Google y le carga 3 productos de demo."""
    profile = store.get_profile(user.uid)
    if profile is None:
        profile = new_profile(user.uid, user.name, user.email, user.picture)
        store.save_profile(profile)
        store.replace_items(user.uid, demo_items(user.uid, profile.city))
    return profile


@router.get("/inventory", response_model=InventoryResponse, response_model_exclude_none=True)
def list_inventory(user: CurrentUser, store: Store) -> InventoryResponse:
    profile = store.get_profile(user.uid)
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado: llama antes a POST /api/auth")
    items = sorted(store.list_items(user.uid), key=lambda item: item.created_at, reverse=True)
    return InventoryResponse(profile=profile, items=items, totals=inventory_totals(items))


@router.post("/inventory", response_model=InventoryItem, response_model_exclude_none=True)
def save_item(item: InventoryItem, user: CurrentUser, store: Store) -> InventoryItem:
    """Crea o reemplaza (mismo id) un artículo; siempre queda a nombre del usuario de la sesión."""
    owned_item = item.model_copy(update={"user_id": user.uid})
    store.save_item(owned_item)
    return owned_item


@router.delete("/inventory", status_code=204)
def delete_item(item_id: Annotated[str, Query(alias="id")], user: CurrentUser, store: Store) -> None:
    if not store.delete_item(user.uid, item_id):
        raise HTTPException(status_code=404, detail=f"No existe el artículo {item_id}")


@router.post("/store/reset", response_model=InventoryResponse, response_model_exclude_none=True)
def reset_demo(user: CurrentUser, store: Store) -> InventoryResponse:
    """Restaura los 3 productos de demo del usuario antes de presentar al jurado."""
    profile = login(user, store)
    store.replace_items(user.uid, demo_items(user.uid, profile.city))
    return list_inventory(user, store)
