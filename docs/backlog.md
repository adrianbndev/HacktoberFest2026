# Backlog — deferred items

Classified per the phase briefs. **No blocking items remain in Phase 2**; the
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
