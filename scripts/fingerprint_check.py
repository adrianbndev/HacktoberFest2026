#!/usr/bin/env python3
"""Non-blocking fingerprint spike: drives the MCP against bot-detection pages.

Usage (from the repo root, with the browser container running):
    python scripts/fingerprint_check.py
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_client import MCPClient, MCPError, parse_tool_payload

DEFAULT_BROWSER_URL = "http://127.0.0.1:9222"
SITES = {
    "sannysoft": "https://bot.sannysoft.com/",
    "creepjs": "https://abrahamjuliot.github.io/creepjs/",
}
WAIT_JS = "async () => { await new Promise((resolve) => setTimeout(resolve, 3500)); return true; }"
FINGERPRINT_JS = """
() => {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  let vendor = null;
  let renderer = null;
  if (gl) {
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    if (ext) {
      vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
      renderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
    }
  }
  return {
    url: location.href,
    title: document.title,
    webdriver: navigator.webdriver,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    languages: Array.from(navigator.languages || []),
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    plugins: Array.from(navigator.plugins || []).map((plugin) => plugin.name),
    windowChrome: typeof window.chrome,
    webglVendor: vendor,
    webglRenderer: renderer,
    puppeteer: typeof window.__puppeteer,
    playwright: typeof window.__playwright,
    screen: {
      width: screen.width,
      height: screen.height,
      colorDepth: screen.colorDepth
    }
  };
}
"""


def _page_id(client: MCPClient) -> int:
    text = client.call_tool_text("list_pages", {})
    for line in text.splitlines():
        match = re.match(r"\s*(\d+):", line)
        if match:
            return int(match.group(1))
    return 1


def _evaluate(client: MCPClient, page_id: int, function: str) -> Any:
    text = client.call_tool_text(
        "evaluate_script", {"pageId": page_id, "function": function}
    )
    return parse_tool_payload(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-url", default=DEFAULT_BROWSER_URL)
    parser.add_argument(
        "--mcp-command",
        default="",
        help="Override the MCP command (defaults to npx chrome-devtools-mcp@1.10.1)",
    )
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    command = (
        shlex.split(args.mcp_command)
        if args.mcp_command
        else [
            "npx",
            "-y",
            "chrome-devtools-mcp@1.10.1",
            "--browserUrl",
            args.browser_url,
        ]
    )
    report: dict[str, Any] = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "status": "error",
        "browserUrl": args.browser_url,
        "mcpCommand": command,
        "sites": {},
    }

    client: MCPClient | None = None
    try:
        with MCPClient(
            command,
            timeout_sec=args.timeout,
            env={"CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1"},
        ) as client:
            page_id = _page_id(client)
            for name, url in SITES.items():
                client.call_tool("navigate_page", {"pageId": page_id, "url": url})
                _evaluate(client, page_id, WAIT_JS)
                report["sites"][name] = _evaluate(client, page_id, FINGERPRINT_JS)
            report["status"] = "ok"
    except (MCPError, OSError, ValueError) as exc:
        report["error"] = str(exc)
        report["stderrTail"] = client.stderr_tail if client is not None else ""
        print(f"fingerprint spike failed: {exc}", file=sys.stderr)

    artifacts = Path(args.artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)
    output = artifacts / "fingerprint.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"report written to {output} (status={report['status']})")
    # The spike is explicitly non-blocking: a failed report must not fail the build.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
