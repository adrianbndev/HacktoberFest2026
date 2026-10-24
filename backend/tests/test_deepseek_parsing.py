"""DeepSeek query parsing, relevance and model-policy tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.config import Settings
from app.mcp.deepseek import DeepSeekRecommender, ParsedQuery
from app.mcp.deepseek_client import CompletionResult
from app.models.sdd import MarketListingSample
from tests.deepseek_support import FakeCompletion, make_settings


async def test_parse_query_extracts_structured_fields() -> None:
    body = CompletionResult(
        json.dumps(
            {
                "query": "Nintendo Switch OLED",
                "brand": "Nintendo",
                "model": "Switch OLED",
                "category": "Consolas",
                "keywords": ["oled", "64gb"],
            }
        )
    )

    parsed = await DeepSeekRecommender(
        make_settings(), completion=FakeCompletion([body])
    ).parse_query("Consola Nintendo Switch OLED 64GB blanca", budget_sec=1.0)

    assert parsed == ParsedQuery(
        query="Nintendo Switch OLED",
        brand="Nintendo",
        model="Switch OLED",
        category="Consolas",
        keywords=["oled", "64gb"],
    )


async def test_parse_query_falls_back_deterministically() -> None:
    parsed = await DeepSeekRecommender(Settings(_env_file=None)).parse_query(
        "  Consola Nintendo Switch OLED 64GB blanca  "
    )

    assert parsed.query == "Consola Nintendo Switch OLED 64GB"
    assert parsed.brand is None


def test_relevance_filter_drops_unrelated_titles() -> None:
    recommender = DeepSeekRecommender(Settings(_env_file=None))
    listings = [
        MarketListingSample(
            title="Samsung Galaxy S23", price=380, platform="ebay", condition="Buen estado"
        ),
        MarketListingSample(
            title="iPhone 13 128GB", price=330, platform="wallapop", condition="Buen estado"
        ),
    ]

    ranked = recommender.score_relevance("iPhone 13", listings)

    assert [listing.title for listing in ranked] == ["iPhone 13 128GB"]


def test_legacy_reasoner_model_is_never_hard_coded() -> None:
    app_dir = Path(__file__).parents[1] / "app"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in app_dir.rglob("*.py"))

    assert "deepseek-reasoner" not in sources


@pytest.mark.parametrize("model", ["deepseek-v4-pro", "deepseek-flash"])
def test_default_models_are_the_approved_ones(model: str) -> None:
    settings = make_settings()

    assert model in {settings.deepseek_reasoning_model, settings.deepseek_fast_model}


@pytest.mark.parametrize(
    ("query", "title", "accepted"),
    [
        ("iPhone 13", "iPhone 14 128GB", False),
        ("iPhone 13", "iPhone 13 Pro", True),
        ("iPhone 13", "Xiaomi 13 128GB", False),
        ("iPhone 13", "Apple iPhone 13 128GB", True),
        ("iPhone 13 128 GB", "iPhone 12 128 GB", False),
        ("iPhone 13 128 GB", "iPhone 13 128GB", True),
        ("PS5", "PS4 Slim", False),
        ("PS5", "Sony PS5 Digital Edition", True),
        ("PS5", "Sony PlayStation 5", True),
        ("PlayStation 5", "PS5", True),
        ("Xbox Series X", "Xbox Series S", False),
        ("S23", "Samsung Galaxy S24", False),
        ("S23", "Samsung Galaxy S23 Ultra", True),
        ("AirPods Pro 2", "Apple AirPods Pro 2", True),
        ("AirPods Pro 2", "Sony WF-1000XM5", False),
        ("iPhone", "iPhone 14 128GB", True),
        ("iPhone", "Samsung Galaxy S23", False),
    ],
)
def test_model_tokens_are_required_and_conflicts_are_rejected(
    query: str, title: str, accepted: bool
) -> None:
    recommender = DeepSeekRecommender(Settings(_env_file=None))
    listings = [
        MarketListingSample(
            title=title, price=300, platform="wallapop", condition="Buen estado"
        )
    ]

    ranked = recommender.score_relevance(query, listings)

    assert bool(ranked) is accepted
