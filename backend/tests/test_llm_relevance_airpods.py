"""AirPods matrix: no prefilter, only `exact` accepted, prompt contract."""

from __future__ import annotations

import json
from time import monotonic

from app.mcp.llm_relevance import SYSTEM_PROMPT
from tests.llm_relevance_support import (
    AIRPODS_MATRIX,
    make_airpods_request,
    make_listings,
    make_relevance_filter,
)


async def test_all_sanitised_listings_reach_the_llm_and_only_exact_is_accepted() -> None:
    relevance, completion = make_relevance_filter()
    titles = [title for title, _ in AIRPODS_MATRIX]

    accepted = await relevance.classify(
        make_airpods_request(), make_listings(titles), monotonic() + 5
    )

    assert [listing.title for listing in accepted] == [
        "AirPods Pro 2",
        "Apple AirPods Pro 2",
        "AirPods Pro 2nd generation",
        "AirPods Pro 2 con estuche",
    ]
    assert completion.sent_titles == titles
    assert completion.calls[0]["model"] == "deepseek-flash"
    assert completion.calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}


async def test_prompt_carries_the_target_fields_and_the_airpods_rules() -> None:
    relevance, completion = make_relevance_filter()
    listings = make_listings(["AirPods Pro 2", "Funda para AirPods Pro 2"])

    await relevance.classify(make_airpods_request(), listings, monotonic() + 5)

    messages = completion.calls[0]["messages"]
    payload = json.loads(messages[1]["content"])
    assert payload["target"] == {
        "name": "Apple AirPods Pro 2",
        "brand": "Apple",
        "model": "AirPods Pro 2",
        "category": "Audio",
        "description": "Auriculares con estuche original",
        "conditionLabel": "Como nuevo",
        "conditionScore": 85,
    }
    assert [item["title"] for item in payload["listings"]] == [
        "AirPods Pro 2",
        "Funda para AirPods Pro 2",
    ]
    for title, _label in AIRPODS_MATRIX:
        assert title in SYSTEM_PROMPT
    assert "con estuche" in SYSTEM_PROMPT
    assert "solo izquierdo" in SYSTEM_PROMPT
    assert "para piezas" in SYSTEM_PROMPT
