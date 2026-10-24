# 🕵️ MOD-04: Motor MCP Stealth Multi-Web y las 3 Medidas de Precio ($P_{\min}, P_{\text{avg}}, P_{\max}$)

* **Nivel SDD:** 🟢 Nivel 1.4
* **Responsable:** **Track C (Matías)**
* **Estado Actual:** `🚧 IN_PROGRESS` (Fase 1 — fast valuation core)
* **SLA de Latencia:** $\le 3000\text{ ms}$ (incluyendo *jitter* humano de $800\text{ ms} - 2200\text{ ms}$)

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
| `backend/app/routers/market.py` | Endpoint FastAPI `POST /api/market/valuate` (y `/refresh` en Nivel 2) | $\le 70$ |

---

## 4. Checklist de Control y Calidad (MOD-04)

- [x] Tests unitarios sobre `pricing_math.py` (equivalente Python de `pricing-math.ts`) verificando que para cualquier combinación de precios y `conditionScore` $\in [0, 100]$ se cumple $0 < P_{\min} < P_{\text{avg}} < P_{\max}$ (`backend/tests/test_pricing_math.py`, property-based con Hypothesis).
- [x] Verificación de que un `conditionScore = 95` ("Nuevo") devuelve un $P_{\text{avg}}$ superior a un `conditionScore = 50` ("Desgaste visible") para el mismo artículo (test de monotonicidad).
- [x] Jitter humano configurable (`human_jitter`, 650-1200 ms por defecto según `stealth-market-mcp.md` §2.1; `max_sec=0` instantáneo para tests unitarios).
- [x] Retorno de `comparableListings` con muestras de `wallapop`, `milanuncios` y `ebay` (Vinted diferido a Fase 2, ver ADR-002).
- [x] Endpoint `/api/market/valuate` respondiendo en $< 3.5\text{ s}$ (SLA interna $< 2.8\text{ s}$ con conectores mockeados).
- [ ] Servidor MCP operable por CLI (`backend/mcp_server.py`): fuera del alcance de la Fase 1 (ver ADR-002).

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

* `pytest -q`: **137 tests** verdes; `ruff check app tests` y `mypy app` limpios.
* `docker compose config` válido; `lifeos-backend` y `market-browser` en estado `healthy`.
* `POST /api/market/valuate` medido en Docker: **1.8–2.3 s** con todas las fuentes bloqueadas y fallback determinista; SLA interna ≤ 2.8 s con conectores mockeados.
* `503` estructurado verificado por tests de API cuando `MARKET_ALLOW_FALLBACK=false`.
* Spike de navegador (arm64, Chromium 156/Xvfb): `webdriver=false`, `es-ES`, `Europe/Madrid`, sin `__puppeteer`/`__playwright`; Wallapop 40 anuncios; eBay 60 en la primera pasada y página anti-bot después.

### Diferido (no bloqueante)

* Conector Vinted.
* `backend/mcp_server.py` (FastMCP) y `POST /api/market/analyze` + SSE + caché SQLite + motor de navegador completo (Fase 2).
* Espejo de campos opcionales en `src/types/sdd.ts` (MOD-00 / Track A).
* Validación con una API key real de DeepSeek (no disponible en este entorno).
