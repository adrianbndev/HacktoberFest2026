#!/usr/bin/env python3
"""Live smoke test for the Phase 2 deep market analysis.

Usage (repo root, backend and market-browser running):
    python scripts/smoke_analyze.py --query "Silla de madera" --description "Silla en buen estado"

The script calls `/api/market/analyze` twice and reports per-source counts,
latency and whether the second call was served from the SQLite cache. With
`--stream` it consumes `/api/market/analyze/stream` and prints the SSE order.
It never writes or prints credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib import error, request

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_SOURCES = "ebay,wallapop,milanuncios"


def _body(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "name": args.query,
        "description": args.description or args.query,
        "category": args.category,
        "brand": args.brand,
        "model": args.model,
        "conditionScore": args.condition_score,
        "conditionLabel": args.condition_label,
        "sources": [item.strip() for item in args.sources.split(",") if item.strip()],
        "includeRecommendation": not args.no_recommendation,
    }


def post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"detail": raw[:500]}
        return exc.code, parsed if isinstance(parsed, dict) else {"detail": raw[:500]}


def post_stream(url: str, payload: dict[str, Any], timeout: float) -> list[tuple[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    events: list[tuple[str, Any]] = []
    event_name = ""
    with request.urlopen(http_request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:") and event_name:
                try:
                    events.append((event_name, json.loads(line[len("data:") :].strip())))
                except json.JSONDecodeError:
                    events.append((event_name, line[len("data:") :].strip()))
                event_name = ""
    return events


def print_run(index: int, status: int, body: dict[str, Any], elapsed: float) -> None:
    print(f"run {index}: HTTP {status} in {elapsed:.2f}s cached={body.get('cached')}")
    if status != 200:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return
    valuation = body.get("valuation", {})
    print(
        "  valuation: "
        f"min={valuation.get('priceMin')} avg={valuation.get('priceAvg')} "
        f"max={valuation.get('priceMax')} sample={valuation.get('sampleSize')} "
        f"confidence={valuation.get('confidence')}"
    )
    for source in body.get("sources", []):
        print(
            f"  {source.get('source')}: status={source.get('status')} "
            f"sample={source.get('sampleSize')} latencyMs={source.get('latencyMs')} "
            f"listings={len(source.get('listings', []))}"
        )
    print(f"  comparableListings={len(body.get('comparableListings', []))}")
    for warning in body.get("warnings", []):
        print(f"  warning: {warning}")


def run_stream(base_url: str, body: dict[str, Any], timeout: float) -> int:
    started = time.monotonic()
    try:
        events = post_stream(f"{base_url}/api/market/analyze/stream", body, timeout)
    except (error.URLError, OSError, ValueError) as exc:
        print(f"stream failed: {exc}", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - started
    names = [name for name, _ in events]
    print(f"stream: {len(events)} events in {elapsed:.2f}s")
    print("  order: " + " -> ".join(names))
    for name, payload in events:
        if name == "source_result":
            print(
                f"  {payload.get('source')}: status={payload.get('status')} "
                f"sample={payload.get('sampleSize')} latencyMs={payload.get('latencyMs')}"
            )
        elif name == "error":
            print(f"  error: {payload}")
    if "analysis_started" not in names or not any(name in {"done", "error"} for name in names):
        print("stream did not emit the required started/done (or error) events", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="Silla de madera")
    parser.add_argument("--description", default="")
    parser.add_argument("--category", default="Mobiliario")
    parser.add_argument("--brand", default="Sin marca")
    parser.add_argument("--model", default="")
    parser.add_argument("--condition-score", type=int, default=85)
    parser.add_argument("--condition-label", default="Como nuevo")
    parser.add_argument("--sources", default=DEFAULT_SOURCES)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--no-recommendation", action="store_true")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()

    body = _body(args)
    base_url = args.base_url.rstrip("/")
    if args.stream:
        return run_stream(base_url, body, args.timeout)

    cache_hits = 0
    for index in range(1, max(1, args.runs) + 1):
        started = time.monotonic()
        try:
            status, response_body = post_json(
                f"{base_url}/api/market/analyze", body, args.timeout
            )
        except (error.URLError, OSError, ValueError) as exc:
            print(f"run {index} failed: {exc}", file=sys.stderr)
            return 1
        elapsed = time.monotonic() - started
        print_run(index, status, response_body, elapsed)
        if status != 200:
            if index == 1:
                return 2
            continue
        if response_body.get("cached"):
            cache_hits += 1

    if args.runs >= 2 and cache_hits == 0:
        print("expected at least one cache hit on the second run", file=sys.stderr)
        return 2
    print(f"ok: {cache_hits} cache hit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
