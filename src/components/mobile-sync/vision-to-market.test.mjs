import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MARKET_ANALYSIS_SOURCES,
  visionToMarketAnalysis,
} from "./vision-to-market.ts";

function vision(overrides = {}) {
  return {
    name: "iPhone 13 128GB",
    category: "Móviles",
    brand: "Apple",
    model: "iPhone 13",
    conditionScore: 82,
    conditionLabel: "Como nuevo",
    conditionReasoning: "Sin arañazos visibles",
    seoTitle: "iPhone 13 128GB como nuevo",
    seoDescription: "iPhone 13 128GB en muy buen estado, batería al 91%.",
    ...overrides,
  };
}

test("maps vision fields to the analyze request", () => {
  assert.deepEqual(visionToMarketAnalysis(vision()), {
    name: "iPhone 13 128GB",
    category: "Móviles",
    conditionScore: 82,
    conditionLabel: "Como nuevo",
    description: "iPhone 13 128GB en muy buen estado, batería al 91%.",
    brand: "Apple",
    model: "iPhone 13",
    sources: ["ebay", "wallapop", "milanuncios"],
    includeRecommendation: true,
  });
});

test("always requests the three deep sources in display order", () => {
  assert.deepEqual(MARKET_ANALYSIS_SOURCES, ["ebay", "wallapop", "milanuncios"]);
  assert.deepEqual(visionToMarketAnalysis(vision()).sources, ["ebay", "wallapop", "milanuncios"]);
});

test("omits placeholder brands and models", () => {
  for (const placeholder of ["Sin marca", "Genérica", "N/A", "-", "Unknown", "No aplica", "  ", ""]) {
    const request = visionToMarketAnalysis(vision({ brand: placeholder, model: placeholder }));
    assert.equal("brand" in request, false, `brand should be omitted for ${JSON.stringify(placeholder)}`);
    assert.equal("model" in request, false, `model should be omitted for ${JSON.stringify(placeholder)}`);
  }
});

test("omits a model that merely repeats the product name", () => {
  for (const model of ["iPhone 13 128GB", " iphone 13 128gb ", "IPHONE 13 128GB"]) {
    const request = visionToMarketAnalysis(vision({ model }));
    assert.equal("model" in request, false, `model should be omitted for ${JSON.stringify(model)}`);
  }
});

test("keeps a real model even when it shares words with the name", () => {
  const request = visionToMarketAnalysis(vision({ name: "Apple iPhone 13", model: "iPhone 13" }));
  assert.equal(request.model, "iPhone 13");
});

test("omits blank description instead of sending an empty string", () => {
  const request = visionToMarketAnalysis(vision({ seoDescription: "   " }));
  assert.equal("description" in request, false);
});

test("trims free-text fields", () => {
  const request = visionToMarketAnalysis(
    vision({ name: "  Silla de madera  ", category: " Mobiliario ", brand: " Ikea ", model: " Poäng " }),
  );
  assert.equal(request.name, "Silla de madera");
  assert.equal(request.category, "Mobiliario");
  assert.equal(request.brand, "Ikea");
  assert.equal(request.model, "Poäng");
});
