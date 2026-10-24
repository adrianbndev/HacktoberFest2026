"""Normalisation and filtering rules (MOD-04 §2.2)."""

from __future__ import annotations

import pytest
from app.mcp.normalize import (
    build_listing_sample,
    dedupe_listings,
    filter_usable_listings,
    is_accessory_listing,
    normalize_condition,
    normalize_query,
    parse_price_eur,
)
from app.models.sdd import MarketListingSample, MarketPlatform

LONG_VISION_NAME = "Consola Nintendo Switch OLED 64GB Blanca en excelente estado"


def test_query_uses_brand_and_model_and_trims_filler_words() -> None:
    assert normalize_query(LONG_VISION_NAME) == "Consola Nintendo Switch OLED 64GB"
    assert normalize_query(LONG_VISION_NAME, brand="Nintendo", model="Switch OLED") == (
        "Nintendo Switch OLED"
    )
    assert normalize_query("iPhone 13 en muy buen estado") == "iPhone 13 buen"


def test_query_does_not_duplicate_the_brand_inside_the_model() -> None:
    assert normalize_query("Apple iPhone 13", brand="Apple", model="Apple iPhone 13") == (
        "Apple iPhone 13"
    )


@pytest.mark.parametrize(
    "title",
    [
        "Funda oficial iPhone 13",
        "CAJA VACÍA iPhone 13",
        "iPhone 13 solo caja",
        "Protector de pantalla iPhone 13",
        "Cable Lightning original",
        "iPhone 13 para piezas",
    ],
)
def test_accessory_and_bait_listings_are_detected(title: str) -> None:
    assert is_accessory_listing(title) is True


def test_legitimate_listings_with_a_box_are_not_rejected() -> None:
    assert is_accessory_listing("iPhone 13 con caja original y factura") is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Nuevo, precintado", "Nuevo"),
        ("Como nuevo", "Como nuevo"),
        ("Muy buen estado", "Buen estado"),
        ("Desgaste visible en la tapa", "Desgaste visible"),
        ("Para piezas o reparar", "Para piezas"),
        ("", "Buen estado"),
    ],
)
def test_condition_mapping(text: str, expected: str) -> None:
    assert normalize_condition(text) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("330,00 EUR", 330),
        ("EUR 379.95", 380),
        ("1.250 €", 1250),
        ("1.250,50 €", 1251),
        ("€ 1.999", 1999),
        ("349.5", 350),
        ("sin precio", None),
        ("0", None),
    ],
)
def test_price_parsing(raw: str, expected: int | None) -> None:
    assert parse_price_eur(raw) == expected


def test_usable_filter_drops_symbolic_prices_accessories_and_extremes() -> None:
    listings = [
        _listing("iPhone 13 128GB", 325),
        _listing("Funda iPhone 13", 15),
        _listing("iPhone 13 128GB barato", 3),
        _listing("iPhone 13 128GB caro", 90_000),
        _listing("iPhone 13 128GB azul", 349),
    ]

    filtered = filter_usable_listings(listings, max_price_eur=10_000)

    assert [listing.price for listing in filtered] == [325, 349]


def test_dedupe_keeps_one_copy_per_platform_title_and_price() -> None:
    listings = [
        _listing("iPhone 13 128GB", 325, platform="wallapop"),
        _listing("iphone 13 128gb", 325, platform="wallapop"),
        _listing("iPhone 13 128GB", 325, platform="ebay"),
        _listing("iPhone 13 128GB", 330, platform="wallapop"),
    ]

    unique = dedupe_listings(listings)

    assert len(unique) == 3
    assert {listing.platform for listing in unique} == {"wallapop", "ebay"}


def test_build_listing_sample_resolves_relative_urls() -> None:
    sample = build_listing_sample(
        title="iPhone 13 128GB",
        price=330,
        platform="ebay",
        href="/itm/123",
        base_url="https://www.ebay.es",
    )

    assert sample is not None
    assert sample.url == "https://www.ebay.es/itm/123"
    assert sample.condition == "Buen estado"


def test_build_listing_sample_rejects_invalid_items() -> None:
    assert (
        build_listing_sample(
            title="",
            price=330,
            platform="ebay",
            href=None,
            base_url="https://www.ebay.es",
        )
        is None
    )
    assert (
        build_listing_sample(
            title="iPhone",
            price=None,
            platform="ebay",
            href=None,
            base_url="https://www.ebay.es",
        )
        is None
    )


def _listing(
    title: str, price: int, *, platform: MarketPlatform = "wallapop"
) -> MarketListingSample:
    return MarketListingSample(
        title=title,
        price=price,
        platform=platform,
        condition="Buen estado",
    )
