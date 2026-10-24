# Market valuation API (MOD-04, Phase 1 + Phase 2 + Phase 3)

Second-hand valuation for the LifeOS & ReCommerce AI demo, with two independent
paths sharing the same pricing contract:

```
Fast path (frozen, <= 2.8 s)               Deep path (Phase 3, <= 60 s)
POST /api/market/valuate                   POST /api/market/analyze
  -> normalise query                         -> clean generic brand/model
  -> eBay + Wallapop + Milanuncios           -> 2 MCP slots: eBay + Wallapop
     in parallel (1.6 s/source)              -> Milanuncios HTTP (3 pages) in parallel
  -> filter / dedupe / IQR                   -> HTTP blocked/<8: browser fallback
  -> P_min < P_avg < P_max                   -> per-source statuses + listings
  -> comparable listings                     -> relevance + one IQR pass
  -> optional DeepSeek recommendation        -> per-platform quota (4/12)
                                             -> confidence + cached recommendation
                                             -> SQLite cache (15 min, real only)

                                           POST /api/market/analyze/stream (SSE)
```

`/valuate` and its contracts are frozen. The deep path never uses
`catalog_fallback` or synthetic fixtures: if every source is blocked it returns
HTTP `503` with per-source statuses.

## Architecture and dependency direction

```
routers/market.py                  -> mcp/market_analysis.py (fast, frozen)
                                   -> mcp/deep_analysis.py (shared browser manager)
routers/market_analysis.py         -> mcp/deep_analysis.py, mcp/sse.py
mcp/deep_analysis.py
  -> mcp/deep_parallel.py          -> run_sources + aggregate_results
  -> mcp/deep_sources.py           -> mcp/browser/pool.py
                                   -> mcp/deep_milanuncios.py
                                   -> mcp/browser/sources/{base,ebay,wallapop,milanuncios}.py
  -> mcp/deep_milanuncios.py       -> mcp/connectors.py, mcp/browser/pool.py
  -> mcp/browser/pool.py           -> mcp/browser/session.py, mcp/browser/mcp_client.py
  -> mcp/deep_support.py           -> mcp/analysis_query.py, mcp/pricing_math.py
  -> mcp/deep_recommend.py         -> mcp/deepseek.py
  -> mcp/deep_cache.py             -> mcp/cache.py
  -> mcp/{relevance,pricing_math}.py
mcp/cache.py                       -> standard library only
models/market_health.py            -> models/sdd.py only
models/                            -> no mcp/ imports
```

`pricing_math.py` is pure: no network, no LLM, no settings. Sources never raise
to the router; a blocked/timeout/error source becomes a status. `app/` never
imports `scripts/`; `scripts/mcp_client.py` is a shim over
`app/mcp/browser/mcp_client.py`.

## Quick start

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

pytest -q
ruff check app tests
mypy app

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger UI: <http://127.0.0.1:8000/docs>

### Health

```bash
curl -s http://127.0.0.1:8000/api/market/health
```

```json
{
  "status": "ok",
  "service": "LifeOS ReCommerce Market API",
  "version": "0.1.0",
  "fallbackEnabled": true,
  "jitterEnabled": true,
  "recommendationEnabled": false,
  "timestamp": "2026-10-24T11:34:18.876869+00:00",
  "browser": {
    "connected": false,
    "url": "http://market-browser:9222",
    "lastError": null
  },
  "cache": {
    "path": "/app/data/market_cache.sqlite",
    "ttlSeconds": 900
  },
  "analysisEnabled": true
}
```

`browser.connected` reflects the process-wide MCP client: `false` means it has
not been used yet (or the last probe failed). Before spawning the MCP, the
analyzer performs a TCP reachability probe against `CDP_URL`; a missing browser
fails fast with `503 browser_unavailable` (the MCP is never allowed to launch
its own Chrome). `analysisEnabled` mirrors
`MARKET_ANALYSIS_ENABLED`; when `false`, `/analyze` returns `503`.

