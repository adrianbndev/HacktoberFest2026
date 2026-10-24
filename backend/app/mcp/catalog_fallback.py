"""Deterministic Spain-2026 fallback catalog and estimator (MOD-04 §4)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.mcp.analysis_query import build_platform_search_url
from app.mcp.normalize import normalize_query, strip_accents
from app.mcp.pricing_math import compute_price_triplet
from app.models.sdd import MarketListingSample, MarketPlatform, MarketValuationResult

FALLBACK_WARNING = (
    "Fuentes en vivo no disponibles: tasación determinista con el catálogo curado España 2026."
)
MAX_LISTINGS = 12
SAMPLE_MULTIPLIERS = (0.82, 0.86, 0.91, 0.95, 0.98, 1.00, 1.03, 1.07, 1.12, 1.17, 1.23)
FALLBACK_PLATFORMS: tuple[MarketPlatform, ...] = ("wallapop", "milanuncios", "ebay")
CATEGORY_BASE_PRICES: dict[str, float] = {
    "moviles": 320.0,
    "consolas": 240.0,
    "portatiles": 620.0,
    "audio": 130.0,
    "monitores": 160.0,
    "camaras": 340.0,
    "fotografia": 340.0,
    "bicicletas": 260.0,
    "ropa": 45.0,
    "libros": 18.0,
    "electrodomesticos": 180.0,
}
DEFAULT_CATEGORY_BASE = 120.0


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A curated market baseline (median price for standard condition)."""

    label: str
    keywords: tuple[str, ...]
    base_price_eur: float
    category: str


CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry("iPhone 13", ("iphone 13",), 330.0, "moviles"),
    CatalogEntry("iPhone 14", ("iphone 14",), 430.0, "moviles"),
    CatalogEntry("iPhone 15", ("iphone 15",), 560.0, "moviles"),
    CatalogEntry("iPhone 12", ("iphone 12",), 265.0, "moviles"),
    CatalogEntry("Samsung Galaxy S23", ("galaxy s23",), 380.0, "moviles"),
    CatalogEntry(
        "Nintendo Switch OLED", ("nintendo switch oled", "switch oled"), 235.0, "consolas"
    ),
    CatalogEntry("Nintendo Switch", ("nintendo switch",), 175.0, "consolas"),
    CatalogEntry("PlayStation 5", ("playstation 5", "ps5"), 385.0, "consolas"),
    CatalogEntry("Xbox Series X", ("xbox series x",), 330.0, "consolas"),
    CatalogEntry("MacBook Air M1", ("macbook air m1",), 520.0, "portatiles"),
    CatalogEntry("MacBook Pro 14 M3", ("macbook pro 14",), 1300.0, "portatiles"),
    CatalogEntry("iPad Air", ("ipad air",), 300.0, "portatiles"),
    CatalogEntry("AirPods Pro 2", ("airpods pro 2",), 170.0, "audio"),
    CatalogEntry("Sony WH-1000XM4", ("wh-1000xm4", "1000xm4"), 150.0, "audio"),
    CatalogEntry("Dyson V11", ("dyson v11",), 250.0, "electrodomesticos"),
    CatalogEntry("Canon EOS 2000D", ("eos 2000d", "canon 2000d"), 300.0, "camaras"),
    CatalogEntry("Xiaomi Scooter Pro 2", ("scooter pro 2",), 250.0, "bicicletas"),
)


def find_catalog_entry(query: str, category: str | None = None) -> CatalogEntry | None:
    """Return the most specific curated entry whose keyword appears in the query."""
    haystack = _haystack(normalize_query(query), category or "")
    matches = [
        (len(keyword), entry)
        for entry in CATALOG
        for keyword in entry.keywords
        if keyword in haystack
    ]
    if not matches:
        return None
    return max(matches, key=lambda pair: (pair[0], -pair[1].base_price_eur))[1]


def estimate_base_price(query: str, category: str | None = None) -> float:
    """Deterministic estimate for uncatalogued items (category base + hash jitter)."""
    haystack = _haystack(normalize_query(query), category or "")
    base = _category_base(haystack)
    digest = hashlib.sha256(haystack.encode("utf-8")).digest()
    factor = 0.85 + (int.from_bytes(digest[:4], "big") % 31) / 100
    return max(5.0, round(base * factor, 2))


def build_deep_link(platform: MarketPlatform, query: str) -> str | None:
    """Functional search URL for a platform (fallback listings are never dead links)."""
    return build_platform_search_url(platform, query)


def build_fallback_result(
    *,
    query: str,
    category: str,
    condition_score: int,
    max_listings: int = MAX_LISTINGS,
) -> MarketValuationResult:
    """Build a contract-complete valuation from the curated catalog."""
    entry = find_catalog_entry(query, category)
    base_price = entry.base_price_eur if entry is not None else estimate_base_price(query, category)
    triplet = compute_price_triplet(
        [base_price * multiplier for multiplier in SAMPLE_MULTIPLIERS], condition_score
    )
    listings = _build_comparables(query, base_price, max(1, min(max_listings, MAX_LISTINGS)))
    return MarketValuationResult(
        price_min=triplet.price_min,
        price_avg=triplet.price_avg,
        price_max=triplet.price_max,
        sample_size=len(SAMPLE_MULTIPLIERS),
        platforms=list(dict.fromkeys(listing.platform for listing in listings)),
        comparable_listings=listings,
        source="stealth_fallback",
        warnings=[FALLBACK_WARNING],
    )


def _build_comparables(
    query: str, base_price: float, max_listings: int
) -> list[MarketListingSample]:
    title = f"{normalize_query(query)} · Buen estado"
    listings: list[MarketListingSample] = []
    for index, multiplier in enumerate(SAMPLE_MULTIPLIERS[:max_listings]):
        platform = FALLBACK_PLATFORMS[index % len(FALLBACK_PLATFORMS)]
        listings.append(
            MarketListingSample(
                title=title,
                price=max(1, round(base_price * multiplier)),
                platform=platform,
                condition="Buen estado",
                url=build_deep_link(platform, query),
            )
        )
    return listings


def _haystack(*parts: str) -> str:
    return strip_accents(" ".join(part for part in parts if part).lower())


def _category_base(haystack: str) -> float:
    for name, base in CATEGORY_BASE_PRICES.items():
        if strip_accents(name) in haystack:
            return base
    return DEFAULT_CATEGORY_BASE
