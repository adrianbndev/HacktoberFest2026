"""Lazy, single-page MCP browser session with one lock and crash recovery.

The MCP server is started by `BrowserSessionManager` (never Chrome itself):
`chrome-devtools-mcp@1.10.1 --browserUrl <CDP_URL>` attaches to the headful
browser launched by the `market-browser` container. All blocking stdio calls run
in a worker thread so the FastAPI event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import re
import shlex
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings
from app.mcp.browser.mcp_client import MCPClient, MCPError, parse_tool_payload

PAGE_ID_PATTERN = re.compile(r"^\s*(\d+):", re.MULTILINE)
DEFAULT_PAGE_ID = 1
MAX_ERROR_LENGTH = 300
BROWSER_ENV = {"CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1"}
SCROLL_FUNCTION = (
    "() => { window.scrollTo(0, document.body.scrollHeight); return true; }"
)


class BrowserUnavailableError(RuntimeError):
    """The MCP server or the CDP browser could not be reached."""


class McpClientProtocol(Protocol):
    """The subset of the stdio client the session manager depends on."""

    def initialize(self) -> dict[str, Any]: ...

    def call_tool_text(self, name: str, arguments: dict[str, Any]) -> str: ...

    def close(self) -> None: ...


ClientFactory = Callable[[Sequence[str]], McpClientProtocol]


@dataclass(frozen=True, slots=True)
class BrowserHealth:
    connected: bool
    url: str
    last_error: str | None


class BrowserPage:
    """A page handle bound to the manager's single lock-protected tab."""

    def __init__(self, manager: BrowserSessionManager, page_id: int) -> None:
        self._manager = manager
        self._page_id = page_id

    @property
    def page_id(self) -> int:
        return self._page_id

    async def navigate(self, url: str) -> None:
        await self._manager.invoke(
            "navigate_page", {"pageId": self._page_id, "url": url}
        )

    async def evaluate(self, function: str) -> Any:
        text = await self._manager.invoke(
            "evaluate_script", {"pageId": self._page_id, "function": function}
        )
        return parse_tool_payload(text)

    async def scroll(self, *, steps: int = 4, pause_ms: int = 350) -> None:
        for _ in range(max(1, steps)):
            await self.evaluate(SCROLL_FUNCTION)
            await asyncio.sleep(max(0, pause_ms) / 1000)

    async def close(self) -> None:
        await self._manager.invoke("close_page", {"pageId": self._page_id})


class BrowserSessionManager:
    """Owns the MCP client: lazy spawn, one lock, one page, restart on crash."""

    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: ClientFactory | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        self._settings = settings
        self._timeout_sec = (
            timeout_sec if timeout_sec is not None else settings.market_browser_timeout_sec
        )
        self._client_factory: ClientFactory = client_factory or self._spawn_client
        self._lock = asyncio.Lock()
        self._client: McpClientProtocol | None = None
        self._page_id: int | None = None
        self._last_error: str | None = None

    @property
    def url(self) -> str:
        return self._settings.cdp_url

    @property
    def command(self) -> tuple[str, ...]:
        command = shlex.split(self._settings.market_browser_mcp_command)
        if "--browserUrl" not in command:
            command += ["--browserUrl", self._settings.cdp_url]
        return tuple(command)

    @property
    def connected(self) -> bool:
        return self._client is not None and self._last_error is None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        async with self._lock:
            await self._ensure_client()

    async def stop(self) -> None:
        """Close the tab(s) and the MCP process; safe to call twice."""
        async with self._lock:
            await self._close_page_best_effort()
            await self._discard_client()

    async def health(self, *, probe: bool = False) -> BrowserHealth:
        """Report state; `probe=True` performs a cheap `list_pages` round-trip."""
        if probe:
            async with self._lock:
                try:
                    client = await self._ensure_client()
                    await self._call(client, "list_pages", {})
                    self._last_error = None
                except (BrowserUnavailableError, MCPError, OSError, TimeoutError) as exc:
                    self._last_error = _sanitize(str(exc))
                    await self._discard_client()
        return BrowserHealth(
            connected=self.connected, url=self.url, last_error=self._last_error
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[BrowserPage]:
        """Serialize browser use; the lock is released only when the block exits."""
        async with self._lock:
            page = await self._ensure_page()
            yield page

    async def invoke(
        self, tool: str, arguments: dict[str, Any], *, retries: int = 1
    ) -> str:
        """Call a tool, restarting the MCP client once if it crashed."""
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            client = await self._ensure_client()
            try:
                return await self._call(client, tool, arguments)
            except (MCPError, OSError, TimeoutError) as exc:
                last_error = exc
                self._last_error = _sanitize(str(exc))
                await self._discard_client()
                if attempt >= retries:
                    break
        raise BrowserUnavailableError(self._last_error or "browser_unavailable") from last_error

    async def _call(
        self, client: McpClientProtocol, tool: str, arguments: dict[str, Any]
    ) -> str:
        return await asyncio.wait_for(
            asyncio.to_thread(client.call_tool_text, tool, arguments),
            timeout=self._timeout_sec,
        )

    async def _ensure_client(self) -> McpClientProtocol:
        if self._client is not None:
            return self._client
        client = self._client_factory(self.command)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(client.initialize), timeout=self._timeout_sec
            )
        except (MCPError, OSError, TimeoutError) as exc:
            self._last_error = _sanitize(str(exc))
            await asyncio.to_thread(client.close)
            raise BrowserUnavailableError(self._last_error) from exc
        self._client = client
        self._last_error = None
        return client

    async def _ensure_page(self) -> BrowserPage:
        client = await self._ensure_client()
        if self._page_id is None:
            text = await self._call(client, "list_pages", {})
            self._page_id = parse_page_id(text)
        return BrowserPage(self, self._page_id)

    async def _close_page_best_effort(self) -> None:
        if self._page_id is None or self._client is None:
            return
        try:
            await self._call(self._client, "close_page", {"pageId": self._page_id})
        except (MCPError, OSError, TimeoutError):
            pass
        finally:
            self._page_id = None

    async def _discard_client(self) -> None:
        client = self._client
        self._client = None
        self._page_id = None
        if client is not None:
            await asyncio.to_thread(client.close)

    def _spawn_client(self, command: Sequence[str]) -> McpClientProtocol:
        return MCPClient(command, timeout_sec=self._timeout_sec + 5, env=BROWSER_ENV)


def parse_page_id(text: str) -> int:
    """Extract the first `N: url` page id from `list_pages` output."""
    match = PAGE_ID_PATTERN.search(text)
    return int(match.group(1)) if match is not None else DEFAULT_PAGE_ID


def _sanitize(message: str) -> str:
    cleaned = " ".join(message.split())
    return cleaned[:MAX_ERROR_LENGTH] or "browser_unavailable"
