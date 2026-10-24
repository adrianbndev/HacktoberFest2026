# 🏗️ SDD Architecture & Data Contracts (`.agent/architecture.md`)

> **Propósito:** Definir de forma inequívoca el esquema de datos, los contratos de API REST/SSE y la estructura de directorios para que **Antigravity CLI**, **Claude Code** y **OpenCode** generen código 100% compatible entre los Tracks de **Ales**, **Adri** y **Matías**.

---

## 1. Estructura de Carpetas del Proyecto (Frontend Next.js + Backend Python FastAPI)

```text
/
├── AGENTS.md                           # Constitución SDD universal (Antigravity CLI & OpenCode)
├── CLAUDE.md                           # Entrypoint SDD para Claude Code (@imports)
├── docker-compose.yml                  # Orquestación: Python Backend (:8000) + Next.js (:3000) + Cloudflared Tunnel
├── .env.example                        # Variables de entorno estandarizadas para los 3 Tracks
├── firebase.json / .firebaserc         # Proyecto Firebase lifeos-recommerce-hf26 (plan gratuito Spark)
├── firestore.rules                     # Reglas: ningún acceso directo desde el navegador (solo el backend)
├── firebase-service-account.json       # Clave del backend (NO va al repo: .gitignore; se comparte en privado)
├── .agent/                             # Especificaciones SDD, Módulos, Reglas y Skills Agénticas
├── src/                                # FRONTEND: Next.js (App Router + TypeScript + Tailwind + Lucide)
│   ├── types/
│   │   ├── sdd.ts                      # Contratos TypeScript (espejo de backend/app/models/)
│   │   └── vision-follow-up.ts         # Amplía VisionAnalyzeRequest/Result con preguntas de seguimiento
│   ├── lib/
│   │   ├── firebase.ts                 # Firebase Auth en el navegador (config pública) + proveedor de Google
│   │   ├── api.ts                      # fetch JSON que añade el ID token de Firebase (Authorization: Bearer)
│   │   └── mobile-sync/
│   │       └── image-compressor.ts     # Track B: Compresión cliente en <canvas> (<200KB JPEG) antes de subir
│   ├── components/
│   │   ├── dashboard/                  # Login con Google, barra superior (usuario + Salir), Bento Grid
│   │   ├── inventory/                  # Track A: Tarjetas de Producto, 3 Precios, Sparklines SVG
│   │   ├── notifications/              # Track A: Centro de Alertas y Badges de tendencia
│   │   ├── mobile-sync/                # Track B: Modal QR, Estado de Conexión SSE/Polling
│   │   └── lifeos/                     # Track A + B: Widgets de Planes, Clima, Calendario y GitHub
│   └── app/
│       ├── (dashboard)/                # Track A: Vista principal unificada por niveles
│       └── mobile-capture/
│           └── [sessionId]/page.tsx    # Track B: Vista móvil de captura directa de cámara (capture="environment")
│   # Nota: next.config.ts redirige /api/:path* -> http://127.0.0.1:8000/api/:path* (Cero problemas CORS en móvil)
└── backend/                            # BACKEND PYTHON: FastAPI + Reconocimiento Imágenes + Motor MCP Stealth
    ├── Dockerfile                      # Imagen Python 3.11-slim con FastAPI, Pillow, httpx, mcp, firebase-admin
    ├── requirements.txt                # Dependencias Python fijadas
    ├── mcp_server.py                   # Track C: Servidor MCP oficial en Python (FastMCP stdio/SSE)
    ├── tests/                          # Tests unitarios con pytest (invariantes MCP, Visión y Store)
    └── app/
        ├── main.py                     # Entrypoint FastAPI (CORS, monta todos los routers de app/routers en /api/*)
        ├── firebase.py                 # Conexión con Firebase Admin (clave de servicio)
        ├── auth.py                     # CurrentUser: verifica el ID token de Firebase (401 si falta o no es válido)
        ├── models/
        │   ├── base.py                 # CamelModel, literales, PriceTriplet (0 < P_min < P_avg < P_max)
        │   ├── domain.py               # Usuarios, inventario, sesiones de captura, LifeOS (+ preguntas de seguimiento)
        │   └── sdd.py                  # Track B: contratos de Visión IA y tasación
        ├── store/
        │   ├── repository.py           # StoreRepository (interfaz) + get_store() -> Firestore (503 sin clave)
        │   ├── firestore_repository.py # users/{uid}, users/{uid}/items/{id}, captureSessions/{id}
        │   └── seed_data.py            # Perfil del primer login desde Google + 3 productos de demo
        ├── vision/                     # Track B (Adri): Reconocimiento de Imágenes en Python + Salud + SEO
        │   ├── image_processor.py      # Decodificación Base64, validación y análisis visual con Pillow (PIL)
        │   ├── gemini_provider.py      # Reconocimiento multimodal con google-genai (Gemini 2.5 Flash)
        │   ├── openai_provider.py      # Reconocimiento multimodal con OpenAI Vision (gpt-4o-mini)
        │   ├── fallback_provider.py    # Reconocedor determinista en Python (análisis de color/aspecto PIL + catálogo)
        │   └── orchestrator.py         # Cadena de responsabilidad con asyncio.wait_for (timeout <= 2.5s)
        ├── mcp/                        # Track C (Matías): Motor MCP Stealth Multi-Web + 3 Precios en Python
        │   ├── pricing_math.py         # Funciones puras en Python: filtro IQR, W_health y 0 < P_min < P_avg < P_max
        │   ├── stealth_http.py         # Rotación de User-Agents reales, cabeceras ES y human_jitter (0.65s - 1.2s)
        │   ├── connectors.py           # Conectores async (httpx + BeautifulSoup4) para Wallapop, Vinted, Milanuncios, eBay
        │   ├── catalog_fallback.py     # Catálogo curado España 2026 + estimador determinista por hash + deep links
        │   ├── stealth_engine.py       # Orquestador paralelo asyncio.gather con timeout <= 2.8s
        │   └── market_refresh.py       # Nivel 2: Re-escaneo de inventario, cálculo de deltas y alertas
        ├── lifeos/                     # Track C (Matías): Servicios LifeOS en Python (Niveles 3 y 4)
        │   ├── weather_service.py      # Cliente async Open-Meteo + modo simulación lluvia/sol + fallback
        │   ├── plans_engine.py         # Recomendador de planes locales cruzados con subida/valor de inventario
        │   ├── calendar_service.py     # Gestión de agenda personal y citas de entrega de Wallapop
        │   └── github_service.py       # Buscador GitHub API Hacktoberfest 2026 + Resumen IA 2 líneas
        └── routers/                    # Controladores HTTP FastAPI (<= 60 líneas por archivo)
            ├── auth_inventory.py       # POST /api/auth, GET/POST/DELETE /api/inventory, POST /api/store/reset (con token)
            ├── capture_session.py      # Track B: POST /api/capture-session, GET/PUT /api/capture-session/{id}
            ├── vision.py               # Track B: POST /api/vision/analyze
            ├── market.py               # Track C: POST /api/market/valuate, POST /api/market/refresh
            └── lifeos.py               # Track C: GET/POST /api/lifeos/{weather,plans,calendar,github}
```

