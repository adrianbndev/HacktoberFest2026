/**
 * Pure row model for `MarketProgress`: the three requested sources in display
 * order plus any unexpected source returned by the API.
 *
 * After a failed analysis nothing else is coming, so a source without a result
 * must render as "Sin datos" instead of an endless spinner.
 */

import type { MarketSourceResult, MarketSourceStatus } from "@/types/market-analysis";
import type { MarketPlatform } from "@/types/sdd";

/** Display order of the requested sources; guarded by the row test against drift. */
const REQUESTED_SOURCES = ["ebay", "wallapop", "milanuncios"] as const satisfies readonly MarketPlatform[];

export type MarketRowStatus = MarketSourceStatus | "pending" | "not_run";

export interface MarketRow {
  source: MarketPlatform;
  status: MarketRowStatus;
  sampleSize: number;
}

export function buildMarketRows(sources: MarketSourceResult[], hasError: boolean): MarketRow[] {
  const known = new Map(sources.map((source) => [source.source, source]));
  const missingStatus: MarketRowStatus = hasError ? "not_run" : "pending";
  const rows: MarketRow[] = REQUESTED_SOURCES.map((source) => {
    const result = known.get(source);
    return result
      ? { source, status: result.status, sampleSize: result.sampleSize }
      : { source, status: missingStatus, sampleSize: 0 };
  });
  for (const result of sources) {
    if (!REQUESTED_SOURCES.some((source) => source === result.source)) {
      rows.push({ source: result.source, status: result.status, sampleSize: result.sampleSize });
    }
  }
  return rows;
}
