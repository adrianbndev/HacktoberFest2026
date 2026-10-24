import assert from "node:assert/strict";
import { test } from "node:test";

import { sourcesFromError } from "./market-error.ts";

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