---

## 2. Modelos de Datos Oficiales (`src/types/sdd.ts`)

Todo agente debe respetar exactamente estas interfaces TypeScript (espejo de los modelos Pydantic v2 de `backend/app/models/`: `domain.py`, `sdd.py` y `base.py`):

```typescript
// ==========================================
// 1. USUARIO Y PERFIL (Nivel 1 & Nivel 4)
// ==========================================
export type TeamMemberId = string;  // uid de Firebase Auth (login con Google)

export interface UserProfile {
  id: TeamMemberId;
  name: string;
  role: string;
  avatarUrl: string;
  city: string;                   // Ej. "Madrid", "Barcelona", "Valencia"
  favoriteLanguages: string[];    // Para Nivel 4 (ej. ["TypeScript", "Python", "Rust"])
  createdAt: string;
  email?: string;                 // De la cuenta de Google
}

// ==========================================
// 2. PRODUCTO, SALUD IA Y 3 PRECIOS MCP (Niveles 1 y 2)
// ==========================================
export type ConditionLabel =
  | 'Nuevo'
  | 'Como nuevo'
  | 'Buen estado'
  | 'Desgaste visible'
  | 'Para piezas';

export type MarketPlatform = 'wallapop' | 'vinted' | 'milanuncios' | 'ebay';

export interface PricePoint {
  timestamp: string;              // ISO 8601
  priceMin: number;               // P_min: Venta inmediata (EUR)
  priceAvg: number;               // P_avg: Valor real de mercado (EUR)
  priceMax: number;               // P_max: Techo de mercado impecable (EUR)
  sampleSize: number;             // Nº de anuncios analizados
  platforms: MarketPlatform[];
}

export interface MarketListingSample {
  title: string;
  price: number;
  platform: MarketPlatform;
  condition: string;
  url?: string;
}

export interface InventoryItem {
  id: string;
  userId: TeamMemberId;
  photoUrl: string;               // Data URL optimizada o ruta local en /uploads
  name: string;                   // Ej. "Nintendo Switch OLED 64GB Blanca"
  category: string;               // Ej. "Consolas y Videojuegos"
  brand: string;                  // Ej. "Nintendo"
  model: string;                  // Ej. "Switch OLED HEG-001"
  conditionScore: number;         // 0 a 100 (%)
  conditionLabel: ConditionLabel;
  conditionReasoning: string;     // Explicación breve de la IA sobre el estado visual
  seoTitle: string;               // Título optimizado para Wallapop
  seoDescription: string;         // Descripción persuasiva lista para copiar
  priceMin: number;               // Precio Mínimo actual (EUR)
  priceAvg: number;               // Precio Medio actual (EUR)
  priceMax: number;               // Precio Más Alto actual (EUR)
  priceTrend: 'up' | 'down' | 'stable';
  priceDeltaPercent: number;      // Ej. +12.5 o -5.2 (%)
  priceDeltaEur: number;          // Ej. +22 o -10 (EUR respecto al escaneo previo)
  priceHistory: PricePoint[];     // Histórico de evolución de las 3 medidas
  comparableListings: MarketListingSample[];
  status: 'in_stock' | 'listed' | 'reserved' | 'sold';
  createdAt: string;
  lastUpdatedAt: string;
  details?: string;               // Texto libre del usuario para identificar mejor el producto
}

// ==========================================
// 3. SINCRONIZACIÓN MÓVIL <-> PC (Nivel 1)
// ==========================================
export type CaptureSessionStatus =
  | 'waiting_for_mobile'
  | 'mobile_connected'
  | 'photo_uploaded'
  | 'analyzing'
  | 'completed'
  | 'error';

export interface MobileCaptureSession {
  sessionId: string;
  userId: TeamMemberId;
  status: CaptureSessionStatus;
  photoDataUrl?: string;
  resultItem?: InventoryItem;
  createdAt: string;
  updatedAt: string;
}

// ==========================================
// 4. NOTIFICACIONES Y ALERTAS DE MERCADO (Nivel 2)
// ==========================================
export type NotificationType = 'price_up' | 'price_down' | 'sell_opportunity' | 'delivery_reminder';
export type MetricChanged = 'priceMin' | 'priceAvg' | 'priceMax';

export interface MarketNotification {
  id: string;
  userId: TeamMemberId;
  itemId: string;
  itemName: string;
  type: NotificationType;
  metricChanged: MetricChanged;
  oldValue: number;
  newValue: number;
  deltaPercent: number;
  message: string;                // Mensaje formateado con emojis para el Centro de Alertas
  read: boolean;
  createdAt: string;
}

// ==========================================
// 5. MÓDULOS LIFEOS: PLANES, CLIMA, CALENDARIO Y GITHUB (Niveles 3 y 4)
// ==========================================
export interface WeatherForecast {
  city: string;
  currentTempC: number;
  condition: 'sunny' | 'cloudy' | 'rainy' | 'windy';
  conditionText: string;
  recommendIndoor: boolean;       // true si llueve o hace mal tiempo
  daily: Array<{
    day: string;
    tempMaxC: number;
    tempMinC: number;
    condition: 'sunny' | 'cloudy' | 'rainy' | 'windy';
  }>;
}

export interface LocalPlan {
  id: string;
  title: string;
  category: 'gastronomia' | 'eventos' | 'aire_libre' | 'cultura';
  estimatedCostEur: number;
  environment: 'indoor' | 'outdoor' | 'both';
  location: string;
  description: string;
  matchReason: string;            // Ej. "Cubierto por la subida de +25 € de tu inventario hoy"
  affordableWith: 'inventory_gain' | 'single_item_sale' | 'total_inventory';
}

export interface CalendarEvent {
  id: string;
  userId: TeamMemberId;
  title: string;
  date: string;                   // YYYY-MM-DD
  time: string;                   // HH:mm
  type: 'personal' | 'wallapop_delivery' | 'local_plan' | 'hacktoberfest';
  relatedItemId?: string;         // Si es entrega de un objeto de Wallapop
  location?: string;
  notes?: string;
}

export interface HacktoberfestRepo {
  id: string;
  fullName: string;               // Ej. "vercel/next.js"
  url: string;
  stars: number;
  language: string;
  openHacktoberfestIssues: number;
  labels: string[];               // ["hacktoberfest", "good-first-issue"]
  aiArchitectureSummary: string;  // Línea 1: Arquitectura del repo
  aiQuickStartGuide: string;      // Línea 2: Cómo contribuir rápido hoy
}

// ==========================================
// 6. DTOs DE INTERCAMBIO ENTRE TRACKS & ESTADO GLOBAL DEL STORE
// ==========================================
export interface VisionAnalysisResult {
  name: string;
  category: string;
  brand: string;
  model: string;
  conditionScore: number;         // 0 a 100
  conditionLabel: ConditionLabel;
  conditionReasoning: string;
  seoTitle: string;
  seoDescription: string;
  source?: 'gemini' | 'openai' | 'deterministic_fallback';
}

export interface MarketValuationRequest {        // POST /api/market/valuate (body)
  query: string;
  brand?: string;
  model?: string;
  category: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
}

export interface MarketValuationResult {
  priceMin: number;
  priceAvg: number;
  priceMax: number;
  sampleSize: number;
  platforms: MarketPlatform[];
  comparableListings: MarketListingSample[];
  source: 'live_mcp' | 'stealth_fallback';
}

export interface InventoryTotals {
  totalMin: number;               // Suma de P_min (Liquidez inmediata)
  totalAvg: number;               // Suma de P_avg (Valor real de mercado)
  totalMax: number;               // Suma de P_max (Techo potencial)
  dailyGainEur: number;           // Suma de subidas recientes > 0 €
  itemCount: number;
}

export interface MarketRefreshResponse {
  updatedItems: InventoryItem[];
  newNotifications: MarketNotification[];
  totals: InventoryTotals;
  refreshedAt: string;
}

export interface AppStoreState {        // Referencia del contrato: los datos viven en Firestore (§5)
  profiles: Record<TeamMemberId, UserProfile>;
  inventory: InventoryItem[];
  captureSessions: Record<string, MobileCaptureSession>;
  notifications: MarketNotification[];
  calendarEvents: CalendarEvent[];
  lastUpdatedAt: string;
}

export interface InventoryResponse { profile: UserProfile; items: InventoryItem[]; totals: InventoryTotals }
export interface CaptureSessionCreated { sessionId: string; mobileUrl: string; lanIps: string[] }
export interface CaptureSessionUpdate { status: CaptureSessionStatus; photoDataUrl?: string }

// src/types/vision-follow-up.ts amplía (module augmentation) los contratos de Visión de Track B:
//   VisionAnalyzeRequest.answers?: VisionAnswer[]
//   VisionAnalysisResult.confidence?: number; VisionAnalysisResult.followUpQuestions?: VisionFollowUpQuestion[]
// En Python: VisionAnalyzeRequestWithAnswers y VisionAnalysisWithFollowUp en backend/app/models/domain.py.
```