### Valuate

```bash
curl -s -X POST http://127.0.0.1:8000/api/market/valuate \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "iPhone 13 128GB",
    "category": "Móviles",
    "conditionScore": 80,
    "conditionLabel": "Como nuevo",
    "brand": "Apple",
    "model": "iPhone 13",
    "description": "Caja original, batería 89%, sin arañazos",
    "includeRecommendation": true
  }'
```

```json
{
  "priceMin": 284,
  "priceAvg": 346,
  "priceMax": 430,
  "sampleSize": 11,
  "platforms": ["wallapop", "milanuncios", "ebay"],
  "comparableListings": [
    {
      "title": "iPhone 13 128GB · Buen estado",
      "price": 271,
      "platform": "wallapop",
      "condition": "Buen estado",
      "url": "https://es.wallapop.com/app/search?keywords=Apple%20iPhone%2013"
    }
  ],
  "source": "stealth_fallback",
  "recommendation": {
    "summary": "iPhone 13 128GB: valor medio de 346 € en un rango de 284-430 €.",
    "suggestedPrice": 346,
    "bullets": [
      "Estado Como nuevo (80/100): valor de mercado ajustado a 346 €.",
      "Publica en wallapop, milanuncios, ebay con un rango de 284-430 €.",
      "Tasación basada en 11 anuncios comparables. Destaca: original, bateria."
    ],
    "risks": ["El precio final puede variar según la demanda local y la urgencia de la venta."],
    "negotiationMarginEur": 17
  },
  "warnings": [
    "Fuente ebay no disponible (blocked_http_403).",
    "Fuente milanuncios no disponible (timeout).",
    "Fuente wallapop no disponible (no_listings_parsed).",
    "Fuentes en vivo no disponibles: tasación determinista con el catálogo curado España 2026."
  ]
}
```

`recommendation` is omitted when `includeRecommendation` is `false` or the LLM
fails (a warning is added instead).

## Deep analysis: `POST /api/market/analyze`

Real data only. eBay and Wallapop use two independent
`chrome-devtools-mcp@1.10.1` processes (one page each) attached to the headful
browser managed by the `market-browser` container. Milanuncios tries the fast
HTTP connector first (3 pages by default) in parallel with them; if HTTP is
blocked, empty or yields fewer than 8 usable listings, it falls back to the
browser source on a free pool slot. The engine never launches Chrome itself,
never uses `--headless`/`--enable-automation`, and never solves a captcha.

### Request

| Field | Type | Required | Rules |
|---|---|---|---|
| `name` | string | yes | 2–200 chars; this is the marketplace query |
| `description` | string | no | ≤ 2000 chars; relevance/recommendation only |
| `category` | string | yes | 1–120 chars |
| `brand` | string | no | ≤ 80; generic values (`Sin marca`, `Genérica`, `N/A`, `-`, `unknown`, `No aplica`) are treated as absent |
| `model` | string | no | ≤ 120; generic values or a model equal to `name` are treated as absent |
| `conditionScore` | integer | yes | 0–100 |
| `conditionLabel` | enum | yes | five canonical labels |
| `location` | object | no | `{lat, lng}` |
| `sources` | array | no | subset of `wallapop|vinted|milanuncios|ebay`; default `["ebay","wallapop","milanuncios"]` |
| `includeRecommendation` | boolean | no | default `true` |

`name` alone builds the search query (normalised, filler words removed). The
cleaned brand/model feed the relevance filter; `description` is never used to
search and is never stored in the cache.

```bash
curl -s -X POST http://127.0.0.1:8000/api/market/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Silla de madera",
    "description": "Silla de madera en estado Como nuevo, con pequenas marcas.",
    "category": "Mobiliario",
    "brand": "Sin marca",
    "model": "Silla de madera",
    "conditionScore": 85,
    "conditionLabel": "Como nuevo",
    "sources": ["ebay", "wallapop", "milanuncios"],
    "includeRecommendation": true
  }'
```

### Response

