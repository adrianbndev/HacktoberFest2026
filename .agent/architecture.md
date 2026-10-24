# 🏗️ SDD Architecture & Data Contracts (`.agent/architecture.md`)

> **Propósito:** Definir de forma inequívoca el esquema de datos, los contratos de API REST/SSE y la estructura de directorios para que **Antigravity CLI**, **Claude Code** y **OpenCode** generen código 100% compatible entre los Tracks de **Ales**, **Adri** y **Matías**.

---

## 1. Estructura de Carpetas del Proyecto (Target Codebase)

```text
/
├── AGENTS.md                           # Constitución SDD universal (Antigravity CLI & OpenCode)
├── CLAUDE.md                           # Entrypoint SDD para Claude Code (@imports)
├── .agent/                             # Especificaciones SDD y Reglas Agénticas
│   ├── roadmap.md                      # Checklist maestro de los 4 niveles y Gates
│   ├── architecture.md                 # Este documento (Contratos de Datos y APIs)
│   ├── mcp/
│   │   └── stealth-market-mcp.md       # Especificación del motor MCP anti-bot y fallback
│   ├── rules/
│   │   └── hackathon-guardrails.md     # Reglas de seguridad, tiempos (<6s) y cero fallos en demo
│   ├── specs/
│   │   ├── level-1-core-recommerce.md  # Spec funcional Nivel 1
│   │   ├── level-2-price-tracking-alerts.md # Spec funcional Nivel 2
│   │   ├── level-3-lifeos-plans-calendar.md # Spec funcional Nivel 3
│   │   └── level-4-github-hacktoberfest.md  # Spec funcional Nivel 4
│   └── tracks/
│       └── team-tracks-contract.md     # División de trabajo sin conflictos (Ales, Adri, Matías)
└── src/                                # Código fuente Next.js (App Router)
    ├── types/
    │   └── sdd.ts                      # Contratos TypeScript inmutables compartidos por los 3 Tracks
    ├── lib/
    │   ├── store/                      # Persistencia JSON/SQLite en disco (/data/store.json)
    │   ├── vision/                     # Track B: Cliente Visión IA + Salud + SEO + Fallback
    │   ├── mcp/                        # Track C: Motor MCP Stealth Multi-Web + Ponderación + Fallback
    │   └── lifeos/                     # Track C: Servicios de Clima, Planes Locales y GitHub
    ├── mcp/
    │   └── server.ts                   # Track C: Definición de Tools MCP estándar
    ├── components/
    │   ├── dashboard/                  # Track A: Layout Bento Grid, Header, Selector de Perfil
    │   ├── inventory/                  # Track A: Tarjetas de Producto, 3 Precios, Sparklines
    │   ├── notifications/              # Track A: Centro de Alertas y Badges de tendencia
    │   ├── mobile-sync/                # Track B: Modal QR, Estado de Conexión SSE/Polling
    │   └── lifeos/                     # Track A + C: Widgets de Planes, Clima, Calendario y GitHub
    └── app/
        ├── (dashboard)/                # Track A: Vista principal unificada por niveles
        ├── mobile-capture/
        │   └── [sessionId]/page.tsx    # Track B: Vista móvil de captura directa de cámara
        └── api/
            ├── auth/route.ts           # Sesión rápida de usuario (Ales, Adri, Matías, Jurado)
            ├── inventory/route.ts      # CRUD de productos del perfil
            ├── capture-session/
            │   └── [sessionId]/route.ts # Track B: Sincronización Móvil <-> PC (POST foto / GET SSE-Polling)
            ├── vision/
            │   └── analyze/route.ts    # Track B: Inferencia de producto, salud (0-100%) y SEO
            ├── market/
            │   ├── valuate/route.ts    # Track C: Tasación MCP Stealth (P_min, P_avg, P_max)
            │   └── refresh/route.ts    # Track C: Cron / Botón Demo "Forzar Actualización de Mercado"
            └── lifeos/
                ├── plans/route.ts      # Track C: Planes locales cruzados con valor de inventario
                ├── weather/route.ts    # Track C: Clima y recomendación Interior/Exterior
                ├── calendar/route.ts   # Track C: Agenda personal + entregas de Wallapop
                └── github/route.ts     # Track C: Buscador Hacktoberfest 2026 + Resumen IA 2 líneas
```

