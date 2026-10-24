#!/usr/bin/env python3
"""Spike 1b: Milanuncios fast HTTP connector vs the browser source.

Measures the fast HTTP connector at 1, 2 and 3 result pages (latency, raw and
usable listings) and compares it with the browser depth measured by
`scripts/pool_spike.py`. Writes `artifacts/milanuncios-http-spike.json`.

Usage (from the repo root):
    python scripts/milanuncios_http_spike.py --query "iPhone 13 128GB"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.mcp.connectors import MilanunciosConnector, looks_blocked
from app.mcp.normalize import dedupe_listings, filter_usable_listings
from app.mcp.stealth_http import build_headers

DEFAULT_QUERY = "iPhone 13 128GB"
DEFAULT_PAGES = (1, 2, 3)
USABLE_THRESHOLD = 8
HTTP_BUDGET_SEC = 5.0
SEARCH_TEMPLATE = "https://www.milanuncios.com/anuncios/?s={query}"
PAGE_TEMPLATE = "https://www.milanuncios.com/anuncios/?s={query}&pagina={page}"
BROWSER_SPIKE = Path("artifacts/pool-spike.json")
OUTPUT = Path("artifacts/milanuncios-http-spike.json")


@dataclass
class PageMeasurement:
    page: int
    statusCode: int
    latencyMs: int
    blocked: bool
    rawListings: int
    usableListings: int


@dataclass
class DepthMeasurement:
    pages: int
    latencyMs: int
    rawListings: int
    usableListings: int
    blocked: bool
    statusCodes: list[int] = field(default_factory=list)
    pagesDetail: list[PageMeasurement] = field(default_factory=list)


@dataclass
class DepthSummary:
    pages: int
    samples: int
    medianLatencyMs: int
    medianUsableListings: int
    minUsableListings: int
    maxUsableListings: int
    medianRawListings: int
    blockedRuns: int
    runs: list[DepthMeasurement] = field(default_factory=list)


@dataclass
class SpikeResult:
    generatedAt: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    query: str = DEFAULT_QUERY
    usableThreshold: int = USABLE_THRESHOLD
    httpBudgetMs: int = int(HTTP_BUDGET_SEC * 1000)
    depths: list[DepthSummary] = field(default_factory=list)
    browser: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)


def _url(query: str, page: int) -> str:
    if page == 1:
        return SEARCH_TEMPLATE.format(query=quote_plus(query))
    return PAGE_TEMPLATE.format(query=quote_plus(query), page=page)


async def _fetch(
    client: httpx.AsyncClient, query: str, page: int
) -> tuple[int, str, int]:
    started = time.monotonic()
    response = await client.get(_url(query, page), headers=build_headers())
    latency = int((time.monotonic() - started) * 1000)
    return response.status_code, response.text, latency


async def _measure_depth(
    client: httpx.AsyncClient, parser: MilanunciosConnector, query: str, pages: int
) -> DepthMeasurement:
    started = time.monotonic()
    listings: list[Any] = []
    details: list[PageMeasurement] = []
    blocked = False
    for page in range(1, pages + 1):
        status, html, latency = await _fetch(client, query, page)
        page_blocked = looks_blocked(html, status)
        blocked = blocked or page_blocked
        parsed = [] if page_blocked else parser.parse(html)
        listings.extend(parsed)
        usable = filter_usable_listings(
            dedupe_listings(listings), max_price_eur=100_000
        )
        details.append(
            PageMeasurement(
                page=page,
                statusCode=status,
                latencyMs=latency,
                blocked=page_blocked,
                rawListings=len(parsed),
                usableListings=len(usable),
            )
        )
    usable = filter_usable_listings(dedupe_listings(listings), max_price_eur=100_000)
    return DepthMeasurement(
        pages=pages,
        latencyMs=int((time.monotonic() - started) * 1000),
        rawListings=len(dedupe_listings(listings)),
        usableListings=len(usable),
        blocked=blocked,
        statusCodes=[detail.statusCode for detail in details],
        pagesDetail=details,
    )


def _summarize(pages: int, runs: list[DepthMeasurement]) -> DepthSummary:
    return DepthSummary(
        pages=pages,
        samples=len(runs),
        medianLatencyMs=int(statistics.median(run.latencyMs for run in runs)),
        medianUsableListings=int(
            statistics.median(run.usableListings for run in runs)
        ),
        minUsableListings=min(run.usableListings for run in runs),
        maxUsableListings=max(run.usableListings for run in runs),
        medianRawListings=int(statistics.median(run.rawListings for run in runs)),
        blockedRuns=sum(1 for run in runs if run.blocked),
        runs=runs,
    )


def _browser_depth() -> dict[str, Any]:
    if not BROWSER_SPIKE.exists():
        return {}
    try:
        payload = json.loads(BROWSER_SPIKE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        item["configuredPages"]: {
            "latencyMs": item["latencyMs"],
            "usableListings": item["usableListings"],
            "rawListings": item["rawListings"],
        }
        for item in payload.get("milanunciosDepth", [])
        if "configuredPages" in item
    }


def _decide(result: SpikeResult) -> dict[str, Any]:
    by_pages = {depth.pages: depth for depth in result.depths}
    three = by_pages.get(3)
    two = by_pages.get(2)
    if three is None:
        return {"transport": "browser", "reason": "3-page HTTP measurement missing"}
    fast_enough = three.medianLatencyMs <= result.httpBudgetMs
    enough_samples = three.medianUsableListings >= result.usableThreshold
    browser_three = result.browser.get("3") or result.browser.get(3) or {}
    return {
        "transport": "http" if fast_enough and enough_samples else "auto",
        "http3PagesUsable": three.medianUsableListings,
        "http3PagesLatencyMs": three.medianLatencyMs,
        "http3PagesUsableRange": [three.minUsableListings, three.maxUsableListings],
        "http3PagesWithinBudget": fast_enough,
        "http3PagesReachThreshold": enough_samples,
        "http2Pages": (
            {
                "usableListings": two.medianUsableListings,
                "latencyMs": two.medianLatencyMs,
            }
            if two is not None
            else None
        ),
        "browser3Pages": browser_three or None,
        "reason": (
            "HTTP with 3 pages reaches the usable threshold inside the 5 s budget; "
            "auto can prefer HTTP and fall back to the browser when it under-delivers."
            if fast_enough and enough_samples
            else "HTTP does not reach 8 usable samples within 5 s at 3 pages; "
            "keep transport=auto with a browser fallback and document the measured gap."
        ),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--pages", default="1,2,3")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    pages = [int(value) for value in args.pages.split(",") if value]
    result = SpikeResult(query=args.query)
    connector = MilanunciosConnector(timeout_sec=args.timeout)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(args.timeout), follow_redirects=True
    ) as client:
        for depth in pages:
            runs: list[DepthMeasurement] = []
            for _ in range(max(1, args.samples)):
                runs.append(await _measure_depth(client, connector, args.query, depth))
                await asyncio.sleep(0.3)
            result.depths.append(_summarize(depth, runs))
    result.browser = _browser_depth()
    result.decision = _decide(result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if result.decision["transport"] == "http" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
