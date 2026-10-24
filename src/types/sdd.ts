// ============================================================================
// SDD Official Data Contracts (src/types/sdd.ts)
// Mirror 1:1 with backend/app/models/sdd.py
// ============================================================================

export type TeamMemberId = string;  // uid de Firebase Auth

export interface UserProfile {
  id: TeamMemberId;
  name: string;
  role: string;
  avatarUrl: string;
  city: string;
  favoriteLanguages: string[];
  createdAt: string;
  email?: string;
}

export type ConditionLabel = 'Nuevo' | 'Como nuevo' | 'Buen estado' | 'Desgaste visible' | 'Para piezas';

export type MarketPlatform = 'wallapop' | 'vinted' | 'milanuncios' | 'ebay';

export interface PricePoint {
  timestamp: string;
  priceMin: number;
  priceAvg: number;
  priceMax: number;
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
  conditionScore: number;
  conditionLabel: ConditionLabel;
  conditionReasoning: string;
  seoTitle: string;
  seoDescription: string;
  priceMin: number;
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
  details?: string;               // Texto libre para identificar mejor el producto
}

export type CaptureSessionStatus =
  | 'waiting_for_mobile' | 'mobile_connected' | 'photo_uploaded' | 'analyzing' | 'completed' | 'error';

export interface MobileCaptureSession {
  sessionId: string;
  userId: TeamMemberId;
  status: CaptureSessionStatus;
  photoDataUrl?: string;
  resultItem?: InventoryItem;
  busyReason?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CaptureSessionCreated { sessionId: string; mobileUrl: string; lanIps: string[] }
export interface CaptureSessionUpdate {                                     // PUT /api/capture-session/{id}
  status: CaptureSessionStatus;
  photoDataUrl?: string;          // data:image/... comprimida en el móvil (<= 800 px, JPEG 0.75)
  busyReason?: string | null;     // Motivo por el que el PC no admite otra foto ahora mismo
}

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

export interface WeatherForecast {
  city: string;
  currentTempC: number;
  condition: 'sunny' | 'cloudy' | 'rainy' | 'windy';
  conditionText: string;
  recommendIndoor: boolean;
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
  matchReason: string;
  affordableWith: 'inventory_gain' | 'single_item_sale' | 'total_inventory';
}

export interface CalendarEvent {
  id: string;
  userId: TeamMemberId;
  title: string;
  date: string;
  time: string;
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

export type VisionProviderSource = 'ollama_local' | 'gemini' | 'openai' | 'deterministic_fallback';

export interface VisionDynamicField {
  key: string; label: string; value: string;
  fieldType: 'text' | 'select' | 'number'; options?: string[]; placeholder?: string;
}

export interface VisionAnalyzeRequest {
  photoDataUrl: string;
  userHint?: string;
}

export interface VisionAnalysisResult {
  name: string;
  category: string;
  brand: string;
  model: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
  conditionReasoning: string;
  seoTitle: string;
  seoDescription: string;
  dynamicFields?: VisionDynamicField[];
  source?: VisionProviderSource;
  latencyMs?: number;
  modelUsed?: string;
}

export type VisionAnalysis = VisionAnalysisResult;

export interface ValuationRequest {
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

export type ValuationResult = MarketValuationResult;

export interface InventoryTotals {
  totalMin: number;
  totalAvg: number;
  totalMax: number;
  dailyGainEur: number;
  itemCount: number;
}

export interface MarketRefreshResponse {
  updatedItems: InventoryItem[];
  newNotifications: MarketNotification[];
  totals: InventoryTotals;
  refreshedAt: string;
}

export interface AppStoreState {
  profiles: Record<TeamMemberId, UserProfile>;
  inventory: InventoryItem[];
  captureSessions: Record<string, MobileCaptureSession>;
  notifications: MarketNotification[];
  calendarEvents: CalendarEvent[];
  lastUpdatedAt: string;
}

// ---------- Sesión e inventario de la web (MOD-00 / MOD-01, Track de Matías) ----------
// GET /api/inventory (usuario del token de Firebase; items: más recientes primero)
export interface InventoryResponse { profile: UserProfile; items: InventoryItem[]; totals: InventoryTotals }
