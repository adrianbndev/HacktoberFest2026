"""Deterministic fallback catalog acceptance tests (brief §7.4)."""

from __future__ import annotations

import pytest
from app.mcp.catalog_fallback import (
    CATALOG,
    FALLBACK_WARNING,
    build_deep_link,
    build_fallback_result,
    estimate_base_price,
    find_catalog_entry,
)
from app.models.sdd import MarketPlatform


def test_curated_catalog_matches_common_models_specifically() -> None:
    iphone = find_catalog_entry("Apple iPhone 13 128GB", "Móviles")
    switch = find_catalog_entry("Consola Nintendo Switch OLED 64GB blanca", "Consolas")
    ps5 = find_catalog_entry("Sony PlayStation 5 con mando", "Consolas")

    assert iphone is not None and iphone.label == "iPhone 13"
    assert switch is not None and switch.label == "Nintendo Switch OLED"
    assert ps5 is not None and ps5.label == "PlayStation 5"


def test_unknown_models_fall_back_to_the_hash_estimator() -> None:
    assert find_catalog_entry("Objeto artesanal sin marca", "Varios") is None

    first = estimate_base_price("Objeto artesanal sin marca", "Varios")
    second = estimate_base_price("Objeto artesanal sin marca", "Varios")
    other = estimate_base_price("Otro objeto distinto", "Varios")

    assert first == second
    assert first != other
    assert first >= 5


def test_estimator_uses_the_category_baseline() -> None:
    phones = estimate_base_price("Modelo desconocido", "Móviles")
    books = estimate_base_price("Modelo desconocido", "Libros")

    assert phones > books


@pytest.mark.parametrize(
    ("platform", "domain"),
    [
        ("wallapop", "https://es.wallapop.com/app/search?keywords="),
        ("milanuncios", "https://www.milanuncios.com/anuncios/?s="),
        ("ebay", "https://www.ebay.es/sch/i.html?_nkw="),
    ],
)
def test_deep_links_are_functional_and_encoded(platform: MarketPlatform, domain: str) -> None:
    link = build_deep_link(platform, "iPhone 13 128GB")

    assert link is not None
    assert link.startswith(domain)
    assert "iPhone%2013%20128GB" in link


def test_fallback_result_is_contract_complete_and_deterministic() -> None:
    kwargs = {"query": "iPhone 13 128GB", "category": "Móviles", "condition_score": 80}

    result = build_fallback_result(**kwargs)
    again = build_fallback_result(**kwargs)

    assert result == again
    assert result.source == "stealth_fallback"
    assert result.warnings == [FALLBACK_WARNING]
    assert 0 < result.price_min < result.price_avg < result.price_max
    assert result.sample_size == 11
    assert len(result.comparable_listings) == 11
    assert result.platforms == ["wallapop", "milanuncios", "ebay"]
    assert "vinted" not in result.platforms
    assert all(
        listing.url and listing.url.startswith("https://")
        for listing in result.comparable_listings
    )
    assert all(listing.condition == "Buen estado" for listing in result.comparable_listings)


def test_fallback_applies_health_weighting_monotonically() -> None:
    broken = build_fallback_result(
        query="Nintendo Switch OLED", category="Consolas", condition_score=30
    )
    mint = build_fallback_result(
        query="Nintendo Switch OLED", category="Consolas", condition_score=95
    )

    assert broken.price_avg < mint.price_avg


def test_fallback_unknown_model_still_returns_a_valid_triplet() -> None:
    result = build_fallback_result(
        query="Objeto artesanal sin marca", category="Varios", condition_score=55
    )

    assert 0 < result.price_min < result.price_avg < result.price_max
    assert result.comparable_listings


def test_fallback_respects_the_listing_cap() -> None:
    result = build_fallback_result(
        query="iPhone 13", category="Móviles", condition_score=70, max_listings=2
    )

    assert len(result.comparable_listings) == 2
    assert result.platforms == ["wallapop", "milanuncios"]
    assert result.sample_size == 11


def test_catalog_entries_are_unique_and_priced() -> None:
    labels = [entry.label for entry in CATALOG]

    assert len(labels) == len(set(labels))
    assert all(entry.base_price_eur > 0 for entry in CATALOG)
