# Market valuation API (MOD-04, Phase 1)

Fast, spec-compliant second-hand valuation for the LifeOS & ReCommerce AI demo.
This document covers the **fast path** implemented in Phase 1:

```
POST /api/market/valuate
  -> normalise query
  -> eBay + Wallapop + Milanuncios in parallel (1.6 s per source)
  -> filter / dedupe / IQR outliers
  -> P_min < P_avg < P_max (health-weighted)
  -> comparable listings with functional deep links
  -> optional DeepSeek recommendation (grounded, clamped)
```

The browser-MCP deep analysis (`POST /api/market/analyze`, SSE, SQLite cache and
the full browser engine) is **Phase 2** and is not part of this service.

## Architecture and dependency direction

```
routers/market.py
  -> mcp/market_analysis.py
       -> mcp/connectors.py -> mcp/stealth_http.py, mcp/normalize.py
       -> mcp/pricing_math.py
       -> mcp/catalog_fallback.py
       -> mcp/deepseek.py -> mcp/deepseek_client.py
models/sdd.py imports nothing from mcp/
```

`pricing_math.py` is pure: no network, no LLM, no settings. Connectors never raise
to the router; failures are reported as a failed `ConnectorResult`.

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
  "timestamp": "2026-10-24T11:34:18.876869+00:00"
}
```

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
| Recommendation | remaining budget | capped by `DEEPSEEK_RECOMMENDATION_BUDGET_SEC` |
| **Total** | **≤ 2.8 s** | measured with mocks in tests |

Measured in Docker against the real network (all sources blocked): **1.8–2.3 s**
including the deterministic fallback. Live sources are also bounded by the same
deadline.

The 0.65–1.2 s jitter default is reserved for `/refresh` (Level 2), not this
interactive endpoint.

## Fallback policy

- Live sample `source="live_mcp"`.
- If no usable live listing remains, the deterministic catalog supplies the
  sample (`source="stealth_fallback"`) **only when** `MARKET_ALLOW_FALLBACK=true`
  (default).
- With the flag disabled, the API returns the structured `503` above.
- The fallback catalog contains curated Spain-2026 medians for common models and
  a stable SHA-256 estimator for unknown products.
- Every fallback listing links to a real platform search URL.

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
  (text only, never market data).

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
| `DEEPSEEK_TIMEOUT_SEC` | `4.0` | transport timeout |
| `DEEPSEEK_RECOMMENDATION_BUDGET_SEC` | `1.2` | recommendation slice |
| `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS` | `1` | MCP telemetry off |

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

# Optional Phase 2 / spike browser
docker compose --profile browser up --build market-browser
curl -s http://127.0.0.1:9222/json/version
```

- `lifeos-backend`: Python 3.13 + Node 22 + `chrome-devtools-mcp@1.10.1`,
  port `8000`, non-root user, healthcheck on `/api/market/health`.
- `market-browser`: Debian + headful Chromium/Chrome under Xvfb, port `9222`,
  persistent `chrome-profile` volume, `shm_size: 2g`, no host display needed.
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

The browser path is therefore viable but must remain Phase 2 and must not be on
the `/valuate` hot path.

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
| DeepSeek returns empty content | Automatic retry + deterministic template; no user action needed. |

## Frontend mirror (owned by MOD-00 / Track A)

Do **not** create `src/types/sdd.ts` from this phase. When Track A mirrors the
contract, add these optional fields:

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
pytest -q          # 137 tests
ruff check app tests
mypy app
docker compose config
```
