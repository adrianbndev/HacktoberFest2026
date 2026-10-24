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

1. **Human-Like Stealth Navigation:**
   * Random jitter delay between $800\text{ ms}$ and $2200\text{ ms}$ (`humanJitter(800, 2200)`).
   * Rotating realistic desktop/mobile Spanish browser headers (`Accept-Language: es-ES,es;q=0.9`).
   * Hard timeout of $3500\text{ ms}$ per platform using `AbortSignal.timeout(3500)`.
2. **Mathematical Pricing & Health Weighting (`pricing-math.ts`):**
   * Interquartile Range (IQR) outlier removal to discard $1\text{ €}$ spam listings or overpriced outliers.
   * Health weighting factor:
     $$W_{\text{health}}(\text{score}) = 0.65 + 0.50 \times \left(\frac{\text{clamp}(\text{score}, 0, 100)}{100}\right)$$
   * Strict invariant enforcement:
     $$0 < P_{\min} < P_{\text{avg}} < P_{\max}$$
3. **Zero-Downtime Deterministic Fallback:**
   * If live scraping is blocked or offline, seamlessly fall back to the curated 2026 Spanish market catalog + deterministic hash estimator.

---

## Verification Workflow

### Step 1: Run the Standalone Pricing Math & Invariant Harness
Run the reference verification script to validate all mathematical invariants before integrating into Next.js:
```bash
node .agent/skills/mcp-stealth-builder/scripts/test-mcp-math.mjs
```
*(See [test-mcp-math.mjs](./scripts/test-mcp-math.mjs)).*

### Step 2: Verify MCP Stdio Server Registration
When `src/mcp/server.ts` is implemented, verify that it responds to MCP `tools/list` and `tools/call` for:
* `search_secondhand_market`
* `simulate_market_tick`
