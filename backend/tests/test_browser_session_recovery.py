"""BrowserSessionManager crash recovery and timeout behaviour."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from app.mcp.browser.session import BrowserUnavailableError
from tests.test_browser_session import FakeFactory, FakeMCPClient, _manager


class OneCrashFactory(FakeFactory):
    """Only the first spawned client fails; the restart must recover."""

    def __call__(self, command: Sequence[str]) -> FakeMCPClient:
        client = super().__call__(command)
        if len(self.clients) == 1:
            client.fail_tools.add("evaluate_script")
        return client


async def test_a_crashed_client_is_restarted_once() -> None:
    factory = OneCrashFactory()
    manager = _manager(factory)

    async with manager.session() as page:
        assert await page.evaluate("() => 1") == {"value": 42}

    assert len(factory.clients) == 2
    assert factory.clients[0].closed is True
    assert manager.connected is True


async def test_restart_gives_up_after_one_retry() -> None:
    factory = FakeFactory(fail_tools=("evaluate_script",))
    manager = _manager(factory)

    with pytest.raises(BrowserUnavailableError):
        async with manager.session() as page:
            await page.evaluate("() => 1")

    assert len(factory.clients) == 2
    assert all(client.closed for client in factory.clients)


async def test_a_blocking_tool_call_times_out() -> None:
    factory = FakeFactory(delay_sec=0.3)
    manager = _manager(factory, timeout_sec=0.03)

    with pytest.raises(BrowserUnavailableError):
        await manager.invoke("list_pages", {})

    assert manager.connected is False
    assert manager.last_error is not None


async def test_health_probe_surfaces_a_crash() -> None:
    factory = FakeFactory(fail_tools=("list_pages", "evaluate_script"))
    manager = _manager(factory)

    health = await manager.health(probe=True)

    assert health.connected is False
    assert health.last_error is not None