- `sources[]`: one entry per requested source, **sorted by the order of
  `request.sources`**, with `status ∈ {ok, blocked, timeout, no_listings,
  error}`, `sampleSize`, `listings`, `latencyMs` and optional `error`. Every
  listing URL is absolute; a missing listing URL falls back to the platform
  search deep link. Completion order only affects SSE, never this array.
- `valuation`: `0 < priceMin < priceAvg < priceMax`, `sampleSize` is the number
  of listings actually priced after one IQR pass, `platforms` includes every
  source with usable data (even if its listings are not in the final 12), and
  `confidence ∈ [0,1]` blends sample size, coverage, price agreement and source
  reliability.
- `comparableListings`: up to 12 listings, up to 4 per successful source, then
  filled by price proximity to `priceAvg`.
- `recommendation`: omitted when `includeRecommendation=false`, the LLM fails,
  or the budget is exhausted. `suggestedPrice` is always inside
  `[priceMin, priceMax]`; a clamp adds a warning.
- `warnings`: per-source failures, small sample, relevance fallback,
  recommendation skipped/clamped.
- `cached` is `true` only on a real cache hit; `analyzedAt` is ISO 8601.

The deep path uses `deepseek-v4-pro` with thinking and **disables the
deterministic template**: a failed LLM omits the recommendation and adds a
warning instead of inventing text.

### Errors

| Case | HTTP | Body |
|---|---|---|
| Every source blocked / no usable listings | `503` | `{"detail": "...", "sources": {"ebay": "blocked", ...}}` |
| Browser pool/MCP unavailable | `503` | `{"detail": "browser_unavailable", "sources": {}}` |
| Analysis disabled | `503` | `{"detail": "analysis_disabled", "sources": {}}` |
| Unexpected engine error | `503` | `{"detail": "analysis_failed", "sources": {}}` |
| Invalid request | `422` | Pydantic details |

Never `500`, never synthetic data.

## SSE: `POST /api/market/analyze/stream`

`Content-Type: text/event-stream`, `Cache-Control: no-cache`,
`X-Accel-Buffering: no`. Wire format is `event: <name>\ndata: <json>\n\n`.

1. `analysis_started` — `{query, sources, cached}`.
2. `source_started` — `{source}` for **all** requested sources, immediately.
3. `source_result` — the same object as `sources[]`, in **completion order**
   (may differ from the request order).
4. `valuation` — the valuation object.
5. `recommendation` — the recommendation object (omitted when disabled/failed).
6. `done` — the full response object; its `sources[]` is sorted by request order.
7. `error` — `{detail, sources?}` on a fatal error.

- A heartbeat comment (`: ping\n\n`) is sent every 15 s.
- A cache hit emits `analysis_started` with `cached=true` and then `done` fast.
- On client disconnect the producer is cancelled; each in-flight source releases
  **its own** pool slot. The pool and its other slots stay alive for concurrent
  requests (no process-wide stop).

```bash
curl -N -X POST http://127.0.0.1:8000/api/market/analyze/stream \
  -H 'Content-Type: application/json' \
  -d '{"name":"Silla de madera","category":"Mobiliario","conditionScore":85,"conditionLabel":"Como nuevo","sources":["wallapop"]}'
```

## Cache

- SQLite at `MARKET_CACHE_PATH` (default `/app/data/market_cache.sqlite`),
  TTL `MARKET_CACHE_TTL_SEC=900` (15 min).
- Key: normalised query + condition score + sorted sources. `description`, user
  identity and coordinates are never part of the key or payload.
- Only real results are stored (including partial results with at least one
  usable source). A corrupted payload is a miss, never a request failure.
- Writes use `asyncio.to_thread`, one connection per operation, WAL mode and a
  busy timeout. A cache failure never fails the analysis.

## Browser sources

