"""Contratos de dominio: espejo 1:1 de src/types/sdd.ts (.agent/architecture.md §2). Tipos base en base.py."""
from typing import Literal

from pydantic import Field

from app.models.base import (
    CamelModel, CaptureSessionStatus, ConditionLabel, ConditionScore, MarketPlatform, MetricChanged,
    NotificationType, PriceTriplet, TeamMemberId, WeatherCondition,
)


# ---------- 1. Usuario y perfil ----------
class UserProfile(CamelModel):
    id: TeamMemberId
    name: str
    role: str
    avatar_url: str
    city: str
    favorite_languages: list[str]
    created_at: str


# ---------- 2. Producto, salud IA y 3 precios MCP ----------
class PricePoint(PriceTriplet):
    timestamp: str
    sample_size: int
    platforms: list[MarketPlatform]


class MarketListingSample(CamelModel):
    title: str
    price: float
    platform: MarketPlatform
    condition: str
    url: str | None = None


class InventoryItem(PriceTriplet):
    id: str
    user_id: TeamMemberId
    photo_url: str
    name: str
    category: str
    brand: str
    model: str
    condition_score: ConditionScore
    condition_label: ConditionLabel
    condition_reasoning: str
    seo_title: str
    seo_description: str
    price_trend: Literal["up", "down", "stable"]
    price_delta_percent: float
    price_delta_eur: float
    price_history: list[PricePoint]
    comparable_listings: list[MarketListingSample]
    status: Literal["in_stock", "listed", "reserved", "sold"]
    created_at: str
    last_updated_at: str


# ---------- 3. Sincronización móvil <-> PC ----------
class MobileCaptureSession(CamelModel):
    session_id: str
    user_id: TeamMemberId
    status: CaptureSessionStatus
    photo_data_url: str | None = None
    result_item: InventoryItem | None = None
    created_at: str
    updated_at: str


# ---------- 4. Notificaciones de mercado ----------
class MarketNotification(CamelModel):
    id: str
    user_id: TeamMemberId
    item_id: str
    item_name: str
    type: NotificationType
    metric_changed: MetricChanged
    old_value: float
    new_value: float
    delta_percent: float
    message: str
    read: bool
    created_at: str


# ---------- 5. LifeOS: clima, planes, calendario y GitHub ----------
class DailyForecast(CamelModel):
    day: str
    temp_max_c: float
    temp_min_c: float
    condition: WeatherCondition


class WeatherForecast(CamelModel):
    city: str
    current_temp_c: float
    condition: WeatherCondition
    condition_text: str
    recommend_indoor: bool
    daily: list[DailyForecast]


class LocalPlan(CamelModel):
    id: str
    title: str
    category: Literal["gastronomia", "eventos", "aire_libre", "cultura"]
    estimated_cost_eur: float
    environment: Literal["indoor", "outdoor", "both"]
    location: str
    description: str
    match_reason: str
    affordable_with: Literal["inventory_gain", "single_item_sale", "total_inventory"]


class CalendarEvent(CamelModel):
    id: str
    user_id: TeamMemberId
    title: str
    date: str
    time: str
    type: Literal["personal", "wallapop_delivery", "local_plan", "hacktoberfest"]
    related_item_id: str | None = None
    location: str | None = None
    notes: str | None = None


class HacktoberfestRepo(CamelModel):
    id: str
    full_name: str
    url: str
    stars: int
    language: str
    open_hacktoberfest_issues: int
    labels: list[str]
    ai_architecture_summary: str
    ai_quick_start_guide: str


# ---------- 6. DTOs entre Tracks y estado global ----------
class VisionFollowUpQuestion(CamelModel):
    id: str
    question: str
    reason: str
    affects: Literal["identification", "condition"]
    options: list[str] = []


class VisionAnswer(CamelModel):
    question_id: str
    question: str
    answer: str


class VisionAnalyzeRequest(CamelModel):
    photo_data_url: str
    user_hint: str | None = None
    answers: list[VisionAnswer] = []


class VisionAnalysisResult(CamelModel):
    name: str
    category: str
    brand: str
    model: str
    condition_score: ConditionScore
    condition_label: ConditionLabel
    condition_reasoning: str
    seo_title: str
    seo_description: str
    confidence: float = Field(ge=0, le=1)
    follow_up_questions: list[VisionFollowUpQuestion] = []
    source: Literal["llm", "deterministic_fallback"] | None = None


class MarketValuationRequest(CamelModel):
    query: str
    brand: str | None = None
    model: str | None = None
    category: str
    condition_score: ConditionScore
    condition_label: ConditionLabel


class MarketValuationResult(PriceTriplet):
    sample_size: int
    platforms: list[MarketPlatform]
    comparable_listings: list[MarketListingSample]
    source: Literal["live_mcp", "stealth_fallback"]


class InventoryTotals(CamelModel):
    total_min: float
    total_avg: float
    total_max: float
    daily_gain_eur: float
    item_count: int


class MarketRefreshResponse(CamelModel):
    updated_items: list[InventoryItem]
    new_notifications: list[MarketNotification]
    totals: InventoryTotals
    refreshed_at: str


class AuthRequest(CamelModel):
    user_id: TeamMemberId


class AuthSession(CamelModel):
    active_user_id: TeamMemberId
    profiles: list[UserProfile]


class InventoryResponse(CamelModel):
    profile: UserProfile
    items: list[InventoryItem]
    totals: InventoryTotals


class AppStoreState(CamelModel):
    active_user_id: TeamMemberId
    profiles: dict[TeamMemberId, UserProfile]
    inventory: list[InventoryItem]
    capture_sessions: dict[str, MobileCaptureSession]
    notifications: list[MarketNotification]
    calendar_events: list[CalendarEvent]
    last_updated_at: str
