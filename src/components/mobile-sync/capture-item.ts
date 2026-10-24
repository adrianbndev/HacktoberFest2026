"use client";

import type { MarketAnalysisResult, MarketSourceResult } from "@/types/market-analysis";
import type { InventoryItem, TeamMemberId, VisionAnalysisResult } from "@/types/sdd";

/** Reemplaza el resultado de una fuente o lo añade, conservando el orden de llegada. */
export function upsertSourceResult(results: MarketSourceResult[], next: MarketSourceResult): MarketSourceResult[] {
  const index = results.findIndex((result) => result.source === next.source);
  if (index === -1) return [...results, next];
  const updated = [...results];
  updated[index] = next;
  return updated;
}

/** Producto del inventario a partir de la visión ya revisada y del análisis de mercado. */
export function buildInventoryItem(
  userId: TeamMemberId,
  photoUrl: string,
  vision: VisionAnalysisResult,
  analysis: MarketAnalysisResult,
  details?: string,
): InventoryItem {
  const now = new Date().toISOString();
  const { priceMin, priceAvg, priceMax, sampleSize, platforms } = analysis.valuation;
  return {
    id: `item-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
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
