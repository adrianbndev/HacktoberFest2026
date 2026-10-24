# 🏛️ Reglas de Clean Code, SOLID y Arquitectura Limpia (`.agent/rules/clean-code-solid.md`)

> **Aplicación:** Regla activa siempre (`always_on`) en **Antigravity CLI**, **Claude Code** y **OpenCode**. Todo código escrito por cualquier agente debe cumplir estos principios de ingeniería de software.

---

## 1. Arquitectura en Capas (Clean / Hexagonal Pragmática)

Aunque estemos en un hackathon de 9 horas, el desorden arquitectónico genera bugs de integración entre **Ales, Adri y Matías**. Cada funcionalidad debe separar estrictamente **4 capas**:

```text
[1. UI / Componentes React en Next.js (src/)] (Presentación pura, cero lógica de scraping o prompts)
         │  (fetch('/api/...') vía Rewrite Proxy sin CORS)
         ▼
[2. Routers FastAPI en Python (backend/app/routers/*)] (Transporte HTTP, validación Pydantic v2 de entrada/salida, ≤ 60 líneas)
         │  (invoca casos de uso asíncronos)
         ▼
[3. Dominio / Casos de Uso en Python (backend/app/{vision,mcp,lifeos}/*)] (Reglas de negocio puras, cálculo de precios, alertas, cruces LifeOS)
         │  (depende de Protocol / ABC ports)
         ▼
[4. Adaptadores e Infraestructura en Python] (Pillow, Gemini/OpenAI SDK, conectores httpx MCP, Open-Meteo, GitHub API, JSON Store Atómico)
```

---

## 2. Principios SOLID Aplicados al Proyecto (TypeScript + Python)

### S — Single Responsibility Principle (Responsabilidad Única)
* **Un archivo, una razón para cambiar:**
  * Ningún componente React `.tsx` ni módulo Python `.py` puede superar las **220-250 líneas**. Si crece, extrae subcomponentes presentacionales puros (`PriceTrioCard.tsx`, `HealthScoreBadge.tsx`) o submódulos Python (`pricing_math.py`, `image_processor.py`).
  * Ningún Router FastAPI (`backend/app/routers/*.py`) debe contener prompts de IA ni algoritmos matemáticos: solo valida el request con Pydantic v2, llama al servicio de `backend/app/` y devuelve el modelo tipado.

### O — Open/Closed Principle (Abierto/Cerrado)
* Los motores de **Reconocimiento de Imágenes (`vision`)**, **Tasación MCP (`mcp`)** y **Recomendación de Planes (`lifeos`)** deben estar abiertos a extensión y cerrados a modificación:
  * Para añadir una nueva plataforma de segunda mano (ej. *CashConverters* o *Todocolección*), se añade una clase en Python que implemente `MarketConnectorProtocol` y se registra en la lista de conectores sin tocar la lógica de ponderación $W_{\text{health}}$.

### L — Liskov Substitution Principle (Sustitución de Liskov)
* **Paridad Total entre Proveedores Live y Fallback en Python:**
  * Todo adaptador de contingencia (`FallbackVisionProvider`, `FallbackMarketConnector`, `FallbackWeatherService`, `FallbackGithubService`) debe implementar exactamente el mismo `Protocol` Python que el servicio en vivo, devolver los mismos modelos Pydantic v2, respetar las mismas invariantes matemáticas (ej. $0 < P_{\min} < P_{\text{avg}} < P_{\max}$) y nunca devolver datos incompletos.

### I — Interface Segregation Principle (Segregación de Interfaces)
* Los componentes de UI solo reciben las props que necesitan.
* En `src/types/sdd.ts` y `backend/app/models/sdd.py`, mantener esquemas granulares (`VisionAnalysisResult`, `MarketValuationResult`, `PricePoint`, `MarketNotification`) que luego se componen en `InventoryItem`.

### D — Dependency Inversion Principle (Inversión de Dependencias)
* Los servicios de dominio en `backend/app/` reciben sus dependencias (repositorios o proveedores externos) por constructor o parámetro con valores por defecto (FastAPI `Depends` o Default Dependency Injection), permitiendo inyectar *mocks* instantáneos en los tests unitarios de `pytest`.

---

## 3. Estándares de Clean Code (TypeScript Strict + Python Type Hints & Pydantic v2)

1. **Tipado Estricto en Ambos Lenguajes:**
   * En Frontend (`src/`): Prohibido `any` y `as unknown as`. Usar siempre `src/types/sdd.ts`.
   * En Backend (`backend/`): Type hints obligatorios en todas las funciones Python (`def calculate_three_prices(raw_prices: list[float], condition_score: int) -> PriceTriplet:`) y validación de todos los payloads externos con **Pydantic v2 (`BaseModel`)**.
2. **Manejo Explícito de Errores (Zero Unhandled Exceptions):**
   * Toda llamada de red en Python (`httpx`, SDK de Gemini/OpenAI, GitHub API) debe usar `asyncio.wait_for` / `httpx.Timeout` y capturar excepciones específicas activando el proveedor Fallback Liskov sin lanzar jamás un HTTP 500 hacia el frontend.
3. **Nombres Auto-Documentados y Constantes con Significado:**
   * Prohibido usar números mágicos. Definir constantes semánticas:
     * `MCP_HUMAN_JITTER_MIN_SEC = 0.65`
     * `MCP_HUMAN_JITTER_MAX_SEC = 1.20`
     * `MAX_END_TO_END_LATENCY_SEC = 6.0`
     * `MOBILE_POLLING_INTERVAL_MS = 1200`
     * `MOBILE_IMAGE_MAX_DIMENSION_PX = 800`
4. **Funciones Puras para Lógica Financiera y de Salud (`pricing_math.py`):**
   * El cálculo de $W_{\text{health}}$, $P_{\min}, P_{\text{avg}}, P_{\max}$, $\Delta\text{ €}$, $\Delta\%$ y el presupuesto de planes locales deben ser **funciones puras deterministas en Python** (sin efectos secundarios ni llamadas de red dentro del cálculo), ubicadas en `backend/app/mcp/pricing_math.py`.
