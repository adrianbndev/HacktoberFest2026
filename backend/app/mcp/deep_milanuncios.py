"""Hybrid Milanuncios transport: fast HTTP first, real browser fallback.

The HTTP connector is fast but the venue network sometimes serves an anti-bot
page. A blocked/empty/short HTTP result falls back to the browser source on a
free pool slot. No synthetic data is ever produced.
"""

from __future__ import annotations

import asyncio
import logging
from time import monotonic

from app.config import Settings
from app.mcp.browser.pool import BrowserSessionPool
from app.mcp.browser.session import BrowserUnavailableError
from app.mcp.browser.sources.base import BrowserSourceProtocol, SourceOutcome
from app.mcp.browser.sources.milanuncios import MilanunciosSource
from app.mcp.connectors import (
    ConnectorResult,
    MarketConnectorProtocol,
    MilanunciosConnector,
)
from app.mcp.normalize import dedupe_listings, filter_usable_listings
from app.models.market_analysis import MarketSourceStatus
from app.models.sdd import MarketListingSample

logger = logging.getLogger(__name__)

MIN_USABLE_LISTINGS = 8
BLOCKED_PREFIX = "blocked_http_"
HTTP_NO_LISTINGS = "no_listings_parsed"


class MilanunciosHybridRunner:
    """Collect Milanuncios over HTTP and optionally recover with the browser."""

    def __init__(
        self,
        settings: Settings,
        browser: BrowserSessionPool,
        *,
        browser_source: BrowserSourceProtocol | None = None,
        http_connector: MarketConnectorProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._browser = browser
        self._transport = settings.market_milanuncios_transport
        self._browser_source: BrowserSourceProtocol = browser_source or MilanunciosSource(
            max_pages=settings.market_milanuncios_max_pages
        )
        self._http: MarketConnectorProtocol = http_connector or MilanunciosConnector(
            timeout_sec=settings.market_connector_timeout_sec,
            max_pages=settings.market_milanuncios_max_pages,
            page_delay_min_sec=settings.market_milanuncios_page_delay_min_sec,
            page_delay_max_sec=settings.market_milanuncios_page_delay_max_sec,
        )

    async def collect(self, query: str, deadline: float) -> SourceOutcome:
        if self._transport == "browser":
            return await self._collect_browser(query, deadline)
        http_outcome = await self._collect_http(query, deadline)
        if self._transport == "http" or self._has_enough(http_outcome):
            return http_outcome
        browser_outcome = await self._collect_browser(query, deadline)
        return self._prefer(http_outcome, browser_outcome)

    async def _collect_http(self, query: str, deadline: float) -> SourceOutcome:
        started = monotonic()
        remaining = deadline - started
        if remaining <= 0:
            return self._outcome("timeout", (), started, "deadline_exceeded")
        timeout = min(self._settings.market_source_timeout_sec, remaining)
        try:
            result = await asyncio.wait_for(self._http.search(query), timeout=timeout)
        except TimeoutError:
            return self._outcome("timeout", (), started, "source_timeout")
        except Exception:
            logger.warning("milanuncios HTTP failed", exc_info=True)
            return self._outcome("error", (), started, "http_error")
        return self._from_connector(result, started)

    def _from_connector(self, result: ConnectorResult, started: float) -> SourceOutcome:
        if result.ok:
            return self._outcome("ok", result.listings, started)
        reason = result.failure_reason or "http_error"
        status: MarketSourceStatus
        if reason.startswith(BLOCKED_PREFIX):
            status = "blocked"
        elif reason == HTTP_NO_LISTINGS:
            status = "no_listings"
        elif reason == "timeout":
            status = "timeout"
        else:
            status = "error"
        return self._outcome(status, (), started, reason)

    async def _collect_browser(self, query: str, deadline: float) -> SourceOutcome:
        started = monotonic()
        remaining = deadline - started
        if remaining <= 0:
            return self._outcome("timeout", (), started, "deadline_exceeded")
        try:
            async with self._browser.session() as page:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return self._outcome("timeout", (), started, "deadline_exceeded")
                timeout = min(self._settings.market_source_timeout_sec, remaining)
                return await asyncio.wait_for(
                    self._browser_source.collect(page, query), timeout=timeout
                )
        except BrowserUnavailableError:
            return self._outcome("error", (), started, "browser_unavailable")
        except TimeoutError:
            return self._outcome("timeout", (), started, "source_timeout")
        except Exception:
            logger.warning("milanuncios browser fallback failed", exc_info=True)
            return self._outcome("error", (), started, "source_error")

    def _has_enough(self, outcome: SourceOutcome) -> bool:
        return outcome.status == "ok" and self._usable_count(outcome) >= MIN_USABLE_LISTINGS

    def _prefer(
        self, http_outcome: SourceOutcome, browser_outcome: SourceOutcome
    ) -> SourceOutcome:
        if http_outcome.status == "ok" and (
            browser_outcome.status != "ok"
            or self._usable_count(http_outcome) >= self._usable_count(browser_outcome)
        ):
            return http_outcome
        return browser_outcome

    def _usable_count(self, outcome: SourceOutcome) -> int:
        return len(
            filter_usable_listings(
                dedupe_listings(outcome.listings),
                max_price_eur=self._settings.market_max_listing_price_eur,
            )
        )

    def _outcome(
        self,
        status: MarketSourceStatus,
        listings: tuple[MarketListingSample, ...],
        started: float,
        error: str | None = None,
    ) -> SourceOutcome:
        return SourceOutcome(
            source="milanuncios",
            status=status,
            listings=tuple(listings),
            latency_ms=max(0, int((monotonic() - started) * 1000)),
            error=error,
        )
