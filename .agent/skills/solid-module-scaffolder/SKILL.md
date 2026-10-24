---
name: solid-module-scaffolder
description: >-
  Use this skill whenever creating or implementing any functional module (MOD-00 through MOD-07)
  to ensure strict adherence to SOLID principles, Clean Architecture layers, Zod validation,
  Liskov-compliant deterministic fallbacks, and module tracking updates.
---

# 🏛️ SOLID & Clean Architecture Module Scaffolder Skill

Use this blueprint every time you implement a module from [`.agent/modules/INDEX-control-tower.md`](../../modules/INDEX-control-tower.md).

## The 6-Step Module Implementation Recipe

### Step 1: Read the Module Spec & Mark `🚧 IN_PROGRESS`
1. Read the corresponding `.agent/modules/MOD-0X-*.md` file and `.agent/architecture.md`.
2. Verify that all prerequisite modules in the dependency graph are complete.
3. Update the module status to `🚧 IN_PROGRESS` in `.agent/modules/INDEX-control-tower.md`.

### Step 2: Contract & Zod Boundary First (Interface Segregation)
1. Ensure the TypeScript interfaces exist in `src/types/sdd.ts` (zero `any` types).
2. Add or verify the runtime **Zod** schema in `src/lib/schema/sdd-schema.ts`.

### Step 3: Pure Domain Functions (Single Responsibility)
1. Implement all mathematical calculations, condition mappings, delta computations, or budget bridges as **pure, deterministic functions** (no network or disk I/O inside calculation functions).
2. Keep every file under **220 lines**.

### Step 4: Dual Adapters — Live Provider + Liskov Fallback (Open/Closed & Liskov)
1. Define a clean port interface (e.g., `IVisionProvider`, `IMarketConnector`, `IWeatherProvider`, `IGithubFinder`).
2. Implement the **Live Adapter** with `AbortSignal.timeout(3500)`.
3. Implement the **Deterministic Fallback Adapter** honoring the exact same interface and domain invariants.
4. Wrap both in a resilient orchestrator so the UI never receives an unhandled error during the demo.

### Step 5: Thin Route Handler & Isolated UI Components
1. Create the Next.js Route Handler (`src/app/api/.../route.ts` $\le 50\text{ lines}$) that validates input with Zod, invokes the domain service, and returns JSON.
2. Build modular UI components respecting Track boundaries ([`.agent/tracks/team-tracks-contract.md`](../../tracks/team-tracks-contract.md)).

### Step 6: Run Harness & Mark `✅ DONE`
1. Run `node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs`.
2. Check off completed items in `.agent/modules/MOD-0X-*.md` and `.agent/roadmap.md`.
3. Update the module status to `✅ DONE` in `.agent/modules/INDEX-control-tower.md`.
