"""Compatibility shim for the Phase 1 spike scripts.

The real implementation lives in `backend/app/mcp/browser/mcp_client.py` so the
backend never imports `scripts/`. Running `python scripts/browser_spike.py` adds
this directory (not `backend/`) to `sys.path`, hence the explicit path insert.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.mcp.browser.mcp_client import (  # noqa: E402
    MCP_PROTOCOL_VERSION,
    MCPClient,
    MCPError,
    parse_tool_payload,
    unwrap_result,
)

__all__ = [
    "MCP_PROTOCOL_VERSION",
    "MCPClient",
    "MCPError",
    "parse_tool_payload",
    "unwrap_result",
]
