"""`/api/market` routes: health probe and (next step) valuation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.sdd import MarketHealthResponse

router = APIRouter(prefix="/market", tags=["market"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=MarketHealthResponse, summary="Market engine health")
async def market_health(settings: SettingsDep) -> MarketHealthResponse:
    return MarketHealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        fallback_enabled=settings.market_allow_fallback,
        jitter_enabled=settings.market_jitter_max_sec > 0,
        timestamp=datetime.now(UTC).isoformat(),
    )
