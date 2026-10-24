# 🧭 ADR-001: Análisis de Opciones Tecnológicas, Arquitectura y Trade-offs (Hackathon 9h)

> **Estado:** Aprobado (Fase de Planificación SDD)
> **Equipo:** Ales (Track A), Adri (Track B), Matías (Track C)
> **Objetivo:** Analizar qué opciones tecnológicas tenemos para cada subsistema de **LifeOS & ReCommerce AI**, justificar la elección óptima bajo criterios de **velocidad de desarrollo (9h), Clean Architecture, SOLID y resiliencia absoluta en demo**, y definir el plan B (fallback) de cada pieza.

---

## 1. Resumen Ejecutivo de Decisiones

| Subsistema | Opción Elegida (Primaria) | Alternativa Descartada / Secundaria | Fallback de Supervivencia en Demo |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | **Next.js (App Router) + TypeScript Strict + Rewrite Proxy** | SPA sin proxy (genera bloqueos CORS en móvil) | Proxy interno `/api/* -> :8000` (un único puerto `:3000` para PC y Móvil) |
| **Backend & APIs** | **Python 3.11+ (FastAPI + Uvicorn + Pydantic v2)** | Backend monolítico en Node.js | Swagger UI automático en `:8000/docs` + tipado estricto Pydantic |
| **UI & Gráficas** | **Tailwind CSS + Bento Grid + SVG Sparklines nativos** | Librerías pesadas (Chart.js / Recharts con problemas SSR) | Componentes SVG puros sin dependencias externas |
| **Captura Cámara Móvil** | **`<input type="file" accept="image/*" capture="environment">` + Canvas Compress** | `navigator.mediaDevices.getUserMedia` exclusivo | Botón *"Simular Captura Móvil"* en PC + Galería local |
| **Sync Móvil $\leftrightarrow$ PC** | **FastAPI Endpoints `/api/capture-session` + Short-Polling $1.2\text{ s}$ / SSE** | Socket.io / Pusher / WebSockets externos | Short-polling HTTP puro cada $1.2\text{ s}$ (indestructible en cualquier red) |
| **Conectividad Móvil-PC** | **Auto-detección IP LAN (`192.168.x.x`) en Python + QR dinámico** | Solo `localhost` (inaccesible desde el móvil) | `npx cloudflared tunnel --url http://localhost:3000` si el Wi-Fi aísla clientes |
| **Reconocimiento Imágenes** | **Python `Pillow` + `google-genai` (Gemini 2.5 Flash) / `openai`** | Procesamiento en JS sin librerías de visión nativas | `DeterministicVisionProvider` en Python (análisis visual `PIL` + catálogo en $<50\text{ ms}$) |
| **Motor MCP de Precios** | **Python `FastMCP` (`mcp`) + `httpx` Async + `BeautifulSoup4`** | Scraping síncrono con Selenium/Playwright pesado | `DeterministicMarketFallback` en Python (Catálogo real España 2026 + $W_{\text{health}}$) |
| **Persistencia de Datos** | **Repositorio Python JSON Atómico (`/data/store.json` + `RLock`)** | DB en la nube con latencia o motores SQL complejos | Reset instantáneo en 1 clic (`POST /api/store/reset`) a datos semilla |
| **Validación y Contratos** | **Pydantic v2 (`camelCase`) en Python + TypeScript `strict` en Front** | Diccionarios Python sin esquema (`dict[str, Any]`) | Validación automática de entrada/salida con `model_validate` |

---

## 2. Análisis Detallado por Subsistema

### 2.1 Sincronización Cámara Móvil $\leftrightarrow$ Web PC (Nivel 1.2 — Track B)

#### ¿Qué opciones tenemos para abrir la cámara en el móvil?
* **Opción A (Elegida): Input Nativo con `capture="environment"` + Compresión Canvas en Cliente.**
  * **Cómo funciona:** Cuando el usuario escanea el QR y abre `/mobile-capture/[sessionId]`, pulsa un botón que dispara `<input type="file" accept="image/*" capture="environment" />`. El sistema operativo del móvil (iOS/Android) abre la app de cámara nativa a máxima calidad y con enfoque por hardware. Al confirmar la foto, un script en el cliente la dibuja en un `<canvas>` de máximo $800\text{ px}$ y la exporta como `image/jpeg` al $75\%$ ($<200\text{ KB}$).
  * **Ventaja crítica:** **No requiere HTTPS (`https://`)**. Si estamos en la red local del hackathon (`http://192.168.1.45:3000`), `navigator.mediaDevices.getUserMedia()` es bloqueado por seguridad en Safari y Chrome móvil, mientras que `<input capture="environment">` funciona siempre al 100%.
