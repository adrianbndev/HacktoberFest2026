# 🔴 SDD Spec — NIVEL 4: Módulo de Trabajo & Especial Hacktoberfest 2026

> **Ventana de Tiempo:** Horas 7:30 - 8:30 *(Dejar 8:30 - 9:00 libres exclusivamente para ensayo de la demo)*
> **Prerrequisito:** Niveles 1, 2 y 3 completados y validados al 100%.
> **Objetivo:** Completar la visión LifeOS para desarrolladores integrando un buscador inteligente de repositorios Open Source para **Hacktoberfest 2026** personalizado para **Ales, Adri y Matías**.

---

## 1. Historias de Usuario del Nivel 4

1. **US-4.1 (Buscador de Repositorios GitHub en Vivo):** Como desarrollador en Hacktoberfest 2026, quiero buscar repositorios activos en GitHub directamente desde mi dashboard LifeOS.
2. **US-4.2 (Filtro 1-Clic "Hacktoberfest 2026" por Miembro del Equipo):** Como **Ales, Adri o Matías**, quiero un botón de un solo clic que filtre repositorios con issues abiertas etiquetadas como `hacktoberfest` o `good-first-issue` en mis lenguajes de programación favoritos.
3. **US-4.3 (Resumen Arquitectónico con IA en 2 Líneas):** Como contribuidor con poco tiempo, quiero que cada repositorio incluya una explicación generada con IA de exactamente **2 líneas**: (1) cómo está estructurada su arquitectura y (2) cómo hacer un PR rápido hoy mismo.

---

## 2. Especificación Funcional por Sub-Módulo

### 2.1 Servicio GitHub & Hacktoberfest Finder (`/api/lifeos/github` — `Track C`)
* Consulta la API pública de búsqueda de GitHub (`https://api.github.com/search/repositories`) filtrando por `topic:hacktoberfest`, lenguaje y actividad reciente, con un timeout máximo de $3.5\text{ s}$.
* **Fallback Curado Anti-Rate-Limit:**
  * En eventos con cientos de desarrolladores compartiendo la misma IP pública, la API sin autenticar de GitHub suele devolver `403 rate limit exceeded`.
  * Si hay rate-limit o sin conexión, el servicio devuelve instantáneamente una colección curada de repositorios reales de Hacktoberfest en `TypeScript`, `Python`, `Rust`, `Go` y `React/Next.js` con contadores de estrellas, issues abiertas y enlaces reales.

### 2.2 Filtro Rápido Personalizado para Ales, Adri y Matías (`Track A`)
* Barra de filtros de 1 clic en el widget de Trabajo:
  * Botón destacado: **"🎃 Filtro Rápido: Hacktoberfest 2026 + Good First Issue"**.
  * Chips de lenguaje pre-seleccionados automáticamente según el usuario logueado (`favoriteLanguages` del perfil de **Ales**, **Adri** o **Matías**), permitiendo cambiar entre `TypeScript`, `Python`, `Rust`, `Go`, `JavaScript`.

### 2.3 Resumen con IA en 2 Líneas (`Track C` + `Track A`)
* Cada tarjeta `HacktoberfestRepo` muestra un bloque destacado **"⚡ AI Quick-Contribute Brief (2 Líneas)"**:
  * **Línea 1 (`aiArchitectureSummary`):** Síntesis de la arquitectura técnica del repo (ej. *"Monorepo en Turborepo con paquetes core en TypeScript estricto y tests unitarios en Vitest."*).
  * **Línea 2 (`aiQuickStartGuide`):** Guía directa de contribución rápida (ej. *"Revisa `packages/ui/src/components`, ejecuta `pnpm test` y resuelve las issues de accesibilidad marcadas con `good-first-issue`."*).
* Botón **"🚀 Agendar Sprint de Contribución"** para añadir un bloque de tiempo Hacktoberfest en el Calendario del Nivel 3, cerrando el círculo del ecosistema LifeOS.

---

## 3. Criterios de Aceptación (Definition of Done — Nivel 4)

1. [ ] El buscador devuelve repositorios relevantes en $< 3\text{ s}$ (vía GitHub API en vivo o fallback curado sin errores de rate-limit).
2. [ ] El botón **"🎃 Hacktoberfest 2026"** filtra en 1 clic por issues `hacktoberfest` / `good-first-issue` adaptándose a los lenguajes favoritos de **Ales, Adri y Matías**.
3. [ ] Cada repositorio muestra su resumen IA de 2 líneas (Arquitectura + Guía rápida de PR).
