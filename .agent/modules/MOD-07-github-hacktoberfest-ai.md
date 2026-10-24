# 🎃 MOD-07: Módulo de Trabajo & Especial Hacktoberfest 2026 (GitHub + Resumen IA 2 Líneas)

* **Nivel SDD:** 🔴 Nivel 4 (Horas 7:30 - 8:30)
* **Responsables:** **Track C (Matías)** — GitHub Search Adapter & Resumen IA | **Track A (Ales)** — Widget UI & Filtros 1-Clic
* **Estado Actual:** `🔒 LOCKED (Requiere Gate Nivel 3)`
* **SLA de Latencia:** Búsqueda + Resumen IA 2 líneas $\le 2000\text{ ms}$

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID

* **`IGithubRepoFinder` (`LiveGithubApiAdapter` + `CuratedHacktoberfestFallbackAdapter`):**
  * Busca repositorios reales con issues abiertas etiquetadas como `hacktoberfest` o `good-first-issue` filtradas por el lenguaje favorito del miembro del equipo activo (**Ales**, **Adri** o **Matías**).
  * Incluye caché en memoria y fallback instantáneo ante límites de tasa (`403 API rate limit exceeded`) de la red del hackathon.
* **`RepoTwoLineSummarizer`:**
  * Genera o recupera un resumen estructurado en **exactamente 2 líneas accionables**:
    1. `aiArchitectureSummary` (Línea 1: Arquitectura técnica del repositorio).
    2. `aiQuickStartGuide` (Línea 2: Ruta exacta de archivos/comandos para contribuir rápido).

---

## 2. Archivos del Módulo (`Track C` + `Track A`)

| Archivo | Track | Propósito | Límite Líneas |
| :--- | :---: | :--- | :---: |
| `backend/app/lifeos/github_service.py` | Track C | Cliente Python async GitHub API + generador de resumen IA 2 líneas + fallback curado | $\le 160$ |
| `backend/app/routers/lifeos.py` | Track C | Endpoint FastAPI `GET /api/lifeos/github` con parámetros `query`, `language`, `hacktoberfest` | $\le 90$ |
| `src/components/lifeos/HacktoberfestWorkWidget.tsx` | Track A | Buscador en vivo, botón 1-clic *"Hacktoberfest 2026"* y tarjetas con resumen IA | $\le 180$ |

---

## 3. Checklist de Control y Calidad (MOD-07)

- [ ] Buscador en vivo conectado a `/api/lifeos/github`.
- [ ] Botón de 1 clic **"🎃 Filtro Rápido: Hacktoberfest 2026"** que selecciona automáticamente los lenguajes favoritos del perfil activo (**Ales, Adri o Matías**).
- [ ] Cada repositorio renderiza claramente las **2 líneas de resumen IA** (`aiArchitectureSummary` y `aiQuickStartGuide`) y enlace directo a las issues abiertas.
- [ ] Resiliencia probada: desconectando la red o forzando error 403 de GitHub, el widget sigue funcionando sin errores visibles.
