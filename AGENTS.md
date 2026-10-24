# 🚀 AGENTS.md — Constitución SDD: LifeOS & ReCommerce AI (Hacktoberfest 2026)

> **COMPATIBILIDAD MULTI-AGENTE:** Este archivo es la fuente de verdad principal para **Antigravity CLI**, **OpenCode** y **Claude Code** (vía `CLAUDE.md`). Todo agente debe regirse por esta especificación bajo la metodología **SDD (Spec-Driven Development)**.
> **SCRATCHPAD ACTIVO:** El archivo [`user-taks-prompt.md`](user-taks-prompt.md) (ignorado en Git) es el scratchpad de trabajo para la tarea que estamos desarrollando ahora mismo.

---

## 1. Visión del Producto y Contexto del Hackathon

* **Proyecto:** LifeOS & ReCommerce AI
* **Evento:** Hacktoberfest 2026 — **Timebox estricto: 9 Horas**
* **Equipo:** **Ales, Adri y Matías**
* **Propósito:** Plataforma web inteligente con inicio de sesión y perfil de usuario centrada en la **tasación y gestión de inventario de segunda mano en tiempo real** (Wallapop, Vinted, Milanuncios, eBay) mediante **Visión Artificial + sincronización instantánea Móvil-PC + MCP Stealth**, integrada en un **Dashboard de Vida (LifeOS)** que conecta el valor de tus objetos con tu calendario diario, el clima, planes locales y contribuciones a GitHub/Hacktoberfest.

---

## 2. Metodología SDD (Spec-Driven Development) — Flujo de Trabajo Obligatorio

Ningún agente debe escribir código de implementación a ciegas. Todo desarrollo sigue el ciclo **SDD**:

1. **Leer la Especificación (Spec First):** Antes de tocar código de cualquier funcionalidad, leer:
   * Hoja de ruta y estado actual: [`.agent/roadmap.md`](.agent/roadmap.md)
   * Contratos de datos y API: [`.agent/architecture.md`](.agent/architecture.md)
   * Guardrails de demo y restricciones: [`.agent/rules/hackathon-guardrails.md`](.agent/rules/hackathon-guardrails.md)
   * Especificación del motor MCP: [`.agent/mcp/stealth-market-mcp.md`](.agent/mcp/stealth-market-mcp.md)
   * Especificación del Nivel correspondiente en `.agent/specs/level-*.md`
   * Fronteras de trabajo en equipo: [`.agent/tracks/team-tracks-contract.md`](.agent/tracks/team-tracks-contract.md)
2. **Validación Estricta por Niveles (Gatekeeping):**
   * 🟢 **NIVEL 1 (Horas 0:00 - 3:30):** Core ReCommerce (Login/Perfil + Sync Cámara Móvil $\leftrightarrow$ PC + Visión IA Estado/Salud + MCP Stealth 3 Precios + SEO).
   * 🟡 **NIVEL 2 (Horas 3:30 - 5:30):** Rastreo Periódico de Precios + Botón Demo "Forzar Actualización" + Centro de Notificaciones y Tendencias ($\uparrow/\downarrow$).
   * 🟠 **NIVEL 3 (Horas 5:30 - 7:30):** Expansión LifeOS — Planes Locales (presupuestados con el valor/subida del inventario) + Clima + Calendario/Entregas.
   * 🔴 **NIVEL 4 (Horas 7:30 - 8:30):** Módulo Trabajo & Especial Hacktoberfest 2026 (Buscador GitHub API + Filtro 1-clic + Resumen IA 2 líneas).
3. **Prohibición de Salto de Nivel:** **QUEDA TERMINANTEMENTE PROHIBIDO** escribir una sola línea de código del Nivel $N+1$ hasta que todos los criterios de cierre del Nivel $N$ estén marcados como `[x]` en [`.agent/roadmap.md`](.agent/roadmap.md) y verificados de extremo a extremo.
4. **Principio de Producto Terminado:** En cualquier minuto de las 9 horas en que se detenga el desarrollo, la interfaz debe lucir como un producto 100% terminado. **Cero botones muertos, cero vistas "En construcción" o `TODO` visibles al jurado.**

---

## 3. Stack Tecnológico Oficial (Frontend Next.js + Backend Python FastAPI & Visión IA)

