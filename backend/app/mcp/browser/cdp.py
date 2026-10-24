"""CDP reachability and small parsing helpers for the browser session."""

from __future__ import annotations

import re
import socket
from urllib.parse import urlsplit

PAGE_ID_PATTERN = re.compile(r"^\s*(\d+):", re.MULTILINE)
DEFAULT_PAGE_ID = 1
MAX_ERROR_LENGTH = 300
BROWSER_ENV = {"CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1"}
SCROLL_FUNCTION = (
    "() => { window.scrollTo(0, document.body.scrollHeight); return true; }"
)


def probe_cdp(url: str, timeout_sec: float) -> None:
    """Fail fast when Chrome/CDP is unreachable; never launch a browser here."""
    parts = urlsplit(url)
    if not parts.hostname:
        raise OSError("CDP URL has no host")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    timeout = max(0.05, min(timeout_sec, 3.0))
    with socket.create_connection((parts.hostname, port), timeout=timeout):
        pass


def parse_page_id(text: str) -> int:
    """Extract the first `N: url` page id from `list_pages` output."""
    match = PAGE_ID_PATTERN.search(text)
    return int(match.group(1)) if match is not None else DEFAULT_PAGE_ID


def sanitize(message: str) -> str:
    cleaned = " ".join(message.split())
    return cleaned[:MAX_ERROR_LENGTH] or "browser_unavailable"
