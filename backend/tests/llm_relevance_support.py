"""Shared fakes for the DeepSeek relevance tests (no network, no API key)."""

from __future__ import annotations

import json
from collections.abc import Callable

from app.mcp.deepseek_client import CompletionResult, DeepSeekChat
from app.mcp.llm_relevance import EXACT, LlmRelevanceFilter
from app.models.market_analysis import MarketAnalysisRequest
from app.models.sdd import MarketListingSample
from tests.support import make_settings

AIRPODS_TARGET = "AirPods Pro 2"
AIRPODS_MATRIX: tuple[tuple[str, str], ...] = (
    ("AirPods Pro 2", EXACT),
    ("Apple AirPods Pro 2", EXACT),
    ("AirPods Pro 2nd generation", EXACT),
    ("AirPods Pro 2 con estuche", EXACT),
    ("AirPods 2", "different_model"),
    ("AirPods Pro", "different_model"),
    ("AirPods Pro 3", "different_model"),
    ("AirPods Pro 2 solo izquierdo", "single_item"),
    ("AirPods Pro 2 rotos", "broken"),
    ("Funda para AirPods Pro 2", "accessory"),
    ("Estuche AirPods Pro 2", "accessory"),
    ("AirPods Pro 2 para piezas", "broken"),
    ("Lote 2x AirPods Pro 2", "bundle"),
)


class LabelingCompletion:
    """Fake transport that labels each received listing from a title mapping."""

    def __init__(self, label_for: Callable[[str], str]) -> None:
        self._label_for = label_for
        self.calls: list[dict[str, object]] = []
        self.sent_titles: list[str] = []

    async def __call__(self, **kwargs: object) -> CompletionResult:
        self.calls.append(kwargs)
        messages = kwargs["messages"]
        assert isinstance(messages, list)
        payload = json.loads(messages[1]["content"])
        listings = payload["listings"]
        self.sent_titles.extend(item["title"] for item in listings)
        labelled = [
            {"id": item["id"], "label": self._label_for(item["title"])}
            for item in listings
        ]
        return CompletionResult(json.dumps({"listings": labelled}))


def make_airpods_request(*, name: str = "Apple AirPods Pro 2") -> MarketAnalysisRequest:
    return MarketAnalysisRequest.model_validate(
        {
            "name": name,
            "description": "Auriculares con estuche original",
            "category": "Audio",
            "brand": "Apple",
            "model": AIRPODS_TARGET,
            "conditionScore": 85,
            "conditionLabel": "Como nuevo",
            "sources": ["wallapop"],
            "includeRecommendation": False,
        }
    )


def make_listings(titles: list[str]) -> list[MarketListingSample]:
    return [
        MarketListingSample(
            title=title,
            price=200 + index,
            platform="wallapop",
            condition="Buen estado",
            url=f"https://example.com/{index}",
        )
        for index, title in enumerate(titles)
    ]


def make_chat(settings: object, completion: object) -> DeepSeekChat:
    return DeepSeekChat(settings, completion=completion)  # type: ignore[arg-type]


def make_relevance_filter(
    **overrides: object,
) -> tuple[LlmRelevanceFilter, LabelingCompletion]:
    label_by_title = dict(AIRPODS_MATRIX)
    completion = LabelingCompletion(lambda title: label_by_title.get(title, "unrelated"))
    settings = make_settings(**overrides)
    return LlmRelevanceFilter(settings, chat=make_chat(settings, completion)), completion
