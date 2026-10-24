import assert from "node:assert/strict";
import { test } from "node:test";

import { platformTotals, settledItems, statusTotals } from "./inventory-aggregates.ts";

function item(overrides = {}) {
  return {
    id: "item-a",
    userId: "user-1",
    photoUrl: "data:image/png;base64,AAAA",
    name: "iPhone 13",
    category: "Móviles",
    brand: "Apple",
    model: "iPhone 13",
    conditionScore: 80,
    conditionLabel: "Como nuevo",
    conditionReasoning: "Sin arañazos",
    seoTitle: "iPhone 13 como nuevo",
    seoDescription: "iPhone 13 en muy buen estado",
    priceMin: 280,
    priceAvg: 320,
    priceMax: 380,
    priceTrend: "stable",
    priceDeltaPercent: 0,
    priceDeltaEur: 0,
    priceHistory: [],
    comparableListings: [],
    status: "in_stock",
    createdAt: "2026-10-24T10:00:00.000Z",
    lastUpdatedAt: "2026-10-24T10:00:00.000Z",
    ...overrides,
  };
}

const pendingItem = item({ id: "pending-1", priceMin: 0, priceAvg: 0, priceMax: 0 });

test("settledItems removes every pending valuation", () => {
  const settled = settledItems([item(), pendingItem], { "pending-1": {} });
  assert.deepEqual(settled.map(({ id }) => id), ["item-a"]);
});

test("status totals never add the placeholder prices of a pending item", () => {
  const settled = settledItems([item({ priceAvg: 320 }), pendingItem], { "pending-1": {} });
  const inStock = statusTotals(settled).find(({ status }) => status === "in_stock");

  assert.deepEqual(inStock, { status: "in_stock", count: 1, value: 320 });
});

test("status totals count each status and sum its fair prices", () => {
  const totals = statusTotals([
    item({ id: "a", status: "in_stock", priceAvg: 100 }),
    item({ id: "b", status: "in_stock", priceAvg: 50 }),
    item({ id: "c", status: "sold", priceAvg: 70 }),
  ]);

  assert.deepEqual(
    totals.map(({ status, count, value }) => [status, count, value]),
    [
      ["in_stock", 2, 150],
      ["listed", 0, 0],
      ["reserved", 0, 0],
      ["sold", 1, 70],
    ],
  );
});

test("platform totals exclude pending valuations and sold items", () => {
  const listing = (platform, price) => ({ title: "x", price, platform, condition: "Buen estado", url: "https://example.com" });
  const totals = platformTotals(
    settledItems(
      [
        item({
          id: "a",
          status: "in_stock",
          comparableListings: [listing("wallapop", 100), listing("wallapop", 200), listing("ebay", 300)],
        }),
        item({
          id: "pending-1",
          comparableListings: [listing("wallapop", 999), listing("ebay", 999)],
        }),
        item({
          id: "sold-1",
          status: "sold",
          comparableListings: [listing("wallapop", 500)],
        }),
      ],
      { "pending-1": {} },
    ),
  );

  assert.deepEqual(totals, [
    { platform: "ebay", value: 300 },
    { platform: "wallapop", value: 150 },
  ]);
});
