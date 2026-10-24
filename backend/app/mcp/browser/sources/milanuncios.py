"""Milanuncios browser source with PerimeterX / captcha detection."""

from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.mcp.browser.sources.base import BaseBrowserSource, page_payload_script
from app.mcp.normalize import parse_price_eur, squeeze
from app.models.sdd import MarketListingSample, MarketPlatform

MILANUNCIOS_ITEMS_SCRIPT = """
  const items = [];
  const seen = new Set();
  const cards = Array.from(document.querySelectorAll(
    "article[data-testid='AD_CARD'], article"
  ));
  for (const card of cards) {
    const titleEl = card.querySelector(
      '.ma-AdCardListingV2-TitleLink, h2, .mt-SerpCard-title'
    );
    const priceEl = card.querySelector(
      '.ma-AdPrice-value, .mt-SerpCard-prices, .mt-SerpCard-prices-price'
    );
    if (!titleEl || !priceEl) continue;
    const linkEl = titleEl.tagName === 'A' ? titleEl : card.querySelector('a[href]');
    const url = linkEl ? linkEl.href : null;
    if (!url || seen.has(url)) continue;
    seen.add(url);
    items.push({
      title: (titleEl.textContent || '').trim(),
      price: (priceEl.textContent || '').trim(),
      url,
      condition: '',
    });
  }
"""


class MilanunciosSource(BaseBrowserSource):
    platform: MarketPlatform = "milanuncios"
    base_url = "https://www.milanuncios.com"
    blocked_markers = (
        "pardon our interruption",
        "captcha",
        "access denied",
        "perimeterx",
        "px-captcha",
        "please verify you are a human",
        "unusual traffic",
    )
    render_wait_ms = 1_200

    def search_url(self, query: str) -> str:
        return f"{self.base_url}/anuncios/?s={quote_plus(query)}"

    def extract_script(self) -> str:
        return page_payload_script(MILANUNCIOS_ITEMS_SCRIPT)

    def parse_html(self, html: str) -> list[MarketListingSample]:
        soup = BeautifulSoup(html, "lxml")
        raw_items: list[dict[str, object]] = []
        seen: set[str] = set()
        for card in soup.select("article[data-testid='AD_CARD'], article"):
            title_el = card.select_one(
                ".ma-AdCardListingV2-TitleLink, h2, .mt-SerpCard-title"
            )
            price_el = card.select_one(
                ".ma-AdPrice-value, .mt-SerpCard-prices, .mt-SerpCard-prices-price"
            )
            if title_el is None or price_el is None:
                continue
            link_el = card.select_one("a[href]")
            href = link_el.get("href") if link_el is not None else None
            if not isinstance(href, str) or href in seen:
                continue
            seen.add(href)
            raw_items.append(
                {
                    "title": squeeze(title_el.get_text(" ", strip=True)),
                    "price": squeeze(price_el.get_text(" ", strip=True)),
                    "url": href,
                }
            )
        return self.parse_items(raw_items)

    def block_reason(self, text: str, title: str = "") -> str | None:
        """Return the matched marker (safe for logs) or ``None``."""
        haystack = f"{title}\n{text}".casefold()
        for marker in self.blocked_markers:
            if marker in haystack:
                return marker
        return None


def looks_like_perimeterx(html: str) -> bool:
    """Fixture helper: the same markers the browser path checks on visible text."""
    haystack = html.casefold()
    return any(
        marker in haystack
        for marker in ("pardon our interruption", "px-captcha", "access denied", "captcha")
    )


def milanuncios_price(text: str) -> int | None:
    return parse_price_eur(text)
