"""CDP reachability probe: fail fast without letting the MCP launch Chrome."""

from __future__ import annotations

from typing import Any

import pytest
from app.mcp.browser.session import BrowserSessionManager, BrowserUnavailableError
from tests.support import make_settings


class NeverFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, command: Any) -> Any:
        self.calls += 1
        raise AssertionError("the MCP must not start when CDP is unreachable")


async def test_unreachable_cdp_is_reported_before_the_mcp_starts() -> None:
    factory = NeverFactory()

    def _fail_probe(url: str, timeout: float) -> None:
        raise OSError("connection refused")

    manager = BrowserSessionManager(
        make_settings(), client_factory=factory, cdp_probe=_fail_probe
    )

    with pytest.raises(BrowserUnavailableError):
        await manager.start()

    assert factory.calls == 0
    assert manager.connected is False
    assert manager.last_error is not None
    assert "cdp_unreachable" in manager.last_error
