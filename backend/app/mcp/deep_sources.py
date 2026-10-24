"""Per-source collection for the deep analysis engine (Phase 3 hybrid).

eBay and Wallapop use one browser pool slot each. Milanuncios tries the fast
HTTP connector first and falls back to the browser source when HTTP is blocked,
empty or yields fewer than 8 usable listings. A source failure never aborts the
other sources; only a missing browser is fatal (`None`).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from time import monotonic

from app.config import Settings
from app.mcp.analysis_query import build_platform_search_url
from app.mcp.browser.pool import BrowserSessionPool
from app.mcp.browser.session import BrowserUnavailableError
from app.mcp.browser.sources.base import BrowserSourceProtocol, SourceOutcome
from app.mcp.browser.sources.ebay import EbaySource
from app.mcp.browser.sources.milanuncios import MilanunciosSource
from app.mcp.browser.sources.wallapop import WallapopSource
from app.mcp.deep_milanuncios import MilanunciosHybridRunner
from app.mcp.normalize import dedupe_listings, filter_usable_listings
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
    """Runs one source on a pool slot or through the hybrid Milanuncios runner."""

    def __init__(
        self,
        settings: Settings,
        browser: BrowserSessionPool,
        sources: Mapping[MarketPlatform, BrowserSourceProtocol],
        *,
        milanuncios: MilanunciosHybridRunner | None = None,
    ) -> None:
        self._settings = settings
        self._browser = browser
        self._sources = dict(sources)
        self._milanuncios = milanuncios or MilanunciosHybridRunner(
            settings, browser, browser_source=self._sources.get("milanuncios")
        )

    async def run(
        self, platform: MarketPlatform, query: str, deadline: float
    ) -> tuple[MarketSourceResult, list[MarketListingSample]] | None:
        started = monotonic()
        outcome: SourceOutcome | None
        if platform == "milanuncios":
            try:
                outcome = await self._milanuncios.collect(query, deadline)
            except BrowserUnavailableError:
                return None
        else:
            outcome = await self._browser_outcome(platform, query, deadline)
        if outcome is None:
            return None

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
                platform,
                status,
                usable,
                started,
                query,
                outcome.error,
                outcome.latency_ms,
            ),
            usable if status == "ok" else [],
        )

    async def _browser_outcome(
        self, platform: MarketPlatform, query: str, deadline: float
    ) -> SourceOutcome | None:
        started = monotonic()
        source = self._sources.get(platform)
        if source is None:
            return SourceOutcome(
                source=platform,
                status="error",
                listings=(),
                latency_ms=0,
                error=SOURCE_NOT_IMPLEMENTED,
            )
        remaining = deadline - started
        if remaining <= 0:
            return SourceOutcome(
                source=platform,
                status="timeout",
                listings=(),
                latency_ms=0,
                error="deadline_exceeded",
            )
        timeout = min(self._settings.market_source_timeout_sec, remaining)
        try:
            async with self._browser.session() as page:
                return await asyncio.wait_for(
                    source.collect(page, query), timeout=timeout
                )
        except BrowserUnavailableError:
            return None
        except TimeoutError:
            return SourceOutcome(
                source=platform,
                status="timeout",
                listings=(),
                latency_ms=max(0, int((monotonic() - started) * 1000)),
                error="source_timeout",
            )
        except Exception:
            logger.warning("deep source %s failed", platform, exc_info=True)
            return SourceOutcome(
                source=platform,
                status="error",
                listings=(),
                latency_ms=max(0, int((monotonic() - started) * 1000)),
                error="source_error",
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


def default_sources(settings: Settings) -> dict[MarketPlatform, BrowserSourceProtocol]:
    return {
        "ebay": EbaySource(),
        "wallapop": WallapopSource(),
        "milanuncios": MilanunciosSource(
            max_pages=settings.market_milanuncios_max_pages
        ),
    }
