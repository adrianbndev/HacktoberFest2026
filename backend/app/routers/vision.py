"""FastAPI Router for Vision AI Recognition (POST /api/vision/analyze)."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query

from app.models.sdd import VisionAnalysisResult, VisionAnalyzeRequest
from app.vision.ollama_provider import OllamaVisionProvider
from app.vision.orchestrator import ResilientVisionOrchestrator

router = APIRouter(prefix="/api/vision", tags=["vision"])
_orchestrator = ResilientVisionOrchestrator()


@router.post("/analyze", response_model=VisionAnalysisResult, response_model_by_alias=True)
async def analyze_product_image(payload: VisionAnalyzeRequest) -> VisionAnalysisResult:
    """Analyzes a captured product photo and returns structured fields for the user form."""
    try:
        return await _orchestrator.analyze_photo(
            photo_source=payload.photo_data_url,
            user_hint=payload.user_hint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {exc}") from exc


@router.get("/node-status")
async def get_vision_node_status(force: bool = Query(default=False)) -> dict[str, Any]:
    """Checks connectivity with Matías's Mac Ollama Vision node in the LAN."""
    provider = OllamaVisionProvider()
    status = await provider.check_node_health(force=force)
    status["activeProviders"] = _orchestrator.get_provider_ids()
    return status
