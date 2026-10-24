"""Async stealth connectors for eBay, Wallapop and Milanuncios (MOD-04 §2.3).

Adapters are defensive by design: HTTP failures, anti-bot pages and parse
errors are reported as a failed ``ConnectorResult`` and never raised.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup, Tag

from app.mcp.normalize import (
    build_listing_sample,
    iter_json_listing_items,
    json_price_amount,
    parse_price_eur,
    squeeze,
)
from app.mcp.stealth_http import build_headers
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
SKIPPED_TITLES = frozenset({"shop on ebay"})


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    """Outcome of one platform query, including why it produced nothing."""

    platform: MarketPlatform
    listings: tuple[MarketListingSample, ...] = ()
    failure_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.failure_reason is None


class MarketConnectorProtocol(Protocol):
    platform: MarketPlatform

    async def search(self, query: str) -> ConnectorResult: ...


def _href(tag: Tag | None) -> str | None:
    value = tag.get("href") if tag is not None else None
    return value if isinstance(value, str) else None


def looks_blocked(html: str, status_code: int) -> bool:
    if status_code in BLOCK_STATUS_CODES:
        return True
    haystack = html.lower()
    return any(marker in haystack for marker in BLOCK_MARKERS)


class _HtmlConnector:
    """Shared fetch/parse pipeline; subclasses provide the site-specific parser."""

    platform: MarketPlatform = "ebay"
    base_url: str = ""
    search_template: str = ""

    def __init__(
        self, *, timeout_sec: float = 1.6, client: httpx.AsyncClient | None = None
    ) -> None:
        self._timeout_sec = timeout_sec
        self._client = client

    async def search(self, query: str) -> ConnectorResult:
        clean_query = squeeze(query)
        if len(clean_query) < 2:
            return ConnectorResult(self.platform, failure_reason="empty_query")
        try:
            status_code, html = await self._fetch(clean_query)
        except httpx.HTTPError:
            return ConnectorResult(self.platform, failure_reason="network_error")
        except Exception:
            return ConnectorResult(self.platform, failure_reason="unexpected_error")
        if looks_blocked(html, status_code):
            return ConnectorResult(self.platform, failure_reason=f"blocked_http_{status_code}")
        try:
            listings = tuple(self.parse(html))
        except Exception:
            return ConnectorResult(self.platform, failure_reason="parse_error")
        if not listings:
            return ConnectorResult(self.platform, failure_reason="no_listings_parsed")
        return ConnectorResult(self.platform, listings)

    async def _fetch(self, query: str) -> tuple[int, str]:
        url = self.search_template.format(query=quote_plus(query))
        headers = build_headers()
        if self._client is not None:
            response = await self._client.get(url, headers=headers)
            return response.status_code, response.text
        timeout = httpx.Timeout(self._timeout_sec)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            return response.status_code, response.text

    def parse(self, html: str) -> list[MarketListingSample]:
        raise NotImplementedError


class EbayConnector(_HtmlConnector):
    platform: MarketPlatform = "ebay"
    base_url = "https://www.ebay.es"
    search_template = "https://www.ebay.es/sch/i.html?_nkw={query}&_sacat=0"

    def parse(self, html: str) -> list[MarketListingSample]:
        soup = BeautifulSoup(html, "lxml")
        listings: list[MarketListingSample] = []
        for card in soup.select("li.s-item, li.s-card"):
            title_el = card.select_one(".s-item__title, .s-card__title")
            price_el = card.select_one(".s-item__price, .s-card__price")
            link_el = card.select_one("a.s-item__link, a.s-card__link, a[href*='/itm/']")
            if title_el is None or price_el is None:
                continue
            title = title_el.get_text(" ", strip=True)
            if title.lower() in SKIPPED_TITLES:
                continue
            sample = build_listing_sample(
                title=title,
                price=parse_price_eur(price_el.get_text(" ", strip=True)),
                platform=self.platform,
                href=_href(link_el),
                base_url=self.base_url,
            )
            if sample is not None:
                listings.append(sample)
        return listings


class WallapopConnector(_HtmlConnector):
    platform: MarketPlatform = "wallapop"
    base_url = "https://es.wallapop.com"
    search_template = "https://es.wallapop.com/app/search?keywords={query}&order_by=newest"

    def parse(self, html: str) -> list[MarketListingSample]:
        soup = BeautifulSoup(html, "lxml")
        listings = self._parse_next_data(soup)
        if listings:
            return listings
        for anchor in soup.select("a[href*='/item/']"):
            card = anchor.find_parent(["article", "div"]) or anchor
            sample = build_listing_sample(
                title=anchor.get_text(" ", strip=True),
                price=parse_price_eur(card.get_text(" ", strip=True)),
                platform=self.platform,
                href=_href(anchor),
                base_url=self.base_url,
            )
            if sample is not None:
                listings.append(sample)
        return listings

    def _parse_next_data(self, soup: BeautifulSoup) -> list[MarketListingSample]:
        script = soup.find("script", id="__NEXT_DATA__")
        if not isinstance(script, Tag) or not script.string:
            return []
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            return []
        listings: list[MarketListingSample] = []
        for item in iter_json_listing_items(payload):
            sample = build_listing_sample(
                title=str(item.get("title", "")),
                price=json_price_amount(item.get("price")),
                platform=self.platform,
                href=self._item_url(item),
                base_url=self.base_url,
                condition_hint=str(item.get("condition", "")),
            )
            if sample is not None:
                listings.append(sample)
        return listings

    def _item_url(self, item: dict[str, Any]) -> str | None:
        slug = item.get("web_slug") or item.get("slug")
        if isinstance(slug, str) and slug:
            return f"{self.base_url}/item/{slug}"
        item_id = item.get("id")
        return f"{self.base_url}/item/{item_id}" if isinstance(item_id, str) and item_id else None


class MilanunciosConnector(_HtmlConnector):
    platform: MarketPlatform = "milanuncios"
    base_url = "https://www.milanuncios.com"
    search_template = "https://www.milanuncios.com/anuncios/?s={query}"

    def parse(self, html: str) -> list[MarketListingSample]:
        soup = BeautifulSoup(html, "lxml")
        listings: list[MarketListingSample] = []
        cards = soup.select("article[data-testid='AD_CARD'], article")
        for card in cards:
            title_el = card.select_one(
                ".ma-AdCardListingV2-TitleLink, h2, .mt-SerpCard-title"
            )
            price_el = card.select_one(
                ".ma-AdPrice-value, .mt-SerpCard-prices, .mt-SerpCard-prices-price"
            )
            if title_el is None or price_el is None:
                continue
            link_el = (
                title_el
                if isinstance(title_el, Tag) and title_el.get("href")
                else card.select_one("a[href]")
            )
            sample = build_listing_sample(
                title=title_el.get_text(" ", strip=True),
                price=parse_price_eur(price_el.get_text(" ", strip=True)),
                platform=self.platform,
                href=_href(link_el) if isinstance(link_el, Tag) else None,
                base_url=self.base_url,
            )
            if sample is not None:
                listings.append(sample)
        return listings