* **Opción B (Mejora Progresiva):** `getUserMedia` en vivo.
  * Solo se activa si `window.isSecureContext === true` (por ejemplo, si levantamos un túnel HTTPS con `cloudflared`).

#### ¿Qué opciones tenemos para comunicar el Móvil con el PC en tiempo real?
* **Opción A (Elegida): Arquitectura Híbrida SSE + Short-Polling ($1.2\text{ s}$).**
  * **Cómo funciona:** El servidor mantiene un `CaptureSessionRepository`. El PC abre un stream SSE (`GET /api/capture-session/[sessionId]/stream`) y, en paralelo o como respaldo automático, consulta `GET /api/capture-session/[sessionId]` cada $1.2\text{ s}$.
  * **Por qué gana:** En Next.js App Router, los WebSockets puros requieren un servidor Node custom fuera del estándar, y servicios cloud como Pusher o Supabase Realtime requieren cuentas y conexión externa estable. El híbrido SSE + Polling local no necesita dependencias externas y garantiza que la foto aparezca en el PC en $<1.5\text{ s}$.

---

### 2.2 Reconocimiento de Imágenes en Python: Identificación + Salud ($0-100\%$) + SEO (Nivel 1.3 — Track B)

#### ¿Por qué Python para Visión IA y Procesamiento de Imágenes?
1. **Procesamiento Nativo con `Pillow (PIL)` (`backend/app/vision/image_processor.py`):**
   * Decodifica el `photoDataUrl` Base64, verifica integridad, extrae histogramas de color/brillo/nitidez y optimiza la imagen antes de enviarla al modelo multimodal.
2. **SDKs Multimodales Oficiales en Python con Salida Estructurada Pydantic v2:**
   * **`google-genai` (`gemini-2.5-flash`):** Recibe directamente objetos `PIL.Image` y un esquema `response_schema=VisionAnalysisResult` en Pydantic v2, respondiendo en $\sim 1.4\text{ s}$.
   * **`openai` (`gpt-4o-mini`):** Soporte nativo de `beta.chat.completions.parse` con modelos Pydantic.
3. **Proveedor Determinista con Visión Local (`FallbackVisionProvider` en Python):**
   * Si la API key agota su cuota o el Wi-Fi cae, analiza métricas reales de la imagen con `Pillow` (dimensiones, color dominante, luminancia) o el `userHint` y selecciona del banco de productos de demo devolviendo un diagnóstico visual inmediato ($< 40\text{ ms}$).

#### Diseño SOLID en Python (`Protocol` / `ABC`) aplicado a Visión IA:
* Definimos el puerto `VisionAnalyzerProtocol` en `backend/app/vision/`:
  ```python
  class VisionAnalyzerProtocol(Protocol):
      provider_name: str
      async def analyze_product_photo(
          self, image: Image.Image, raw_data_url: str, hint: str | None = None
      ) -> VisionAnalysisResult: ...
  ```
* Implementamos un `ResilientVisionOrchestrator` con `asyncio.wait_for(..., timeout=2.5)` que intenta el proveedor primario y, ante cualquier excepción o timeout, delega de forma transparente en el siguiente proveedor sin romper la experiencia del usuario.

---

### 2.3 Motor MCP Stealth en Python y Cálculo de los 3 Precios (Nivel 1.4 — Track C)

