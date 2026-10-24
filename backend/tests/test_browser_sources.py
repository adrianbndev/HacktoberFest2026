"""Parser fixtures and browser-collection behaviour for the three sources."""

from __future__ import annotations

from typing import Any, cast

import pytest
from app.mcp.browser.sources.base import BLOCKED_ERROR, PAYLOAD_ERROR, SourceOutcome
from app.mcp.browser.sources.ebay import EbaySource
from app.mcp.browser.sources.milanuncios import MilanunciosSource
from app.mcp.browser.sources.wallapop import WallapopSource
from app.mcp.deep_sources import default_sources
from tests.support import make_settings


class FakePage:
    def __init__(self, payloads: list[Any]) -> None:
        self.payloads = list(payloads)
        self.urls: list[str] = []
        self.scroll_calls: list[tuple[int, int]] = []

    async def navigate(self, url: str) -> None:
        self.urls.append(url)

    async def evaluate(self, function: str) -> Any:
        if function.startswith("async () =>"):
            return True
        if not self.payloads:
            raise AssertionError("the source requested more payloads than expected")
        return self.payloads.pop(0)

    async def scroll(self, *, steps: int = 4, pause_ms: int = 350) -> None:
        self.scroll_calls.append((steps, pause_ms))


def _payload(items: list[dict[str, Any]], text: str = "", title: str = "") -> dict[str, Any]:
    return {"items": items, "text": text, "title": title}


def _raw_item(title: str, price: str, url: str) -> dict[str, Any]:
    return {"title": title, "price": price, "url": url, "condition": ""}


# --------------------------------------------------------------------------- URLs


def test_search_urls_match_the_frozen_browser_contract() -> None:
    ebay = EbaySource().search_urls("Silla de madera")
    assert len(ebay) == 2
    assert "https://www.ebay.es/sch/i.html?_nkw=Silla+de+madera&_sacat=0" in ebay[0]
    assert "LH_BIN=1" in ebay[0]
    assert "LH_ItemCondition=3000" in ebay[0]
    assert "_ipg=60" in ebay[0]
    assert ebay[1].endswith("&_pgn=2")

    assert WallapopSource().search_url("Silla de madera") == (
        "https://es.wallapop.com/app/search?keywords=Silla+de+madera&order_by=newest"
    )
    milanuncios = MilanunciosSource().search_urls("Silla de madera")
    assert milanuncios[0] == "https://www.milanuncios.com/anuncios/?s=Silla+de+madera"
    assert milanuncios[1].endswith("&pagina=2")
    assert milanuncios[2].endswith("&pagina=3")
    assert len(milanuncios) == 3


@pytest.mark.parametrize("pages", [1, 3, 4, 6])
def test_milanuncios_page_depth_is_configurable(pages: int) -> None:
    urls = MilanunciosSource(max_pages=pages).search_urls("Silla de madera")

    assert len(urls) == pages
    assert urls[0] == "https://www.milanuncios.com/anuncios/?s=Silla+de+madera"
    if pages > 1:
        assert urls[-1].endswith(f"&pagina={pages}")


def test_default_sources_reads_the_configured_page_depth() -> None:
    sources = default_sources(make_settings(market_milanuncios_max_pages=4))

    milanuncios = cast(MilanunciosSource, sources["milanuncios"])
    assert milanuncios.max_pages == 4
    assert len(milanuncios.search_urls("Silla de madera")) == 4


def test_milanuncios_rejects_an_out_of_range_page_depth() -> None:
    with pytest.raises(ValueError):
        MilanunciosSource(max_pages=0)
    with pytest.raises(ValueError):
        MilanunciosSource(max_pages=7)


# --------------------------------------------------------------------------- collection


async def test_ebay_requests_page_two_only_when_page_one_is_short() -> None:
    source = EbaySource()
    page = FakePage(
        [
            _payload([_raw_item("Silla A", "30 €", "/itm/a")]),
            _payload(
                [
                    _raw_item("Silla B", "40 €", "/itm/b"),
                    _raw_item("Silla C", "50 €", "/itm/c"),
                ]
            ),
        ]
    )

    outcome = await source.collect(page, "Silla de madera")

    assert len(page.urls) == 2
    assert [listing.price for listing in outcome.listings] == [30, 40, 50]
    assert outcome.status == "ok"
    assert outcome.latency_ms >= 0


async def test_ebay_stops_at_page_one_with_enough_results() -> None:
    source = EbaySource()
    items = [_raw_item(f"Silla {index}", f"{20 + index} €", f"/itm/{index}") for index in range(20)]
    page = FakePage([_payload(items)])

    outcome = await source.collect(page, "Silla de madera")

    assert len(page.urls) == 1
    assert len(outcome.listings) == 20


async def test_milanuncios_paginates_until_it_has_enough_cards() -> None:
    source = MilanunciosSource(max_pages=6)
    page = FakePage(
        [
            _payload([_raw_item(f"Silla {index}", "30 €", f"/silla/{index}") for index in range(5)]),
            _payload([_raw_item("Silla extra", "35 €", "/silla/extra")]),
            _payload([_raw_item(f"Silla mid {index}", "38 €", f"/silla/mid-{index}") for index in range(5)]),
            _payload([_raw_item(f"Silla final {index}", "40 €", f"/silla/final-{index}") for index in range(4)]),
        ]
    )

    outcome = await source.collect(page, "Silla de madera")

    assert len(page.urls) == 4
    assert outcome.status == "ok"
    assert len(outcome.listings) == 15


async def test_wallapop_scrolls_before_extracting() -> None:
    source = WallapopSource()
    page = FakePage([_payload([_raw_item("Silla de madera", "35 €", "/item/silla-1")])])

    outcome = await source.collect(page, "Silla de madera")

    assert page.scroll_calls == [(3, 300)]
    assert outcome.status == "ok"
    assert outcome.listings[0].url == "https://es.wallapop.com/item/silla-1"


async def test_blocked_page_is_reported_without_solving_the_captcha() -> None:
    source = MilanunciosSource()
    page = FakePage(
        [_payload([], text="Pardon our interruption - captcha", title="Access Denied")]
    )

    outcome = await source.collect(page, "Silla de madera")

    assert outcome.status == "blocked"
    assert outcome.error == BLOCKED_ERROR
    assert outcome.listings == ()


async def test_empty_results_are_no_listings_not_a_block() -> None:
    source = WallapopSource()
    page = FakePage([_payload([], text="Silla de madera", title="wallapop")])

    outcome = await source.collect(page, "Silla de madera")

    assert outcome.status == "no_listings"
    assert outcome.error is None


async def test_unexpected_payload_is_an_error() -> None:
    source = EbaySource()
    page = FakePage(["not-an-object"])

    outcome = await source.collect(page, "Silla de madera")

    assert outcome.status == "error"
    assert outcome.error == PAYLOAD_ERROR


@pytest.mark.parametrize(
    "source",
    [EbaySource(), WallapopSource(), MilanunciosSource()],
)
def test_every_source_outcome_carries_its_platform(source: Any) -> None:
    outcome = SourceOutcome(source=source.platform, status="no_listings", listings=(), latency_ms=0)
    assert outcome.source == source.platform
