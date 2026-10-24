"""`/api/market` routes: health probe and fast valuation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.mcp.market_analysis import MarketAnalyzer, MarketUnavailableError
from app.models.sdd import MarketHealthResponse, MarketValuationResult, ValuationRequest

router = APIRouter(prefix="/market", tags=["market"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_market_analyzer(settings: SettingsDep) -> MarketAnalyzer:
    return MarketAnalyzer(settings)


AnalyzerDep = Annotated[MarketAnalyzer, Depends(get_market_analyzer)]


@router.get("/health", response_model=MarketHealthResponse, summary="Market engine health")
async def market_health(settings: SettingsDep) -> MarketHealthResponse:
    return MarketHealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        fallback_enabled=settings.market_allow_fallback,
        jitter_enabled=settings.market_jitter_max_sec > 0,
        recommendation_enabled=settings.deepseek_api_key is not None,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post(
    "/valuate",
    response_model=MarketValuationResult,
    response_model_exclude_none=True,
    summary="Fast market valuation (P_min, P_avg, P_max)",
    responses={503: {"description": "No live sources and fallback disabled"}},
)
async def valuate(
    request: ValuationRequest, analyzer: AnalyzerDep
) -> MarketValuationResult | JSONResponse:
    try:
        return await analyzer.valuate(request)
    except MarketUnavailableError as exc:
        return JSONResponse(
            status_code=503, content={"detail": exc.detail, "sources": exc.sources}
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Tasación no disponible temporalmente.",
                "sources": {},
            },
        )
