"""eBay.es browser source (buy-it-now, used condition, 60 items per page)."""

from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.mcp.browser.sources.base import BaseBrowserSource, page_payload_script
from app.models.sdd import MarketListingSample, MarketPlatform

EBAY_ITEMS_SCRIPT = """
  const items = [];
  const cards = Array.from(document.querySelectorAll('li.s-item, li.s-card'));
  for (const card of cards) {
    const titleEl = card.querySelector('.s-item__title, .s-card__title');
    const priceEl = card.querySelector('.s-item__price, .s-card__price');
    if (!titleEl || !priceEl) continue;
    const linkEl = card.querySelector('a.s-item__link, a.s-card__link, a[href*="/itm/"]');
    const conditionEl = card.querySelector('.s-item__subtitle, .s-card__subtitle, .SECONDARY_INFO');
    items.push({
      title: (titleEl.textContent || '').trim(),
      price: (priceEl.textContent || '').trim(),
      url: linkEl ? linkEl.href : null,
      condition: conditionEl ? (conditionEl.textContent || '').trim() : '',
    });
  }
"""


class EbaySource(BaseBrowserSource):
    platform: MarketPlatform = "ebay"
    base_url = "https://www.ebay.es"
    blocked_markers = (
        "error page | ebay",
        "pardon our interruption",
        "captcha",
        "access denied",
        "unusual traffic",
        "robot check",
    )
    render_wait_ms = 1_200
    min_results = 20

    def search_url(self, query: str) -> str:
        encoded = quote_plus(query)
        return (
            f"{self.base_url}/sch/i.html?_nkw={encoded}&_sacat=0"
            "&LH_BIN=1&LH_ItemCondition=3000&_ipg=60"
        )

    def search_urls(self, query: str) -> tuple[str, ...]:
        first = self.search_url(query)
        return (first, f"{first}&_pgn=2")

    def extract_script(self) -> str:
        return page_payload_script(EBAY_ITEMS_SCRIPT)

    def parse_html(self, html: str) -> list[MarketListingSample]:
        soup = BeautifulSoup(html, "lxml")
        raw_items: list[dict[str, object]] = []
        for card in soup.select("li.s-item, li.s-card"):
            title_el = card.select_one(".s-item__title, .s-card__title")
            price_el = card.select_one(".s-item__price, .s-card__price")
            if title_el is None or price_el is None:
                continue
            link_el = card.select_one("a.s-item__link, a.s-card__link, a[href*='/itm/']")
            condition_el = card.select_one(
                ".s-item__subtitle, .s-card__subtitle, .SECONDARY_INFO"
            )
            raw_items.append(
                {
                    "title": title_el.get_text(" ", strip=True),
                    "price": price_el.get_text(" ", strip=True),
                    "url": link_el.get("href") if link_el is not None else None,
                    "condition": (
                        condition_el.get_text(" ", strip=True)
                        if condition_el is not None
                        else ""
                    ),
                }
            )
        return self.parse_items(raw_items)