| Source | Search URL | Extraction | Expected good-connection count |
|---|---|---|---|
| eBay | `ebay.es/sch/i.html` with `LH_BIN=1`, `LH_ItemCondition=3000`, `_ipg=60` | `li.s-item, li.s-card`, strips the accessibility suffix, skips "Shop on eBay", optional page 2 if < 20 | ≥ 20 |
| Wallapop | `es.wallapop.com/app/search?keywords=…&order_by=newest` | scrolls 4 times, extracts `a[href*='/item/']`, parses `1.234 €` and `1.234,56 €` | ≥ 20 |
| Milanuncios | `milanuncios.com/anuncios/?s=…&pagina=N` | **HTTP first**: `article` cards, depth `MARKET_MILANUNCIOS_MAX_PAGES` (1–6, default 3); PerimeterX/captcha/access-denied → browser fallback. `MARKET_MILANUNCIOS_TRANSPORT=auto|http|browser` | ≥ 8 with 3 pages |

Parser unit tests use saved HTML fixtures under `backend/tests/fixtures/`
(`*_browser.html`, `milanuncios_blocked.html`). Fixtures are test-only and are
never imported by the runtime deep path. Vinted is deferred (backlog).

### Milanuncios page depth

`MARKET_MILANUNCIOS_MAX_PAGES` (1–6, default **3**) bounds how many result pages
the browser source visits. Measured on 2026-10-24 (`iPhone 13 128GB`, forced
depth, headful Chromium under Xvfb):

| Pages | Latency | Raw listings | Usable listings |
|---|---|---|---|
| 3 | **10.7 s** | 8 | **8** |
| 6 | 21.5 s | 16 | 15 |

Three pages reach the 8 usable samples a demo needs; six pages cost **+10.8 s**
for **+7 usable samples** (~1.5 s per extra usable listing). Use `3` for the
demo and `6` only for completeness runs. In normal operation the source stops
early once it has 14 raw cards, so 6 pages is an upper bound. This is a
configuration knob only: the `/analyze` request/response contract does not
change.

## Contract

### Request (frozen fields + additive optional ones)

| Field | Type | Required | Rules |
|---|---|---|---|
| `query` | string | yes | 2–200 chars |
| `category` | string | yes | non-blank |
| `conditionScore` | integer | yes | 0–100 |
| `conditionLabel` | enum | yes | `Nuevo`, `Como nuevo`, `Buen estado`, `Desgaste visible`, `Para piezas` |
| `brand` | string | no | ≤ 80 chars |
| `model` | string | no | ≤ 120 chars |
| `description` | string | no | ≤ 2000 chars |
| `includeRecommendation` | boolean | no | default `false` |

Unknown fields are rejected with `422`.

### Response

| Field | Type | Notes |
|---|---|---|
| `priceMin`, `priceAvg`, `priceMax` | integer | always `0 < min < avg < max` |
| `sampleSize` | integer | usable listings after IQR filtering |
| `platforms` | array | deduplicated platforms present in `comparableListings` |
| `comparableListings` | array | ≤ 12; every item has a functional URL |
| `source` | enum | `live_mcp` or `stealth_fallback` |
| `recommendation` | object? | only with `includeRecommendation=true` and a usable LLM/template |
| `warnings` | array | additive diagnostics |

The Pydantic response model rejects `null`, `NaN` and non-positive prices, so an
invalid payload can never be serialised.

### 503 body

When `MARKET_ALLOW_FALLBACK=false` and every live source fails:

```json
{
  "detail": "Ninguna fuente de mercado devolvió anuncios utilizables y el fallback está desactivado.",
  "sources": {
    "wallapop": "network_error",
    "milanuncios": "timeout",
    "ebay": "blocked_http_403"
  }
}
```

Never `500` for the valuation paths.

## Latency budget

| Stage | Budget | Notes |
|---|---|---|
| Jitter in `/valuate` | 0.2–0.6 s | `human_jitter`, disabled with `0` |
| Connectors (parallel) | 1.6 s | hard `asyncio.wait_for` per source |
| Filtering + pricing | < 5 ms | pure functions |
| Recommendation (opt-in) | separate window | `DEEPSEEK_RECOMMENDATION_BUDGET_SEC` (default 25 s); not part of the 2.8 s market SLA |
| **Total** | **≤ 2.8 s** | measured with mocks in tests |

