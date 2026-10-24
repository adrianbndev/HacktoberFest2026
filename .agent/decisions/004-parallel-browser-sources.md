# ADR-004: Parallel browser sources (Phase 3)

* **Status:** Accepted (Phase 3 / MOD-04)
* **Date:** 2026-10-24
* **Owners:** Track C (Matías)
* **Supersedes:** ADR-003 §3 (single page + global lock) and the “multiple
  parallel pages” rejected alternative. Everything else in ADR-003 stands.

## Context

Phase 2 runs eBay, Wallapop and Milanuncios sequentially on one locked page
(`BrowserSessionManager`). Measured live latency is dominated by Milanuncios
(≈11 s with 3 result pages, ≈21 s with 6) while eBay/Wallapop finish in 4–5 s,
so the deep path costs the sum of the three sources and can exhaust the shared
deadline.

`chrome-devtools-mcp@1.10.1` serializes tool calls **per process** (global tool
mutex), and `BrowserSessionManager` adds a process-wide `asyncio.Lock`. Parallel
sources therefore require several MCP processes, not several calls on one
process. The Phase 3 brief makes a spike a hard gate: plan A = N MCP processes
against the same Chrome, one page each; plan B = one Chrome container per
source.

## Spike (mandatory gate)

Script: `scripts/pool_spike.py` (committed). Result:
`artifacts/pool-spike.json` (gitignored). Environment: macOS arm64 host, Docker
`market-browser:local` (Debian Chromium 156, Xvfb, headful), query
`iPhone 13 128GB`, 2026-10-24.

### Plan A measurements

Measured with the new 3-page Milanuncios default
(`MARKET_MILANUNCIOS_MAX_PAGES=3`):

| Run | Processes / pages | Wall | Sum of sources | Max source |
|---|---|---|---|---|
| Sequential baseline | 1 / 1 | 20 618 ms | 20 500 ms | 11 067 ms (Milanuncios) |
| Parallel | 3 / 3 | **11 970 ms** | 22 774 ms | 11 969 ms (Milanuncios) |

- `wall / max(source) = 1.00`, `wall / sum(sources) = 0.53`: the three pages
  really run concurrently and the wall time tracks the slowest source.
- Parallel speed-up vs this sequential baseline: **1.72×**. The theoretical cap
  is bounded by Milanuncios; eBay and Wallapop are fully hidden.
- Per source (parallel): eBay 5 279 ms (`ok`, 60 listings), Wallapop 5 526 ms
  (`ok`, 40 listings), Milanuncios 11 969 ms (`ok`, 7 usable listings).
- An earlier run with the old 6-page Milanuncios depth measured 31 132 ms
  sequential vs 20 860 ms parallel (1.49×); the lower page depth is what makes
  the parallel path fit the demo budget.
- Focus test: `select_page(bringToFront=true)` on the Milanuncios page while all
  three were working took 2 170 ms inside its own MCP process and did **not**
  block or delay the other pages (they kept their expected latencies). A second
  `select_page(bringToFront=false)` also succeeded. No focus stealing that
  changes results.
- Fingerprint on all three pages: `navigator.webdriver=false`,
  `HeadlessChrome=false`, `__puppeteer`/`__playwright` `undefined`,
  `window.chrome=object`, `es-ES`, `Europe/Madrid`, `hardwareConcurrency=8`.
  All pages reported `visibilityState="visible"` under Xvfb.
- Resources: container CPU **16.46 %**, memory **1.271 GiB / 7.808 GiB**
  (16.27 %), **18** Chromium processes, **2 276 MB** summed Chromium RSS, 257
  container PIDs during the parallel run.

### Decision

**Plan A is accepted.** Three MCP processes, each with its own `new_page`, attach
to the single `market-browser` Chrome. Plan B (three Chrome containers, one CDP
each) is documented as the fallback but is not implemented.

### Milanuncios page depth (3 vs 6)

Milanuncios was fetching up to 6 result pages unconditionally. The depth is now
`MARKET_MILANUNCIOS_MAX_PAGES` (default **3**, max 6). The spike forced every
configured page (raising `min_results`) to measure the real page cost:

| Pages | Latency | Raw listings | Usable listings |
|---|---|---|---|
| 3 | **10 696 ms** | 8 | **8** |
| 6 | 21 491 ms | 16 | 15 |

- 3 pages already reach the 8 usable samples needed for a stable demo, so the
  conditional 4-page run was not needed.
- 6 pages add **+10 795 ms** for **+7 usable samples** (~1.54 s per extra usable
  listing). That is a completeness mode, not the interactive default.
- In production the source still stops early once it has 14 raw cards, so the
  6-page numbers are an upper bound; the default 3-page run is the measured
  demo latency.
- Trade-off: 3 pages keep the deep path near 12 s parallel / 20 s sequential;
  6 pages raise it to ~21 s parallel / ~31 s sequential. Both are inside the
  60 s deadline, but only 3 pages fit a snappy demo.
- `/api/market/analyze` request/response contracts are unchanged; this is a
  configuration knob only.

### Spike 1b: Milanuncios HTTP connector vs browser

Script: `scripts/milanuncios_http_spike.py` (committed), result
`artifacts/milanuncios-http-spike*.json` (gitignored). It drives the fast
`MilanunciosConnector` parser over real HTTP pages and compares it with the
browser depth above.

| Transport | Pages | Latency | Usable listings |
|---|---|---|---|
| HTTP (first run) | 1 | 0.92 s | 1 |
| HTTP (first run) | 2 | **1.52 s** | **10** |
| HTTP (first run) | 3 | 2.51 s | 7 |
| Browser | 3 | 10.70 s | 8 |
| Browser | 6 | 21.49 s | 15 |