#### ¿Cómo estructuramos el MCP en Python para que sea un MCP real y a la vez ultrarrápido?
* **Doble Exposición sobre el mismo motor Python (`backend/app/mcp/`):**
  1. **Núcleo de Dominio (`backend/app/mcp/stealth_engine.py` & `pricing_math.py`):** Contiene la lógica pura en Python: rotación de cabeceras humanas, `await human_jitter(0.65, 1.20)`, conectores asíncronos con `httpx.AsyncClient` + `BeautifulSoup4` (`WallapopConnector`, `VintedConnector`, `MilanunciosConnector`, `EbayConnector`), filtrado estadístico de *outliers* por rango intercuartílico (IQR), ponderación por salud $W_{\text{health}}$ y el catálogo semilla determinista.
  2. **Servidor MCP Estándar en Python (`backend/mcp_server.py`):** Expone las herramientas `search_secondhand_market` y `simulate_market_tick` mediante **`FastMCP` (`from mcp.server.fastmcp import FastMCP`)** sobre transporte `stdio`/SSE. Así se puede registrar directamente en Antigravity CLI, Claude Code o OpenCode y demostrar al jurado el protocolo MCP en Python funcionando.
  3. **Router FastAPI (`backend/app/routers/market.py`):** Invoca `await stealth_engine.valuate(...)` directamente en el mismo proceso asíncrono de Python para garantizar latencia $<2.8\text{ s}$ en la web.

#### ¿Por qué no usar Puppeteer / Playwright Headless en vivo para cada búsqueda?
* Levantar un navegador Chromium headless consume $>400\text{ MB}$ de RAM y tarda $4-9\text{ segundos}$ solo en arrancar, rompiendo el límite de $6\text{ s}$ del hackathon y arriesgando bloqueos por CAPTCHA.
* **Solución Profesional:** Peticiones HTTP ligeras (`httpx.AsyncClient` con `httpx.Timeout(1.6)`) usando las cabeceras de API pública/web móvil con *jitter* humano + **Capa de Fallback Determinista Curada** con datos reales del mercado español 2026.

---

### 2.4 Rastreo Periódico de Precios y Modo Demo (Nivel 2 — Track C & Track A)

#### Opciones para el Job Periódico:
* **Opción A (Elegida): Scheduler Híbrido (Client Interval + Server Endpoint `/api/market/refresh` + Botón Demo 1-Clic).**
  * En el dashboard, un `useEffect` opcional dispara un refresco silencioso cada $X$ minutos, pero el protagonista para el jurado es el botón **"⚡ Forzar Actualización de Mercado (Demo Mode)"**.
  * Al pulsarlo, el motor genera un nuevo `PricePoint` en cada producto del inventario, calcula la derivada ($\Delta\text{ €}$ y $\Delta\%$) respecto al punto anterior, actualiza las 3 curvas ($P_{\min}, P_{\text{avg}}, P_{\max}$) y emite notificaciones inteligentes en el Centro de Alertas.

---

### 2.5 Módulos LifeOS: Clima, Planes Locales, Calendario y GitHub (Niveles 3 y 4)

1. **Clima (`/api/lifeos/weather`):**
   * **Primario:** API de **Open-Meteo** (`https://api.open-meteo.com/v1/forecast`), que es 100% gratuita, no requiere API Key y responde en $<200\text{ ms}$ para coordenadas de Madrid, Barcelona, Valencia, Sevilla, Bilbao, etc.
   * **Fallback + Toggle Demo:** Permite alternar entre el clima real y un selector rápido de simulación (*"☀️ Soleado"* vs *"🌧️ Lluvia"*) para demostrar en vivo ante el jurado cómo cambian los planes recomendados de exterior a interior.
2. **Planes Locales Conectados al Inventario (`/api/lifeos/plans`):**
   * Motor de reglas (`PlanRecommendationEngine`) que recibe `{ userCity, weatherCondition, inventoryGainEur, totalInventoryValueEur }` y filtra un catálogo rico de planes locales asignando a cada plan un `matchReason` dinámico vinculado a los productos reales del usuario.
3. **GitHub Hacktoberfest 2026 (`/api/lifeos/github`):**
   * **Primario:** GitHub Search API (`q=label:hacktoberfest+language:TypeScript+state:open`) con caché en memoria de 10 minutos para no agotar los 60 req/h sin token (o 5000 req/h si hay `GITHUB_TOKEN` en `.env.local`).
   * **Fallback + Resumen IA 2 Líneas:** Pre-cálculo y generación en vivo de `aiArchitectureSummary` (Línea 1) y `aiQuickStartGuide` (Línea 2) adaptados a los lenguajes favoritos de **Ales**, **Adri** y **Matías**.
