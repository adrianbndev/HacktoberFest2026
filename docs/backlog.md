# Backlog — deferred items

Classified per the phase brief (§8). **No blocking items remain in Phase 1.**

| # | Item | Reason | Status | Blocking? |
|---|---|---|---|---|
| 1 | Vinted connector | Contract supports a subset; scope is eBay + Wallapop + Milanuncios | Deferred to Phase 2 | No |
| 2 | `POST /api/market/analyze` + SSE + SQLite cache + full browser engine | Two-path strategy: browser latency (4–9 s cold start) does not fit the 2.8 s `/valuate` budget | Phase 2 | No |
| 3 | Custom minimal CDP MCP | Only needed if `chrome-devtools-mcp` failed the fingerprint check; it passed (`webdriver=false`, no `__puppeteer`/`__playwright`) | Not needed for now | No |
| 4 | GHCR multi-arch CI | Build locally on the demo laptop for the hackathon | Phase 2 / post-hackathon | No |
| 5 | Mirror new optional fields in `src/types/sdd.ts` | Track A / MOD-00 owns the TypeScript contract; fields documented in ADR-002 and `docs/market-analysis.md` | Pending MOD-00 | No |
| 6 | Full MOD-00 (store, auth, seed data, Next.js) | Separate phase by design; this phase only added the minimum backend for MOD-04 | Separate phase | No |
| 7 | `backend/mcp_server.py` (FastMCP CLI exposure) | Not part of the Phase 1 file scope; the library is already MCP-ready | Phase 2 | No |
| 8 | Clean eBay accessibility suffix in browser-spike titles | eBay appends "Se abre en una nueva ventana o pestaña"; harmless for the spike, should be stripped before using browser samples in Phase 2 | Phase 2 | No |
| 9 | WebGL vendor/renderer under Xvfb | Software rendering returns `null`; evaluate `--use-gl=angle --use-angle=swiftshader` or llvmpipe if Phase 2 needs a realistic GPU fingerprint | Phase 2 | No |
| 10 | DeepSeek live validation | Validated with the provided key; `deepseek-v4-pro` takes ~12–23 s, hence the opt-in recommendation window | Done | No |
| 11 | Split dev dependencies out of the runtime image | `requirements.txt` includes pytest/ruff/mypy so the documented `pip install -r requirements.txt && pytest` works out of the box; the image is heavier than strictly needed | Post-hackathon | No |
| 12 | Wallapop fast connector | Its search HTML is a JS shell (0 server-rendered items); only the Phase 2 browser engine currently gets its 40 listings | Phase 2 | No |

## Verification follow-ups (non-blocking)

1. `platforms` is derived from `comparableListings` and can omit a minority platform; consider a per-platform quota.
2. The opt-in recommendation window (25 s) exceeds the 6 s guardrail; the frontend must not request `includeRecommendation` on the hot path.
3. `DeepSeekChat`/`AsyncOpenAI` is created per request and never closed; cache the analyzer or add a shutdown hook.
4. IQR filtering runs twice and `sampleSize` can differ from the sample actually valued; compute it once.
5. The router catch-all turns programmer errors into `503`; log a redacted reason and use a distinct code.
6. A connector is marked `ok` even when it parses 0 listings; report `no_listings_parsed` / `filtered_out`.
7. "Grounded" bullets are enforced only by prompt; validate that they cite the supplied listings/prices.
8. Privacy/prompt injection: `description` is sent verbatim to DeepSeek; redact phone/email and delimit the text.
9. Config does not validate `jitter_max + connector_timeout < deadline`; add the invariant.
10. Relevance rejects `Sony PlayStation 5` vs `PlayStation 5` (asymmetric identity); treat the brand as optional when the model matches and the title has no identity.
11. Relevance loses single-digit generation numbers; `AirPods Pro 2` vs `AirPods Pro 3` is accepted.
12. Aliases use `str.replace` without word boundaries; use `re.sub` with `\b`.
13. `keywords()` does not normalise capacities/aliases (template-only impact).
14. Missing a direct `tests/test_relevance.py` and the `iPhone 13 mini` case.
15. The timeout test uses 0.05 s, not the production 1.6 s value.
