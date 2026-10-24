# Backlog — deferred items

Classified per the phase briefs. **No blocking items remain in Phase 3**; the
Level 1 gate stays open until the end-to-end UI verification.

## Closed in Phase 2

| # | Item | Resolution |
|---|---|---|
| 1 | `POST /api/market/analyze` + SSE + SQLite cache + full browser engine | Implemented: `mcp/deep_analysis.py`, `deep_sources.py`, `deep_support.py`, `deep_cache.py`, `mcp/sse.py`, `routers/market_analysis.py` |
| 2 | Clean eBay accessibility suffix | Browser eBay parser strips “Se abre en una nueva ventana o pestaña” and skips “Shop on eBay” |
| 3 | Per-platform quota / `platforms` coherence | `/analyze` takes ≤ 4 listings per successful source, fills to 12 by proximity, and declares every platform with usable data |
| 4 | Double IQR / `sampleSize` mismatch | `/analyze` computes IQR fences once and prices exactly the filtered listings |
| 5 | Browser spike is non-blocking | Fingerprint and smoke scripts documented; a blocked source is an explicit `blocked` status, never synthetic data |
| 6 | Real DeepSeek recommendation in the deep path | `deepseek-v4-pro` with thinking, validated, clamped; the deterministic template is disabled so failures omit the recommendation |

## Still deferred (non-blocking)

| # | Item | Reason | Status | Blocking? |
|---|---|---|---|---|
| 1 | Vinted connector | Contract supports a subset; Phase 2 scope is eBay + Wallapop + Milanuncios | Deferred | No |
| 2 | `backend/mcp_server.py` (FastMCP CLI) | The library is MCP-ready but not exposed as a CLI; not needed for the demo | Deferred | No |
| 3 | `/api/market/refresh` + alerts | Level 2 scope | Deferred | No |
| 4 | UI wiring of `/analyze` and SSE | Track A owns dashboard components; Track C provides the client only | Pending Track A | No |
| 5 | Mirror Phase 1 optional fields in `src/types/sdd.ts` | Track A / MOD-00 owns the frozen TypeScript contract | Pending MOD-00 | No |
| 6 | GHCR multi-arch CI | Build locally on the demo laptop | Post-hackathon | No |
| 7 | Custom minimal CDP MCP | Only needed if `chrome-devtools-mcp` failed the fingerprint; it passed | Not needed | No |
| 8 | Split dev dependencies out of the runtime image | `requirements.txt` includes pytest/ruff/mypy so the documented flow works; image is heavier | Post-hackathon | No |
| 9 | Full MOD-00 (store, auth, seed data) | Separate phase by design | Separate phase | No |

## Phase 2 follow-ups (non-blocking)

1. **Sequential sources.** One page/lock protects the fingerprint but adds
   latency; a very slow network can make the last source `timeout`. A bounded
   page pool is a possible future optimization.
2. **Partial cache.** A result with one blocked source is cached for 15 minutes;
   the blocked source's recovery is delayed. Consider caching only all-ok
   results, or a shorter TTL for partials.
3. **App shutdown.** `shared_analyzer` keeps the MCP process alive for reuse;
   there is no FastAPI lifespan hook that calls `browser.stop()`. The OS closes
   the child on process exit; a lifespan hook would be cleaner.
4. **Hot reload.** The singleton is keyed by `Settings` identity; `uvicorn
   --reload` can create a new manager while the old MCP process is still
   closing. Production runs without reload are unaffected.
5. **SSE heartbeat granularity.** Heartbeats are emitted between engine events
   (queue timeout), not from inside a blocking MCP call; a source that hangs
   still produces pings because the engine runs in a producer task.
6. **`comparableListings` is additive.** The brief's example omitted it but its
   rules referenced it; `/analyze` adds a top-level capped set (documented in
   ADR-003). Track A can ignore it safely.
7. **Description privacy.** `description` is not cached, but it is still sent
   verbatim to DeepSeek for relevance/recommendation (existing Phase 1 item).
   Redaction/delimiting of phone/email remains a follow-up.
8. **Live verification is environment-dependent.** Parser and API tests are
   hermetic; live counts (`>=20 eBay`, `>=20 Wallapop`, `>=10 Milanuncios`) must
   be re-checked on the demo network and are reported by
   `scripts/smoke_analyze.py`.

## Phase 2 verification follow-ups

1. **`includeRecommendation` is not in the cache key.** A cached response with
   a recommendation can be returned to a later request with
   `includeRecommendation=false` within the TTL. Add the flag to the key or drop
   `recommendation` when reading a hit for a no-recommendation request.
2. **Recommendation derived from `description` is cached cross-caller.** The
   cached text can be replayed to other callers with the same key. Redact and
   delimit `description`, and namespace the cache per caller once auth exists.
3. **MCP crash retry reuses the stale `pageId`.** Route the retry through
   `_ensure_page()`/`new_page` instead of re-issuing the old page id.
