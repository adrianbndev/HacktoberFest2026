"use client";

import { requestJson } from "@/lib/api";
import { streamMarketAnalysis } from "@/lib/market-analysis";
import type {
  MarketAnalysisEvent,
  MarketAnalysisResult,
  MarketSourceResult,
} from "@/types/market-analysis";
import type {
  InventoryItem,
  MarketValuationResult,
  TeamMemberId,
  ValuationRequest,
  VisionAnalysisResult,
} from "@/types/sdd";
import { visionToMarketAnalysis } from "./vision-to-market";

/** Reemplaza el resultado de una fuente o lo añade, conservando el orden de llegada. */
export function upsertSourceResult(results: MarketSourceResult[], next: MarketSourceResult): MarketSourceResult[] {
  const index = results.findIndex((result) => result.source === next.source);
  if (index === -1) return [...results, next];
  const updated = [...results];
  updated[index] = next;
  return updated;
}

export function createInventoryItemId(): string {
  return `item-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

/** Producto provisional mientras se buscan los precios en segundo plano. */
export function buildPendingInventoryItem(
  userId: TeamMemberId,
  photoUrl: string,
  vision: VisionAnalysisResult,
  details?: string,
  id: string = createInventoryItemId(),
): InventoryItem {
  const now = new Date().toISOString();
  return {
    id,
    userId,
    photoUrl,
    name: vision.name,
    category: vision.category,
    brand: vision.brand,
    model: vision.model,
    conditionScore: vision.conditionScore,
    conditionLabel: vision.conditionLabel,
    conditionReasoning: vision.conditionReasoning,
    seoTitle: vision.seoTitle,
    seoDescription: vision.seoDescription,
    priceMin: 1,
    priceAvg: 2,
    priceMax: 3,
    priceTrend: "stable",
    priceDeltaPercent: 0,
    priceDeltaEur: 0,
    priceHistory: [],
    comparableListings: [],
    status: "in_stock",
    createdAt: now,
    lastUpdatedAt: now,
    details: details?.trim() || undefined,
  };
}

/** Producto del inventario a partir de la visión ya revisada y del análisis de mercado. */
export function buildInventoryItem(
  userId: TeamMemberId,
  photoUrl: string,
  vision: VisionAnalysisResult,
  analysis: MarketAnalysisResult,
  details?: string,
  id: string = createInventoryItemId(),
): InventoryItem {
  const now = new Date().toISOString();
  const { priceMin, priceAvg, priceMax, sampleSize, platforms } = analysis.valuation;
  return {
    id,
    userId,
    photoUrl,
    name: vision.name,
    category: vision.category,
    brand: vision.brand,
    model: vision.model,
    conditionScore: vision.conditionScore,
    conditionLabel: vision.conditionLabel,
    conditionReasoning: vision.conditionReasoning,
    seoTitle: vision.seoTitle,
    seoDescription: vision.seoDescription,
    priceMin,
    priceAvg,
    priceMax,
    priceTrend: "stable",
    priceDeltaPercent: 0,
    priceDeltaEur: 0,
    priceHistory: [{ timestamp: now, priceMin, priceAvg, priceMax, sampleSize, platforms }],
    comparableListings: analysis.comparableListings,
    status: "in_stock",
    createdAt: now,
    lastUpdatedAt: now,
    details: details?.trim() || undefined,
  };
}

/** Producto del inventario a partir del endpoint rápido /api/market/valuate (respaldo). */
export function buildInventoryItemFromValuation(
  userId: TeamMemberId,
  photoUrl: string,
  vision: VisionAnalysisResult,
  valuation: MarketValuationResult,
  details?: string,
  id: string = createInventoryItemId(),
): InventoryItem {
  const now = new Date().toISOString();
  const { priceMin, priceAvg, priceMax, sampleSize, platforms, comparableListings } = valuation;
  return {
    id,
    userId,
    photoUrl,
    name: vision.name,
    category: vision.category,
    brand: vision.brand,
    model: vision.model,
    conditionScore: vision.conditionScore,
    conditionLabel: vision.conditionLabel,
    conditionReasoning: vision.conditionReasoning,
    seoTitle: vision.seoTitle,
    seoDescription: vision.seoDescription,
    priceMin,
    priceAvg,
    priceMax,
    priceTrend: "stable",
    priceDeltaPercent: 0,
    priceDeltaEur: 0,
    priceHistory: [{ timestamp: now, priceMin, priceAvg, priceMax, sampleSize, platforms }],
    comparableListings,
    status: "in_stock",
    createdAt: now,
    lastUpdatedAt: now,
    details: details?.trim() || undefined,
  };
}

/** Ejecuta el análisis profundo SSE con respaldo automático a /api/market/valuate si falla el navegador. */
export async function runMarketValuationWithFallback(params: {
  userId: TeamMemberId;
  photoUrl: string;
  vision: VisionAnalysisResult;
  details: string;
  itemId: string;
  signal: AbortSignal;
  onEvent: (event: MarketAnalysisEvent) => void;
}): Promise<InventoryItem> {
  const { userId, photoUrl, vision, details, itemId, signal, onEvent } = params;
  try {
    const analysis = await streamMarketAnalysis(visionToMarketAnalysis(vision), { signal, onEvent });
    return buildInventoryItem(userId, photoUrl, vision, analysis, details, itemId);
  } catch (streamErr) {
    if (signal.aborted) throw streamErr;
    const fallbackReq: ValuationRequest = {
      query: vision.name,
      brand: vision.brand,
      model: vision.model,
      category: vision.category,
      conditionScore: vision.conditionScore,
      conditionLabel: vision.conditionLabel,
    };
    const valuation = await requestJson<MarketValuationResult>("/api/market/valuate", "POST", fallbackReq).catch(() => {
      throw streamErr;
    });
    return buildInventoryItemFromValuation(userId, photoUrl, vision, valuation, details, itemId);
  }
}