Measured in Docker: **1.79 s** with live Milanuncios listings, and **1.8–2.3 s**
when every source was blocked and the deterministic fallback ran. Live sources
are bounded by the same deadline.

The 0.65–1.2 s jitter default is reserved for `/refresh` (Level 2), not this
interactive endpoint.

### Deep path targets

| Stage | Target | Hard bound |
|---|---|---|
| First `source_result` on a warm browser | < 6 s | `MARKET_SOURCE_TIMEOUT_SEC` (25 s) |
| Full analysis without recommendation | < 20 s | `MARKET_ANALYSIS_DEADLINE_SEC` (60 s) |
| Recommendation (when enabled) | minutes are not acceptable | remaining deadline ∩ `DEEPSEEK_RECOMMENDATION_BUDGET_SEC` |
| Cache hit (`/analyze` and SSE) | < 1 s | no browser call |

eBay and Wallapop run on two browser slots; Milanuncios HTTP runs in parallel
with them. When HTTP is blocked, the browser fallback waits for a free slot
(eBay/Wallapop usually release it in ~4–5 s), so the worst case is
`max(eBay, Wallapop) + Milanuncios browser` ≈ 16 s. The deadline is shared, and
a source that would exceed it is reported as `timeout` instead of aborting the
response.

## Fallback policy

- Live sample `source="live_mcp"`.
- If no usable live listing remains, the deterministic catalog supplies the
  sample (`source="stealth_fallback"`) **only when** `MARKET_ALLOW_FALLBACK=true`
  (default).
- With the flag disabled, the API returns the structured `503` above.
- The fallback catalog contains curated Spain-2026 medians for common models and
  a stable SHA-256 estimator for unknown products.
- Every fallback listing links to a real platform search URL.
- **The deep path (`/analyze`) never uses this fallback.** It returns `503` when
  no real browser listing is usable.

## DeepSeek recommendation

- Base URL `https://api.deepseek.com` (OpenAI-compatible SDK).
- `DEEPSEEK_REASONING_MODEL` (default `deepseek-v4-pro`): `extra_body={"thinking":
  {"type": "enabled"}}` and `reasoning_effort="max"`.
- `DEEPSEEK_FAST_MODEL` (default `deepseek-flash`): thinking disabled; used for
  query parsing and as the `model_not_found` fallback.
- JSON output (`response_format={"type": "json_object"}`); empty or invalid
  content is retried once per model, then the deterministic template is used.
- Every payload is validated with Pydantic. `suggestedPrice` is clamped to
  `[priceMin, priceMax]`; a clamp adds a warning.
- `deepseek-reasoner` is legacy and is not referenced anywhere in the code.
- Without `DEEPSEEK_API_KEY` the template recommendation is returned immediately
  (text only, never market data). The `/analyze` engine constructs the
  recommender with `allow_template=False`, so a missing key or LLM failure omits
  the recommendation and adds a warning instead.
