"""Wallapop browser source: the search page is a JS shell, the DOM is the API."""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.mcp.browser.sources.base import BaseBrowserSource, page_payload_script
from app.mcp.normalize import parse_price_eur, squeeze
from app.models.sdd import MarketListingSample, MarketPlatform

WALLAPOP_ITEMS_SCRIPT = """
  const items = [];
  const seen = new Set();
  const anchors = Array.from(document.querySelectorAll("a[href*='/item/']"));
  for (const anchor of anchors) {
    const url = anchor.href;
    if (!url || seen.has(url)) continue;
    const card = anchor.closest('article') || anchor.closest('[data-testid]')
      || anchor.parentElement || anchor;
    const text = (card.innerText || '').trim();
    const priceMatch = text.match(/\\d[\\d.,]*\\s*€/);
    const title = ((anchor.getAttribute('aria-label') || anchor.innerText || '')
      .trim().split('\\n')[0]);
    if (!title || !priceMatch) continue;
    seen.add(url);
    items.push({title, price: priceMatch[0], url, condition: ''});
  }
"""

TRAILING_PRICE = re.compile(r"\s*[-–|,]?\s*\d[\d.,]*\s*€\s*$")


class WallapopSource(BaseBrowserSource):
    platform: MarketPlatform = "wallapop"
    base_url = "https://es.wallapop.com"
    blocked_markers = (
        "captcha",
        "access denied",
        "unusual traffic",
        "just a moment",
        "cf-chl",
        "verifying you are human",
    )
    render_wait_ms = 1_500
    scroll_steps = 4
    scroll_pause_ms = 300

    def search_url(self, query: str) -> str:
        encoded = quote_plus(query)
        return f"{self.base_url}/app/search?keywords={encoded}&order_by=newest"

    def extract_script(self) -> str:
        return page_payload_script(WALLAPOP_ITEMS_SCRIPT)

    def clean_title(self, title: str) -> str:
        cleaned = super().clean_title(title)
        return TRAILING_PRICE.sub("", cleaned).strip()

    def parse_html(self, html: str) -> list[MarketListingSample]:
        soup = BeautifulSoup(html, "lxml")
        raw_items: list[dict[str, object]] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href*='/item/']"):
            href = anchor.get("href")
            if not isinstance(href, str) or href in seen:
                continue
            card = anchor.find_parent("article") or anchor.parent
            text = card.get_text(" ", strip=True) if card is not None else ""
            title = anchor.get("aria-label") or anchor.get_text(" ", strip=True)
            if parse_price_eur(text) is None:
                continue
            seen.add(href)
            raw_items.append({"title": squeeze(str(title)), "price": text, "url": href})
        return self.parse_items(raw_items)