---

## 2. Modelos de Datos Oficiales (`src/types/sdd.ts`)

Todo agente debe respetar exactamente estas interfaces TypeScript:

```typescript
// ==========================================
// 1. USUARIO Y PERFIL (Nivel 1 & Nivel 4)
// ==========================================
export type TeamMemberId = 'ales' | 'adri' | 'matias' | 'jurado';

export interface UserProfile {
  id: TeamMemberId;
  name: string;
  role: string;
  avatarUrl: string;
  city: string;                   // Ej. "Madrid", "Barcelona", "Valencia"
  favoriteLanguages: string[];    // Para Nivel 4 (ej. ["TypeScript", "Python", "Rust"])
  createdAt: string;
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
```

---

## 3. Contratos de Endpoints REST / SSE

### 3.1 Sincronización Móvil-PC (`/api/capture-session/[sessionId]`)
* **`POST /api/capture-session`**
  * Crea una nueva sesión con `sessionId` único para el usuario activo y devuelve `{ sessionId, mobileUrl }`.
* **`GET /api/capture-session/[sessionId]`**
  * Devuelve el estado actual `MobileCaptureSession` (usado tanto por el móvil al abrir el QR como por el PC en polling cada $1.5\text{ s}$ o stream SSE).
* **`PUT /api/capture-session/[sessionId]`**
  * El móvil envía `{ status: 'photo_uploaded', photoDataUrl: 'data:image/jpeg;base64,...' }`.
  * El PC detecta `photo_uploaded` en $<1.5\text{ s}$ y lanza automáticamente el pipeline Visión IA $\rightarrow$ MCP Stealth.

### 3.2 Pipeline de Visión IA y Tasación MCP
* **`POST /api/vision/analyze`**
  * **Body:** `{ photoDataUrl: string }`
  * **Response:** `{ name, category, brand, model, conditionScore, conditionLabel, conditionReasoning, seoTitle, seoDescription }`
* **`POST /api/market/valuate`**
  * **Body:** `{ query: string, category: string, conditionScore: number, conditionLabel: ConditionLabel }`
  * **Response:** `{ priceMin, priceAvg, priceMax, sampleSize, platforms, comparableListings, source: 'live_mcp' | 'stealth_fallback' }`

### 3.3 Rastreo de Precios y Notificaciones (Nivel 2)
* **`POST /api/market/refresh`**
  * **Body:** `{ userId: TeamMemberId, demoMode?: boolean }`
  * **Acción:** Recorre los artículos del usuario, consulta el MCP (o aplica variación realista de mercado en `demoMode: true` si se invoca desde el botón *"Forzar Actualización de Mercado"*), añade un nuevo `PricePoint` a `priceHistory`, recalcula `priceTrend`, `priceDeltaPercent`, `priceDeltaEur` y genera objetos `MarketNotification` para subidas o bajadas significativas ($\ge 5\%$ o $\ge 5\text{ €}$).

### 3.4 Módulos LifeOS (Niveles 3 y 4)
* **`GET /api/lifeos/weather?city=Madrid`** $\rightarrow$ `WeatherForecast`
* **`GET /api/lifeos/plans?userId=ales`** $\rightarrow$ Cruza el `WeatherForecast` + el valor total y variación $\Delta\text{ €}$ del inventario del usuario para devolver `LocalPlan[]` personalizados.
* **`GET / POST /api/lifeos/calendar`** $\rightarrow$ Lista o agenda eventos personales y citas de entrega de Wallapop.
* **`GET /api/lifeos/github?language=TypeScript&hacktoberfest=true`** $\rightarrow$ Devuelve `HacktoberfestRepo[]` con el resumen IA de 2 líneas.
