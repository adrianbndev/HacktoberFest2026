/**
 * Pure mapping from a failed `/api/market/analyze` payload to per-source rows.
 *
 * A `503` all-blocked response still carries `sources: { <platform>: <reason> }`
 * (docs/market-analysis.md §503 body). Without this mapping the UI cannot tell
 * "still running" from "finished with an error" and leaves every row spinning.
 *
 * Kept dependency-free (types only) so it can be covered by `node --test`.
 */

import type { MarketSourceResult, MarketSourceStatus } from "@/types/market-analysis";
import type { MarketPlatform } from "@/types/sdd";

/** Sources that may appear in an error payload, mirroring the backend contract. */
const ERROR_SOURCE_KEYS: readonly MarketPlatform[] = ["ebay", "wallapop", "milanuncios", "vinted"];

function isSourceKey(value: string): value is MarketPlatform {
  return ERROR_SOURCE_KEYS.some((source) => source === value);
}

function statusFromReason(reason: string): MarketSourceStatus {
  const normalized = reason.trim().toLowerCase();
  if (normalized.startsWith("blocked")) return "blocked";
  if (normalized === "timeout") return "timeout";
  if (normalized.startsWith("no_listings")) return "no_listings";
  return "error";
}

/**
 * Map the optional `sources` map of a `MarketAnalysisError` to source results.
 * Unknown keys are ignored, and every mapped row has no listings by definition.
 */
export function sourcesFromError(reasons?: Record<string, string>): MarketSourceResult[] {
  if (!reasons) return [];
  return Object.entries(reasons)
    .filter(([source]) => isSourceKey(source))
    .map(([source, reason]) => ({
      source: source as MarketPlatform,
      status: statusFromReason(reason),
      sampleSize: 0,
      listings: [],
      latencyMs: 0,
      error: reason,
    }));
}

/**
 * Add error rows for sources that never sent a `source_result`, preserving the
 * partial results already received. A real result always wins over an error.
 */
export function mergeSourceResults(
  current: MarketSourceResult[],
  incoming: MarketSourceResult[],
): MarketSourceResult[] {
  const known = new Set(current.map((result) => result.source));
  const merged = [...current];
  for (const result of incoming) {
    if (known.has(result.source)) continue;
    known.add(result.source);
    merged.push(result);
  }
  return merged;
}
