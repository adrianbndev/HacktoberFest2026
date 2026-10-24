"""Shared HTTP pipeline for the stealth HTML connectors (MOD-04 §2.3).

Subclasses only implement the site-specific parser. The base class keeps one
persistent client per search (so cookies survive between pages), applies a
bounded inter-page jitter and turns a later-page block into a real partial
result when earlier pages already produced listings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote_plus

import httpx

from app.mcp.normalize import squeeze
from app.mcp.stealth_http import build_headers, human_jitter
from app.models.sdd import MarketListingSample, MarketPlatform

BLOCK_STATUS_CODES = frozenset({403, 429})
BLOCK_MARKERS = (
    "captcha",
    "datadome",
    "cf-chl",
    "access denied",
    "unusual traffic",
    "just a moment",
    "robot check",
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    """Outcome of one platform query, including why it produced nothing."""

    platform: MarketPlatform
    listings: tuple[MarketListingSample, ...] = ()
    failure_reason: str | None = None
    # True when a later page blocked but earlier pages already had real listings.
    partial: bool = False

    @property
    def ok(self) -> bool:
        return self.failure_reason is None


class MarketConnectorProtocol(Protocol):
    platform: MarketPlatform

    async def search(self, query: str) -> ConnectorResult: ...


def looks_blocked(html: str, status_code: int) -> bool:
    if status_code in BLOCK_STATUS_CODES:
        return True
    haystack = html.lower()
    return any(marker in haystack for marker in BLOCK_MARKERS)


class HtmlConnector:
    """Shared fetch/parse pipeline; subclasses provide the site-specific parser."""

    platform: MarketPlatform = "ebay"
    base_url: str = ""
    search_template: str = ""
    page_template: str | None = None

    def __init__(
        self,
        *,
        timeout_sec: float = 1.6,
        client: httpx.AsyncClient | None = None,
        max_pages: int = 1,
        page_delay_min_sec: float = 0.25,
        page_delay_max_sec: float = 0.75,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        if page_delay_min_sec < 0 or page_delay_max_sec < page_delay_min_sec:
            raise ValueError("page delay bounds must satisfy 0 <= min <= max")
        self._timeout_sec = timeout_sec
        self._client = client
        self._max_pages = max_pages
        self._page_delay_min_sec = page_delay_min_sec
        self._page_delay_max_sec = page_delay_max_sec

    async def search(self, query: str) -> ConnectorResult:
        clean_query = squeeze(query)
        if len(clean_query) < 2:
            return ConnectorResult(self.platform, failure_reason="empty_query")
        client = self._client if self._client is not None else self._make_client()
        owns_client = self._client is None
        headers = build_headers()
        try:
            listings: list[MarketListingSample] = []
            for page in range(1, self._max_pages + 1):
                if page > 1:
                    await human_jitter(
                        self._page_delay_min_sec, self._page_delay_max_sec
                    )
                try:
                    status_code, html = await self._fetch(
                        client, clean_query, page, headers
                    )
                except httpx.HTTPError:
                    return ConnectorResult(self.platform, failure_reason="network_error")
                except Exception:
                    return ConnectorResult(
                        self.platform, failure_reason="unexpected_error"
                    )
                if looks_blocked(html, status_code):
                    reason = f"blocked_http_{status_code}"
                    logger.warning(
                        "%s page %d blocked (%s) after %d listings",
                        self.platform,
                        page,
                        reason,
                        len(listings),
                    )
                    if listings:
                        return ConnectorResult(
                            self.platform, tuple(listings), partial=True
                        )
                    return ConnectorResult(self.platform, failure_reason=reason)
                try:
                    listings.extend(self.parse(html))
                except Exception:
                    return ConnectorResult(self.platform, failure_reason="parse_error")
            if not listings:
                return ConnectorResult(
                    self.platform, failure_reason="no_listings_parsed"
                )
            return ConnectorResult(self.platform, tuple(listings))
        finally:
            if owns_client:
                await client.aclose()

    def _make_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(self._timeout_sec)
        return httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    def _url_for(self, query: str, page: int) -> str:
        if page <= 1:
            return self.search_template.format(query=quote_plus(query))
        template = self.page_template
        if template is None:
            raise ValueError("page_template is required for multi-page connectors")
        return template.format(query=quote_plus(query), page=page)

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        query: str,
        page: int,
        headers: dict[str, str],
    ) -> tuple[int, str]:
        request_headers = dict(headers)
        if page > 1:
            request_headers["Referer"] = self._url_for(query, page - 1)
            if self.base_url:
                request_headers["Origin"] = self.base_url
        response = await client.get(self._url_for(query, page), headers=request_headers)
        return response.status_code, response.text

    def parse(self, html: str) -> list[MarketListingSample]:
        raise NotImplementedError
