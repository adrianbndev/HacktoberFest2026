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
