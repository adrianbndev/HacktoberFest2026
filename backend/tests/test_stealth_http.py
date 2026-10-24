"""Header coherence and jitter behaviour of the stealth HTTP layer."""

from __future__ import annotations

import random

import pytest
from app.mcp import stealth_http
from app.mcp.stealth_http import (
    MCP_HUMAN_JITTER_MAX_SEC,
    MCP_HUMAN_JITTER_MIN_SEC,
    USER_AGENT_POOL,
    build_headers,
    human_jitter,
)


def test_user_agent_pool_is_modern_and_varied() -> None:
    agents = {profile.user_agent for profile in USER_AGENT_POOL}

    assert len(USER_AGENT_POOL) >= 6
    assert len(agents) == len(USER_AGENT_POOL)
    assert any("Chrome/128" in agent for agent in agents)
    assert any("Safari/605" in agent or "Version/17" in agent for agent in agents)
    assert any("Firefox/130" in agent for agent in agents)


def test_headers_are_spanish_and_match_the_user_agent_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for profile in USER_AGENT_POOL:
        monkeypatch.setattr(stealth_http, "USER_AGENT_POOL", (profile,))
        headers = build_headers(random.Random(7))

        assert headers["User-Agent"] == profile.user_agent
        assert headers["Accept-Language"].startswith("es-ES")
        if profile.sec_ch_ua_platform is None:
            assert "Sec-Ch-Ua-Platform" not in headers
            assert "Sec-Ch-Ua-Mobile" not in headers
        else:
            assert headers["Sec-Ch-Ua-Platform"] == f'"{profile.sec_ch_ua_platform}"'
            assert headers["Sec-Ch-Ua-Mobile"] == "?0"


def test_default_jitter_matches_spec_budget() -> None:
    assert MCP_HUMAN_JITTER_MIN_SEC == 0.65
    assert MCP_HUMAN_JITTER_MAX_SEC == 1.20


async def test_jitter_is_disabled_with_zero_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(stealth_http.asyncio, "sleep", fake_sleep)

    await human_jitter(0, 0)

    assert sleep_calls == []


async def test_jitter_sleeps_inside_the_requested_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(stealth_http.asyncio, "sleep", fake_sleep)

    await human_jitter(0.2, 0.6, random.Random(3))

    assert len(sleep_calls) == 1
    assert 0.2 <= sleep_calls[0] <= 0.6


@pytest.mark.parametrize(("low", "high"), [(-1, 0.1), (0.5, 0.2)])
async def test_jitter_rejects_invalid_bounds(low: float, high: float) -> None:
    with pytest.raises(ValueError):
        await human_jitter(low, high)
