"""Server-Sent Events framing for the deep analysis stream (brief §5.2)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from typing import Any, Protocol

from app.mcp.analysis_events import (
    AnalysisDone,
    AnalysisFailed,
    AnalysisStarted,
    DeepAnalysisEvent,
    RecommendationReady,
    SourceFinished,
    SourceStarted,
    ValuationReady,
)
from app.models.market_analysis import MarketAnalysisRequest

logger = logging.getLogger(__name__)

HEARTBEAT_SEC = 15.0
FALLBACK_ERROR_DETAIL = "analysis_failed"


class AnalysisStreamer(Protocol):
    def stream(
        self, request: MarketAnalysisRequest
    ) -> AsyncIterator[DeepAnalysisEvent]: ...


OnDisconnect = Callable[[], Awaitable[None]]


async def stream_analysis(
    analyzer: AnalysisStreamer,
    request: MarketAnalysisRequest,
    *,
    heartbeat_sec: float = HEARTBEAT_SEC,
    on_disconnect: OnDisconnect | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames; heartbeat while a source is slow; cancel on disconnect.

    `on_disconnect` (the router passes `browser.stop`) closes the page and the
    MCP process only when the stream did not finish normally.
    """
    queue: asyncio.Queue[DeepAnalysisEvent | None] = asyncio.Queue()

    async def produce() -> None:
        try:
            async for event in analyzer.stream(request):
                await queue.put(event)
        except Exception:
            logger.warning("analysis stream failed", exc_info=True)
            await queue.put(AnalysisFailed(FALLBACK_ERROR_DETAIL, {}))
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(produce())
    completed = False
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_sec)
            except TimeoutError:
                yield ": ping\n\n"
                continue
            if event is None:
                completed = True
                break
            yield serialize_event(event)
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        if not completed and on_disconnect is not None:
            with suppress(Exception):
                await on_disconnect()


def serialize_event(event: DeepAnalysisEvent) -> str:
    """Wire format `event: <name>\\ndata: <json>\\n\\n`."""
    name, payload = _event_name_and_payload(event)
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _event_name_and_payload(event: DeepAnalysisEvent) -> tuple[str, dict[str, Any]]:
    if isinstance(event, AnalysisStarted):
        return (
            "analysis_started",
            {"query": event.query, "sources": list(event.sources), "cached": event.cached},
        )
    if isinstance(event, SourceStarted):
        return "source_started", {"source": event.source}
    if isinstance(event, SourceFinished):
        return "source_result", event.result.model_dump(by_alias=True, exclude_none=True)
    if isinstance(event, ValuationReady):
        return "valuation", event.valuation.model_dump(by_alias=True)
    if isinstance(event, RecommendationReady):
        return "recommendation", event.recommendation.model_dump(by_alias=True)
    if isinstance(event, AnalysisDone):
        return "done", event.result.model_dump(by_alias=True, exclude_none=True)
    payload: dict[str, Any] = {"detail": event.detail}
    if event.sources:
        payload["sources"] = event.sources
    return "error", payload