* **Frontend Web (`src/`):** Next.js (App Router, TypeScript `strict: true`, Tailwind CSS + diseño **Bento Grid** moderno + `lucide-react`). Configura `rewrites` en `next.config.ts` (`/api/:path*` $\rightarrow$ `http://127.0.0.1:8000/api/:path*`) para operar bajo un único puerto (`:3000`) sin errores CORS en el móvil.
* **Backend & API (`backend/`):** **Python 3.11+ con FastAPI + Uvicorn + Pydantic v2** (`camelCase` serializado 1:1 con `src/types/sdd.ts`).
* **Sincronización Móvil $\leftrightarrow$ PC:** Endpoints FastAPI en `/api/capture-session/{session_id}` con Server-Sent Events (SSE) y/o *short-polling* rápido cada $1.2\text{ s}$ (garantizando compatibilidad total en redes de hackathon).
* **Usuarios y Persistencia (Firebase, plan gratuito Spark sin facturación):** login con **Google** mediante Firebase Auth (el backend verifica el ID token en `backend/app/auth.py`) y datos en **Firestore** solo a través del backend (`backend/app/store/`, `users/{uid}/items/{itemId}` con la foto comprimida dentro). Cada usuario empieza con 3 productos de demo. Ver [`.agent/architecture.md`](.agent/architecture.md) §5.
* **Reconocimiento de Imágenes & Visión IA (Python — `backend/app/vision/`):** Procesamiento de imagen con **Pillow (`PIL`)** + SDK multimodal en Python (`google-genai` Gemini 2.5 Flash / `openai` Vision) con validación **Pydantic v2** estructurada (nombre, marca, categoría, `conditionScore` $0-100$, `conditionLabel`, `seoTitle`, `seoDescription`) y fallback determinista en Python con análisis visual de imagen.
* **MCP (Model Context Protocol en Python — `backend/app/mcp/` & `backend/mcp_server.py`):** Servidor MCP estándar con **`FastMCP` (`mcp` Python SDK)** y motor asíncrono `httpx` + `beautifulsoup4` (`stealth-market-mcp`) con cabeceras humanas rotativas, *jitter* aleatorio ($650\text{ ms} - 1200\text{ ms}$), ponderación por salud del artículo y **capa de fallback determinista blindada** ante bloqueos de red.

---

## 4. Organización Modular del Equipo (Sin Conflictos de Git)

Para que **Ales, Adri y Matías** (y sus respectivos agentes en Antigravity CLI, Claude Code u OpenCode) trabajen en paralelo sin pisarse archivos, el código se divide en **3 Tracks con fronteras estrictas** (ver detalle en [`.agent/tracks/team-tracks-contract.md`](.agent/tracks/team-tracks-contract.md)):

| Track | Responsable Sugerido | Dominio y Directorios Exclusivos |
| :--- | :--- | :--- |
| **Track A** | **Ales** | **Frontend Next.js, Bento Grid UI, Auth/Perfil & Centro de Notificaciones:** `src/components/dashboard/`, `src/components/inventory/`, `src/components/notifications/`, `src/app/(dashboard)/` |
| **Track B** | **Adri** | **Sync Móvil-PC (QR/Cámara) & Reconocimiento de Imágenes / Visión IA en Python:** `src/app/mobile-capture/`, `src/components/mobile-sync/`, `backend/app/vision/`, `backend/app/routers/vision.py`, `backend/app/routers/capture_session.py` |
| **Track C** | **Matías** | **Motor MCP Stealth en Python, Cron de Precios & Módulos LifeOS (Clima/Planes/GitHub):** `backend/mcp_server.py`, `backend/app/mcp/`, `backend/app/lifeos/`, `backend/app/routers/market.py`, `backend/app/routers/lifeos.py` |

> **Regla de Oro de Git:** Los archivos `src/types/sdd.ts` (Frontend TS) y `backend/app/models/sdd.py` (Backend Pydantic v2) reflejan exactamente el contrato de [`.agent/architecture.md`](.agent/architecture.md). Ningún Track rompe las firmas exportadas en ambos contratos.

### Convención de Ramas y Commits
* **Ramas:** `feat/track-a-<feature>`, `feat/track-b-<feature>`, `feat/track-c-<feature>` o trabajo coordinado por módulos sobre `main`.
* **Commits Semánticos con Autor/Track:**
  * `feat(L1-trackA): ...`
  * `feat(L1-trackB): ...`
  * `feat(L1-trackC): ...`
  * `fix(L2-trackC): ...`

---

## 5. Mapa Completo de Especificaciones SDD, Módulos, Reglas y Skills (`.agent/`)

Todos los agentes deben consultar y mantener sincronizados los siguientes documentos:

