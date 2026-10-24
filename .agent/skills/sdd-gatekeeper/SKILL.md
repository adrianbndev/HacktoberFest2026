---
name: sdd-gatekeeper
description: >-
  Use this skill before starting a new module, before marking any task or level as completed,
  or when the user asks to check project status, quality gates, SOLID compliance, or SDD progress.
  Audits the roadmap, module control tower, Clean Code limits, and level gatekeeping.
---

# 🛡️ SDD Gatekeeper & Quality Harness Skill

This skill enforces the **Spec-Driven Development (SDD)** workflow, **Level Gatekeeping**, and **Clean Code / SOLID** quality standards across Antigravity CLI, Claude Code, and OpenCode.

## When to Activate

1. **Before starting any task:** To verify which Level and Modules (`MOD-00` to `MOD-07`) are currently unlocked.
2. **After completing a feature or module:** To run the automated harness checks before marking `[x]` in [`.agent/roadmap.md`](../../roadmap.md) or `✅ DONE` in [`.agent/modules/INDEX-control-tower.md`](../../modules/INDEX-control-tower.md).
3. **Before transitioning from Level $N$ to Level $N+1$:** To verify that 100% of Level $N$ criteria pass.

---

## Step-by-Step Procedure

### Step 1: Run the SDD Verification Harness Script
Execute the standalone harness script using `run_command`:
```bash
node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs
```
*(See [verify-sdd-harness.mjs](./scripts/verify-sdd-harness.mjs)).*

### Step 2: Inspect the Harness Report
The script checks:
1. **SDD Documentation Integrity:** Confirms all required `.md` specs, rules, and module trackers exist.
2. **Roadmap & Control Tower Status:** Parses completed `[x]` vs pending `[ ]` tasks per Level (Levels 1, 2, 3, 4).
3. **Strict Gatekeeping Enforcement:** Alerts if code for Level $N+1$ (e.g., `/api/lifeos/github` from Level 4) is created before Level $N$ is closed.
4. **Clean Code & SOLID Static Checks (when `src/` exists):**
   * Checks that no source file in `src/` exceeds the maximum line threshold ($250\text{ lines}$).
   * Checks for forbidden explicit `any` types in `src/`.
   * Checks that `src/types/sdd.ts` exports all required domain contracts.

### Step 3: Run Typecheck & Unit Tests (if `package.json` is initialized)
If the Next.js codebase has been initialized:
```bash
npm run typecheck && npm run test:run
```

### Step 4: Update SDD Tracking Files
Only if Steps 1–3 succeed with zero errors:
1. Update the checklist in `.agent/modules/MOD-0X-*.md`.
2. Update the status column in [`.agent/modules/INDEX-control-tower.md`](../../modules/INDEX-control-tower.md).
3. Check off `[x]` the verified items in [`.agent/roadmap.md`](../../roadmap.md).
