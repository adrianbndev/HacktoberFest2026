"""Sesión rápida, CRUD de inventario y reset de la demo (MOD-00 / MOD-01)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.domain import AuthRequest, AuthSession, InventoryItem, InventoryResponse, InventoryTotals, TeamMemberId
from app.models.domain import UserProfile
from app.store.repository import StoreRepository, get_store

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


@router.get("/auth", response_model=AuthSession)
def get_session(store: Store) -> AuthSession:
    state = store.snapshot()
    return AuthSession(active_user_id=state.active_user_id, profiles=list(state.profiles.values()))


@router.post("/auth", response_model=UserProfile)
def login(body: AuthRequest, store: Store) -> UserProfile:
    with store.transaction() as state:
        state.active_user_id = body.user_id
        return state.profiles[body.user_id]


@router.get("/inventory", response_model=InventoryResponse, response_model_exclude_none=True)
def list_inventory(user_id: Annotated[TeamMemberId, Query(alias="userId")], store: Store) -> InventoryResponse:
    state = store.snapshot()
    items = sorted((i for i in state.inventory if i.user_id == user_id), key=lambda i: i.created_at, reverse=True)
    return InventoryResponse(profile=state.profiles[user_id], items=items, totals=inventory_totals(items))


@router.post("/inventory", response_model=InventoryItem, response_model_exclude_none=True)
def save_item(item: InventoryItem, store: Store) -> InventoryItem:
    """Crea o reemplaza (mismo id) un artículo."""
    with store.transaction() as state:
        state.inventory = [existing for existing in state.inventory if existing.id != item.id] + [item]
    return item


@router.delete("/inventory", status_code=204)
def delete_item(item_id: Annotated[str, Query(alias="id")], store: Store) -> None:
    with store.transaction() as state:
        if not any(item.id == item_id for item in state.inventory):
            raise HTTPException(status_code=404, detail=f"No existe el artículo {item_id}")
        state.inventory = [item for item in state.inventory if item.id != item_id]


@router.post("/store/reset", response_model=AuthSession)
def reset_demo(store: Store) -> AuthSession:
    """Restaura los datos semilla antes de presentar al jurado."""
    state = store.reset_to_seed()
    return AuthSession(active_user_id=state.active_user_id, profiles=list(state.profiles.values()))
