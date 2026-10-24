# 🚀 AGENTS.md — Constitución SDD: LifeOS & ReCommerce AI (Hacktoberfest 2026)

> **COMPATIBILIDAD MULTI-AGENTE:** Este archivo es la fuente de verdad principal para **Antigravity CLI**, **OpenCode** y **Claude Code** (vía `CLAUDE.md`). Todo agente debe regirse por esta especificación bajo la metodología **SDD (Spec-Driven Development)**.

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

## 3. Stack Tecnológico Oficial

* **Framework Web:** Next.js (App Router, Server Actions & Route Handlers para REST/SSE).
* **Lenguaje:** TypeScript estricto (`strict: true`), interfaces compartidas en `src/types/sdd.ts`.
* **Estilos y UI:** Tailwind CSS + diseño **Bento Grid** moderno (modo oscuro/claro pulido, micro-interacciones fluidas) + `lucide-react` para iconografía.
* **Sincronización Móvil $\leftrightarrow$ PC:** Route Handlers en `/api/capture-session/[sessionId]` con Server-Sent Events (SSE) y/o *short-polling* rápido cada $1\text{ s}$ (garantizando compatibilidad total en redes de hackathon).
* **Persistencia:** Almacenamiento híbrido sin fricción (JSON local persistente en disco `/data/store.json` + caché en memoria / SQLite / Supabase opcional) con usuarios preconfigurados para demo (**Ales, Adri, Matías y Jurado**).
* **IA & Visión:** SDK multimodal (Gemini Flash / Pro o OpenAI Vision compatible) con salida estructurada JSON (nombre, marca, categoría, `conditionScore` $0-100$, `conditionLabel`, `seoTitle`, `seoDescription`) y fallback inteligente.
* **MCP (Model Context Protocol):** Servidor y adaptador MCP Stealth (`stealth-market-mcp`) con cabeceras humanas rotativas, *jitter* aleatorio ($800\text{ ms} - 2200\text{ ms}$), ponderación por salud del artículo y **capa de fallback determinista blindada** ante bloqueos de red.

---

## 4. Organización Modular del Equipo (Sin Conflictos de Git)

Para que **Ales, Adri y Matías** (y sus respectivos agentes en Antigravity CLI, Claude Code u OpenCode) trabajen en paralelo sin pisarse archivos, el código se divide en **3 Tracks con fronteras estrictas** (ver detalle en [`.agent/tracks/team-tracks-contract.md`](.agent/tracks/team-tracks-contract.md)):

| Track | Responsable Sugerido | Dominio y Directorios Exclusivos |
| :--- | :--- | :--- |
| **Track A** | **Ales** | **Frontend, Bento Grid UI, Auth/Perfil & Centro de Notificaciones:** `src/components/dashboard/`, `src/components/inventory/`, `src/components/notifications/`, `src/app/(dashboard)/` |
| **Track B** | **Adri** | **Sync Móvil-PC (QR/Cámara) & Visión IA (Salud + SEO):** `src/app/mobile-capture/`, `src/app/api/capture-session/`, `src/app/api/vision/`, `src/lib/vision/`, `src/components/mobile-sync/` |
| **Track C** | **Matías** | **MCP Stealth Engine, Cron de Precios & Módulos LifeOS (Clima/Planes/GitHub):** `src/mcp/`, `src/lib/mcp/`, `src/app/api/market/`, `src/app/api/lifeos/`, `src/lib/lifeos/` |

> **Regla de Oro de Git:** El archivo `src/types/sdd.ts` refleja exactamente el contrato de [`.agent/architecture.md`](.agent/architecture.md). Ningún Track rompe las firmas exportadas en `src/types/sdd.ts`.

### Convención de Ramas y Commits
* **Ramas:** `feat/track-a-<feature>`, `feat/track-b-<feature>`, `feat/track-c-<feature>` o trabajo coordinado por módulos sobre `main`.
* **Commits Semánticos con Autor/Track:**
  * `feat(L1-trackA): ...`
  * `feat(L1-trackB): ...`
  * `feat(L1-trackC): ...`
  * `fix(L2-trackC): ...`

---

## 5. Mapa de Especificaciones SDD (`.agent/`)

Todos los agentes deben consultar y mantener sincronizados los siguientes documentos:

* 📋 [`.agent/roadmap.md`](.agent/roadmap.md) — Checklist maestro por niveles (Niveles 1 a 4) y criterios de aceptación.
* 🏗️ [`.agent/architecture.md`](.agent/architecture.md) — Modelos de datos TypeScript, endpoints REST/SSE y arquitectura de carpetas.
* 🕵️ [`.agent/mcp/stealth-market-mcp.md`](.agent/mcp/stealth-market-mcp.md) — Especificación del motor MCP anti-bot, cálculo de $P_{\min}, P_{\text{avg}}, P_{\max}$ y fallback determinista.
* 🛡️ [`.agent/rules/hackathon-guardrails.md`](.agent/rules/hackathon-guardrails.md) — Reglas innegociables de rendimiento ($<6\text{ s}$), captura móvil sin bloqueo HTTPS/CORS y resiliencia en demo.
* 📐 **Especificaciones Funcionales por Nivel:**
  * [`.agent/specs/level-1-core-recommerce.md`](.agent/specs/level-1-core-recommerce.md)
  * [`.agent/specs/level-2-price-tracking-alerts.md`](.agent/specs/level-2-price-tracking-alerts.md)
  * [`.agent/specs/level-3-lifeos-plans-calendar.md`](.agent/specs/level-3-lifeos-plans-calendar.md)
  * [`.agent/specs/level-4-github-hacktoberfest.md`](.agent/specs/level-4-github-hacktoberfest.md)
* 🤝 [`.agent/tracks/team-tracks-contract.md`](.agent/tracks/team-tracks-contract.md) — Contratos de integración entre Ales, Adri y Matías.
