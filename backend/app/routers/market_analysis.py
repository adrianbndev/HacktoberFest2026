"""`/api/market/analyze` and `/api/market/analyze/stream` (Phase 2, additive)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import Settings, get_settings
from app.mcp.analysis_events import DeepAnalysisUnavailableError
from app.mcp.deep_analysis import DeepMarketAnalyzer, shared_analyzer
from app.mcp.sse import stream_analysis
from app.models.market_analysis import MarketAnalysisRequest, MarketAnalysisResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])

SettingsDep = Annotated[Settings, Depends(get_settings)]
FAILED_DETAIL = "analysis_failed"


def get_deep_analyzer(settings: SettingsDep) -> DeepMarketAnalyzer:
    return shared_analyzer(settings)


DeepAnalyzerDep = Annotated[DeepMarketAnalyzer, Depends(get_deep_analyzer)]


@router.post(
    "/analyze",
    response_model=MarketAnalysisResult,
    response_model_exclude_none=True,
    summary="Deep browser-backed market analysis",
    responses={503: {"description": "No usable real data or browser unavailable"}},
)
async def analyze(
    request: MarketAnalysisRequest, analyzer: DeepAnalyzerDep
) -> MarketAnalysisResult | JSONResponse:
    try:
        return await analyzer.analyze(request)
    except DeepAnalysisUnavailableError as exc:
        return JSONResponse(
            status_code=503, content={"detail": exc.detail, "sources": exc.sources}
        )
    except Exception:
        logger.warning("deep analysis failed", exc_info=True)
        return JSONResponse(
            status_code=503, content={"detail": FAILED_DETAIL, "sources": {}}
        )


@router.post(
    "/analyze/stream",
    summary="Deep market analysis as Server-Sent Events",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def analyze_stream(
    request: MarketAnalysisRequest, analyzer: DeepAnalyzerDep
) -> StreamingResponse:
    return StreamingResponse(
        stream_analysis(analyzer, request, on_disconnect=analyzer.browser.stop),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