4. **No guaranteed page recreation after `stop()`/`close_page`.** An empty
   `list_pages` falls back to `DEFAULT_PAGE_ID=1` without `new_page`; verify live
   and recreate a tab when needed.
5. **SSE disconnect stops the process-wide browser singleton.** A disconnect can
   close the browser used by another concurrent client. Decouple stop per
   request, or use a lock/refcount.
6. **`/analyze` and `/analyze/stream` are public.** Anyone can hold the browser
   lock and spend DeepSeek budget. Add auth/rate limiting before public exposure.
7. **`/health` exposes sanitized `lastError` and the cache path.** Decide whether
   these internals should be hidden from unauthenticated callers.
8. **Per-source `sampleSize` can exceed `len(listings)`.** Listings are capped at
   40 while the count is not; align the field with what is serialized.
9. **`sources=["vinted"]` validates but degrades to an opaque error.** Return
   `422` for unsupported sources or document the current behavior.
10. **Dependency-direction deviation.** `browser/sources/base.py` imports
    `browser/session.py`; use a `BrowserPage` Protocol if the brief's letter must
    be respected.
11. **Marketplace prompt-injection surface.** Listing titles and `description`
    reach the LLM. Keep the clamp/validation and consider explicit delimiters.
12. **Test coverage gaps.** `FakeAnalyzer` over-mocks the analyzer; there is no
    test for the frontend `parseSseFrame` nor for a real HTTP disconnect.
13. **`error: null` is omitted for `ok` sources** by `exclude_none`; harmless
    shape difference for clients.
14. **Router catch-all still maps programmer errors to `503`.** Log a redacted
    reason and return a distinct code for genuine bugs.

## Phase 1 verification follow-ups still open

These affect the frozen fast path only and are intentionally not changed here:

1. `/valuate` derives `platforms` from `comparableListings` and can omit a
   minority platform (the deep path fixed this with a quota).
2. `/valuate`'s opt-in recommendation window (25 s) exceeds the 6 s guardrail;
   the frontend must not request it on the hot path.
3. `DeepSeekChat`/`AsyncOpenAI` is created per request and never closed; caching
   the analyzer or adding a shutdown hook is still pending.
4. `/valuate` still runs IQR twice; the deep path fixed it.
5. `/valuate`'s router catch-all turns programmer errors into `503`; the deep
   path uses distinct `analysis_failed`/`browser_unavailable` details.
6. A fast connector is marked `ok` even when it parses 0 listings (the deep path
   reports `no_listings`).
7. “Grounded” bullets are enforced only by prompt.
8. Privacy/prompt injection: `description` is sent verbatim to DeepSeek.
9. Config does not validate `jitter_max + connector_timeout < deadline`.
10. Relevance rejects `Sony PlayStation 5` vs `PlayStation 5` (asymmetric
    identity).
11. Relevance loses single-digit generation numbers (`AirPods Pro 2` vs `3`).
12. Aliases use `str.replace` without word boundaries.
13. `keywords()` does not normalise capacities/aliases.
14. Missing a direct `tests/test_relevance.py` and the `iPhone 13 mini` case.
15. The timeout test uses 0.05 s, not the production 1.6 s value.


## Phase 3 follow-ups (non-blocking)

1. **Milanuncios HTTP anti-bot.** HTTP is 4–10× faster when it works, but after a
   few rapid requests the site returns a 200 anti-bot body. `transport=auto`
   falls back to the browser, which costs ~11 s. A future transport could add
   human jitter/backoff or an HTTP/TLS profile closer to the browser; do not
   solve captchas.
2. **Fallback waits for a browser slot.** With `MARKET_BROWSER_POOL_SIZE=2`, a
   blocked HTTP Milanuncios waits for eBay/Wallapop to release a slot. A third
   ephemeral slot only for fallback is a possible optimization (higher memory).
3. **Pool memory.** Two Chromium pages plus MCP processes measured ~2.3 GB
   summed RSS in the spike. Keep `shm_size: 2g`; monitor on the demo laptop.
4. **Pool lifespan hook.** `shared_analyzer` keeps the pool/MCP processes alive;
   a FastAPI lifespan hook that calls `pool.stop()` on shutdown is still
   pending.
5. **Threshold is a constant.** `MIN_USABLE_LISTINGS = 8` lives in
   `deep_milanuncios.py`; consider exposing it as settings if the demo needs a
   different bar.
6. **Wallapop transient `no_listings`.** One live parallel run returned
   `no_listings` while the next returned 40. It is reported as a partial result,
   never filled synthetically; retry/telemetry would help diagnose.
7. **SSE ordering tests are event-level.** They validate completion order and the
   request-order `done` payload; a true HTTP disconnect test with a pool-backed
   analyzer is still deferred.
8. **Ruff global baseline.** `ruff check app tests` reports 78 pre-existing
   errors in `app/vision/*` (Track B). Phase 3 validates only its own files and
   leaves Track B untouched.