### 🧭 Gobernanza, Arquitectura y Decisiones (ADRs)
* 📋 [`.agent/roadmap.md`](.agent/roadmap.md) — Checklist maestro por niveles (Niveles 1 a 4) y criterios de aceptación.
* 🗼 [`.agent/modules/INDEX-control-tower.md`](.agent/modules/INDEX-control-tower.md) — **Control Tower de Módulos (`MOD-00` a `MOD-07`)**, estados, SLAs y dependencias.
* ⚠️ [`.agent/known-issues.md`](.agent/known-issues.md) — Problemas conocidos pendientes (riesgos aceptados de momento y su responsable).
* 🏗️ [`.agent/architecture.md`](.agent/architecture.md) — Modelos de datos TypeScript, endpoints REST/SSE y arquitectura de carpetas.
* 🧭 [`.agent/decisions/001-tech-stack-and-options-matrix.md`](.agent/decisions/001-tech-stack-and-options-matrix.md) — Análisis de opciones tecnológicas, trade-offs y estrategia de fallbacks.
* 🕵️ [`.agent/mcp/stealth-market-mcp.md`](.agent/mcp/stealth-market-mcp.md) — Especificación del motor MCP anti-bot, cálculo de $P_{\min}, P_{\text{avg}}, P_{\max}$ y fallback determinista.
* 🤝 [`.agent/tracks/team-tracks-contract.md`](.agent/tracks/team-tracks-contract.md) — Contratos de integración sin conflictos entre **Ales (Track A)**, **Adri (Track B)** y **Matías (Track C)**.

### 🛡️ Reglas Activas (`always_on` en `.agent/rules/`)
* [`.agent/rules/hackathon-guardrails.md`](.agent/rules/hackathon-guardrails.md) — Rendimiento ($<6\text{ s}$), captura móvil sin bloqueo HTTPS/CORS y resiliencia en demo.
* [`.agent/rules/clean-code-solid.md`](.agent/rules/clean-code-solid.md) — Principios SOLID, Clean Architecture en 4 capas, límite de 220 líneas por archivo y validación estricta con Pydantic v2.
* [`.agent/rules/testing-and-quality-gates.md`](.agent/rules/testing-and-quality-gates.md) — Invariantes matemáticas obligatorias y protocolo del Harness de Verificación.

### 📦 Fichas de Seguimiento y Control por Módulo (`.agent/modules/`)
* [`.agent/modules/MOD-00-foundation-store-types.md`](.agent/modules/MOD-00-foundation-store-types.md) — Tipos `sdd.ts`, modelos Pydantic v2, login con Google y datos en Firestore.
* [`.agent/modules/MOD-01-auth-and-inventory-ui.md`](.agent/modules/MOD-01-auth-and-inventory-ui.md) — Login rápido, Bento Grid UI y "Mi Inventario" (`Track A`).
* [`.agent/modules/MOD-02-mobile-pc-sync.md`](.agent/modules/MOD-02-mobile-pc-sync.md) — Sync Cámara Móvil $\leftrightarrow$ PC vía QR + compresión Canvas + SSE/Polling (`Track B`).
* [`.agent/modules/MOD-03-vision-health-seo.md`](.agent/modules/MOD-03-vision-health-seo.md) — Visión IA Multimodal, diagnóstico de Salud ($0-100\%$) y generador SEO (`Track B`).
* [`.agent/modules/MOD-04-mcp-stealth-valuation.md`](.agent/modules/MOD-04-mcp-stealth-valuation.md) — Motor MCP Stealth multi-web y cálculo de las 3 medidas ($P_{\min}, P_{\text{avg}}, P_{\max}$) (`Track C`).
* [`.agent/modules/MOD-05-price-tracker-and-alerts.md`](.agent/modules/MOD-05-price-tracker-and-alerts.md) — Rastreo periódico, botón Demo Mode, Sparklines y Centro de Alertas (`Track C + A`).
* [`.agent/modules/MOD-06-lifeos-weather-plans-calendar.md`](.agent/modules/MOD-06-lifeos-weather-plans-calendar.md) — Planes Locales financiados por inventario, Clima y Calendario de entregas (`Track C + A`).
* [`.agent/modules/MOD-07-github-hacktoberfest-ai.md`](.agent/modules/MOD-07-github-hacktoberfest-ai.md) — Buscador GitHub Hacktoberfest 2026 + Resumen IA 2 líneas (`Track C + A`).

### 🛠️ Skills y Harness Tools Ejecutables (`.agent/skills/`)
* **`sdd-gatekeeper`** ([`SKILL.md`](.agent/skills/sdd-gatekeeper/SKILL.md)) $\rightarrow$ Script: `node .agent/skills/sdd-gatekeeper/scripts/verify-sdd-harness.mjs`
* **`mcp-stealth-builder`** ([`SKILL.md`](.agent/skills/mcp-stealth-builder/SKILL.md)) $\rightarrow$ Script: `node .agent/skills/mcp-stealth-builder/scripts/test-mcp-math.mjs`
* **`mobile-sync-debugger`** ([`SKILL.md`](.agent/skills/mobile-sync-debugger/SKILL.md)) $\rightarrow$ Script: `node .agent/skills/mobile-sync-debugger/scripts/detect-lan-and-simulate.mjs`
* **`solid-module-scaffolder`** ([`SKILL.md`](.agent/skills/solid-module-scaffolder/SKILL.md)) $\rightarrow$ Receta de 6 pasos para implementar módulos bajo SOLID y Liskov.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
