# 🧠 CLAUDE.md — Guía Operativa SDD para Claude Code / Antigravity / OpenCode

> **Instrucción Primaria:** Este proyecto utiliza **Spec-Driven Development (SDD)**. Antes de proponer, crear o modificar código, **debes leer y obedecer** las especificaciones enlazadas a continuación.

## 🔗 Contexto SDD Obligatorio (Imports)

@AGENTS.md
@.agent/roadmap.md
@.agent/modules/INDEX-control-tower.md
@.agent/architecture.md
@.agent/decisions/001-tech-stack-and-options-matrix.md
@.agent/mcp/stealth-market-mcp.md
@.agent/rules/hackathon-guardrails.md
@.agent/rules/clean-code-solid.md
@.agent/rules/testing-and-quality-gates.md
@.agent/tracks/team-tracks-contract.md

---

## ⚡ Reglas Rápidas de Ejecución (Hacktoberfest 2026 — 9 Horas)

1. **Equipo & Stack Híbrido (Next.js UI + Python FastAPI Back & Visión IA):**
   * **Ales** (`Track A`: Frontend Next.js, UI Bento, Perfil, Alertas en `src/`).
   * **Adri** (`Track B`: Sync Móvil-PC QR/Cámara en `src/app/mobile-capture/` + Reconocimiento de Imágenes y Visión IA en **Python** `backend/app/vision/` + `backend/app/routers/capture_session.py`).
   * **Matías** (`Track C`: Motor MCP Stealth 3 Precios en **Python** `backend/mcp_server.py` y `backend/app/mcp/`, Cron de Mercado y APIs LifeOS en `backend/app/lifeos/`).
2. **Ejecución Estricta Nivel por Nivel:**
   * **Nivel 1 (0:00 - 3:30):** Login + Perfil + Sync Cámara Móvil $\leftrightarrow$ PC + Visión IA (Estado/Salud + SEO) + MCP Stealth ($P_{\min}, P_{\text{avg}}, P_{\max}$). Ver `@.agent/specs/level-1-core-recommerce.md`.
   * **Nivel 2 (3:30 - 5:30):** Job de actualización de precios + Botón **"Forzar Actualización de Mercado (Demo Mode)"** + Indicadores $\uparrow/\downarrow$ + Centro de Notificaciones. Ver `@.agent/specs/level-2-price-tracking-alerts.md`.
   * **Nivel 3 (5:30 - 7:30):** Planes Locales conectados al valor/subida del inventario + Clima (interior/exterior) + Calendario Día a Día y entregas Wallapop. Ver `@.agent/specs/level-3-lifeos-plans-calendar.md`.
   * **Nivel 4 (7:30 - 8:30):** Buscador GitHub API en vivo + Filtro 1-clic `hacktoberfest` / `good-first-issue` por lenguaje favorito + Resumen IA de 2 líneas. Ver `@.agent/specs/level-4-github-hacktoberfest.md`.
3. **Prohibición de Salto:** Nunca implementes código de un nivel superior si el nivel actual no cumple el 100% de sus criterios de cierre en `.agent/roadmap.md`.
4. **Resiliencia en Vivo:** Toda llamada externa (Visión IA, scraping MCP en Wallapop/Vinted/Milanuncios/eBay, Clima, GitHub API) **DEBE** tener un timeout estricto ($< 6\text{ s}$ total) y un *fallback* determinista realista para que la demo jamás falle ante el jurado.
5. **Actualización del Estado SDD:** Cada vez que completes una tarea o sub-módulo, marca la casilla correspondiente `[x]` en `.agent/roadmap.md`.
