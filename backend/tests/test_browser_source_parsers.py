"""Parser fixture tests for the eBay, Wallapop and Milanuncios sources."""

from __future__ import annotations

from pathlib import Path

from app.mcp.browser.sources.ebay import EbaySource
from app.mcp.browser.sources.milanuncios import (
    MilanunciosSource,
    looks_like_perimeterx,
)
from app.mcp.browser.sources.wallapop import WallapopSource
from bs4 import BeautifulSoup

FIXTURES = Path(__file__).parent / "fixtures"


# --------------------------------------------------------------------------- parsers


def test_ebay_fixture_strips_accessibility_suffix_and_skips_shop_card() -> None:
    samples = EbaySource().parse_html((FIXTURES / "ebay_browser.html").read_text("utf-8"))

    assert [sample.title for sample in samples] == [
        "Silla de madera vintage",
        "Silla de madera",
        "Silla de madera antigua",
    ]
    assert [sample.price for sample in samples] == [35, 52, 1235]
    assert all(sample.url and sample.url.startswith("https://www.ebay.es/itm/") for sample in samples)
    assert all(sample.platform == "ebay" for sample in samples)


def test_wallapop_fixture_parses_both_price_formats_and_dedupes_urls() -> None:
    samples = WallapopSource().parse_html(
        (FIXTURES / "wallapop_browser.html").read_text("utf-8")
    )

    assert [sample.title for sample in samples] == [
        "Silla de madera",
        "Silla de roble",
        "Silla de comedor",
    ]
    assert [sample.price for sample in samples] == [35, 1234, 1235]
    assert samples[0].url == "https://es.wallapop.com/item/silla-madera-123"


def test_milanuncios_fixture_parses_article_cards() -> None:
    samples = MilanunciosSource().parse_html(
        (FIXTURES / "milanuncios_browser.html").read_text("utf-8")
    )

    assert [sample.title for sample in samples] == [
        "Silla de madera",
        "Silla de roble maciza",
        "Silla de comedor",
    ]
    assert [sample.price for sample in samples] == [35, 120, 1235]
    assert samples[0].url == "https://www.milanuncios.com/silla-de-madera/123.htm"


def test_milanuncios_parser_works_with_the_saved_iphone_fixture() -> None:
    samples = MilanunciosSource().parse_html(
        (FIXTURES / "milanuncios_search_v2.html").read_text("utf-8")
    )

    assert [sample.price for sample in samples] == [299, 250]


def test_perimeterx_blocked_fixture_is_detected_and_never_parsed() -> None:
    html = (FIXTURES / "milanuncios_blocked.html").read_text("utf-8")
    source = MilanunciosSource()
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)

    assert looks_like_perimeterx(html) is True
    assert source.is_blocked(text, "Access Denied") is True
    assert source.block_reason(text, "Access Denied") is not None
    assert source.parse_html(html) == []


def test_legit_page_is_not_flagged_as_blocked() -> None:
    source = MilanunciosSource()
    text = BeautifulSoup(
        (FIXTURES / "milanuncios_browser.html").read_text("utf-8"), "lxml"
    ).get_text(" ", strip=True)

    assert source.is_blocked(text, "Silla de madera - Milanuncios") is False
