#!/usr/bin/env python3
"""Smoke-test the running market backend (stdlib only, no extra dependencies).

Usage (from the repo root):
    python scripts/smoke_live.py --query "iPhone 13 128GB"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8001"


def _request(
    url: str, *, payload: dict[str, object] | None = None, timeout: float
) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data else "GET"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="iPhone 13 128GB")
    parser.add_argument("--category", default="Móviles")
    parser.add_argument("--condition-score", type=int, default=80)
    parser.add_argument("--condition-label", default="Como nuevo")
    parser.add_argument("--description", default="Caja original, batería 89%, sin arañazos")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--include-recommendation", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    try:
        status, health = _request(f"{base_url}/api/market/health", timeout=args.timeout)
        print(f"health: HTTP {status} {health.get('status')}")
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"health failed: {exc}", file=sys.stderr)
        return 1

    payload = {
        "query": args.query,
        "category": args.category,
        "conditionScore": args.condition_score,
        "conditionLabel": args.condition_label,
        "description": args.description,
        "includeRecommendation": args.include_recommendation,
    }
    started = time.perf_counter()
    try:
        status, body = _request(
            f"{base_url}/api/market/valuate", payload=payload, timeout=args.timeout
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"valuate: HTTP {exc.code} {detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"valuate failed: {exc}", file=sys.stderr)
        return 1
    elapsed_ms = (time.perf_counter() - started) * 1000

    print(f"valuate: HTTP {status} in {elapsed_ms:.0f} ms")
    print(f"source: {body.get('source')} | samples: {body.get('sampleSize')}")
    print(
        "prices: "
        f"min={body.get('priceMin')} € avg={body.get('priceAvg')} € max={body.get('priceMax')} €"
    )
    print(f"platforms: {', '.join(body.get('platforms', []))}")
    if body.get("recommendation"):
        print(f"recommendation: {body['recommendation'].get('summary')}")
    for warning in body.get("warnings", []):
        print(f"warning: {warning}")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
