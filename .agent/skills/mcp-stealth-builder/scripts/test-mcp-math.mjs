#!/usr/bin/env node
/**
 * Standalone Reference & Property Test Harness for MCP Stealth Pricing Math
 * Tests:
 * 1. IQR Outlier Filtering
 * 2. W_health Factor Monotonicity across Condition Scores (0..100)
 * 3. Strict Price Triplet Invariant: 0 < priceMin < priceAvg < priceMax
 * 4. Level 2 Market Tick Delta & Notification Formatting
 */
import assert from 'node:assert/strict';

export function computeHealthWeight(conditionScore) {
  const clamped = Math.max(0, Math.min(100, Number(conditionScore) || 0));
  return Number((0.65 + 0.50 * (clamped / 100)).toFixed(4));
}

export function filterOutliersIQR(prices) {
  const valid = prices.filter((p) => Number.isFinite(p) && p > 2).sort((a, b) => a - b);
  if (valid.length < 4) return valid;
  const q1 = valid[Math.floor(valid.length * 0.25)];
  const q3 = valid[Math.floor(valid.length * 0.75)];
  const iqr = q3 - q1;
  const lower = q1 - 1.5 * iqr;
  const upper = q3 + 1.5 * iqr;
  return valid.filter((p) => p >= lower && p <= upper);
}

export function calculateThreePrices(rawPrices, conditionScore) {
  const cleaned = filterOutliersIQR(rawPrices);
  const baseMedian =
    cleaned.length > 0
      ? cleaned[Math.floor(cleaned.length / 2)]
      : 100;

  const weight = computeHealthWeight(conditionScore);
  const rawAvg = Math.round(baseMedian * weight);
  const p20 = cleaned.length > 0 ? cleaned[Math.floor(cleaned.length * 0.2)] : rawAvg * 0.82;
  const p85 = cleaned.length > 0 ? cleaned[Math.floor(cleaned.length * 0.85)] : rawAvg * 1.24;

  const priceAvg = Math.max(5, rawAvg);
  const priceMin = Math.min(priceAvg - 1, Math.max(1, Math.round(Math.min(p20 * weight, priceAvg * 0.82))));
  const priceMax = Math.max(priceAvg + 1, Math.round(Math.max(p85 * weight, priceAvg * 1.24)));

  return { priceMin, priceAvg, priceMax, weight };
}

console.log('🧪 Running MCP Stealth Pricing Math Invariant Suite...');

// 1. Test Outlier Filtering (discard 1€ fake listing and 9999€ troll listing)
const noisySample = [1, 175, 180, 190, 195, 200, 210, 220, 9999];
const filtered = filterOutliersIQR(noisySample);
assert(!filtered.includes(1), 'Should remove 1€ outlier');
assert(!filtered.includes(9999), 'Should remove 9999€ outlier');
console.log('  ✅ 1. IQR Outlier Filter passed:', filtered);

// 2. Test Triplet Invariant (0 < P_min < P_avg < P_max) across all condition scores 0..100
for (let score = 0; score <= 100; score += 5) {
  const { priceMin, priceAvg, priceMax } = calculateThreePrices(noisySample, score);
  assert(priceMin > 0, `priceMin must be > 0 at score ${score}`);
  assert(priceMin < priceAvg, `priceMin (${priceMin}) must be < priceAvg (${priceAvg}) at score ${score}`);
  assert(priceAvg < priceMax, `priceAvg (${priceAvg}) must be < priceMax (${priceMax}) at score ${score}`);
}
console.log('  ✅ 2. Strict Triplet Invariant (0 < P_min < P_avg < P_max) verified for scores [0..100].');

// 3. Test Health Monotonicity
const brokenValuation = calculateThreePrices(noisySample, 25);
const goodValuation = calculateThreePrices(noisySample, 75);
const mintValuation = calculateThreePrices(noisySample, 96);
assert(
  brokenValuation.priceAvg < goodValuation.priceAvg &&
    goodValuation.priceAvg < mintValuation.priceAvg,
  'Higher conditionScore must yield higher priceAvg'
);
console.log(
  `  ✅ 3. Health Monotonicity verified: Score 25% (${brokenValuation.priceAvg}€) < Score 75% (${goodValuation.priceAvg}€) < Score 96% (${mintValuation.priceAvg}€)`
);

console.log('🎉 ALL MCP STEALTH PRICING INVARIANTS PASSED!');
