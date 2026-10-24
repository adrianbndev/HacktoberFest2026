---
target: dashboard
total_score: 18
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/matiasgarridopenni/claude_proyects/hacktoberfest_26/src/app/(dashboard)/page.tsx"
target_fingerprint: "sha256:6968d9a80cf0b3a15f6ee5b19dead1a5f083eea03055f927614177f669e49e1a"
target_path: /Users/matiasgarridopenni/claude_proyects/hacktoberfest_26/src/app/(dashboard)/page.tsx
timestamp: 2026-10-24T13-43-30Z
slug: src-app-dashboard-page-tsx
---
Method: dual-agent (A: design review · B: detector + browser). Dashboard rendered in an isolated browser with a mocked session and seed-equivalent data (Google sign-in not possible).

## Design Health Score (Nielsen)

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | No price freshness / sample size / source per card; blank screen during session check |
| 2 | Match System / Real World | 2 | "ΣP avg", "MCP Stealth", "Liquidez inmediata", "Techo" |
| 3 | User Control and Freedom | 1 | No delete/edit/sold; AI result auto-saved; modal error has no retry |
| 4 | Consistency and Standards | 2 | Two vocabularies for the same 3 prices; "Como nuevo" shown in amber |
| 5 | Error Prevention | 2 | AI result saved before review (useCaptureSession.ts:62) |
| 6 | Recognition Rather Than Recall | 3 | Everything visible and labelled; vocabulary mapping only |
| 7 | Flexibility and Efficiency | 1 | No sort/filter/search, no shortcuts, SEO copy needs a modal |
| 8 | Aesthetic and Minimalist Design | 2 | 825 px cards, ~9 blocks and 7 euro figures each; filler profile tile |
| 9 | Error Recovery | 2 | BACKEND_DOWN ("npm run dev:api") shown for every failure incl. 401/503 |
| 10 | Help and Documentation | 1 | Nothing explains the 3 prices, health score or price source |
| **Total** | | **18/40** | **Poor** |

## Design Specificity Verdict

Category-interchangeable: create-next-app starter + zinc Tailwind. Starter tokens only in globals.css, Geist default font, Sparkles logo (TopNav.tsx:13, LoginScreen.tsx:23), uniform rounded-3xl/2xl, identical KPI tiles, emoji-on-flat-colour demo photos (backend/app/store/seed_data.py). Nothing from second-hand trade (tags, tickets, platform marks, photo as hero).

Detector: 0 findings across dashboard markup (CLI) and 0 on the login screen (browser overlay). Verified it scans .tsx with a probe file. Agrees with the review: no loud anti-patterns; the problem is absence of identity, which the detector does not measure. No overlay visible in the user's browser.

## Priority Issues

1. [P1] Template identity + demo looks fake. Fix: brand tokens, wordmark instead of Sparkles, display face for amounts, real photos for demo items, varied radii. Command: bolder, typeset, colorize.
2. [P1] 825 px cards; aspect-[4/3] not applied (img size-full wins → 355×355, InventoryItemCard.tsx:25-27); skeleton h-[34rem] mismatches (InventoryGrid.tsx:21); inventory below the fold on mobile. Fix: fix img ratio, compact card (photo, name, condition chip, P_avg big with min–max ruler), expandable details/comparables, promote SEO copy, mobile order. Command: layout, distill, adapt.
3. [P1] No control over AI results: auto-save before confirm, no delete/sold (DELETE /api/inventory exists), no retry on modal error, close button reads as status. Fix: Save/Discard or Undo toast, per-card menu, retry with uploaded photo. Command: harden.
4. [P2] Jargon, two vocabularies, developer error string (useDashboardState.ts:9). Fix: one vocabulary with sub-labels, provenance line per card, mapped error messages with retry. Command: clarify.
5. [P2] Health colour thresholds 85/60 vs label bands 80/65 (HealthScoreBadge.tsx:9-14); amber label ≈3.2:1, 11 px price labels 4.39:1; "Venta rápida" wraps and misaligns the trio. Fix: colour by label, 700 shades, 12 px min. Command: polish (audit).

## Persona Red Flags

- Alex: no sort/filter/search, no add shortcut, 2 clicks per SEO copy, no bulk sold.
- Sam: no h1; id="seo-title" duplicated (SeoAnnouncementModal.tsx:39,43); 3 identical copy buttons; ΣP read as "sigma P avg"; meter lacks aria-valuetext.
- Jordan: product purpose unclear in 5 s; "Salud 82%" of what; emoji photos look like placeholders; comparable chips open a search, not the listing; QR modal URL input and "Simular captura" look like debug tools.

## Minor Observations

Next dev indicator visible; empty state without CTA; duplicated item count and name; mostly empty 618/935 € tiles; double icons in pipeline steps; Milanuncios comparable always equals P_avg; SEO modal lacks "Abrir Wallapop".

## Questions to Consider

1. Hero as a sentence: "Si vendes hoy, 618 €. Con paciencia, 754 €."
2. The 3 prices as one ruler with the item placed by condition.
3. Visual language from second-hand trade (tags, tickets, receipts) instead of SaaS bento.
