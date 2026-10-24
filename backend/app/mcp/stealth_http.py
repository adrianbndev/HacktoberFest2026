"""Human-like HTTP fingerprinting and jitter for the stealth connectors."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

MCP_HUMAN_JITTER_MIN_SEC = 0.65
MCP_HUMAN_JITTER_MAX_SEC = 1.20
VALUATE_JITTER_MIN_SEC = 0.20
VALUATE_JITTER_MAX_SEC = 0.60

STEALTH_HEADERS_BASE: dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}


@dataclass(frozen=True, slots=True)
class UserAgentProfile:
    """A user agent plus the platform hint its real browser would send."""

    user_agent: str
    sec_ch_ua_platform: str | None


USER_AGENT_POOL: tuple[UserAgentProfile, ...] = (
    UserAgentProfile(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "macOS",
    ),
    UserAgentProfile(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Windows",
    ),
    UserAgentProfile(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Linux",
    ),
    UserAgentProfile(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        None,
    ),
    UserAgentProfile(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
        None,
    ),
    UserAgentProfile(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        None,
    ),
    UserAgentProfile(
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        None,
    ),
)


def build_headers(rng: random.Random | None = None) -> dict[str, str]:
    """Return coherent browser headers: UA family matches client hints."""
    chooser = rng or random
    profile = chooser.choice(USER_AGENT_POOL)
    headers = dict(STEALTH_HEADERS_BASE)
    headers["User-Agent"] = profile.user_agent
    if profile.sec_ch_ua_platform is not None:
        headers["Sec-Ch-Ua-Mobile"] = "?0"
        headers["Sec-Ch-Ua-Platform"] = f'"{profile.sec_ch_ua_platform}"'
    return headers


async def human_jitter(
    min_sec: float = MCP_HUMAN_JITTER_MIN_SEC,
    max_sec: float = MCP_HUMAN_JITTER_MAX_SEC,
    rng: random.Random | None = None,
) -> None:
    """Sleep a bounded random amount; ``max_sec <= 0`` disables it for tests."""
    if max_sec < 0 or min_sec < 0:
        raise ValueError("jitter bounds must be non-negative")
    if max_sec < min_sec:
        raise ValueError("max_sec must be >= min_sec")
    if max_sec <= 0:
        return
    chooser = rng or random
    await asyncio.sleep(chooser.uniform(min_sec, max_sec))
