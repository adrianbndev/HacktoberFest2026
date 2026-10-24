/**
 * Pure aggregates for the dashboard.
 *
 * A pending valuation is a placeholder `InventoryItem` whose prices are not
 * final yet. It must never contribute to a count or a sum: the views show a
 * skeleton instead, and these helpers keep it out of every aggregate.
 */

import type { InventoryItem, MarketPlatform } from "@/types/sdd";

const STATUS_ORDER = ["in_stock", "listed", "reserved", "sold"] as const satisfies readonly InventoryItem["status"][];
const PLATFORM_ORDER = ["wallapop", "vinted", "milanuncios", "ebay"] as const satisfies readonly MarketPlatform[];

export interface StatusTotal {
  status: InventoryItem["status"];
  count: number;
  value: number;
}

export interface PlatformTotal {
  platform: MarketPlatform;
  value: number;
}

/** Drop items that are still being valued; their placeholder prices are meaningless. */
export function settledItems(
  items: InventoryItem[],
  pendingValuations: Record<string, unknown>,
): InventoryItem[] {
  return items.filter((item) => !pendingValuations[item.id]);
}

/** Count and summed fair price per status, in display order. */
export function statusTotals(items: InventoryItem[]): StatusTotal[] {
  return STATUS_ORDER.map((status) => {
    let count = 0;
    let value = 0;
    for (const item of items) {
      if (item.status !== status) continue;
      count += 1;
      value += item.priceAvg;
    }
    return { status, count, value };
  });
}

// Same per-platform reference as `platformReferences()` in `format.ts`: average of
// the comparable listings of each item, then summed across owned items.
function referencePrice(item: InventoryItem, platform: MarketPlatform): number {
  let total = 0;
  let count = 0;
  for (const listing of item.comparableListings) {
    if (listing.platform !== platform) continue;
    total += listing.price;
    count += 1;
  }
  return count === 0 ? 0 : Math.round(total / count);
}

/** Summed reference value per platform for the inventory still owned (sold excluded). */
export function platformTotals(items: InventoryItem[]): PlatformTotal[] {
  const owned = items.filter((item) => item.status !== "sold");
  return PLATFORM_ORDER.map((platform) => ({
    platform,
    value: owned.reduce((sum, item) => sum + referencePrice(item, platform), 0),
  }))
    .filter(({ value }) => value > 0)
    .sort((a, b) => b.value - a.value);
}
