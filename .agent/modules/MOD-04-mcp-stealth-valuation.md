# 🕵️ MOD-04: Motor MCP Stealth Multi-Web y las 3 Medidas de Precio ($P_{\min}, P_{\text{avg}}, P_{\max}$)

* **Nivel SDD:** 🟢 Nivel 1.4
* **Responsable:** **Track C (Matías)**
* **Estado Actual:** `🚧 IN_PROGRESS` (Fases 1–3; el gate del Nivel 1 sigue abierto)
* **SLA de Latencia:** $\le 2800\text{ ms}$ (incluyendo *jitter* humano de $650\text{ ms} - 1200\text{ ms}$; $200-600\text{ ms}$ en `/valuate`)

---

## 1. Responsabilidad Única (SRP) y Diseño SOLID en Python

* **Separación Matemática vs Scraping (Clean Architecture en Python):**
  * `backend/app/mcp/pricing_math.py`: Funciones matemáticas **100% puras y deterministas en Python** (filtrado de *outliers* por IQR, filtro léxico anti-cajas vacías, cálculo del factor $W_{\text{health}}$, cálculo de $P_{\min}, P_{\text{avg}}, P_{\max}$ y garantía de la invariante $0 < P_{\min} < P_{\text{avg}} < P_{\max}$).
  * `backend/app/mcp/stealth_http.py`: Generador de cabeceras humanas rotativas (`User-Agent`, `Accept-Language`, `Sec-Fetch-*`) y corrutina `await human_jitter(0.65, 1.20)`.
  * `backend/app/mcp/connectors.py`: Adaptadores asíncronos con `httpx.AsyncClient` + `BeautifulSoup4` por plataforma (`wallapop`, `vinted`, `milanuncios`, `ebay`) que implementan `MarketConnectorProtocol`.
  * `backend/app/mcp/catalog_fallback.py`: Catálogo curado del mercado español 2026 + estimador determinista por hash semántico + deep links reales cuando hay bloqueo anti-bot o corte de red.
  * `backend/mcp_server.py`: Servidor **MCP estándar en Python (`FastMCP`)** para conexión directa con **Antigravity CLI**, **Claude Code** y **OpenCode**.

---

## 2. Fórmulas e Invariantes del Módulo

1. **Factor de Ponderación por Salud ($W_{\text{health}}$):**
   $$W_{\text{health}}(\text{score}) = 0.65 + 0.50 \times \left(\frac{\text{clamp}(\text{score}, 0, 100)}{100}\right)$$
2. **Las 3 Medidas Obligatorias:**
   * 🎯 **`priceAvg` ($P_{\text{avg}}$):** Valor real de mercado ponderado por $W_{\text{health}}$.
   * 📉 **`priceMin` ($P_{\min}$):** Precio para venta rápida inmediata ($\le \min(P_{20}, \text{round}(P_{\text{avg}} \times 0.82))$).
   * 📈 **`priceMax` ($P_{\max}$):** Techo de mercado para estado impecable ($\ge \max(P_{85}, \text{round}(P_{\text{avg}} \times 1.24))$).
3. **Guardia de Invariante Estricta en Python:**
   ```python
   def enforce_price_triplet_invariant(p_min: float, p_avg: float, p_max: float) -> tuple[int, int, int]:
       safe_avg = max(5, round(p_avg))
       safe_min = min(safe_avg - 1, max(1, round(p_min)))
       safe_max = max(safe_avg + 1, round(p_max))
       return safe_min, safe_avg, safe_max
   ```

---

## 3. Archivos del Módulo en Python (`Track C`)