- `deepseek-v4-pro` with `reasoning_effort="max"` takes **~12–23 s** for a real
  recommendation. That is why `includeRecommendation=true` is an **opt-in**
  window outside the 2.8 s market SLA. The default `/valuate` call (no
  recommendation) stays under 2.8 s. For a snappy demo, either omit
  `includeRecommendation` or set `DEEPSEEK_REASONING_MODEL=deepseek-flash` in
  `.env` (≈4 s, lower quality). `DEEPSEEK_RECOMMENDATION_BUDGET_SEC=0` forces
  the deterministic template.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MARKET_ALLOW_FALLBACK` | `true` | allow the deterministic catalog |
| `MARKET_JITTER_MIN_SEC` | `0.2` | `/valuate` jitter lower bound |
| `MARKET_JITTER_MAX_SEC` | `0.6` | `/valuate` jitter upper bound (`0` disables) |
| `MARKET_CONNECTOR_TIMEOUT_SEC` | `1.6` | per-source timeout |
| `MARKET_DEADLINE_SEC` | `2.8` | whole-request deadline |
| `MARKET_MAX_COMPARABLE_LISTINGS` | `12` | response cap |
| `MARKET_MIN_SAMPLE_SIZE` | `3` | below it, a small-sample warning is added |
| `MARKET_MAX_LISTING_PRICE_EUR` | `100000` | sanity cap for parsed listings |
| `DEEPSEEK_API_KEY` | empty | enables recommendations |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible endpoint |
| `DEEPSEEK_REASONING_MODEL` | `deepseek-v4-pro` | recommendation model |
| `DEEPSEEK_FAST_MODEL` | `deepseek-flash` | parsing / fallback model |
| `DEEPSEEK_TIMEOUT_SEC` | `30.0` | transport timeout per attempt |
| `DEEPSEEK_RECOMMENDATION_BUDGET_SEC` | `25.0` | opt-in recommendation window (`0` disables the LLM) |
| `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS` | `1` | MCP telemetry off |
| `MARKET_ANALYSIS_ENABLED` | `true` | expose the deep analysis |
| `MARKET_ANALYSIS_DEADLINE_SEC` | `60` | whole deep request deadline |
| `MARKET_SOURCE_TIMEOUT_SEC` | `25` | per-source browser timeout |
| `MARKET_BROWSER_TIMEOUT_SEC` | `45` | MCP tool-call timeout |
| `MARKET_PLATFORM_QUOTA` | `4` | max listings per source in the final 12 |
| `MARKET_MILANUNCIOS_MAX_PAGES` | `3` | Milanuncios result pages (1–6); 6 = completeness |
| `MARKET_MILANUNCIOS_TRANSPORT` | `auto` | `http`, `browser` or `auto` (HTTP first, browser fallback) |
| `MARKET_BROWSER_POOL_SIZE` | `2` | MCP processes/pages for eBay + Wallapop (1–3) |
| `MARKET_SOURCE_CONCURRENCY` | `3` | simultaneous sources (1 = Phase 2 sequential) |
| `MARKET_CACHE_PATH` | `/app/data/market_cache.sqlite` | SQLite cache (`./data/...` works locally too) |
| `MARKET_CACHE_TTL_SEC` | `900` | cache TTL; `0` disables hits |
| `CDP_URL` | `http://market-browser:9222` | Chrome DevTools endpoint |

Copy `.env.example` to the repo-root `.env` for local overrides (this repository
already ships a gitignored `.env` with an empty `DEEPSEEK_API_KEY`). Both
`uvicorn` from `backend/` and `docker compose` read that same root file. Never
commit `.env`.

After pasting a key, recreate the backend container so the env is injected:

```bash
docker compose up -d --force-recreate lifeos-backend
curl -s http://127.0.0.1:8000/api/market/health | jq .recommendationEnabled
```

## Docker

```bash
docker compose config
docker compose up --build lifeos-backend
curl -s http://127.0.0.1:8000/api/market/health

# Phase 2 deep analysis (optional browser + backend)
docker compose --profile browser up --build -d market-browser
docker compose up --build lifeos-backend
curl -s http://127.0.0.1:9222/json/version
python scripts/fingerprint_check.py
python scripts/smoke_analyze.py --query "Silla de madera" --description "Silla en buen estado"
```

Without the `browser` profile the backend still starts; `analysisEnabled` stays
true but `/analyze` returns `503 browser_unavailable` until a browser is
reachable. `lifeos-backend` declares the browser as an **optional healthy**
dependency (`condition: service_healthy`, `required: false`), and the
`market-cache` named volume persists the SQLite cache across restarts.

- `lifeos-backend`: Python 3.11 + Node 22 + `chrome-devtools-mcp@1.10.1`,
  port `8000`, non-root user, healthcheck on `/api/market/health`.
