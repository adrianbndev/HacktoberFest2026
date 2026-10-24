"""BrowserSessionManager behaviour with a fake MCP client (no CDP, no network)."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Sequence
from typing import Any

import pytest
from app.mcp.browser.mcp_client import MCPError
from app.mcp.browser.session import (
    BrowserSessionManager,
    BrowserUnavailableError,
    parse_page_id,
)
from tests.support import make_settings


class FakeMCPClient:
    def __init__(
        self,
        *,
        pages: str = "1: about:blank",
        fail_tools: Sequence[str] = (),
        delay_sec: float = 0.0,
    ) -> None:
        self.pages = pages
        self.fail_tools = set(fail_tools)
        self.delay_sec = delay_sec
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.initialized = False
        self.closed = False
        self.active = 0
        self.max_active = 0
        self._guard = threading.Lock()

    def initialize(self) -> dict[str, Any]:
        self.initialized = True
        return {"protocolVersion": "test"}

    def call_tool_text(self, name: str, arguments: dict[str, Any]) -> str:
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.delay_sec:
                time.sleep(self.delay_sec)
            self.calls.append((name, dict(arguments)))
            if name in self.fail_tools:
                raise MCPError(f"{name} crashed")
            if name == "list_pages":
                return self.pages
            if name == "evaluate_script":
                return '{"value": 42}'
            return "{}"
        finally:
            with self._guard:
                self.active -= 1

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, **client_kwargs: Any) -> None:
        self.clients: list[FakeMCPClient] = []
        self.commands: list[tuple[str, ...]] = []
        self._kwargs = client_kwargs

    def __call__(self, command: Sequence[str]) -> FakeMCPClient:
        self.commands.append(tuple(command))
        client = FakeMCPClient(**self._kwargs)
        self.clients.append(client)
        return client


def _manager(factory: FakeFactory, *, timeout_sec: float = 1.0) -> BrowserSessionManager:
    return BrowserSessionManager(
        make_settings(),
        client_factory=factory,
        cdp_probe=lambda url, timeout: None,
        timeout_sec=timeout_sec,
    )


async def test_client_is_spawned_lazily_and_reused() -> None:
    factory = FakeFactory()
    manager = _manager(factory)

    assert factory.clients == []
    async with manager.session() as first:
        assert first.page_id == 1
    async with manager.session() as second:
        assert second.page_id == 1

    assert len(factory.clients) == 1
    assert factory.clients[0].initialized is True
    assert manager.connected is True


async def test_command_attaches_to_the_shared_browser_without_automation_flags() -> None:
    factory = FakeFactory()
    manager = _manager(factory)

    async with manager.session() as page:
        await page.navigate("https://www.ebay.es/sch/i.html?_nkw=silla")

    command = " ".join(factory.commands[0])
    assert "chrome-devtools-mcp@1.10.1" in command
    assert "--browserUrl http://market-browser:9222" in command
    assert "--headless" not in command
    assert "--enable-automation" not in command


async def test_navigate_and_evaluate_go_through_the_same_page() -> None:
    factory = FakeFactory()
    manager = _manager(factory)

    async with manager.session() as page:
        await page.navigate("https://example.com")
        payload = await page.evaluate("() => ({ value: 42 })")

    assert payload == {"value": 42}
    calls = factory.clients[0].calls
    assert ("navigate_page", {"pageId": 1, "url": "https://example.com"}) in calls
    assert calls[-1][0] == "evaluate_script"


async def test_scroll_repeats_the_scroll_script() -> None:
    factory = FakeFactory()
    manager = _manager(factory)

    async with manager.session() as page:
        await page.scroll(steps=3, pause_ms=0)

    scrolls = [call for call in factory.clients[0].calls if call[0] == "evaluate_script"]
    assert len(scrolls) == 3


async def test_one_lock_serializes_concurrent_sessions() -> None:
    factory = FakeFactory()
    manager = _manager(factory)
    active = 0
    max_active = 0

    async def worker() -> None:
        nonlocal active, max_active
        async with manager.session():
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1

    await asyncio.gather(*(worker() for _ in range(4)))

    assert max_active == 1


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


async def test_stop_closes_the_page_and_the_mcp_process() -> None:
    factory = FakeFactory()
    manager = _manager(factory)

    async with manager.session() as page:
        await page.navigate("https://example.com")
    await manager.stop()

    first = factory.clients[0]
    assert ("close_page", {"pageId": 1}) in first.calls
    assert first.closed is True
    assert manager.connected is False


async def test_health_reports_state_and_can_probe() -> None:
    factory = FakeFactory()
    manager = _manager(factory)

    initial = await manager.health()
    assert initial.connected is False
    assert initial.url == "http://market-browser:9222"
    assert initial.last_error is None

    async with manager.session():
        pass

    assert (await manager.health()).connected is True
    assert (await manager.health(probe=True)).connected is True


async def test_health_probe_surfaces_a_crash() -> None:
    factory = FakeFactory(fail_tools=("list_pages", "evaluate_script"))
    manager = _manager(factory)

    health = await manager.health(probe=True)

    assert health.connected is False
    assert health.last_error is not None


def test_parse_page_id_handles_the_list_pages_format() -> None:
    assert parse_page_id("1: about:blank\n2: https://example.com") == 1
    assert parse_page_id("no pages") == 1