---

## 3. Contratos de Endpoints REST / SSE

> **Usuario de cada petición:** el navegador envía `Authorization: Bearer <ID token de Firebase>` (lo añade `requestJson` de `src/lib/api.ts`). El backend lo verifica y usa su `uid`; **ningún endpoint recibe `userId` del cliente**. Sin token o con uno inválido: `401`. Sin la clave de servicio de Firebase en el backend: `503`.

### 3.0 Sesión e Inventario (con token)
* **`POST /api/auth`** $\rightarrow$ `UserProfile`. En el primer acceso crea el perfil desde la cuenta de Google y le carga 3 productos de demo.
* **`GET /api/inventory`** $\rightarrow$ `InventoryResponse` (productos del usuario, más recientes primero, y `InventoryTotals` sin los vendidos).
* **`POST /api/inventory`** · Body `InventoryItem` $\rightarrow$ crea o reemplaza (mismo `id`); `userId` siempre queda como el `uid` del token.
* **`DELETE /api/inventory?id=…`** $\rightarrow$ `204`, o `404` si no existe o es de otro usuario.
* **`POST /api/store/reset`** $\rightarrow$ `InventoryResponse`: restaura los 3 productos de demo del usuario antes de presentar.

### 3.1 Sincronización Móvil-PC (`/api/capture-session/[sessionId]`)
* **`POST /api/capture-session`** (con token, sin body)
  * Crea la sesión a nombre del usuario del token y devuelve `CaptureSessionCreated` (`sessionId` de 32 hex: es la única credencial del móvil, que no inicia sesión).
