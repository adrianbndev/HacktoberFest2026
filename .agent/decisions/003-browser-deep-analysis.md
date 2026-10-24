# ADR-003: Browser MCP deep analysis (Phase 2)

* **Status:** Accepted (Phase 2 / MOD-04)
* **Date:** 2026-10-24
* **Owners:** Track C (Matías)
* **Supersedes:** nothing. Extends ADR-002 without changing the fast path.

## Context

Phase 1 delivered a frozen, demo-proof `POST /api/market/valuate` in ≤ 2.8 s
using HTTP connectors and a deterministic fallback. Two sources are not usable
that way on this network: Wallapop renders its search page with JavaScript, and
eBay serves an anti-bot interstitial after the first HTTP request. The Phase 2
brief asks for a deeper, *real-browser* valuation with per-source statuses, a
per-platform comparable quota, an SSE progress stream and a short-lived cache.

The deep path must not regress the fast path, must never invent prices, and must
keep working (with an explicit `503`) when the browser is absent.

## Decisions

### 1. `/valuate` stays frozen; the deep path is additive

`ValuationRequest`, `MarketValuationResult`, `/valuate` behavior and
`src/types/sdd.ts` are untouched. Two new endpoints are added:

- `POST /api/market/analyze` → `MarketAnalysisResult`.
- `POST /api/market/analyze/stream` → SSE over the same engine.

New backend contracts live in `backend/app/models/market_analysis.py`; the
frontend mirror lives in `src/types/market-analysis.ts`. The deep `valuation`
object is intentionally narrower than `MarketValuationResult` (three prices,
sample size, platforms, confidence) and adds a top-level `comparableListings`
set capped at 12.

**Consequences:** Track A can adopt the new client incrementally. The 2.8 s SLA
is defined only for `/valuate`; the deep path has its own 60 s deadline.

### 2. Real browser data only; never synthetic

The deep engine never imports `catalog_fallback` and never generates listings.
Every price comes from a page rendered by the shared browser. If all requested
sources are blocked, timed out or produce no usable listing, the API returns:

```json
{"detail": "Ninguna fuente de mercado profunda devolvió anuncios utilizables.",
 "sources": {"ebay": "blocked", "wallapop": "no_listings"}}
```

If the MCP/CDP browser is unavailable the body is
`{"detail": "browser_unavailable", "sources": {}}`. Unexpected engine errors
are mapped to `analysis_failed`; the deep path never returns `500`.

### 3. Browser ownership: shared manager, one lock, one page

`BrowserSessionManager` owns the `chrome-devtools-mcp@1.10.1` stdio process:

- lazy spawn with `--browserUrl $CDP_URL`; Chrome is launched by the
  `market-browser` container (headful under Xvfb), never by the MCP;
- one `asyncio.Lock` and one tab, so page operations cannot interleave;
- blocking JSON-RPC calls run via `asyncio.to_thread`;
- per-call timeout, one restart on crash, `close_page` + process close on stop;
- `navigator.webdriver=false` was already verified by the Phase 1 fingerprint
  spike; no `--headless` or `--enable-automation` is ever passed.

The analyzer is process-wide (`shared_analyzer(settings)`) so the browser lock,
MCP process and SQLite cache are reused across requests.

**Consequences:** sources run sequentially, which is slower than parallel pages
but keeps the single-page anti-bot footprint and memory low. The first
`source_result` is still targeted at < 6 s on a warm browser.

### 4. Source adapters: browser extraction + fixture parity

`mcp/browser/sources/{ebay,wallapop,milanuncios}.py` each provide:

- `search_url(s)` matching the brief;
- a JavaScript DOM extractor executed with `evaluate_script`;
- `parse_html()` for saved HTML fixtures and `parse_items()` for the shared
  normalisation (`build_listing_sample`, price parsing, URL join).

Milanuncios/eBay/Wallapop anti-bot markers (`Pardon our interruption`, captcha,
Access Denied, unusual traffic, `just a moment`) map to `status="blocked"`. A
captcha is never solved. Missing listing URLs fall back to the platform search
deep link so the UI never shows a dead link.