- `market-browser`: Debian + headful Chromium/Chrome under Xvfb, port `9222`,
  persistent `chrome-profile` volume, `shm_size: 2g`, no host display needed.
  The entrypoint disables background-tab/renderer throttling
  (`--disable-background-tab-throttling`, `--disable-renderer-backgrounding`,
  `--disable-backgrounding-occluded-windows`) so the two pages keep running.
- Marker: the MCP never launches Chrome and never uses `--headless` or
  `--enable-automation`.

### CDP proxy (Chrome 136+ compatibility)

Current Chrome/Chromium only listens on `127.0.0.1` and rejects non-local `Host`
headers. That would break `--browserUrl http://market-browser:9222`. The browser
image therefore runs a tiny stdlib proxy:

- listens on `0.0.0.0:9222`;
- forwards HTTP and WebSocket to `127.0.0.1:9223` with a local `Host`;
- rewrites `webSocketDebuggerUrl`/`devtoolsFrontendUrl` to the caller's host, so
  both the host (`127.0.0.1:9222`) and other containers
  (`market-browser:9222`) work.

This is an additive compatibility fix, documented in ADR-002.

### Multi-arch fingerprints

| Platform | Browser | Notes |
|---|---|---|
| `amd64` | Google Chrome stable | preferred for the demo laptop; closer to desktop Chrome |
| `arm64` | Debian Chromium | same engine family, different UA/GPU/codecs |

Always run the fingerprint check on the architecture used for the demo.

## Live source status (2026-10-24)

| Source | Fast `/valuate` path | Deep path (Phase 3) |
|---|---|---|
| Milanuncios | **Working** (12 cards parsed, 5 usable after filtering) | HTTP 3 pages **7–10 usable in 1.5–2.5 s** when not blocked; after warming, HTTP returns an anti-bot page → browser fallback **8 usable in ~10.7 s** |
| eBay | HTTP 403 from this network | **58 usable** (~4.0–4.4 s) on its own MCP slot; the intermittent eBay error page is reported as `blocked` |
| Wallapop | HTML is a JS shell (0 server-rendered items) | **40 usable** (~4.5–5.5 s) on its own MCP slot |

Measured on 2026-10-24 in this worktree (arm64, Debian Chromium 156, Xvfb):

- Hybrid smoke (`transport=auto`, query `iPhone 13 128GB`): eBay **58
  usable / 4.0 s**, Wallapop **40 / 4.5 s**, Milanuncios HTTP blocked → browser
  **7 / 11.1 s**; total **17.3–18.4 s** (*reported* in the Phase 3 session; not
  persisted as an artifact), all three platforms in the valuation, no warnings.
  The Phase 2 sequential engine took 25–32 s for the same query.
- Parallel spike with 3 pages: sequential 20.6 s vs parallel **12.0 s**
  (wall/max = 1.00, wall/sum = 0.53).
- Milanuncios depth: 3 pages **10.7 s / 8 usable**; 6 pages **21.5 s / 15
  usable**. The demo default is 3; 6 is completeness mode.
- HTTP spike: first run 2 pages **1.52 s / 10 usable**, 3 pages **2.51 s / 7
  usable**; subsequent HTTP runs were blocked and fell back to the browser.
  Because 7 is below `MIN_USABLE_LISTINGS=8`, `transport=auto` falls back to the
  browser instead of pricing the short HTTP sample.
- Fingerprint (`scripts/fingerprint_check.py`): `webdriver=false`, no
  `HeadlessChrome`, `__puppeteer`/`__playwright` undefined, `es-ES`,
  `Europe/Madrid`.
- Second identical run: `cached=true` in **0.01 s**.
- eBay alternates between working and its anti-bot error page across runs; when
  blocked it is reported explicitly, never replaced with synthetic prices.

The `/analyze` results are reported by `python scripts/smoke_analyze.py`:
per-source status, usable count, latency and the second-run cache hit. The live
counts depend on the venue network.

## Browser spike (non-blocking)