* **`GET /api/capture-session/[sessionId]`** (sin token)
  * Devuelve el estado actual `MobileCaptureSession` (usado tanto por el móvil al abrir el QR como por el PC en polling cada $1.2\text{ s}$ o stream SSE).
* **`PUT /api/capture-session/[sessionId]`**
  * El móvil envía `{ status: 'photo_uploaded', photoDataUrl: 'data:image/jpeg;base64,...' }` ($\le 200\text{ KB}$ comprimido en `<canvas>`).
  * El PC detecta `photo_uploaded` en $<1.5\text{ s}$ y lanza automáticamente el pipeline Visión IA $\rightarrow$ MCP Stealth.

### 3.2 Pipeline de Visión IA y Tasación MCP
* **`POST /api/vision/analyze`**
  * **Body:** `{ photoDataUrl: string, userHint?: string }`
  * **Response:** `VisionAnalysisResult` (SLA $\le 2.5\text{ s}$)
* **`POST /api/market/valuate`**
  * **Body:** `MarketValuationRequest`
  * **Response:** `MarketValuationResult` (SLA $\le 2.8\text{ s}$)

### 3.3 Rastreo de Precios y Notificaciones (Nivel 2)
* **`POST /api/market/refresh`**
  * **Body:** `{ demoMode?: boolean }` (usuario del token)
  * **Acción:** Recorre los artículos del usuario, consulta el MCP (o aplica variación realista de mercado en `demoMode: true` si se invoca desde el botón *"Forzar Actualización de Mercado"*), añade un nuevo `PricePoint` a `priceHistory`, recalcula `priceTrend`, `priceDeltaPercent`, `priceDeltaEur` y genera objetos `MarketNotification` para subidas o bajadas significativas ($\ge 4\%$ o $\ge 5\text{ €}$), **como máximo una por artículo** (la métrica con mayor variación %).
  * **Response:** `MarketRefreshResponse` (inventario actualizado + solo las notificaciones nuevas).