After the first run, nine consecutive HTTP samples (three per depth) returned
HTTP 200 with an anti-bot/PerimeterX body: **0 usable listings in 0.2–0.8 s**.
The block persisted across a later single-sample run. The browser pages kept
working with a clean fingerprint.

Decision:

- `MARKET_MILANUNCIOS_TRANSPORT=auto` (default): try HTTP first with up to
  `MARKET_MILANUNCIOS_MAX_PAGES` (3) pages; if it is blocked, has no listings or
  yields fewer than **8 usable** listings, fall back to the browser source on a
  free pool slot. All data is real; there is no synthetic fallback.
- `http` is kept for measurement/debugging and reports the HTTP failure status
  without a browser retry; `browser` forces the browser source.
- HTTP is 4–10× faster when it works, but it is not reliable enough to be the
  only transport on the venue network. The 8-usable threshold is unchanged.
- The fast `/valuate` connector remains single-page and frozen; multi-page HTTP
  is only used by the deep path.

Because background pages reported `visible` and the measured latencies did not
degrade, the spike did not prove throttling. The entrypoint still gains
`--disable-background-tab-throttling --disable-renderer-backgrounding
--disable-backgrounding-occluded-windows` as hardening for venues/GPUs where
occluded tabs would be throttled; this is additive and does not change the
fingerprint.

## Decisions

### 1. `BrowserSessionPool`

A bounded pool of `BrowserSessionManager` slots (`MARKET_BROWSER_POOL_SIZE`,
default **2**: eBay + Wallapop). Each slot owns:

- one `chrome-devtools-mcp` stdio process (`--browserUrl $CDP_URL`, never
  `--headless`, never `--enable-automation`, never launches Chrome);
- one page created with `new_page` and a unique data-URL token (background
  tab), parsed by token from `list_pages` so two concurrent `new_page` calls
  cannot make two slots share the globally "selected" page; the page is reused
  by that slot only;
- its **own** `asyncio.Lock`, so slots do not serialize each other;
- per-operation timeout, one restart of a dead MCP process, and `close_page`
  plus process shutdown on release/shutdown.

`async with pool.session() as page:` acquires a free slot with a bounded wait. A
disconnect or cancellation releases only the slot that was in use. The pool
never falls back to the fast path or to synthetic data.

### 2. Parallel engine

`DeepMarketAnalyzer` starts all requested sources at once
(`asyncio.gather`/`as_completed`). eBay and Wallapop each take one of the two
browser slots; Milanuncios uses the fast HTTP connector (2–3 pages) in parallel
with them. If HTTP Milanuncios is blocked, empty or yields fewer than 8 usable
listings, the engine falls back to the browser Milanuncios source on a free
slot (waiting for eBay/Wallapop if needed). `MARKET_SOURCE_CONCURRENCY ∈
{1,2,3}` (default 3) caps simultaneous sources; `1` reproduces Phase 2's
sequential behavior. Aggregation is unchanged: one IQR pass, per-platform quota,
confidence, partial statuses. `sources[]` in the final payload is sorted by
`request.sources`; SSE `source_result` follows completion order.

### 3. Failure semantics (unchanged from Phase 2)

- One blocked source → HTTP 200, that source `status=blocked` with `error`, the
  other sources priced normally.
- All requested sources blocked/no usable listings → `503` with per-source
  statuses.
- Pool or browser unavailable → `503 browser_unavailable`; never `500`, never
  fallback data.
- A captcha is reported, never solved.

### 4. Configuration

| Variable | Default | Meaning |
|---|---|---|
| `MARKET_SOURCE_CONCURRENCY` | `3` | simultaneous source collections (1–3) |
| `MARKET_BROWSER_POOL_SIZE` | `2` | MCP processes/pages for eBay + Wallapop (1–3) |
| `MARKET_MILANUNCIOS_MAX_PAGES` | `3` | Milanuncios result pages (1–6); 6 = completeness |
| `MARKET_MILANUNCIOS_TRANSPORT` | `auto` | `http`, `browser` or `auto` (HTTP first, browser fallback) |

The pool size bounds browser slots only; HTTP does not consume one. Extra
browser sources wait for a free slot instead of failing, and a Milanuncios
browser fallback waits for eBay/Wallapop to release one. Anti-throttling flags
live in `backend/docker/browser-entrypoint.sh`.

## Rejected alternatives

- **One MCP process, parallel calls:** impossible; the MCP has a per-process
  global tool mutex.
- **Plan B (three Chrome containers):** viable in principle, but triples memory
  and Xvfb/profile complexity for no measured gain; kept as a documented
  fallback if plan A regresses.
- **Headless browser:** changes the fingerprint and is forbidden by the
  guardrails.
- **Global lock around the pool:** would reproduce Phase 2 latency; each slot is
  locked independently.
- **Fallback/synthetic data on a blocked source:** violates the Phase 2/3
  contract.

## Consequences and risks

- Memory grows with the pool: each Chromium renderer is ~100–200 MB; the spike
  measured ~2.5 GB summed RSS for three active pages, still under the 7.8 GB
  container limit. `shm_size: 2g` is retained.
- More concurrent pages increase the anti-bot surface; the fingerprint was clean
  in the spike, and blocking is reported rather than bypassed.
- Milanuncios remains the critical path (≈11 s with 3 pages, ≈21 s with 6);
  parallel sources cannot reduce below its own latency.
- Pool restarts and shutdown are covered by fake-MCP tests; live behavior still
  depends on the venue network and is re-checked with the spike/smoke scripts.
