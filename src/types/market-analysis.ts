/**
 * Phase 2 deep market analysis contract (additive).
 *
 * Mirrors `backend/app/models/market_analysis.py`. It deliberately lives in its
 * own file: `src/types/sdd.ts` is the frozen Track A contract and must not be
 * edited by Track C.
 */

import type { ConditionLabel, MarketListingSample, MarketPlatform } from "./sdd";

export interface MarketAnalysisLocation {
  lat: number;
  lng: number;
}

export interface MarketAnalysisRequest {
  name: string;
  description?: string;
  category: string;
  brand?: string;
  model?: string;
  conditionScore: number;
  conditionLabel: ConditionLabel;
  location?: MarketAnalysisLocation;
  /** Defaults to `["ebay", "wallapop", "milanuncios"]` on the server. */
  sources?: MarketPlatform[];
  /** Defaults to `true` on the server. */
  includeRecommendation?: boolean;
}

export type MarketSourceStatus = "ok" | "blocked" | "timeout" | "no_listings" | "error";

export interface MarketSourceResult {
  source: MarketPlatform;
  status: MarketSourceStatus;
  sampleSize: number;
  listings: MarketListingSample[];
  latencyMs: number;
  error?: string;
}

export interface MarketAnalysisValuation {
  priceMin: number;
  priceAvg: number;
  priceMax: number;
  sampleSize: number;
  platforms: MarketPlatform[];
  confidence: number;
}

export interface MarketAnalysisRecommendation {
  summary: string;
  suggestedPrice: number;
  bullets: string[];
  risks: string[];
  negotiationMarginEur: number;
}

export interface MarketAnalysisResult {
  query: string;
  sources: MarketSourceResult[];
  valuation: MarketAnalysisValuation;
  comparableListings: MarketListingSample[];
  recommendation?: MarketAnalysisRecommendation;
  warnings: string[];
  cached: boolean;
  analyzedAt: string;
}

export interface AnalysisStartedEvent {
  query: string;
  sources: MarketPlatform[];
  cached: boolean;
}

export interface SourceStartedEvent {
  source: MarketPlatform;
}

export interface AnalysisErrorEvent {
  detail: string;
  sources?: Record<string, string>;
}

export type MarketAnalysisEventName =
  | "analysis_started"
  | "source_started"
  | "source_result"
  | "valuation"
  | "recommendation"
  | "done"
  | "error";

export type MarketAnalysisEvent =
  | { type: "analysis_started"; data: AnalysisStartedEvent }
  | { type: "source_started"; data: SourceStartedEvent }
  | { type: "source_result"; data: MarketSourceResult }
  | { type: "valuation"; data: MarketAnalysisValuation }
  | { type: "recommendation"; data: MarketAnalysisRecommendation }
  | { type: "done"; data: MarketAnalysisResult }
  | { type: "error"; data: AnalysisErrorEvent };