```bash
python scripts/fingerprint_check.py
python scripts/browser_spike.py --query "iPhone 13 128GB"
```

Both scripts speak MCP over stdio to `chrome-devtools-mcp@1.10.1` and write
`artifacts/fingerprint.json` / `artifacts/browser-spike.json`
(gitignored). A failure is documented in the report and does not fail the build.

Result on 2026-10-24 (arm64, Debian Chromium 156, Xvfb):

- `navigator.webdriver = false`
- `navigator.language = es-ES`, `languages = ["es-ES", "es"]`
- timezone `Europe/Madrid`
- `window.chrome = "object"`
- `__puppeteer` / `__playwright` = `undefined`
- WebGL vendor/renderer = `null` (software rendering under Xvfb)
- Wallapop extraction: 40 listings (stable)
- eBay extraction: 60 listings on the first run; later runs hit eBay's
  `Error Page | eBay` anti-bot interstitial, so the spike reports `partial`

The browser path is therefore viable but must remain on the deep path and must
not be on the `/valuate` hot path.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `source="stealth_fallback"` with warnings | Sources blocked/empty; expected on venue Wi-Fi. Check egress and keep the flag enabled for the demo. |
| HTTP `503` | `MARKET_ALLOW_FALLBACK=false` and no live listings. Inspect `sources`. |
| No recommendation | Check `recommendationEnabled` in `/api/market/health`. Missing/invalid `DEEPSEEK_API_KEY`, timeout, empty JSON or exhausted budget. A warning is returned and the valuation still succeeds. |
| `422` | Invalid enum/score/query; unknown fields are rejected on purpose. |
| Browser container `unhealthy` | Check `docker compose logs market-browser`; the entrypoint clears stale X/profile locks on restart. If needed, remove the `chrome-profile` volume. |
| `curl 9222` resets | Chrome is loopback-only; always go through the built-in CDP proxy (`9222`, not `9223`). |
| Docker build network error | Retry; the Dockerfile retries pip downloads. |
| DeepSeek returns empty content | In `/valuate` it retries then uses the template; in `/analyze` the recommendation is omitted with a warning. |
| `/analyze` returns `503 browser_unavailable` | Start the browser profile (`docker compose --profile browser up -d market-browser`) and check `/api/market/health`. |
| Milanuncios HTTP is blocked but browser works | Expected on the venue network: `transport=auto` falls back to the browser automatically. Use `transport=browser` to force it. |
| Browser connected but every source `blocked` | Anti-bot/captcha page; this is reported, not solved. Retry later or use another egress. |
| Second `/analyze` is not `cached` | Query, conditionScore or sources changed; the key is exact. TTL `0` also disables hits. |
| `analysisEnabled=false` | Set `MARKET_ANALYSIS_ENABLED=true` and recreate `lifeos-backend`. |

## Frontend contract (Phase 2, additive)

Track C adds two files without touching `src/types/sdd.ts` or Track A
components:

- `src/types/market-analysis.ts`: request, response, source status, SSE event
  types.
- `src/lib/market-analysis.ts`: `analyzeMarket()` and
  `streamMarketAnalysis()` (POST + `text/event-stream` reader, because
  `EventSource` cannot POST). Both forward the Firebase ID token like
  `requestJson`.

The Phase 1 optional-field mirror remains Track A's responsibility:

```ts
interface ValuationRequest {
  query: string;
  category: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
  brand?: string;
  model?: string;
  description?: string;
  includeRecommendation?: boolean;
}

interface ValuationRecommendation {
  summary: string;
  suggestedPrice: number;
  bullets: string[];
  risks: string[];
  negotiationMarginEur: number;
}

interface MarketValuationResult {
  // frozen fields unchanged
  recommendation?: ValuationRecommendation;
  warnings?: string[];
}
```

## Quality gates

```bash
cd backend
pytest -q          # 336 tests (hermetic; no CDP, no network)
ruff check app tests
mypy app
docker compose config
```
