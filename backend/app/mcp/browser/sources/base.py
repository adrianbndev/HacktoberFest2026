"""Shared browser-source behaviour: URL, render wait, extraction and statuses.

Each source owns two things: a JavaScript extractor that runs inside the real
page, and a pure `parse_html`/`parse_items` pipeline used by fixture tests. The
browser path never solves captchas: an anti-bot page is reported as `blocked`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from time import monotonic
from typing import Any

from app.mcp.browser.session import BrowserPage
from app.mcp.normalize import (
    build_listing_sample,
    dedupe_listings,
    json_price_amount,
    squeeze,
)
from app.models.market_analysis import MarketSourceStatus
from app.models.sdd import MarketListingSample, MarketPlatform

EBAY_ACCESSIBILITY_SUFFIX = "se abre en una nueva ventana o pestaña"
SKIPPED_TITLES = frozenset({"shop on ebay"})
BLOCKED_ERROR = "blocked_or_antibot_page"
PAYLOAD_ERROR = "unexpected_payload"


@dataclass(frozen=True, slots=True)
class SourceOutcome:
    """One source's contribution to a deep analysis."""

    source: MarketPlatform
    status: MarketSourceStatus
    listings: tuple[MarketListingSample, ...]
    latency_ms: int
    error: str | None = None


class BaseBrowserSource:
    """Template method: navigate -> wait -> scroll -> extract -> normalise."""

    platform: MarketPlatform = "ebay"
    base_url: str = ""
    blocked_markers: tuple[str, ...] = ()
    render_wait_ms = 1_200
    scroll_steps = 0
    scroll_pause_ms = 350
    min_results = 0

    def search_urls(self, query: str) -> tuple[str, ...]:
        return (self.search_url(query),)

    def search_url(self, query: str) -> str:
        raise NotImplementedError

    def extract_script(self) -> str:
        raise NotImplementedError

    def parse_html(self, html: str) -> list[MarketListingSample]:
        raise NotImplementedError

    def parse_items(self, raw_items: Sequence[Any]) -> list[MarketListingSample]:
        samples: list[MarketListingSample] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            title = self.clean_title(str(raw.get("title") or ""))
            if not title or title.casefold() in SKIPPED_TITLES:
                continue
            sample = build_listing_sample(
                title=title,
                price=json_price_amount(raw.get("price")),
                platform=self.platform,
                href=_optional_str(raw.get("url")),
                base_url=self.base_url,
                condition_hint=_optional_str(raw.get("condition")),
            )
            if sample is not None:
                samples.append(sample)
        return samples

    def clean_title(self, title: str) -> str:
        cleaned = squeeze(title)
        lowered = cleaned.casefold()
        index = lowered.find(EBAY_ACCESSIBILITY_SUFFIX)
        if index != -1:
            cleaned = squeeze(cleaned[:index])
        return cleaned.strip(" |-–—")

    def is_blocked(self, text: str, title: str = "") -> bool:
        haystack = f"{title}\n{text}".casefold()
        return any(marker in haystack for marker in self.blocked_markers)

    async def collect(self, page: BrowserPage, query: str) -> SourceOutcome:
        started = monotonic()
        listings: list[MarketListingSample] = []
        for url in self.search_urls(query):
            if listings and len(listings) >= self.min_results:
                break
            await page.navigate(url)
            await self._render(page)
            payload = await page.evaluate(self.extract_script())
            outcome = self._outcome_from_payload(started, payload, listings)
            if outcome is not None:
                if outcome.status == "blocked" and listings:
                    break
                return outcome
            listings.extend(self._payload_listings(payload))
        deduped = dedupe_listings(listings)
        status: MarketSourceStatus = "ok" if deduped else "no_listings"
        return self._outcome(started, status, deduped)

    async def _render(self, page: BrowserPage) -> None:
        await page.evaluate(_wait_function(self.render_wait_ms))
        if self.scroll_steps > 0:
            await page.scroll(steps=self.scroll_steps, pause_ms=self.scroll_pause_ms)

    def _outcome_from_payload(
        self,
        started: float,
        payload: Any,
        already_collected: Sequence[MarketListingSample],
    ) -> SourceOutcome | None:
        if not isinstance(payload, dict):
            return self._outcome(
                started, "error", list(already_collected), error=PAYLOAD_ERROR
            )
        text = str(payload.get("text") or "")
        title = str(payload.get("title") or "")
        if self.is_blocked(text, title):
            return self._outcome(
                started, "blocked", list(already_collected), error=BLOCKED_ERROR
            )
        return None

    def _payload_listings(self, payload: Any) -> list[MarketListingSample]:
        if not isinstance(payload, dict):
            return []
        items = payload.get("items")
        return self.parse_items(items) if isinstance(items, list) else []

    def _outcome(
        self,
        started: float,
        status: MarketSourceStatus,
        listings: Sequence[MarketListingSample],
        *,
        error: str | None = None,
    ) -> SourceOutcome:
        return SourceOutcome(
            source=self.platform,
            status=status,
            listings=tuple(listings),
            latency_ms=max(0, int((monotonic() - started) * 1000)),
            error=error,
        )


def _wait_function(milliseconds: int) -> str:
    return (
        "async () => { await new Promise((resolve) => "
        f"setTimeout(resolve, {max(0, milliseconds)})); return true; }}"
    )


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def page_payload_script(items_script: str) -> str:
    """Wrap a DOM item extractor with the visible text/title used for blocking."""
    return (
        "() => {\n"
        f"{items_script}\n"
        "  return {\n"
        "    items,\n"
        "    title: document.title || '',\n"
        "    text: (document.body ? document.body.innerText : '').slice(0, 20000),\n"
        "  };\n"
        "}"
    )


__all__ = [
    "BLOCKED_ERROR",
    "PAYLOAD_ERROR",
    "BaseBrowserSource",
    "SourceOutcome",
    "page_payload_script",
]