| Archivo | Propósito | Límite Líneas |
| :--- | :--- | :---: |
| `backend/app/mcp/pricing_math.py` | Algoritmos puros IQR, $W_{\text{health}}$ y guardia $P_{\min} < P_{\text{avg}} < P_{\max}$ | $\le 120$ |
| `backend/app/mcp/stealth_http.py` | Pool de User-Agents reales, cabeceras HTTP y `human_jitter` | $\le 90$ |
| `backend/app/mcp/catalog_fallback.py` | Base de conocimiento de precios de segunda mano en España + deep links | $\le 180$ |
| `backend/app/mcp/connectors.py` | Conectores asíncronos `httpx` + `BeautifulSoup4` por plataforma | $\le 160$ |
| `backend/app/mcp/stealth_engine.py` | Orquestador paralelo multi-web con `asyncio.gather` y fallback automático | $\le 150$ |
| `backend/mcp_server.py` | Servidor MCP en Python (`FastMCP`) exponiendo `search_secondhand_market` y `simulate_market_tick` | $\le 140$ |
| `backend/app/mcp/deep_analysis.py` | Orquestador del análisis profundo: eventos, cuota por plataforma, confianza y caché | $\le 230$ |
| `backend/app/mcp/analysis_query.py` | Limpieza de marca/modelo genéricos y deep links (solo `/analyze`) | $\le 90$ |
| `backend/app/mcp/deep_recommend.py` | Ventana LLM opcional con clamp y omisión segura | $\le 90$ |
| `backend/app/models/market_health.py` | `browser`, `cache` y `analysisEnabled` del health | $\le 60$ |
| `backend/app/mcp/deep_sources.py` | Ejecución por fuente con aislamiento de bloqueos/timeouts | $\le 220$ |
| `backend/app/mcp/deep_parallel.py` | `run_sources` concurrente + agregación (IQR único, cuota, confianza) | $\le 180$ |
| `backend/app/mcp/deep_milanuncios.py` | Transporte híbrido Milanuncios: HTTP primero, navegador de fallback | $\le 180$ |
| `backend/app/mcp/browser/pool.py` | Pool acotado de `BrowserSessionManager` con lock por slot y página propia | $\le 150$ |
| `backend/app/mcp/deep_support.py` | Selección de comparables, avisos y clamp (puro) | $\le 130$ |
| `backend/app/mcp/deep_cache.py` | Serialización y persistencia del resultado en SQLite | $\le 60$ |
| `backend/app/mcp/browser/session.py` | `BrowserSessionManager`: MCP lazy, lock único, una pestaña, reinicio | $\le 230$ |
| `backend/app/mcp/browser/sources/*.py` | Extractores eBay/Wallapop/Milanuncios + parsers de fixtures | $\le 180$ |
| `backend/app/mcp/cache.py` | Caché SQLite TTL 15 min (solo stdlib) | $\le 120$ |
| `backend/app/routers/market_analysis.py` | `POST /api/market/analyze` y `/analyze/stream` (SSE) | $\le 80$ |

---

## 4. Checklist de Control y Calidad (MOD-04)

- [x] Tests unitarios sobre `pricing_math.py` (equivalente Python de `pricing-math.ts`) verificando que para cualquier combinación de precios y `conditionScore` $\in [0, 100]$ se cumple $0 < P_{\min} < P_{\text{avg}} < P_{\max}$ (`backend/tests/test_pricing_math.py`, property-based con Hypothesis).
- [x] Verificación de que un `conditionScore = 95` ("Nuevo") devuelve un $P_{\text{avg}}$ superior a un `conditionScore = 50` ("Desgaste visible") para el mismo artículo (test de monotonicidad).
- [x] Jitter humano configurable (`human_jitter`, 650-1200 ms por defecto según `stealth-market-mcp.md` §2.1; `max_sec=0` instantáneo para tests unitarios).
- [x] Retorno de `comparableListings` con muestras de `wallapop`, `milanuncios` y `ebay` (Vinted diferido a Fase 2, ver ADR-002).
- [x] Endpoint `/api/market/valuate` respondiendo en $< 3.5\text{ s}$ (SLA interna $< 2.8\text{ s}$ con conectores mockeados).
- [x] `POST /api/market/analyze` con datos reales de navegador, estados por fuente, IQR único, cuota por plataforma (máx. 4) y confianza determinista.
- [x] `POST /api/market/analyze/stream` (SSE): orden `analysis_started → source_started → source_result → valuation → recommendation? → done`, heartbeat cada 15 s y cancelación al desconectar.
- [x] Caché SQLite TTL 900 s (`MARKET_CACHE_PATH`), clave query + condición + fuentes, sin `description` ni PII; `cached=true` solo en hit real.
- [x] Gestor de navegador MCP compartido: `chrome-devtools-mcp@1.10.1 --browserUrl $CDP_URL`, lock único, una pestaña, timeout, reinicio y cierre.
- [x] Fuentes eBay, Wallapop y Milanuncios con detección de captcha/anti-bot (`blocked`); Vinted diferido.
- [x] Pool de 2 procesos MCP (eBay + Wallapop) con una página propia por slot, lock por slot y reinicio de proceso.
- [x] Milanuncios híbrido: HTTP (3 páginas) en paralelo; fallback real al navegador si HTTP bloquea, no devuelve anuncios o da < 8 usables.
- [x] `asyncio` concurrente para las 3 fuentes, `source_result` en orden de finalización y `sources[]` en orden de request.
- [x] Config `MARKET_MILANUNCIOS_TRANSPORT=auto|http|browser`, `MARKET_BROWSER_POOL_SIZE=2`, `MARKET_SOURCE_CONCURRENCY=3`.
- [ ] Servidor MCP operable por CLI (`backend/mcp_server.py`): fuera del alcance de la Fase 2 (ver ADR-003).

