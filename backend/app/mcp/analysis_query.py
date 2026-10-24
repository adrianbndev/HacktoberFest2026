"""Generic brand/model cleanup and platform deep links for `/analyze`.

These helpers are deliberately separate from `normalize.py`: `/valuate` keeps
its frozen normalisation, while the deep path treats placeholder vision values
as absent and derives the marketplace query from `name`.
"""

from __future__ import annotations

from urllib.parse import quote

from app.mcp.normalize import normalize_query, squeeze, strip_accents
from app.models.sdd import MarketPlatform

GENERIC_BRAND_VALUES = frozenset(
    {"sin marca", "generica", "n/a", "na", "-", "unknown", "no aplica"}
)
GENERIC_MODEL_VALUES = frozenset({"generico", "generica", "n/a", "-"})

PLATFORM_SEARCH_URLS: dict[MarketPlatform, str] = {
    "wallapop": "https://es.wallapop.com/app/search?keywords={query}",
    "vinted": "https://www.vinted.es/catalog?search_text={query}",
    "milanuncios": "https://www.milanuncios.com/anuncios/?s={query}",
    "ebay": "https://www.ebay.es/sch/i.html?_nkw={query}",
}


def build_platform_search_url(platform: MarketPlatform, query: str) -> str | None:
    """Functional platform search deep link (never a dead listing URL)."""
    template = PLATFORM_SEARCH_URLS.get(platform)
    if template is None:
        return None
    return template.format(query=quote(normalize_query(query), safe=""))


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
    if identity_brand and identity_model:
        return normalize_query(name, brand=identity_brand, model=identity_model)
    # A generic/equal-to-name model adds no signal: the name already contains the
    # identity. Using the brand alone would reject listings that omit it.
    return build_analysis_query(name)
