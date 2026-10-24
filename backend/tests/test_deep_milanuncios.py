"""Hybrid Milanuncios transport: HTTP first, real browser fallback."""

from __future__ import annotations

import asyncio
from time import monotonic

from app.mcp.connectors import ConnectorResult
from app.mcp.deep_milanuncios import MIN_USABLE_LISTINGS, MilanunciosHybridRunner
from app.models.sdd import MarketListingSample
from tests.deep_analysis_support import FakeBrowser, FakeSource
from tests.support import make_settings


class FakeConnector:
    platform = "milanuncios"

    def __init__(
        self,
        prices: list[int] | None = None,
        *,
        failure_reason: str | None = None,
        partial: bool = False,
        delay_sec: float = 0.0,
    ) -> None:
        self.prices = prices or []
        self.failure_reason = failure_reason
        self.partial = partial
        self.delay_sec = delay_sec
        self.calls = 0

    async def search(self, query: str) -> ConnectorResult:
        self.calls += 1
        if self.delay_sec:
            await asyncio.sleep(self.delay_sec)
        listings = tuple(
            MarketListingSample(
                title=f"{query} {index}",
                price=price,
                platform="milanuncios",
                condition="Buen estado",
                url=f"https://www.milanuncios.com/item/{index}",
            )
            for index, price in enumerate(self.prices)
        )
        return ConnectorResult(
            "milanuncios",
            listings=listings,
            failure_reason=self.failure_reason,
            partial=self.partial,
        )


def _runner(
    *,
    transport: str = "auto",
    browser: FakeBrowser | None = None,
    browser_source: FakeSource | None = None,
    http: FakeConnector | None = None,
) -> tuple[MilanunciosHybridRunner, FakeBrowser, FakeSource, FakeConnector]:
    settings = make_settings(market_milanuncios_transport=transport)
    fake_browser = browser or FakeBrowser()
    source = browser_source or FakeSource("milanuncios", [30, 35, 40])
    connector = http or FakeConnector([30, 35, 40])
    runner = MilanunciosHybridRunner(
        settings,
        fake_browser,  # type: ignore[arg-type]
        browser_source=source,
        http_connector=connector,
    )
    return runner, fake_browser, source, connector


async def test_auto_uses_http_when_it_reaches_the_threshold() -> None:
    runner, browser, source, http = _runner(
        http=FakeConnector(list(range(30, 30 + MIN_USABLE_LISTINGS)))
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == MIN_USABLE_LISTINGS
    assert source.calls == 0
    assert browser.sessions == 0
    assert http.calls == 1


async def test_auto_falls_back_to_the_browser_on_a_short_http_sample() -> None:
    runner, browser, source, _ = _runner(
        browser_source=FakeSource("milanuncios", list(range(30, 40))),
        http=FakeConnector([30, 35, 40]),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == 10
    assert source.calls == 1
    assert browser.sessions == 1


async def test_auto_falls_back_when_http_is_blocked() -> None:
    runner, _, source, _ = _runner(
        browser_source=FakeSource("milanuncios", list(range(30, 40))),
        http=FakeConnector(failure_reason="blocked_http_200"),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert source.calls == 1


async def test_auto_keeps_http_when_the_browser_is_also_blocked() -> None:
    runner, _, source, _ = _runner(
        browser_source=FakeSource("milanuncios", status="blocked"),
        http=FakeConnector([30, 35, 40]),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == 3
    assert source.calls == 1


async def test_auto_reports_blocked_when_both_transports_block() -> None:
    runner, _, source, _ = _runner(
        browser_source=FakeSource("milanuncios", status="blocked"),
        http=FakeConnector(failure_reason="blocked_http_200"),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "blocked"
    assert outcome.listings == ()
    assert source.calls == 1


async def test_http_transport_returns_a_partial_http_sample() -> None:
    runner, browser, source, _ = _runner(
        transport="http",
        http=FakeConnector([30, 35, 40], partial=True),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == 3
    assert source.calls == 0
    assert browser.sessions == 0


async def test_auto_keeps_a_partial_sample_above_the_threshold() -> None:
    runner, browser, source, _ = _runner(
        browser_source=FakeSource("milanuncios", list(range(30, 40))),
        http=FakeConnector(list(range(30, 30 + MIN_USABLE_LISTINGS)), partial=True),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == MIN_USABLE_LISTINGS
    assert source.calls == 0
    assert browser.sessions == 0


async def test_auto_falls_back_to_the_browser_on_a_short_partial_sample() -> None:
    runner, _, source, _ = _runner(
        browser_source=FakeSource("milanuncios", list(range(30, 40))),
        http=FakeConnector([30, 35, 40], partial=True),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == 10
    assert source.calls == 1


async def test_http_transport_never_touches_the_browser() -> None:
    runner, browser, source, _ = _runner(
        transport="http",
        http=FakeConnector([30, 35, 40]),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == 3
    assert source.calls == 0
    assert browser.sessions == 0


async def test_browser_transport_never_touches_http() -> None:
    runner, _, source, http = _runner(
        transport="browser",
        browser_source=FakeSource("milanuncios", list(range(30, 40))),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert source.calls == 1
    assert http.calls == 0


async def test_http_no_listings_falls_back_to_the_browser() -> None:
    runner, _, source, _ = _runner(
        browser_source=FakeSource("milanuncios", list(range(30, 40))),
        http=FakeConnector(failure_reason="no_listings_parsed"),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert source.calls == 1


async def test_a_partial_http_result_survives_an_unavailable_browser() -> None:
    runner, _, _, _ = _runner(
        browser=FakeBrowser(fail=True),
        http=FakeConnector([30, 35, 40], partial=True),
    )

    outcome = await runner.collect("Silla", monotonic() + 5)

    assert outcome.status == "ok"
    assert len(outcome.listings) == 3


async def test_an_expired_deadline_returns_timeout_without_calls() -> None:
    runner, _, source, http = _runner()

    outcome = await runner.collect("Silla", monotonic() - 1)

    assert outcome.status == "timeout"
    assert source.calls == 0
    assert http.calls == 0
