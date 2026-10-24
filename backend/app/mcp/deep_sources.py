"""Per-source browser collection for the deep analysis engine.

Isolates failure handling: a blocked source, a timeout or a crashed page never
aborts the other sources; only a missing browser is fatal (`None` result).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from time import monotonic

from app.config import Settings
from app.mcp.browser.session import BrowserSessionManager, BrowserUnavailableError
from app.mcp.browser.sources.base import BrowserSourceProtocol
from app.mcp.normalize import (
    build_platform_search_url,
    dedupe_listings,
    filter_usable_listings,
)
from app.models.market_analysis import (
    MAX_SOURCE_LISTINGS,
    MarketSourceResult,
    MarketSourceStatus,
)
from app.models.sdd import MarketListingSample, MarketPlatform

logger = logging.getLogger(__name__)

SOURCE_NOT_IMPLEMENTED = "source_not_implemented"
FETCHED_STATUSES = frozenset({"blocked", "timeout", "error"})


class BrowserSourceRunner:
    """Runs every requested source sequentially on the single locked page."""

    def __init__(
        self,
        settings: Settings,
        browser: BrowserSessionManager,
        sources: Mapping[MarketPlatform, BrowserSourceProtocol],
    ) -> None:
        self._settings = settings
        self._browser = browser
        self._sources = dict(sources)

    async def run(
        self, platform: MarketPlatform, query: str, deadline: float
    ) -> tuple[MarketSourceResult, list[MarketListingSample]] | None:
        started = monotonic()
        source = self._sources.get(platform)
        if source is None:
            return (
                self._result(platform, "error", [], started, query, SOURCE_NOT_IMPLEMENTED),
                [],
            )
        remaining = deadline - started
        if remaining <= 0:
            return (
                self._result(platform, "timeout", [], started, query, "deadline_exceeded"),
                [],
            )
        timeout = min(self._settings.market_source_timeout_sec, remaining)
        try:
            async with self._browser.session() as page:
                outcome = await asyncio.wait_for(source.collect(page, query), timeout=timeout)
        except BrowserUnavailableError:
            return None
        except TimeoutError:
            return (
                self._result(platform, "timeout", [], started, query, "source_timeout"),
                [],
            )
        except Exception:
            logger.warning("deep source %s failed", platform, exc_info=True)
            return self._result(platform, "error", [], started, query, "source_error"), []

        usable = filter_usable_listings(
            dedupe_listings(outcome.listings),
            max_price_eur=self._settings.market_max_listing_price_eur,
        )
        if outcome.status in FETCHED_STATUSES:
            return (
                self._result(
                    platform,
                    outcome.status,
                    [],
                    started,
                    query,
                    outcome.error,
                    outcome.latency_ms,
                ),
                [],
            )
        status: MarketSourceStatus = "ok" if usable else "no_listings"
        return (
            self._result(
                platform, status, usable, started, query, outcome.error, outcome.latency_ms
            ),
            usable if status == "ok" else [],
        )

    def _result(
        self,
        platform: MarketPlatform,
        status: MarketSourceStatus,
        listings: Sequence[MarketListingSample],
        started: float,
        query: str,
        error: str | None = None,
        latency_ms: int | None = None,
    ) -> MarketSourceResult:
        prepared = [
            listing
            if listing.url
            else listing.model_copy(
                update={"url": build_platform_search_url(listing.platform, query)}
            )
            for listing in listings[:MAX_SOURCE_LISTINGS]
        ]
        return MarketSourceResult(
            source=platform,
            status=status,
            sample_size=len(listings),
            listings=prepared,
            latency_ms=(
                max(0, int((monotonic() - started) * 1000))
                if latency_ms is None
                else max(0, latency_ms)
            ),
            error=error,
        )
