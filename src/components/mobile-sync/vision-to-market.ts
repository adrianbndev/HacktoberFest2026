/**
 * Pure mapping from the vision result to the deep market-analysis request.
 *
 * Vision often reports placeholder brand/model values ("Genérica", "Sin marca",
 * a model identical to the product name…). Sending those to `/analyze` pollutes
 * the relevance filter, so they are omitted before the request is built.
 *
 * Kept dependency-free on purpose: it is imported by the capture hook and
 * covered by a hermetic `node --test` suite.
 */

import type { MarketAnalysisRequest } from "@/types/market-analysis";
import type { MarketPlatform, VisionAnalysisResult } from "@/types/sdd";

/** Sources requested by the mobile capture flow, in display order. */
export const MARKET_ANALYSIS_SOURCES = ["ebay", "wallapop", "milanuncios"] as const satisfies readonly MarketPlatform[];

const GENERIC_BRAND_MODEL = new Set([
  "sin marca",
  "genérica",
  "generica",
  "n/a",
  "-",
  "unknown",
  "no aplica",
]);

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function isGeneric(value: string | undefined | null): boolean {
  return !value || !value.trim() || GENERIC_BRAND_MODEL.has(normalize(value));
}

/**
 * Build the `/api/market/analyze` payload from a (possibly user-edited) vision
 * result. `description` carries the generated SEO copy; brand/model are omitted
 * when they are placeholders or the model merely repeats the name.
 */
export function visionToMarketAnalysis(vision: VisionAnalysisResult): MarketAnalysisRequest {
  const name = vision.name.trim();
  const brand = isGeneric(vision.brand) ? undefined : vision.brand.trim();
  const rawModel = vision.model?.trim();
  const model =
    rawModel && !isGeneric(rawModel) && normalize(rawModel) !== normalize(name)
      ? rawModel
      : undefined;
  const description = vision.seoDescription?.trim();

  return {
    name,
    category: vision.category.trim(),
    conditionScore: vision.conditionScore,
    conditionLabel: vision.conditionLabel,
    sources: [...MARKET_ANALYSIS_SOURCES],
    includeRecommendation: true,
    ...(description ? { description } : {}),
    ...(brand ? { brand } : {}),
    ...(model ? { model } : {}),
  };
}