---

## 5. Estado de implementación — Fase 1 (Fast Valuation Core)

* **Estado:** `🚧 IN_PROGRESS` — núcleo rápido implementado y verificado; `mcp_server.py` y Vinted quedan fuera de esta fase (ver ADR-002).

### Implementado y verificado

* `backend/app/models/sdd.py`: contratos de mercado Pydantic v2 (`camelCase`), invariante estricta y campos aditivos opcionales.
* `backend/app/mcp/pricing_math.py`: funciones puras, IQR, `W_health`, triplete e invariante.
* `backend/app/mcp/normalize.py`, `stealth_http.py`, `connectors.py`: normalización, cabeceras ES coherentes, jitter configurable y conectores eBay/Wallapop/Milanuncios con detección de bloqueo.
* `backend/app/mcp/catalog_fallback.py`: catálogo curado España 2026 + estimador SHA-256 + deep links.
* `backend/app/mcp/deepseek.py` + `deepseek_client.py`: parseo, relevancia y recomendación con validación, reintento, fallback de modelo y plantilla determinista.
* `backend/app/mcp/market_analysis.py` + `routers/market.py`: orquestación, `POST /api/market/valuate`, `GET /api/market/health` y `503` estructurado.
* `backend/Dockerfile`, `backend/Dockerfile.browser`, `docker-compose.yml`, `.env.example`, `scripts/smoke_live.py`.
* Documentación: [`docs/market-analysis.md`](../../docs/market-analysis.md), [`docs/backlog.md`](../../docs/backlog.md), [ADR-002](../decisions/002-market-valuation-contract.md).

### Evidencia

* `pytest -q`: **177 tests** verdes; `ruff check app tests` y `mypy app` limpios.
* `docker compose config` válido; `lifeos-backend` y `market-browser` en estado `healthy`.
* `POST /api/market/valuate` medido en Docker: **1.79 s** con anuncios reales de Milanuncios (`source=live_mcp`) y **1.8–2.3 s** con fallback determinista cuando eBay/Wallapop bloquean; SLA interna ≤ 2.8 s con conectores mockeados.
* `503` estructurado verificado por tests de API cuando `MARKET_ALLOW_FALLBACK=false`.
* Recomendación real con `deepseek-v4-pro` verificada (≈23 s con thinking/max; ventana opt-in fuera del SLA de 2,8 s del mercado).
* Spike de navegador (arm64, Chromium 156/Xvfb): `webdriver=false`, `es-ES`, `Europe/Madrid`, sin `__puppeteer`/`__playwright`; Wallapop 40 anuncios; eBay 60 en la primera pasada y página anti-bot después.

### Diferido (no bloqueante)

* Conector Vinted.
* `backend/mcp_server.py` (FastMCP CLI), Vinted y `/api/market/refresh` (Nivel 2). La Fase 2 (`/analyze`, SSE, caché y motor de navegador) ya está implementada, pero el **gate del Nivel 1 permanece abierto** hasta la verificación end-to-end con la UI.
* Espejo de campos opcionales en `src/types/sdd.ts` (MOD-00 / Track A).
* Validación con una API key real de DeepSeek (no disponible en este entorno).


## 6. Estado de implementación — Fase 2 (Browser Deep Analysis)

* **Estado:** `🚧 IN_PROGRESS` — motor, API, SSE y caché implementados y cubiertos por tests herméticos; el gate del Nivel 1 sigue abierto (no se marca el Nivel 1 como completo).

### Implementado

