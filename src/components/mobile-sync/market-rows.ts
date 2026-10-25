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

export interface MarketRowOptions {
  /** A failed analysis: nothing else is coming, so do not spin. */
  hasError?: boolean;
  /** A finished analysis: a source without a result simply found no listings. */
  complete?: boolean;
}

export function buildMarketRows(sources: MarketSourceResult[], options: MarketRowOptions = {}): MarketRow[] {
  const known = new Map(sources.map((source) => [source.source, source]));
  const missingStatus: MarketRowStatus = options.hasError
    ? "not_run"
    : options.complete
      ? "no_listings"
      : "pending";
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
