import assert from "node:assert/strict";
import { test } from "node:test";

import { buildMarketRows } from "./market-rows.ts";
import { MARKET_ANALYSIS_SOURCES } from "./vision-to-market.ts";

function result(overrides = {}) {
  return {
    source: "ebay",
    status: "ok",
    sampleSize: 3,
    listings: [],
    latencyMs: 100,
    ...overrides,
  };
}

test("keeps a spinner for sources still running before any error", () => {
  const rows = buildMarketRows([], false);
  assert.deepEqual(rows.map((row) => row.status), ["pending", "pending", "pending"]);
});

test("never leaves a spinner once the analysis failed", () => {
  const rows = buildMarketRows([], true);
  assert.deepEqual(rows.map((row) => row.status), ["not_run", "not_run", "not_run"]);
});

test("keeps partial results and marks only the missing sources as not run", () => {
  const rows = buildMarketRows([result({ source: "wallapop", status: "blocked" })], true);
  assert.deepEqual(
    rows.map((row) => [row.source, row.status]),
    [
      ["ebay", "not_run"],
      ["wallapop", "blocked"],
      ["milanuncios", "not_run"],
    ],
  );
});

test("appends unexpected sources after the requested three", () => {
  const rows = buildMarketRows([result({ source: "vinted", status: "error" })], true);
  assert.deepEqual(rows.map((row) => row.source), ["ebay", "wallapop", "milanuncios", "vinted"]);
  assert.equal(rows[3].status, "error");
});

test("keeps the same source order as the analyze request", () => {
  const rows = buildMarketRows([], false);
  assert.deepEqual(
    rows.map((row) => row.source),
    [...MARKET_ANALYSIS_SOURCES],
  );
});
