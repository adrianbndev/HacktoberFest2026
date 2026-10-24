import assert from "node:assert/strict";
import { test } from "node:test";

import { mergeSourceResults, sourcesFromError } from "./market-error.ts";

test("maps every known source reason to its status", () => {
  const rows = sourcesFromError({
    ebay: "blocked_http_403",
    wallapop: "timeout",
    milanuncios: "no_listings_parsed",
    vinted: "browser_unavailable",
  });

  assert.deepEqual(
    rows.map((row) => [row.source, row.status, row.error]),
    [
      ["ebay", "blocked", "blocked_http_403"],
      ["wallapop", "timeout", "timeout"],
      ["milanuncios", "no_listings", "no_listings_parsed"],
      ["vinted", "error", "browser_unavailable"],
    ],
  );
});

test("mapped rows never carry synthetic listings", () => {
  const [row] = sourcesFromError({ ebay: "blocked_http_403" });
  assert.deepEqual(row, {
    source: "ebay",
    status: "blocked",
    sampleSize: 0,
    listings: [],
    latencyMs: 0,
    error: "blocked_http_403",
  });
});

test("filters unknown source keys and keeps the known ones", () => {
  const rows = sourcesFromError({ amazon: "blocked", ebay: "timeout" });
  assert.deepEqual(rows.map((row) => row.source), ["ebay"]);
});

test("treats any other reason as a generic error", () => {
  const rows = sourcesFromError({ wallapop: "network_error", ebay: "  " });
  assert.deepEqual(rows.map((row) => row.status), ["error", "error"]);
});

test("returns no rows when the payload has no source detail", () => {
  assert.deepEqual(sourcesFromError(undefined), []);
  assert.deepEqual(sourcesFromError({}), []);
});

function source(overrides) {
  return {
    source: "ebay",
    status: "ok",
    sampleSize: 3,
    listings: [],
    latencyMs: 120,
    ...overrides,
  };
}

test("merge keeps partial results and appends only missing error rows", () => {
  const partial = source({ source: "wallapop", status: "ok", sampleSize: 4 });
  const merged = mergeSourceResults(
    [partial],
    sourcesFromError({ ebay: "blocked_http_403", wallapop: "timeout" }),
  );

  assert.deepEqual(merged.map((row) => row.source), ["wallapop", "ebay"]);
  assert.equal(merged[0], partial, "a received result must not be overwritten");
  assert.equal(merged[1].status, "blocked");
});

test("merge returns the incoming rows when there are no partial results", () => {
  const merged = mergeSourceResults([], sourcesFromError({ milanuncios: "timeout" }));
  assert.deepEqual(merged.map((row) => row.source), ["milanuncios"]);
});

test("merge does not duplicate a source repeated in the incoming rows", () => {
  const incoming = sourcesFromError({ ebay: "timeout" });
  const merged = mergeSourceResults([], [...incoming, ...incoming]);
  assert.equal(merged.length, 1);
});
