"""Brand/model-aware lexical relevance for market listings.

The rule is deterministic and runs in the request hot path (no LLM call):
digit-bearing tokens identify a model, while brand/name tokens must also match.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from app.models.sdd import MarketListingSample

RELEVANCE_THRESHOLD = 0.34
STOPWORDS = frozenset(
    {"caja", "como", "con", "desde", "esta", "este", "para", "pero", "solo", "todo", "viene"}
)
TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
CAPACITY_RE = re.compile(r"^\d+(?:gb|tb|mb)$")
CAPACITY_SPLIT_RE = re.compile(r"(\d+)\s*(gb|tb|mb)\b")
MODEL_ALIASES: tuple[tuple[str, str], ...] = (
    ("playstation 5", "ps5"),
    ("playstation 4", "ps4"),
    ("playstation5", "ps5"),
    ("playstation4", "ps4"),
    ("xbox series x", "xsx"),
    ("xbox series s", "xss"),
)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def tokens(text: str) -> set[str]:
    normalized = strip_accents(text.lower())
    normalized = CAPACITY_SPLIT_RE.sub(r"\1\2", normalized)
    for phrase, alias in MODEL_ALIASES:
        normalized = normalized.replace(phrase, alias)
    return set(TOKEN_RE.findall(normalized))


def model_tokens(values: set[str]) -> set[str]:
    """Digit-bearing tokens identify a model (13, s23, ps5); capacities do not."""
    return {
        token
        for token in values
        if any(char.isdigit() for char in token) and not CAPACITY_RE.match(token)
    }


def identity_tokens(values: set[str], models: set[str]) -> set[str]:
    """Brand/name tokens that must also appear when a model token is required."""
    return {
        token
        for token in values
        if token not in models and not CAPACITY_RE.match(token) and token not in STOPWORDS
    }


def keywords(text: str, limit: int = 3) -> list[str]:
    found = TOKEN_RE.findall(strip_accents(text.lower()))
    return [token for token in dict.fromkeys(found) if token not in STOPWORDS][:limit]


def score_relevance(
    query: str, listings: Sequence[MarketListingSample]
) -> list[MarketListingSample]:
    """Rank by model/brand overlap; reject conflicting models and wrong brands."""
    query_tokens = tokens(query)
    if not query_tokens:
        return list(listings)
    query_models = model_tokens(query_tokens)
    query_identity = identity_tokens(query_tokens, query_models)
    scored: list[tuple[float, MarketListingSample]] = []
    for listing in listings:
        title_tokens = tokens(listing.title)
        if query_models:
            title_models = model_tokens(title_tokens)
            if not query_models & title_models:
                continue
            if query_identity and not query_identity & title_tokens:
                continue
            overlap = len(query_models & title_models) / len(query_models)
        else:
            overlap = len(query_tokens & title_tokens) / len(query_tokens)
        if overlap >= RELEVANCE_THRESHOLD:
            scored.append((overlap, listing))
    scored.sort(key=lambda pair: (-pair[0], pair[1].price))
    return [listing for _, listing in scored]
