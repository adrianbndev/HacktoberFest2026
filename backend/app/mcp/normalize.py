"""Query and listing normalisation for the stealth market engine (MOD-04 §2.2)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Iterator
from typing import Any
from urllib.parse import urljoin

from app.models.sdd import MarketListingSample, MarketPlatform

MAX_QUERY_LENGTH = 120
MAX_QUERY_WORDS = 5
MIN_SYMBOLIC_PRICE_EUR = 3

FILLER_WORDS = frozenset(
    {
        "a",
        "al",
        "con",
        "como",
        "caja",
        "de",
        "del",
        "el",
        "en",
        "estado",
        "excelente",
        "impecable",
        "la",
        "las",
        "los",
        "muy",
        "nuevo",
        "para",
        "por",
        "sin",
        "un",
        "una",
        "y",
    }
)

ACCESSORY_MARKERS = (
    "caja vacia",
    "solo caja",
    "solo la caja",
    "funda",
    "protector",
    "cable",
    "carcasa",
    "manual",
    "recambio",
    "por piezas",
    "para piezas",
    "no funciona",
    "averiado",
)

_CONDITION_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("para piezas", "averiado", "no funciona", "defectuoso"), "Para piezas"),
    (("desgaste", "regular", "usado", "marcas"), "Desgaste visible"),
    (("como nuevo", "impecable", "excelente"), "Como nuevo"),
    (("precintado", "nuevo"), "Nuevo"),
    (("buen estado", "muy buen estado", "bueno"), "Buen estado"),
)

_WHITESPACE = re.compile(r"\s+")
PRICE_PATTERN = re.compile(r"\d[\d.,\s]*")

# Vision models frequently fill "Sin marca" / "Genérico" into the form. In the
# deep analysis those values must behave as "absent" so they never pollute the
# marketplace query or the relevance filter. `/valuate` is frozen and keeps the
# old behaviour.
GENERIC_BRAND_VALUES = frozenset(
    {"sin marca", "generica", "n/a", "na", "-", "unknown", "no aplica"}
)
GENERIC_MODEL_VALUES = frozenset({"generico", "generica", "n/a", "-"})


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def squeeze(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def normalize_query(query: str, *, brand: str | None = None, model: str | None = None) -> str:
    """Reduce a long vision description to a compact marketplace query."""
    brand = squeeze(brand or "")
    model = squeeze(model or "")
    if brand and model and strip_accents(model.lower()).startswith(strip_accents(brand.lower())):
        hint = model
    else:
        hint = squeeze(" ".join(part for part in (brand, model) if part))

    source = hint or squeeze(query)
    words = [word for word in source.split(" ") if word]
    meaningful = [word for word in words if strip_accents(word.lower()) not in FILLER_WORDS]
    selected = (meaningful or words)[:MAX_QUERY_WORDS]
    return " ".join(selected)[:MAX_QUERY_LENGTH].strip() or squeeze(query)[:MAX_QUERY_LENGTH]


def _identity_key(value: str) -> str:
    return strip_accents(squeeze(value).lower())


def clean_brand(value: str | None) -> str | None:
    """Return the brand, or ``None`` when it is a generic/placeholder value."""
    cleaned = squeeze(value or "")
    if not cleaned or _identity_key(cleaned) in GENERIC_BRAND_VALUES:
        return None
    return cleaned


def clean_model(value: str | None, *, name: str = "") -> str | None:
    """Return the model, or ``None`` when it is generic or just repeats the name."""
    cleaned = squeeze(value or "")
    if not cleaned or _identity_key(cleaned) in GENERIC_MODEL_VALUES:
        return None
    if name and _identity_key(cleaned) == _identity_key(name):
        return None
    return cleaned


def build_analysis_query(name: str) -> str:
    """`name` is the marketplace query for the deep analysis (brief §5.1)."""
    return normalize_query(name)


def build_relevance_query(
    name: str, brand: str | None = None, model: str | None = None
) -> str:
    """Identity-aware query used only for relevance/recommendation, not the URL."""
    identity_brand = clean_brand(brand)
    identity_model = clean_model(model, name=name)
    if identity_brand or identity_model:
        return normalize_query(name, brand=identity_brand, model=identity_model)
    return build_analysis_query(name)


def normalize_condition(*texts: str, default: str = "Buen estado") -> str:
    """Map free-text condition hints onto the five canonical labels."""
    haystack = strip_accents(" ".join(texts).lower())
    for markers, label in _CONDITION_RULES:
        if any(strip_accents(marker) in haystack for marker in markers):
            return label
    return default


def is_accessory_listing(title: str) -> bool:
    haystack = strip_accents(title.lower())
    return any(strip_accents(marker) in haystack for marker in ACCESSORY_MARKERS)


def is_usable_listing(
    listing: MarketListingSample, *, max_price_eur: int, min_price_eur: int = MIN_SYMBOLIC_PRICE_EUR
) -> bool:
    return (
        min_price_eur < listing.price <= max_price_eur
        and bool(listing.title.strip())
        and not is_accessory_listing(listing.title)
    )


def filter_usable_listings(
    listings: Iterable[MarketListingSample], *, max_price_eur: int
) -> list[MarketListingSample]:
    return [
        listing
        for listing in listings
        if is_usable_listing(listing, max_price_eur=max_price_eur)
    ]


def dedupe_listings(listings: Iterable[MarketListingSample]) -> list[MarketListingSample]:
    """Drop exact duplicates, keeping the first occurrence (order preserved)."""
    seen: set[tuple[str, str, float]] = set()
    unique: list[MarketListingSample] = []
    for listing in listings:
        key = (listing.platform, strip_accents(squeeze(listing.title).lower()), listing.price)
        if key in seen:
            continue
        seen.add(key)
        unique.append(listing)
    return unique


def parse_price_eur(text: str) -> int | None:
    """Parse Spanish/EU price strings such as ``1.250,50 €`` or ``EUR 330.00``."""
    match = PRICE_PATTERN.search(text)
    if match is None:
        return None
    value = _to_decimal(match.group(0).strip().replace(" ", ""))
    if value is None or value <= 0:
        return None
    return int(value + 0.5)


def _to_decimal(raw: str) -> float | None:
    if "," in raw and "." in raw:
        raw = (
            raw.replace(".", "").replace(",", ".")
            if raw.rfind(",") > raw.rfind(".")
            else raw.replace(",", "")
        )
    elif "," in raw:
        head, _, tail = raw.rpartition(",")
        raw = f"{head}.{tail}" if len(tail) == 2 else raw.replace(",", "")
    elif "." in raw:
        head, _, tail = raw.rpartition(".")
        if len(tail) > 2 or not head.isdigit():
            raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def build_listing_sample(
    *,
    title: str,
    price: float | None,
    platform: MarketPlatform,
    href: str | None,
    base_url: str,
    condition_hint: str | None = None,
) -> MarketListingSample | None:
    """Build a contract-valid sample, or ``None`` when the raw item is unusable."""
    clean_title = squeeze(title)[:300]
    if not clean_title or price is None or price <= 0:
        return None
    try:
        return MarketListingSample(
            title=clean_title,
            price=int(price + 0.5),
            platform=platform,
            condition=normalize_condition(condition_hint or "", clean_title),
            url=urljoin(base_url, href) if href else None,
        )
    except ValueError:
        return None


def iter_json_listing_items(node: Any) -> Iterator[dict[str, Any]]:
    """Yield embedded-JSON nodes that look like a listing (title + numeric price)."""
    if isinstance(node, dict):
        if isinstance(node.get("title"), str) and json_price_amount(node.get("price")) is not None:
            yield node
        for value in node.values():
            yield from iter_json_listing_items(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_json_listing_items(value)


def json_price_amount(price: Any) -> float | None:
    if isinstance(price, bool):
        return None
    if isinstance(price, (int, float)):
        return float(price)
    if isinstance(price, dict):
        return json_price_amount(price.get("amount"))
    if isinstance(price, str):
        parsed = parse_price_eur(price)
        return float(parsed) if parsed is not None else None
    return None