**Consequences:** parser regressions are caught hermetically with fixtures; a
runtime site redesign is visible as `no_listings`/`blocked` and is fixed in the
extractor without touching pricing.

### 5. Cache: SQLite, 15 minutes, real results only

`mcp/cache.py` stores opaque JSON payloads keyed by SHA-256 of normalized query
+ condition score + sorted sources. `description`, coordinates and identity are
never stored. TTL defaults to 900 s. Reads/writes use `asyncio.to_thread`, one
connection per operation, WAL mode and a busy timeout. Corrupt payloads are a
miss; storage failures are logged and never fail the analysis.

### 6. One IQR pass, per-platform quota and confidence

The engine filters usability once, applies relevance once, then computes IQR
fences once and uses `compute_price_triplet_from_clean` to avoid the Phase 1
double-IQR follow-up. `sampleSize` is exactly the number of listings priced.

The final comparable set takes at most `MARKET_PLATFORM_QUOTA` (4) per successful
source and fills to 12 by price proximity to `priceAvg`. `platforms` is derived
from every source with usable data after the IQR filter, so a minority platform
is not silently dropped.

`confidence_score` is a pure function of sample size, platform coverage, price
dispersion and source reliability; it is reproducible and unit-tested.

### 7. Recommendation: real LLM or omitted

The deep engine uses `DeepSeekRecommender(allow_template=False)`. A missing key,
timeout or invalid JSON omits the recommendation and adds a warning. A
`suggestedPrice` outside `[priceMin, priceMax]` is clamped and warned. This is
stricter than `/valuate`, where the deterministic template remains valid.

### 8. SSE: queue + heartbeat + cancellation

`mcp/sse.py` consumes `DeepAnalysisEvent`s through an `asyncio.Queue`. It emits a
`: ping` comment every 15 s while a source is slow, serializes each event with
the frozen wire names, and cancels the producer task when the client disconnects
(generator close), which releases the browser lock and page. The router
passes `browser.stop` as `on_disconnect`, so an aborted stream also closes the
page and the MCP process; the next request respawns it lazily.

`EventSource` cannot POST, so the frontend uses `fetch` +
`ReadableStream` in `src/lib/market-analysis.ts`.

### 9. Module split

To respect the 220–250 line file rule and keep dependency directions clear:

```
routers/market_analysis.py -> mcp/deep_analysis.py -> mcp/deep_sources.py
                                               -> mcp/deep_support.py
                                               -> mcp/deep_recommend.py
                                               -> mcp/deep_cache.py
                                               -> mcp/analysis_events.py
mcp/analysis_query.py   (generic identity + deep links)
models/market_health.py (health payload; imports only models/sdd.py)
```

`deep_sources` owns per-source failure isolation, `deep_support` is pure
(selection/clamping), `deep_recommend` owns the async LLM window, `deep_cache`
wraps serialization and `analysis_query` keeps `/valuate` normalisation frozen.
No source imports another source; no cycle is introduced.

## Rejected alternatives

- **HTTP-only deep path:** Wallapop is a JS shell and eBay blocks the fast
  connectors; browser data is the requirement.
- **Fallback catalog in `/analyze`:** would make a blocked analysis look
  successful and violate the “real browser data only” decision.
- **Multiple parallel pages:** higher throughput but a worse fingerprint, more
  memory and no single lock; deferred.
- **`EventSource`:** cannot POST a request body.
- **Persisting `description` or coordinates in the cache:** unnecessary PII and
  a stale-relevance risk.

## Consequences and risks

- The deep path depends on the optional `market-browser` profile; without it the
  API returns `503 browser_unavailable` (by design).
- Live counts vary with the venue network; `blocked` is a valid, visible outcome.
- Sequential sources and LLM latency keep the deep path outside the 6 s
  interaction budget; the UI must treat it as a background analysis.
- Vinted, `backend/mcp_server.py` (FastMCP CLI) and the Level 2 refresh remain
  deferred and are tracked in `docs/backlog.md`.