* `backend/app/mcp/browser/session.py` + `mcp_client.py`: cliente stdio MCP tipado, gestor perezoso con lock único, una pestaña, health probe, timeouts y reinicio ante caída. `scripts/mcp_client.py` es ahora un shim; `app/` no importa `scripts/`.
* `backend/app/mcp/browser/sources/`: eBay (BIN/usado, 60 por página, página 2 si <20, limpieza del sufijo de accesibilidad), Wallapop (scroll y precios `1.234 €`/`1.234,56 €`) y Milanuncios (detección PerimeterX). Parsers probados con fixtures HTML guardadas.
* `backend/app/mcp/deep_analysis.py` + `deep_sources.py` + `deep_support.py`: estados por fuente, dedupe/relevancia/filtros, **IQR único**, cuota 4 por fuente y relleno a 12, `platforms` coherentes, confianza y recomendación opcional (sin plantilla).
* `backend/app/mcp/cache.py` + `deep_cache.py`: SQLite WAL, TTL 15 min, clave sin PII, `asyncio.to_thread`; nunca falla la petición por un error de caché.
* `backend/app/routers/market_analysis.py` + `mcp/sse.py`: `/analyze`, `/analyze/stream`, headers SSE, heartbeat y cancelación; `/api/market/health` amplía `browser`, `cache` y `analysisEnabled`.
* `docker-compose.yml`, `.env.example`, `backend/Dockerfile`: volumen `market-cache`, variables `MARKET_*` y dependencia opcional `market-browser` (`service_healthy`, `required: false`).
* `src/types/market-analysis.ts` + `src/lib/market-analysis.ts`: contrato aditivo y cliente POST+SSE; `src/types/sdd.ts` intacto.
* Documentación: [`docs/market-analysis.md`](../../docs/market-analysis.md), [`docs/backlog.md`](../../docs/backlog.md), [ADR-003](../decisions/003-browser-deep-analysis.md).

### Evidencia

* `pytest -q`: **303 tests** verdes y herméticos (sin CDP ni red); `ruff check app tests`, `mypy app`, `npm run typecheck` y `docker compose config` limpios.
* Tests de contrato para `/analyze` (200/503/422), SSE (orden de eventos, headers, heartbeat, cache hit rápido y cancelación), caché (hit/miss/expiración/aislamiento) y fuentes (fixtures + bloqueo).
* Fingerprint y smoke en vivo se registran en `docs/market-analysis.md`; las cifras dependen de la red del evento y nunca se sustituyen por datos sintéticos.

### Diferido (no bloqueante)

* Vinted, `backend/mcp_server.py` (FastMCP CLI), `/api/market/refresh` (Nivel 2), cableado de la UI (Track A), SSE con varias pestañas y CI multi-arch.


## 7. Estado de implementación — Fase 3 (Parallel Browser Sources)

* **Estado:** `🚧 IN_PROGRESS` — pool híbrido implementado y verificado; el gate
  del Nivel 1 sigue abierto.

### Implementado

* `browser/pool.py`: pool acotado (2 por defecto) de `BrowserSessionManager`;
  cada slot crea su propia página con `new_page` y un token único, tiene su
  propio lock y reinicia su proceso MCP si cae. `stop()` solo se usa en
  shutdown; una desconexión SSE libera únicamente su slot.
* `deep_parallel.py`: `run_sources` lanza las 3 fuentes con concurrencia
  configurable y entrega resultados en orden de finalización; `aggregate_results`
  mantiene el IQR único, la cuota por plataforma y la confianza.
* `deep_milanuncios.py`: HTTP primero (3 páginas), fallback al navegador cuando
  HTTP está bloqueado, vacío o da menos de 8 usables. `transport=http|browser`
  fuerza un único transporte. Nunca hay datos sintéticos.
* `deep_analysis.py`: `source_started` para las 3 fuentes al inicio,
  `source_result` en orden de finalización, `sources[]` ordenado por request y
  `503` si las 3 bloquean o el pool no está disponible.
* `connectors.py`: `MilanunciosConnector(max_pages=…)` multi-página; el
  `/valuate` rápido sigue usando 1 página.
* Docker: flags anti-throttling en `browser-entrypoint.sh`; variables
  `MARKET_MILANUNCIOS_TRANSPORT`, `MARKET_BROWSER_POOL_SIZE` y
  `MARKET_SOURCE_CONCURRENCY` en compose y `.env.example`.

### Evidencia

* `pytest`: **336 tests** verdes (herméticos; fake MCP, sin CDP ni red);
  `ruff` scoped a Track C y `mypy app` limpios.
* Spike: 3 procesos MCP contra el mismo Chrome, wall/max = 1.00, speed-up 1.72×
  con 3 páginas de Milanuncios; fingerprint limpio; HTTP 2 páginas 1.52 s / 10
  usables en la primera pasada y bloqueo posterior → fallback validado.
* Smoke híbrido real: eBay 58 usables / 4.0 s, Wallapop 40 / 4.5 s, Milanuncios
  fallback 7 / 11.1 s, total 17.3 s.
* ADR: [`004-parallel-browser-sources.md`](../decisions/004-parallel-browser-sources.md).

### Diferido (no bloqueante)

* Vinted, FastMCP CLI, `/api/market/refresh` y alertas (Nivel 2), cableado UI de
  Track A, backoff/jitter para HTTP Milanuncios, hook de lifespan del pool y CI
  multi-arch. Ver `docs/backlog.md`.
