# ADR-002: Market valuation contract, fallback policy and model choices

* **Status:** Accepted (Phase 1 / MOD-04)
* **Date:** 2026-10-24
* **Owners:** Track C (Matías)
* **Context:** The Phase 1 brief requires a fast, demo-proof `POST /api/market/valuate`
  without a full MOD-00 foundation. Several decisions were already approved by
  the human (minimal foundation, two-path strategy, fallback flag, three
  platforms, DeepSeek models). This ADR records them with their consequences.

## Context

The repo contained specifications only: no `backend/`, no `src/`, no MOD-00.
The market module must return `P_min < P_avg < P_max` in ≤ 2.8 s while Spanish
marketplaces are increasingly protected by Cloudflare/Datadome and Chrome has
hardened remote debugging. The valuation must never break the demo.

## Decisions

### 1. Additive contract only

`MarketValuationResult`, `ValuationRequest`, `MarketListingSample`, `PricePoint`
and `InventoryItem` keep their existing fields. New fields are optional:

- Request: `brand`, `model`, `description`, `includeRecommendation`.
- Response: `recommendation` (only when requested and available) and `warnings`.

`source` remains `live_mcp | stealth_fallback`. Unknown request fields are
rejected (`422`) to catch Track A/B integration typos early.

**Consequence:** Track A can adopt the fields incrementally; `src/types/sdd.ts`
is intentionally not created here and must mirror the optional fields later
(backlog item 5).

### 2. Deterministic fallback only on `/valuate`, behind a flag

- `MARKET_ALLOW_FALLBACK=true` (default): if no live connector yields usable
  listings, the curated Spain-2026 catalog supplies the sample and
  `source="stealth_fallback"`.
- `MARKET_ALLOW_FALLBACK=false`: HTTP `503` with
  `{"detail": ..., "sources": {...}}`.

The Phase 2 deep analysis (`/api/market/analyze`) will never use this fallback.

**Consequences:** the demo remains indestructible on venue Wi-Fi, while a strict
mode is available for verifying live connectivity. The `503` body is structured
and never a `500`.

### 3. Fast HTTP path vs browser path (2.8 s budget)

The live path uses `httpx` + BeautifulSoup with three connectors in parallel,
1.6 s per source, 0.2–0.6 s jitter in `/valuate`, and a 2.8 s request deadline.
A headful browser cold start is 4–9 s, so it cannot be on this path. The browser
engine is Phase 2 and is exposed through a separate endpoint.

The optional recommendation runs in its own opt-in window
(`DEEPSEEK_RECOMMENDATION_BUDGET_SEC`, default 25 s). `deepseek-v4-pro` with
thinking/max reasoning measured **~12–23 s** per real recommendation, so it
cannot fit inside the 2.8 s market SLA. Calls without `includeRecommendation`
keep the 2.8 s budget; the frontend can request the text separately when the
demo can wait. `DEEPSEEK_REASONING_MODEL=deepseek-flash` is available as a
faster (~4 s), lower-quality escape hatch.

**Consequences:** `/valuate` stays within budget with mocked connectors (tests)
and measured 1.8–2.3 s in Docker when every live source was blocked and the
fallback ran. A small amount of residual latency is spent in the optional
recommendation, which shares the remaining budget.

### 4. DeepSeek models and failure handling

- Recommendation: `deepseek-v4-pro`, thinking enabled, `reasoning_effort="max"`.
- Query parsing / `model_not_found` fallback: `deepseek-flash`, thinking disabled.
- `deepseek-reasoner` is legacy and is not referenced in the code.
- JSON output is requested (`response_format={"type": "json_object"}`, the word
  "json" appears in every prompt). Empty or invalid content is retried once per
  model, then the deterministic template is used.
- Every payload passes Pydantic validation. `suggestedPrice` is clamped to
  `[priceMin, priceMax]` and adds `CLAMP_WARNING` when changed.
- The transport timeout is 30 s per attempt with SDK retries disabled; our own
  loop retries once per model and then falls back to the deterministic template.
- Without an API key the template runs immediately; the request still succeeds.

**Consequences:** the recommendation is never a single point of failure.
Bullets are grounded in the request description, the price triplet, the sample
size and the provided comparables; the LLM is explicitly forbidden from
inventing listings or prices.

### 5. Vinted is deferred

`vinted` stays in the `MarketPlatform` union and is supported by the contract,
but no connector is registered in Phase 1. Results only declare platforms that
appear in `comparableListings`.

**Consequence:** a Vinted connector can be added without touching pricing math
(open/closed principle) and without breaking the response contract.

### 6. MCP server is not part of Phase 1

`backend/mcp_server.py` (FastMCP CLI/stdio exposure) is not in the Phase 1 file
scope. The domain engine is already reusable by a thin FastMCP wrapper.

**Consequence:** MOD-04 is not marked `DONE`; the module status remains
`IN_PROGRESS` until the MCP server and Vinted are addressed.

### 7. Chrome 136+ CDP compatibility proxy

The browser image uses headful Chromium under Xvfb (never `--headless`, never
`--enable-automation`; Chrome is launched by our entrypoint). Chrome 136+ only
listens on `127.0.0.1` and rejects non-local `Host` headers, which breaks
`--browserUrl http://market-browser:9222`.

A stdlib proxy inside the browser container listens on `0.0.0.0:9222`, forwards
HTTP and WebSocket to `127.0.0.1:9223` with a local `Host`, and rewrites
`webSocketDebuggerUrl` to the caller's host.

**Consequences:** both the host and other containers can use the documented
`--browserUrl`. Trade-off: one more small process in the browser image and the
proxy must stay in sync with Chrome's DevTools responses. It is covered by a
manual spike, not a unit test.

### 8. Multi-arch browser fingerprint

`amd64` prefers Google Chrome stable; `arm64` uses Debian Chromium. The engine is
the same family but UA/GPU/codecs differ. The fingerprint spike must be run on
the demo architecture.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Browser-only valuation | 4–9 s cold start, CAPTCHA risk, breaks the 2.8 s budget |
| No fallback | Venue Wi-Fi failures would produce `503` during the demo |
| `deepseek-reasoner` | Legacy model, incompatible with the approved model strategy |
| Vinted in Phase 1 | Scope requires three platforms; Vinted adds anti-bot complexity |
| Host-mounted Chrome on the laptop | Depends on the host display/OS and breaks container portability |
| Chrome `--remote-debugging-address=0.0.0.0` | Ignored by Chrome 156; loopback-only + Host validation |

## Verification evidence (Phase 1)

- 137 backend tests, `ruff check app tests`, `mypy app` green.
- `docker compose config` valid; `lifeos-backend` and `market-browser` healthy.
- `/api/market/health` → 200; `/api/market/valuate` → 200 with fallback when all
  sources fail, and a structured `503` when fallback is disabled (API tests).
- Browser spike (arm64): `webdriver=false`, `es-ES`, `Europe/Madrid`, no
  `__puppeteer`/`__playwright`; Wallapop 40 listings; eBay 60 on the first run
  and its anti-bot error page on a later run.
- No production DeepSeek key was available; the transport is covered with fakes
  and the deterministic template is verified.

## Deferred (non-blocking)

See [`docs/backlog.md`](../../docs/backlog.md).
