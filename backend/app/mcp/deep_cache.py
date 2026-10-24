"""Cache read/write helpers for `MarketAnalysisResult` payloads."""

from __future__ import annotations

import logging

from app.mcp.cache import MarketAnalysisCache
from app.models.market_analysis import MarketAnalysisResult

logger = logging.getLogger(__name__)


async def read_cached(
    cache: MarketAnalysisCache, key: str
) -> MarketAnalysisResult | None:
    """Return a real previous result with `cached=true`, or `None` on any miss."""
    try:
        record = await cache.get(key)
    except Exception:
        logger.warning("market cache read failed", exc_info=True)
        return None
    if record is None:
        return None
    try:
        cached = MarketAnalysisResult.model_validate_json(record.payload)
    except ValueError:
        logger.warning("market cache payload is invalid; ignoring it")
        return None
    return cached.model_copy(update={"cached": True})


async def write_cached(
    cache: MarketAnalysisCache, key: str, result: MarketAnalysisResult
) -> None:
    """Persist a real result; a cache failure never fails the analysis."""
    try:
        await cache.set(
            key,
            result.model_dump_json(by_alias=True, exclude_none=True),
            analyzed_at=result.analyzed_at,
        )
    except Exception:
        logger.warning("market cache write failed", exc_info=True)
