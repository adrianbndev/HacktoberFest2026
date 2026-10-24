---
name: mcp-stealth-builder
description: >-
  Use this skill when building, testing, or debugging the stealth-market-mcp engine (MOD-04),
  the 3 price metrics (priceMin, priceAvg, priceMax), health score weighting (W_health),
  deterministic market fallback, or Level 2 periodic price refresh and notifications (MOD-05).
---

# 🕵️ MCP Stealth Engine & Pricing Math Skill (`MOD-04` & `MOD-05`)

This skill guides the implementation and mathematical verification of the **Stealth Market MCP** (`stealth-market-mcp`) for second-hand platforms (**Wallapop, Vinted, Milanuncios, eBay**).

## Core Responsibilities

1. **Human-Like Stealth Navigation (`backend/app/mcp/stealth_http.py`):**
   * Random jitter between $650\text{ ms}$ and $1200\text{ ms}$ (`await human_jitter(0.65, 1.20)`, `0.0` in `pytest`).
   * Rotating realistic desktop/mobile Spanish browser headers (`Accept-Language: es-ES,es;q=0.9`).
   * Platforms queried in parallel (`asyncio.gather`) with a hard `httpx.Timeout(1.6)`, $\le 2.8\text{ s}$ in total.
2. **Mathematical Pricing & Health Weighting (`backend/app/mcp/pricing_math.py`):**
   * Interquartile Range (IQR) outlier removal to discard $1\text{ €}$ spam listings or overpriced outliers.
   * Health weighting factor:
     $$W_{\text{health}}(\text{score}) = 0.65 + 0.50 \times \left(\frac{\text{clamp}(\text{score}, 0, 100)}{100}\right)$$
   * Strict invariant enforcement:
     $$0 < P_{\min} < P_{\text{avg}} < P_{\max}$$
3. **Zero-Downtime Deterministic Fallback:**
   * If live scraping is blocked or offline, seamlessly fall back to the curated 2026 Spanish market catalog + deterministic hash estimator.

---

## Verification Workflow

### Step 1: Run the Pricing Math & Invariant Tests
Once `backend/app/mcp/pricing_math.py` exists, the real check is:
```bash
pytest backend/tests/test_pricing_math.py
```
Before that, the reference script validates the formulas on their own (it tests its own JS copy, not the Python code):
```bash
node .agent/skills/mcp-stealth-builder/scripts/test-mcp-math.mjs
```
*(See [test-mcp-math.mjs](./scripts/test-mcp-math.mjs)).*

### Step 2: Verify MCP Stdio Server Registration
When `backend/mcp_server.py` (`FastMCP`) is implemented, verify that it responds to MCP `tools/list` and `tools/call` for:
* `search_secondhand_market`
* `simulate_market_tick`
