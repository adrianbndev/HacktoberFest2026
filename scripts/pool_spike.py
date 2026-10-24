#!/usr/bin/env python3
"""Mandatory Phase 3 spike: 3 MCP processes, one page each, same Chrome.

Usage (from the repo root, with the browser container running):
    python scripts/pool_spike.py --query "iPhone 13 128GB"

It measures a sequential baseline (1 process, 1 page) against three MCP
processes (one page each) running eBay, Wallapop and Milanuncios concurrently,
checks that `select_page`/`bringToFront` does not block the other pages, records
the anti-detection fingerprint and writes `artifacts/pool-spike.json`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_client import MCPClient, MCPError, parse_tool_payload

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.mcp.browser.sources.base import BaseBrowserSource
from app.mcp.browser.sources.ebay import EbaySource
from app.mcp.browser.sources.milanuncios import MilanunciosSource
from app.mcp.browser.sources.wallapop import WallapopSource

DEFAULT_BROWSER_URL = "http://127.0.0.1:9222"
DEFAULT_MCP_COMMAND = "npx -y chrome-devtools-mcp@1.10.1"
CONTAINER_NAME = "phase-3-trackc-parallel-sources-market-browser-1"
SLOT_TOKEN = "pool-spike-slot"
FINGERPRINT_JS = """
() => {
  return {
    url: location.href,
    title: document.title,
    visibilityState: document.visibilityState,
    hidden: document.hidden,
    webdriver: navigator.webdriver,
    userAgent: navigator.userAgent,
    headlessChrome: /HeadlessChrome/i.test(navigator.userAgent),
    puppeteer: typeof window.__puppeteer,
    playwright: typeof window.__playwright,
    windowChrome: typeof window.chrome,
    language: navigator.language,
    languages: Array.from(navigator.languages || []),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory ?? null
  };
}
"""


@dataclass
class DirectPage:
    """The subset of `BrowserPage` the production sources use."""

    client: MCPClient
    page_id: int

    async def navigate(self, url: str) -> None:
        await asyncio.to_thread(
            self.client.call_tool_text,
            "navigate_page",
            {"pageId": self.page_id, "url": url},
        )

    async def evaluate(self, function: str) -> Any:
        text = await asyncio.to_thread(
            self.client.call_tool_text,
            "evaluate_script",
            {"pageId": self.page_id, "function": function},
        )
        return parse_tool_payload(text)

    async def scroll(self, *, steps: int = 4, pause_ms: int = 350) -> None:
        for _ in range(max(1, steps)):
            await self.evaluate(
                "() => { window.scrollTo(0, document.body.scrollHeight); return true; }"
            )
            await asyncio.sleep(max(0, pause_ms) / 1000)


@dataclass
class SourceMeasurement:
    platform: str
    status: str
    listings: int
    latency_ms: int
    error: str | None = None


@dataclass
class Slot:
    index: int
    platform: str
    client: MCPClient
    page_id: int
    page: DirectPage
    source: BaseBrowserSource
    measurement: SourceMeasurement | None = None
    error: str | None = None


@dataclass
class SpikeResult:
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    browser_url: str = DEFAULT_BROWSER_URL
    query: str = ""
    mcp_command: str = DEFAULT_MCP_COMMAND
    sequential: dict[str, Any] = field(default_factory=dict)
    parallel: dict[str, Any] = field(default_factory=dict)
    focus: dict[str, Any] = field(default_factory=dict)
    fingerprint: list[dict[str, Any]] = field(default_factory=list)
    resources: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generatedAt": self.generated_at,
            "browserUrl": self.browser_url,
            "query": self.query,
            "mcpCommand": self.mcp_command,
            "sequential": self.sequential,
            "parallel": self.parallel,
            "focus": self.focus,
            "fingerprint": self.fingerprint,
            "resources": self.resources,
            "decision": self.decision,
            "errors": self.errors,
        }


def _sources() -> list[BaseBrowserSource]:
    return [EbaySource(), WallapopSource(), MilanunciosSource()]


def _spawn(command: list[str]) -> MCPClient:
    client = MCPClient(command, timeout_sec=90.0)
    client.initialize()
    return client


def _new_page(client: MCPClient, token: str) -> int:
    client.call_tool_text(
        "new_page",
        {"url": f"data:text/html,<title>{token}</title>", "background": True},
    )
    text = client.call_tool_text("list_pages", {})
    for line in text.splitlines():
        if token in line:
            match = re.match(r"\s*(\d+):", line)
            if match:
                return int(match.group(1))
    raise MCPError(f"new page {token} not found in list_pages")


async def _collect(slot: Slot, query: str) -> SourceMeasurement:
    started = time.monotonic()
    try:
        outcome = await slot.source.collect(slot.page, query)
    except Exception as exc:
        return SourceMeasurement(
            platform=slot.platform,
            status="error",
            listings=0,
            latency_ms=int((time.monotonic() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}"[:300],
        )
    return SourceMeasurement(
        platform=slot.platform,
        status=outcome.status,
        listings=len(outcome.listings),
        latency_ms=int((time.monotonic() - started) * 1000),
        error=outcome.error,
    )


async def _run_sequential(command: list[str], query: str) -> dict[str, Any]:
    client = await asyncio.to_thread(_spawn, command)
    page_id = await asyncio.to_thread(_new_page, client, f"{SLOT_TOKEN}-seq")
    page = DirectPage(client=client, page_id=page_id)
    measurements: list[SourceMeasurement] = []
    started = time.monotonic()
    try:
        for source in _sources():
            slot = Slot(
                index=len(measurements),
                platform=source.platform,
                client=client,
                page_id=page_id,
                page=page,
                source=source,
            )
            measurements.append(await _collect(slot, query))
    finally:
        await asyncio.to_thread(_close_page, client, page_id)
        await asyncio.to_thread(client.close)
    wall_ms = int((time.monotonic() - started) * 1000)
    return {
        "processes": 1,
        "pages": 1,
        "wallMs": wall_ms,
        "sumSourceMs": sum(item.latency_ms for item in measurements),
        "sources": [_measurement_dict(item) for item in measurements],
    }


def _close_page(client: MCPClient, page_id: int) -> None:
    with suppress(MCPError):
        client.call_tool_text("close_page", {"pageId": page_id})


async def _start_slots(command: list[str]) -> list[Slot]:
    slots: list[Slot] = []
    for index, source in enumerate(_sources()):
        client = await asyncio.to_thread(_spawn, command)
        page_id = await asyncio.to_thread(
            _new_page, client, f"{SLOT_TOKEN}-{index}"
        )
        slots.append(
            Slot(
                index=index,
                platform=source.platform,
                client=client,
                page_id=page_id,
                page=DirectPage(client=client, page_id=page_id),
                source=source,
            )
        )
    return slots


async def _stop_slots(slots: list[Slot]) -> None:
    for slot in slots:
        await asyncio.to_thread(_close_page, slot.client, slot.page_id)
        await asyncio.to_thread(slot.client.close)


async def _fingerprints(slots: list[Slot]) -> list[dict[str, Any]]:
    async def one(slot: Slot) -> dict[str, Any]:
        try:
            payload = await slot.page.evaluate(FINGERPRINT_JS)
        except Exception as exc:
            return {"platform": slot.platform, "error": f"{type(exc).__name__}: {exc}"}
        if not isinstance(payload, dict):
            return {"platform": slot.platform, "error": "unexpected payload"}
        return {"platform": slot.platform, **payload}

    return list(await asyncio.gather(*(one(slot) for slot in slots)))


async def _run_parallel(
    command: list[str], query: str, *, focus_probe: bool
) -> tuple[dict[str, Any], list[Slot], dict[str, Any]]:
    slots = await _start_slots(command)
    focus: dict[str, Any] = {}
    started = time.monotonic()
    try:
        async def focus_worker() -> None:
            # Exercise select_page/bringToFront while the other pages navigate.
            await asyncio.sleep(0.8)
            target = slots[-1]
            call_started = time.monotonic()
            await asyncio.to_thread(
                target.client.call_tool_text,
                "select_page",
                {"pageId": target.page_id, "bringToFront": True},
            )
            focus["selectPageMs"] = int((time.monotonic() - call_started) * 1000)
            await asyncio.sleep(0.2)
            await asyncio.to_thread(
                target.client.call_tool_text,
                "select_page",
                {"pageId": target.page_id, "bringToFront": False},
            )

        tasks = [asyncio.create_task(_collect(slot, query)) for slot in slots]
        focus_task = asyncio.create_task(focus_worker()) if focus_probe else None
        measurements = await asyncio.gather(*tasks)
        if focus_task is not None:
            await focus_task
    finally:
        pass
    wall_ms = int((time.monotonic() - started) * 1000)
    for slot, measurement in zip(slots, measurements, strict=True):
        slot.measurement = measurement
    result = {
        "processes": len(slots),
        "pages": len(slots),
        "wallMs": wall_ms,
        "sumSourceMs": sum(item.latency_ms for item in measurements),
        "maxSourceMs": max(item.latency_ms for item in measurements),
        "sources": [_measurement_dict(item) for item in measurements],
    }
    return result, slots, focus


def _measurement_dict(item: SourceMeasurement) -> dict[str, Any]:
    return {
        "platform": item.platform,
        "status": item.status,
        "listings": item.listings,
        "latencyMs": item.latency_ms,
        "error": item.error,
    }


def _docker_stats(container: str) -> dict[str, Any]:
    try:
        output = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", container],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}
    if output.returncode != 0:
        return {"error": output.stderr.strip() or "docker stats failed"}
    line = output.stdout.strip().splitlines()
    if not line:
        return {"error": "no stats"}
    try:
        raw = json.loads(line[-1])
    except json.JSONDecodeError:
        return {"raw": line[-1]}
    return {
        "cpuPercent": raw.get("CPUPerc"),
        "memUsage": raw.get("MemUsage"),
        "memPercent": raw.get("MemPerc"),
        "pids": raw.get("PIDs"),
    }


def _chrome_processes(container: str) -> dict[str, Any]:
    command = (
        "ps -eo rss,comm | grep -i chrom | "
        "awk '{count += 1; rss += $1} END {print count + 0, rss + 0}'"
    )
    try:
        output = subprocess.run(
            ["docker", "exec", container, "sh", "-c", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}
    if output.returncode != 0:
        return {"error": output.stderr.strip() or "docker exec failed"}
    parts = output.stdout.split()
    if len(parts) != 2:
        return {"raw": output.stdout.strip()}
    return {
        "chromeProcesses": int(parts[0]),
        "chromeRssMb": round(int(parts[1]) / 1024, 1),
    }


def _decide(result: SpikeResult) -> dict[str, Any]:
    parallel = result.parallel
    sequential = result.sequential
    wall = parallel.get("wallMs")
    sum_ms = parallel.get("sumSourceMs")
    max_ms = parallel.get("maxSourceMs")
    ratio = round(wall / max_ms, 2) if wall and max_ms else None
    speedup = round(sequential["wallMs"] / wall, 2) if wall and sequential.get("wallMs") else None
    sum_ratio = round(wall / sum_ms, 2) if wall and sum_ms else None
    parallel_ok = bool(
        ratio is not None
        and ratio <= 1.2
        and sum_ratio is not None
        and sum_ratio <= 0.85
    )
    fingerprint_ok = all(
        item.get("webdriver") is False
        and item.get("headlessChrome") is False
        and item.get("puppeteer") == "undefined"
        and item.get("playwright") == "undefined"
        for item in result.fingerprint
        if "error" not in item
    ) and len([item for item in result.fingerprint if "error" not in item]) == 3
    focus_ok = result.focus.get("selectPageMs") is not None and all(
        item["status"] in {"ok", "no_listings", "blocked"}
        for item in parallel["sources"]
    )
    plan = "A" if parallel_ok else "B"
    return {
        "plan": plan,
        "parallelTracksMax": parallel_ok,
        "wallToMaxRatio": ratio,
        "wallToSumRatio": sum_ratio,
        "speedupVsSequential": speedup,
        "fingerprintClean": fingerprint_ok,
        "selectPageDidNotBreakSources": focus_ok,
        "reason": (
            "Three MCP processes drive three pages concurrently against one Chrome; "
            "wall time tracks max(source), not the sum."
            if parallel_ok
            else "Parallel wall time did not approach max(source); fall back to plan B "
            "(one Chrome per source) before implementing the pool."
        ),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="iPhone 13 128GB")
    parser.add_argument("--browser-url", default=DEFAULT_BROWSER_URL)
    parser.add_argument("--mcp-command", default=DEFAULT_MCP_COMMAND)
    parser.add_argument("--container", default=CONTAINER_NAME)
    parser.add_argument(
        "--output", default="artifacts/pool-spike.json", type=Path
    )
    args = parser.parse_args()

    command = args.mcp_command.split()
    if "--browserUrl" not in command:
        command += ["--browserUrl", args.browser_url]

    result = SpikeResult(
        browser_url=args.browser_url, query=args.query, mcp_command=args.mcp_command
    )
    result.sequential = await _run_sequential(command, args.query)
    result.parallel, slots, result.focus = await _run_parallel(
        command, args.query, focus_probe=True
    )
    try:
        result.fingerprint = await _fingerprints(slots)
    finally:
        result.resources = {
            "dockerStats": _docker_stats(args.container),
            **_chrome_processes(args.container),
        }
        await _stop_slots(slots)
    result.decision = _decide(result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.decision["plan"] == "A" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
