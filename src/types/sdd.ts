// Contratos compartidos por los 3 Tracks (.agent/architecture.md §2).
// Espejo 1:1 de backend/app/models/sdd.py: si cambias uno, cambia el otro en el mismo commit.

// ---------- 1. Usuario y perfil ----------
export type TeamMemberId = 'ales' | 'adri' | 'matias';

export interface UserProfile {
  id: TeamMemberId;
  name: string;
  role: string;
  avatarUrl: string;
  city: string;
  favoriteLanguages: string[];
  createdAt: string;
}

// ---------- 2. Producto, salud IA y 3 precios MCP ----------
export type ConditionLabel = 'Nuevo' | 'Como nuevo' | 'Buen estado' | 'Desgaste visible' | 'Para piezas';
export type MarketPlatform = 'wallapop' | 'vinted' | 'milanuncios' | 'ebay';

export interface PricePoint {
  timestamp: string;              // ISO 8601
  priceMin: number;               // P_min: venta inmediata (EUR)
  priceAvg: number;               // P_avg: valor real de mercado (EUR)
  priceMax: number;               // P_max: techo de mercado (EUR)
  sampleSize: number;
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
  photoUrl: string;
  name: string;
  category: string;
  brand: string;
  model: string;
  conditionScore: number;         // 0 a 100
  conditionLabel: ConditionLabel;
  conditionReasoning: string;
  seoTitle: string;
  seoDescription: string;
  priceMin: number;               // Invariante: 0 < priceMin < priceAvg < priceMax
  priceAvg: number;
  priceMax: number;
  priceTrend: 'up' | 'down' | 'stable';
  priceDeltaPercent: number;
  priceDeltaEur: number;
  priceHistory: PricePoint[];
  comparableListings: MarketListingSample[];
  status: 'in_stock' | 'listed' | 'reserved' | 'sold';
  createdAt: string;
  lastUpdatedAt: string;
}

// ---------- 3. Sincronización móvil <-> PC ----------
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

export interface CaptureSessionRequest { userId: TeamMemberId }            // POST /api/capture-session (body)
export interface CaptureSessionCreated { sessionId: string; mobileUrl: string; lanIps: string[] }
export interface CaptureSessionUpdate {                                     // PUT /api/capture-session/{id}
  status: CaptureSessionStatus;
  photoDataUrl?: string;          // data:image/... comprimida en el móvil (<= 800 px, JPEG 0.75)
}

// ---------- 4. Notificaciones de mercado ----------
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
  message: string;
  read: boolean;
  createdAt: string;
}

// ---------- 5. LifeOS: clima, planes, calendario y GitHub ----------
export type WeatherCondition = 'sunny' | 'cloudy' | 'rainy' | 'windy';

export interface WeatherForecast {
  city: string;
  currentTempC: number;
  condition: WeatherCondition;
  conditionText: string;
  recommendIndoor: boolean;
  daily: Array<{ day: string; tempMaxC: number; tempMinC: number; condition: WeatherCondition }>;
}

export interface LocalPlan {
  id: string;
  title: string;
  category: 'gastronomia' | 'eventos' | 'aire_libre' | 'cultura';
  estimatedCostEur: number;
  environment: 'indoor' | 'outdoor' | 'both';
  location: string;
  description: string;
  matchReason: string;
  affordableWith: 'inventory_gain' | 'single_item_sale' | 'total_inventory';
}

export interface CalendarEvent {
  id: string;
  userId: TeamMemberId;
  title: string;
  date: string;                   // YYYY-MM-DD
  time: string;                   // HH:mm
  type: 'personal' | 'wallapop_delivery' | 'local_plan' | 'hacktoberfest';
  relatedItemId?: string;
  location?: string;
  notes?: string;
}

export interface HacktoberfestRepo {
  id: string;
  fullName: string;
  url: string;
  stars: number;
  language: string;
  openHacktoberfestIssues: number;
  labels: string[];
  aiArchitectureSummary: string;
  aiQuickStartGuide: string;
}

// ---------- 6. DTOs entre Tracks y estado global ----------
export interface VisionFollowUpQuestion {
  id: string;
  question: string;               // Ej. "¿Qué capacidad de almacenamiento tiene?"
  reason: string;                 // Por qué importa para identificar o tasar
  affects: 'identification' | 'condition';
  options: string[];              // Respuestas rápidas (vacío = respuesta libre)
}

export interface VisionAnswer {
  questionId: string;
  question: string;
  answer: string;
}

export interface VisionAnalyzeRequest {           // POST /api/vision/analyze (body)
  photoDataUrl: string;
  userHint?: string;
  answers?: VisionAnswer[];       // Respuestas a followUpQuestions anteriores para refinar
}

export interface VisionAnalysisResult {           // POST /api/vision/analyze (respuesta)
  name: string;
  category: string;
  brand: string;
  model: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
  conditionReasoning: string;
  seoTitle: string;
  seoDescription: string;
  confidence: number;             // 0 a 1
  followUpQuestions: VisionFollowUpQuestion[];   // Vacío = la IA no necesita más datos
  source?: 'llm' | 'deterministic_fallback';      // llm = el modelo de AI_MODEL (local o cloud)
}

export interface MarketValuationRequest {         // POST /api/market/valuate (body)
  query: string;
  brand?: string;
  model?: string;
  category: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
}

export interface MarketValuationResult {          // POST /api/market/valuate (respuesta)
  priceMin: number;
  priceAvg: number;
  priceMax: number;
  sampleSize: number;
  platforms: MarketPlatform[];
  comparableListings: MarketListingSample[];
  source: 'live_mcp' | 'stealth_fallback';
}

export interface InventoryTotals {
  totalMin: number;
  totalAvg: number;
  totalMax: number;
  dailyGainEur: number;           // Suma de subidas recientes > 0 €
  itemCount: number;              // Los artículos vendidos no cuentan
}

export interface MarketRefreshResponse {          // POST /api/market/refresh
  updatedItems: InventoryItem[];
  newNotifications: MarketNotification[];
  totals: InventoryTotals;
  refreshedAt: string;
}

export interface AuthRequest { userId: TeamMemberId }                    // POST /api/auth
export interface AuthSession { activeUserId: TeamMemberId; profiles: UserProfile[] }  // GET /api/auth

export interface InventoryResponse {              // GET /api/inventory?userId=
  profile: UserProfile;
  items: InventoryItem[];         // Más recientes primero
  totals: InventoryTotals;
}

export interface AppStoreState {
  activeUserId: TeamMemberId;
  profiles: Record<TeamMemberId, UserProfile>;
  inventory: InventoryItem[];
  captureSessions: Record<string, MobileCaptureSession>;
  notifications: MarketNotification[];
  calendarEvents: CalendarEvent[];
  lastUpdatedAt: string;
}
