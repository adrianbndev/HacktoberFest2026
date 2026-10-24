# ADR-004: Parallel browser sources (Phase 3)

* **Status:** Accepted (Phase 3 / MOD-04)
* **Date:** 2026-10-24
* **Owners:** Track C (Matías)
* **Supersedes:** ADR-003 §3 (single page + global lock) and the “multiple
  parallel pages” rejected alternative. Everything else in ADR-003 stands.

## Context

Phase 2 runs eBay, Wallapop and Milanuncios sequentially on one locked page
(`BrowserSessionManager`). Measured live latency is dominated by Milanuncios
(18–22 s, up to 6 result pages) while eBay/Wallapop finish in 4–5 s, so the deep
path costs the sum of the three sources and can exhaust the shared deadline.

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

| Run | Processes / pages | Wall | Sum of sources | Max source |
|---|---|---|---|---|
| Sequential baseline | 1 / 1 | 31 132 ms | 31 021 ms | 22 231 ms (Milanuncios) |
| Parallel | 3 / 3 | **20 860 ms** | 28 451 ms | 20 859 ms (Milanuncios) |

- `wall / max(source) = 1.00`, `wall / sum(sources) = 0.73`: the three pages
  really run concurrently and the wall time tracks the slowest source.
- Parallel speed-up vs this sequential baseline: **1.49×**. The theoretical cap
  is bounded by Milanuncios; eBay and Wallapop are fully hidden.
- Per source (parallel): eBay 2 369 ms (`blocked`, anti-bot interstitial on that
  run), Wallapop 5 223 ms (`ok`, 40 listings), Milanuncios 20 859 ms (`ok`, 16
  listings). The blocked eBay run is reported, never replaced.
- Focus test: `select_page(bringToFront=true)` on the Milanuncios page while all
  three were working took 1 361 ms inside its own MCP process and did **not**
  block or delay the other pages (they kept their expected latencies). A second
  `select_page(bringToFront=false)` also succeeded. No focus stealing that
  changes results.
- Fingerprint on all three pages: `navigator.webdriver=false`,
  `HeadlessChrome=false`, `__puppeteer`/`__playwright` `undefined`,
  `window.chrome=object`, `es-ES`, `Europe/Madrid`, `hardwareConcurrency=8`.
  All pages reported `visibilityState="visible"` under Xvfb.
- Resources: container CPU **10.21 %**, memory **1.464 GiB / 7.808 GiB**
  (18.75 %), **18** Chromium processes, **2 523 MB** summed Chromium RSS, 253
  container PIDs during the parallel run.

### Decision

**Plan A is accepted.** Three MCP processes, each with its own `new_page`, attach
to the single `market-browser` Chrome. Plan B (three Chrome containers, one CDP
each) is documented as the fallback but is not implemented.

Because background pages reported `visible` and the measured latencies did not
degrade, the spike did not prove throttling. The entrypoint still gains
`--disable-background-tab-throttling --disable-renderer-backgrounding
--disable-backgrounding-occluded-windows` as hardening for venues/GPUs where
occluded tabs would be throttled; this is additive and does not change the
fingerprint.

## Decisions

### 1. `BrowserSessionPool`

A bounded pool of `BrowserSessionManager` slots (`MARKET_BROWSER_POOL_SIZE`,
default 3). Each slot owns:

- one `chrome-devtools-mcp` stdio process (`--browserUrl $CDP_URL`, never
  `--headless`, never `--enable-automation`, never launches Chrome);
- one page created with `new_page` and reused by that slot only;
- its **own** `asyncio.Lock`, so slots do not serialize each other;
- per-operation timeout, one restart of a dead MCP process, and `close_page`
  plus process shutdown on release/shutdown.

`async with pool.session() as page:` acquires a free slot with a bounded wait. A
disconnect or cancellation releases only the slot that was in use. The pool
never falls back to the fast path or to synthetic data.

### 2. Parallel engine

`DeepMarketAnalyzer` starts all requested sources at once
(`asyncio.gather`/`as_completed`) with one pool session per source.
`MARKET_SOURCE_CONCURRENCY ∈ {1,2,3}` (default 3) caps simultaneous sources;
`1` reproduces Phase 2's sequential behavior. Aggregation is unchanged: one IQR
pass, per-platform quota, confidence, partial statuses. `sources[]` in the final
payload is sorted by `request.sources`; SSE `source_result` follows completion
order.

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
| `MARKET_BROWSER_POOL_SIZE` | `3` | MCP processes/pages in the pool (1–3) |

The pool size must be ≥ concurrency; a smaller pool serializes the excess
sources instead of failing. Anti-throttling flags live in
`backend/docker/browser-entrypoint.sh`.

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
- Milanuncios remains the critical path (≈20 s); parallel sources cannot reduce
  below its own latency.
- Pool restarts and shutdown are covered by fake-MCP tests; live behavior still
  depends on the venue network and is re-checked with the spike/smoke scripts.