* **`GET /api/notifications`** (usuario del token) $\rightarrow$ `MarketNotification[]` (más recientes primero).
* **`PATCH /api/notifications`**
  * **Body:** `{ id: string, read: true }` $\rightarrow$ `MarketNotification` actualizada.

### 3.4 Módulos LifeOS (Niveles 3 y 4)
* **`GET /api/lifeos/weather?city=Madrid&simulate=rainy|sunny`** $\rightarrow$ `WeatherForecast`
* **`GET /api/lifeos/plans?condition=rainy|sunny`** (usuario del token) $\rightarrow$ Cruza el `WeatherForecast` + el valor total y variación $\Delta\text{ €}$ del inventario del usuario para devolver `{ plans: LocalPlan[], budgetSummary: { dailyGainEur: number, readyToSellTotalEur: number, bannerText: string } }`.
* **`GET / POST / DELETE /api/lifeos/calendar`** $\rightarrow$ Lista, agenda o elimina eventos personales y citas de entrega de Wallapop.
* **`GET /api/lifeos/github?language=TypeScript&hacktoberfest=true&query=...`** $\rightarrow$ Devuelve `HacktoberfestRepo[]` con el resumen IA de 2 líneas.

---

## 4. Puente Frontend $\leftrightarrow$ Backend Python (Zero-CORS) y Variables de Entorno

### 4.1 Proxy Transparente en `next.config.ts`
Para que tanto el PC como el teléfono móvil (al escanear el QR en la red local o por túnel HTTPS) se comuniquen con un **único puerto (`:3000`)** sin errores de CORS ni puertos bloqueados en el firewall, `next.config.ts` redirige automáticamente `/api/*` al backend FastAPI en Python:

```typescript
const nextConfig = {
  async rewrites() {
    const backendUrl = process.env.FASTAPI_INTERNAL_URL || 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};
```

### 4.2 Variables de Entorno Estándar (`.env.example`)
```env
# Visión IA (Track B): variables VISION_* (ver .env.example, que es la fuente de verdad)

# GitHub API para Nivel 4 en Python (Track C - Sube el rate-limit de 60 a 5000 req/h)
GITHUB_TOKEN=

# Conexión Frontend Next.js <-> Backend Python FastAPI
FASTAPI_INTERNAL_URL=http://127.0.0.1:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Firebase: el backend lee firebase-service-account.json de la raíz del repo; solo si está en otro sitio:
# FIREBASE_SERVICE_ACCOUNT=/ruta/absoluta/firebase-service-account.json
```

### 4.3 Reglas de Dockerización (`docker-compose.yml`)
1. **Servicio `lifeos-backend` (Python 3.11 + FastAPI + Pillow + FastMCP):** Expone el puerto `8000` internamente (y en host para Swagger UI `/docs`) y monta `./firebase-service-account.json` en modo solo lectura (los datos están en Firestore).
2. **Servicio `lifeos-web` (Next.js Frontend):** Expone el puerto `3000` con `FASTAPI_INTERNAL_URL=http://lifeos-backend:8000`.
3. **Servicio `mobile-tunnel` (Opcional Anti-AP-Isolation):** `cloudflare/cloudflared:latest` apuntando a `http://lifeos-web:3000` para dar HTTPS público instantáneo al móvil si el Wi-Fi del recinto bloquea tráfico LAN.

---

## 5. Usuarios y Datos: Firebase (plan gratuito Spark, coste cero)

* **Proyecto:** `lifeos-recommerce-hf26`, en el plan **Spark sin cuenta de facturación**: no se puede cobrar nada. **Nunca pasarlo a Blaze.** Por eso no se usa Cloud Storage (desde febrero de 2026 exige Blaze): las fotos van en Firestore.
* **Login (Firebase Auth, solo Google):** `src/lib/firebase.ts` (config pública de la app web) + `signInWithPopup`. Un único usuario por navegador, con botón *Salir*; no hay selector de perfiles ni usuarios de demo fijos. Dominios autorizados: `localhost`, `127.0.0.1`, `macbook-pro-de-matias.local` (el Mac de Matías en la Wi-Fi) y `10.88.7.127` (su IP actual; en otra red hay que autorizar la nueva). Cualquier otro, como un túnel, hay que añadirlo en Firebase Auth y, si es un nombre nuevo, también en `allowedDevOrigins` de `next.config.ts`.
* **Entrar desde otro portátil (Ales, Adri o el jurado):** (a) a la web del Mac de Matías en la misma Wi-Fi, `http://macbook-pro-de-matias.local:3000`, sin instalar nada; o (b) con el repo en local en `http://localhost:3000`, para lo que su backend necesita la clave de servicio. Cada cuenta de Google tiene su propio inventario.
* **Datos (Firestore, solo vía backend):** `backend/app/store/firestore_repository.py` con Firebase Admin y la clave de servicio, detrás de `StoreRepository`. `firestore.rules` bloquea cualquier acceso directo desde el navegador. Timeout de 5 s por llamada.
* **Estructura y formato** (campos en camelCase, idénticos a `sdd.ts`; fechas como texto ISO 8601):
  * `users/{uid}` → `UserProfile`.
  * `users/{uid}/items/{itemId}` → `InventoryItem` completo: precios, `priceHistory`, `comparableListings`, `details` y `photoUrl` (JPEG ≤ 800 px en data URL base64, ~150-200 KB; límite de Firestore: 1 MiB por documento).
  * `captureSessions/{sessionId}` → `MobileCaptureSession` (con la foto subida desde el móvil).
* **Propiedad:** cada producto pertenece al usuario de la sesión (ruta `users/{uid}` y campo `userId`, que el backend fuerza con el `uid` del token). Un usuario no ve, edita ni borra productos ajenos.
* **Clave de servicio:** `firebase-service-account.json` en la raíz del repo (ignorada por git). Sin ella la API responde `503` con el motivo. Se comparte en privado, nunca por el repo.
* **Tests:** `backend/tests/conftest.py` da un almacén en memoria con la misma interfaz (sin red ni credenciales).
