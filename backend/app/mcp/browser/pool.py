"""Bounded pool of MCP browser sessions (Phase 3).

Each slot owns its own `chrome-devtools-mcp` process and page, so sources do
not serialize on a process-wide lock. The pool only schedules slots; a slot's
own `BrowserSessionManager` keeps the per-page lock and crash recovery.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import Settings
from app.mcp.browser.session import (
    BrowserHealth,
    BrowserPage,
    BrowserSessionManager,
    BrowserUnavailableError,
    CdpProbe,
    ClientFactory,
)

POOL_EXHAUSTED = "browser_pool_exhausted"
POOL_CLOSED = "browser_pool_closed"


class BrowserSessionPool:
    """N independent MCP sessions; acquire one with `async with pool.session()`."""

    def __init__(
        self,
        settings: Settings,
        *,
        size: int | None = None,
        client_factory: ClientFactory | None = None,
        cdp_probe: CdpProbe | None = None,
        timeout_sec: float | None = None,
        acquire_timeout_sec: float | None = None,
    ) -> None:
        self._settings = settings
        self._size = size if size is not None else settings.market_browser_pool_size
        if not 1 <= self._size <= 3:
            raise ValueError("pool size must be between 1 and 3")
        self._slots = [
            BrowserSessionManager(
                settings,
                client_factory=client_factory,
                cdp_probe=cdp_probe,
                timeout_sec=timeout_sec,
            )
            for _ in range(self._size)
        ]
        self._free: asyncio.Queue[BrowserSessionManager] = asyncio.Queue()
        for slot in self._slots:
            self._free.put_nowait(slot)
        self._acquire_timeout_sec = (
            acquire_timeout_sec
            if acquire_timeout_sec is not None
            else settings.market_source_timeout_sec
        )
        self._closed = False

    @property
    def size(self) -> int:
        return self._size

    @property
    def url(self) -> str:
        return self._settings.cdp_url

    @property
    def connected(self) -> bool:
        return any(slot.connected for slot in self._slots)

    @property
    def last_error(self) -> str | None:
        if self.connected:
            return None
        return next(
            (slot.last_error for slot in self._slots if slot.last_error is not None),
            None,
        )

    async def start(self) -> None:
        """Spawn every slot eagerly (health probes can also do it lazily)."""
        await asyncio.gather(*(slot.start() for slot in self._slots))

    async def stop(self) -> None:
        """Close every page and MCP process; safe to call twice."""
        self._closed = True
        await asyncio.gather(*(slot.stop() for slot in self._slots))

    async def health(self, *, probe: bool = False) -> BrowserHealth:
        results = await asyncio.gather(
            *(slot.health(probe=probe) for slot in self._slots)
        )
        return BrowserHealth(
            connected=any(result.connected for result in results),
            url=self.url,
            last_error=(
                None
                if any(result.connected for result in results)
                else next(
                    (
                        result.last_error
                        for result in results
                        if result.last_error is not None
                    ),
                    None,
                )
            ),
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[BrowserPage]:
        """Acquire a free slot; the slot returns to the pool on every exit path."""
        if self._closed:
            raise BrowserUnavailableError(POOL_CLOSED)
        try:
            slot = await asyncio.wait_for(
                self._free.get(), timeout=self._acquire_timeout_sec
            )
        except TimeoutError as exc:
            raise BrowserUnavailableError(POOL_EXHAUSTED) from exc
        try:
            async with slot.session() as page:
                yield page
        finally:
            self._free.put_nowait(slot)


__all__ = ["POOL_CLOSED", "POOL_EXHAUSTED", "BrowserSessionPool"]
