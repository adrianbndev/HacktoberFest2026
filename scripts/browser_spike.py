#!/usr/bin/env python3
"""Non-blocking browser spike: extract listings from eBay and Wallapop via MCP.

Usage (from the repo root, with the browser container running):
    python scripts/browser_spike.py --query "iPhone 13 128GB"
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
from urllib.parse import quote_plus

from mcp_client import MCPClient, MCPError, parse_tool_payload

DEFAULT_BROWSER_URL = "http://127.0.0.1:9222"
EXPECTED_LISTINGS = 10
WAIT_JS = "async () => { await new Promise((resolve) => setTimeout(resolve, 4000)); return true; }"
EBAY_JS = """
() => {
  const cards = Array.from(document.querySelectorAll('li.s-item, li.s-card'));
  const listings = [];
  for (const card of cards) {
    const title = card.querySelector('.s-item__title, .s-card__title');
    const price = card.querySelector('.s-item__price, .s-card__price');
    const link = card.querySelector('a.s-item__link, a.s-card__link, a[href*="/itm/"]');
    if (!title || !price) continue;
    const titleText = (title.textContent || '').trim();
    if (titleText.toLowerCase() === 'shop on ebay') continue;
    listings.push({
      title: titleText,
      price: (price.textContent || '').trim(),
      url: link ? link.href : null
    });
  }
  return listings;
}
"""
WALLAPOP_JS = """
() => {
  const anchors = Array.from(document.querySelectorAll("a[href*='/item/']"));
  const seen = new Set();
  const listings = [];
  for (const anchor of anchors) {
    const url = anchor.href;
    if (seen.has(url)) continue;
    const card = anchor.closest('article') || anchor.parentElement || anchor;
    const text = (card.innerText || '').trim();
    const price = text.match(/\\d[\\d.,]*\\s*€/);
    const title = ((anchor.getAttribute('aria-label') || anchor.innerText || '').trim()
      .split('\\n')[0]);
    if (!title || !price) continue;
    seen.add(url);
    listings.push({ title, price: price[0], url });
  }
  return listings;
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


def _collect(
    client: MCPClient, page_id: int, url: str, extractor: str
) -> list[dict[str, Any]]:
    client.call_tool("navigate_page", {"pageId": page_id, "url": url})
    _evaluate(client, page_id, WAIT_JS)
    data = _evaluate(client, page_id, extractor)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="iPhone 13 128GB")
    parser.add_argument("--browser-url", default=DEFAULT_BROWSER_URL)
    parser.add_argument("--mcp-command", default="")
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    encoded = quote_plus(args.query)
    searches = {
        "ebay": f"https://www.ebay.es/sch/i.html?_nkw={encoded}&_sacat=0",
        "wallapop": f"https://es.wallapop.com/app/search?keywords={encoded}&order_by=newest",
    }
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
        "query": args.query,
        "status": "error",
        "browserUrl": args.browser_url,
        "expectedListings": EXPECTED_LISTINGS,
        "sources": {},
    }
    client: MCPClient | None = None

    try:
        with MCPClient(
            command,
            timeout_sec=args.timeout,
            env={"CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1"},
        ) as client:
            page_id = _page_id(client)
            for name, url in searches.items():
                extractor = EBAY_JS if name == "ebay" else WALLAPOP_JS
                listings = _collect(client, page_id, url, extractor)
                report["sources"][name] = {
                    "url": url,
                    "count": len(listings),
                    "ok": len(listings) >= EXPECTED_LISTINGS,
                    "listings": listings[:20],
                }
            counts = [source["count"] for source in report["sources"].values()]
            if all(count >= EXPECTED_LISTINGS for count in counts):
                report["status"] = "ok"
            elif any(count > 0 for count in counts):
                report["status"] = "partial"
            else:
                report["status"] = "blocked_or_empty"
    except (MCPError, OSError, ValueError) as exc:
        report["error"] = str(exc)
        report["stderrTail"] = client.stderr_tail if client is not None else ""
        print(f"browser spike failed: {exc}", file=sys.stderr)

    artifacts = Path(args.artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)
    output = artifacts / "browser-spike.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, source in report["sources"].items():
        print(f"{name}: {source['count']} listings")
    print(f"report written to {output} (status={report['status']})")
    # Non-blocking: a blocked site is documented, not a build failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
