"""Connector parsing against saved HTML snapshots; no network in CI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from app.mcp.connectors import (
    ConnectorResult,
    EbayConnector,
    MilanunciosConnector,
    WallapopConnector,
    looks_blocked,
)

FIXTURES = Path(__file__).parent / "fixtures"
Handler = Callable[[httpx.Request], httpx.Response]


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _static(body: str, status_code: int = 200) -> Handler:
    return lambda request: httpx.Response(status_code, text=body)


async def test_ebay_parses_saved_search_snapshot() -> None:
    async with _client(_static(_fixture("ebay_search.html"))) as client:
        result = await EbayConnector(client=client).search("iPhone 13 128GB")

    assert isinstance(result, ConnectorResult)
    assert result.ok is True
    assert [listing.price for listing in result.listings] == [330, 380]
    assert result.listings[0].title.startswith("iPhone 13 128GB Negro")
    assert result.listings[0].condition == "Como nuevo"
    assert result.listings[0].url is not None
    assert result.listings[0].url.startswith("https://www.ebay.es/itm/")
    assert result.listings[1].url == "https://www.ebay.es/itm/285600000001"


async def test_wallapop_reads_embedded_next_data() -> None:
    async with _client(_static(_fixture("wallapop_search.html"))) as client:
        result = await WallapopConnector(client=client).search("iPhone 13 128GB")

    assert result.ok is True
    assert [listing.price for listing in result.listings] == [325, 15, 350]
    first = result.listings[0]
    assert first.condition == "Como nuevo"
    assert first.url == "https://es.wallapop.com/item/iphone-13-128gb-abc123"
    assert all(listing.platform == "wallapop" for listing in result.listings)


async def test_milanuncios_parses_saved_search_snapshot() -> None:
    async with _client(_static(_fixture("milanuncios_search.html"))) as client:
        result = await MilanunciosConnector(client=client).search("iPhone 13 128GB")

    assert result.ok is True
    assert [listing.price for listing in result.listings] == [340, 280]
    assert result.listings[0].url is not None
    assert result.listings[0].url.startswith("https://www.milanuncios.com/moviles/")
    assert result.listings[1].condition == "Desgaste visible"
    assert result.listings[1].url == "https://www.milanuncios.com/moviles/iphone-13-987654321.htm"


@pytest.mark.parametrize("status_code", [403, 429])
async def test_blocked_status_marks_the_source_as_failed(status_code: int) -> None:
    async with _client(_static("<html>forbidden</html>", status_code)) as client:
        result = await EbayConnector(client=client).search("iPhone 13")

    assert result.ok is False
    assert result.listings == ()
    assert result.failure_reason == f"blocked_http_{status_code}"


async def test_captcha_markers_are_detected_even_with_http_200() -> None:
    body = _fixture("blocked_captcha.html")

    async with _client(_static(body)) as client:
        result = await MilanunciosConnector(client=client).search("iPhone 13")

    assert result.ok is False
    assert result.failure_reason == "blocked_http_200"
    assert looks_blocked(body, 200) is True


async def test_network_errors_never_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    async with _client(handler) as client:
        result = await WallapopConnector(client=client, timeout_sec=0.01).search("iPhone 13")

    assert result.ok is False
    assert result.listings == ()
    assert result.failure_reason == "network_error"


async def test_unexpected_errors_never_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise ValueError("boom")

    async with _client(handler) as client:
        result = await EbayConnector(client=client).search("iPhone 13")

    assert result.ok is False
    assert result.failure_reason == "unexpected_error"


@pytest.mark.parametrize("body", ["<html><body>sin anuncios</body></html>", ""])
async def test_empty_or_unparsable_pages_report_no_listings(body: str) -> None:
    async with _client(_static(body)) as client:
        result = await MilanunciosConnector(client=client).search("iPhone 13")

    assert result.ok is False
    assert result.failure_reason == "no_listings_parsed"


async def test_short_queries_are_rejected_without_a_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request expected for an empty query")

    async with _client(handler) as client:
        result = await EbayConnector(client=client).search(" ")

    assert result.failure_reason == "empty_query"


async def test_milanuncios_fetches_every_configured_page() -> None:
    requested: list[str | None] = []
    body = _fixture("milanuncios_search_v2.html")

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.params.get("pagina"))
        return httpx.Response(200, text=body)

    async with _client(handler) as client:
        result = await MilanunciosConnector(client=client, max_pages=3).search(
            "iPhone 13 128GB"
        )

    assert requested == [None, "2", "3"]
    assert result.ok is True
    assert len(result.listings) == 6


async def test_milanuncios_multi_page_stops_on_a_blocked_page() -> None:
    body = _fixture("milanuncios_search_v2.html")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 2:
            return httpx.Response(200, text=_fixture("milanuncios_blocked.html"))
        return httpx.Response(200, text=body)

    async with _client(handler) as client:
        result = await MilanunciosConnector(client=client, max_pages=3).search(
            "iPhone 13 128GB"
        )

    assert calls == 2
    assert result.ok is False
    assert result.listings == ()
    assert result.failure_reason == "blocked_http_200"


async def test_single_page_is_still_the_default() -> None:
    requested: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.params.get("pagina"))
        return httpx.Response(200, text=_fixture("milanuncios_search_v2.html"))

    async with _client(handler) as client:
        result = await MilanunciosConnector(client=client).search("iPhone 13 128GB")

    assert requested == [None]
    assert result.ok is True


async def test_milanuncios_parses_current_ad_card_markup() -> None:
    async with _client(_static(_fixture("milanuncios_search_v2.html"))) as client:
        result = await MilanunciosConnector(client=client).search("iPhone 13 128GB")

    assert result.ok is True
    assert [listing.price for listing in result.listings] == [299, 250]
    assert result.listings[0].title == "iPhone 13 128gb"
    assert result.listings[0].url == (
        "https://www.milanuncios.com/iphone/iphone-13-128gb-580489426.htm"
    )
    assert result.listings[1].url.startswith("https://www.milanuncios.com/iphone/")
    assert result.listings[1].condition == "Buen estado"
