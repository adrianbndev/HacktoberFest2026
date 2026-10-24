"""HTTP client reuse, jitter and partial results for Milanuncios."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from app.mcp import connector_base
from app.mcp.connectors import MilanunciosConnector

FIXTURES = Path(__file__).parent / "fixtures"
Handler = Callable[[httpx.Request], httpx.Response]


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _static(body: str, status_code: int = 200) -> Handler:
    return lambda request: httpx.Response(status_code, text=body)


async def test_milanuncios_fetches_every_configured_page() -> None:
    requested: list[str | None] = []
    body = _fixture("milanuncios_search_v2.html")

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.params.get("pagina"))
        return httpx.Response(200, text=body)

    async with _client(handler) as client:
        result = await MilanunciosConnector(
            client=client,
            max_pages=3,
            page_delay_min_sec=0,
            page_delay_max_sec=0,
        ).search("iPhone 13 128GB")

    assert requested == [None, "2", "3"]
    assert result.ok is True
    assert result.partial is False
    assert len(result.listings) == 6


async def test_milanuncios_reuses_one_client_and_its_cookies_across_pages() -> None:
    body = _fixture("milanuncios_search_v2.html")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        headers = {"set-cookie": "px_session=abc; Path=/"} if len(requests) == 1 else None
        return httpx.Response(200, text=body, headers=headers)

    async with _client(handler) as client:
        result = await MilanunciosConnector(
            client=client,
            max_pages=3,
            page_delay_min_sec=0,
            page_delay_max_sec=0,
        ).search("iPhone 13 128GB")

    assert result.ok is True
    assert len(requests) == 3
    assert requests[0].headers.get("referer") is None
    assert requests[1].headers["referer"] == (
        "https://www.milanuncios.com/anuncios/?s=iPhone+13+128GB"
    )
    assert requests[2].headers["referer"] == (
        "https://www.milanuncios.com/anuncios/?s=iPhone+13+128GB&pagina=2"
    )
    assert requests[1].headers["origin"] == "https://www.milanuncios.com"
    assert requests[1].headers["cookie"] == "px_session=abc"
    assert requests[2].headers["cookie"] == "px_session=abc"


async def test_milanuncios_creates_a_single_owned_client_per_search(monkeypatch) -> None:
    body = _fixture("milanuncios_search_v2.html")
    owned_client = _client(_static(body))
    created: list[dict[str, object]] = []

    def factory(**kwargs: object) -> httpx.AsyncClient:
        created.append(kwargs)
        return owned_client

    monkeypatch.setattr(connector_base.httpx, "AsyncClient", factory)

    result = await MilanunciosConnector(
        max_pages=3,
        page_delay_min_sec=0,
        page_delay_max_sec=0,
    ).search("iPhone 13 128GB")

    assert result.ok is True
    assert len(result.listings) == 6
    assert len(created) == 1
    assert created[0]["follow_redirects"] is True
    assert owned_client.is_closed is True


def test_milanuncios_rejects_inverted_page_delays() -> None:
    with pytest.raises(ValueError):
        MilanunciosConnector(page_delay_min_sec=1.0, page_delay_max_sec=0.5)


async def test_milanuncios_returns_previous_pages_when_a_later_page_blocks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    body = _fixture("milanuncios_search_v2.html")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 2:
            return httpx.Response(200, text=_fixture("milanuncios_blocked.html"))
        return httpx.Response(200, text=body)

    caplog.set_level(logging.WARNING, logger="app.mcp.connector_base")
    async with _client(handler) as client:
        result = await MilanunciosConnector(
            client=client,
            max_pages=3,
            page_delay_min_sec=0,
            page_delay_max_sec=0,
        ).search("iPhone 13 128GB")

    assert calls == 2
    assert result.ok is True
    assert result.partial is True
    assert result.failure_reason is None
    assert [listing.price for listing in result.listings] == [299, 250]
    assert "blocked_http_200" in caplog.text


async def test_milanuncios_blocked_first_page_stays_a_blocked_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_fixture("milanuncios_blocked.html"))

    async with _client(handler) as client:
        result = await MilanunciosConnector(
            client=client,
            max_pages=3,
            page_delay_min_sec=0,
            page_delay_max_sec=0,
        ).search("iPhone 13 128GB")

    assert result.ok is False
    assert result.partial is False
    assert result.listings == ()
    assert result.failure_reason == "blocked_http_200"
