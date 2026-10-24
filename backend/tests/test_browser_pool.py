"""BrowserSessionPool: per-slot isolation, bounded concurrency and cleanup."""

from __future__ import annotations

import asyncio

import pytest
from app.mcp.browser.pool import (
    POOL_CLOSED,
    POOL_EXHAUSTED,
    BrowserSessionPool,
)
from app.mcp.browser.session import BrowserUnavailableError
from tests.support import make_settings
from tests.test_browser_session import FakeFactory


def _pool(
    factory: FakeFactory,
    *,
    size: int | None = None,
    acquire_timeout_sec: float = 1.0,
    timeout_sec: float = 1.0,
) -> BrowserSessionPool:
    return BrowserSessionPool(
        make_settings(market_browser_pool_size=size or 2),
        size=size,
        client_factory=factory,
        cdp_probe=lambda url, timeout: None,
        timeout_sec=timeout_sec,
        acquire_timeout_sec=acquire_timeout_sec,
    )


async def test_pool_defaults_to_two_lazily_spawned_slots() -> None:
    factory = FakeFactory()
    pool = _pool(factory)

    assert pool.size == 2
    assert factory.clients == []

    async with pool.session() as first:
        assert first.page_id == 2
    async with pool.session() as second:
        assert second.page_id == 2

    assert len(factory.clients) == 2
    assert all(client.initialized for client in factory.clients)


async def test_three_concurrent_sessions_never_exceed_two_slots() -> None:
    factory = FakeFactory(delay_sec=0.01)
    pool = _pool(factory)
    active = 0
    max_active = 0
    completed = 0

    async def worker() -> None:
        nonlocal active, max_active, completed
        async with pool.session():
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1
            completed += 1

    await asyncio.gather(*(worker() for _ in range(3)))

    assert completed == 3
    assert max_active == 2
    assert len(factory.clients) == 2


async def test_a_slot_is_returned_even_when_the_worker_raises() -> None:
    factory = FakeFactory()
    pool = _pool(factory, size=1)

    with pytest.raises(RuntimeError):
        async with pool.session():
            raise RuntimeError("boom")

    async with pool.session() as page:
        await page.navigate("https://example.com")

    assert len(factory.clients) == 1
    assert ("navigate_page", {"pageId": 2, "url": "https://example.com"}) in (
        factory.clients[0].calls
    )


async def test_pool_exhaustion_times_out_with_a_typed_error() -> None:
    factory = FakeFactory()
    pool = _pool(factory, size=1, acquire_timeout_sec=0.02)

    async with pool.session():
        with pytest.raises(BrowserUnavailableError) as exc_info:
            async with pool.session():
                pass

    assert POOL_EXHAUSTED in str(exc_info.value)


async def test_a_closed_pool_rejects_new_sessions() -> None:
    factory = FakeFactory()
    pool = _pool(factory)
    await pool.stop()

    with pytest.raises(BrowserUnavailableError) as exc_info:
        async with pool.session():
            pass

    assert POOL_CLOSED in str(exc_info.value)


async def test_stop_closes_every_slot_and_health_reflects_it() -> None:
    factory = FakeFactory()
    pool = _pool(factory)

    async with pool.session():
        pass
    async with pool.session():
        pass
    assert (await pool.health()).connected is True

    await pool.stop()

    assert all(client.closed for client in factory.clients)
    assert (await pool.health()).connected is False
    assert pool.last_error is None


async def test_health_probe_does_not_serialize_the_slots() -> None:
    factory = FakeFactory(delay_sec=0.01)
    pool = _pool(factory)

    async with pool.session():
        pass
    async with pool.session():
        pass

    health = await pool.health(probe=True)

    assert health.connected is True
    assert health.url == "http://market-browser:9222"
    assert len(factory.clients) == 2


async def test_cancelling_a_session_releases_its_slot() -> None:
    factory = FakeFactory()
    pool = _pool(factory, size=1, acquire_timeout_sec=0.05)
    entered = asyncio.Event()

    async def holder() -> None:
        async with pool.session():
            entered.set()
            await asyncio.sleep(10)

    task = asyncio.create_task(holder())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    async with pool.session() as page:
        assert page.page_id == 2


async def test_each_slot_creates_its_own_page() -> None:
    factory = FakeFactory()
    pool = _pool(factory)

    async with pool.session():
        pass
    async with pool.session():
        pass

    new_page_calls = [
        call
        for client in factory.clients
        for call in client.calls
        if call[0] == "new_page"
    ]
    assert len(new_page_calls) == 2
    urls = [str(call[1].get("url")) for call in new_page_calls]
    assert any("browser-pool-slot-0" in url for url in urls)
    assert any("browser-pool-slot-1" in url for url in urls)
