"""Pure pricing mathematics for the stealth market engine (MOD-04 §2, §3).

No network, no settings and no side effects: every function is deterministic
so it can be property-tested and reused by the fallback and the live engine.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

HEALTH_WEIGHT_INTERCEPT = 0.65
HEALTH_WEIGHT_SLOPE = 0.50
HEALTH_WEIGHT_SCORE_AT_PARITY = 70.0

IQR_MULTIPLIER = 1.5
MIN_VALID_PRICE_EUR = 1.0
MIN_AVERAGE_PRICE_EUR = 5
MIN_PRICE_FLOOR_EUR = 1

LIQUIDITY_DISCOUNT = 0.82
CEILING_PREMIUM = 1.24
LOW_PERCENTILE = 20.0
HIGH_PERCENTILE = 85.0


@dataclass(frozen=True, slots=True)
class PriceTriplet:
    """The three mandatory price metrics plus their derivation inputs."""

    price_min: int
    price_avg: int
    price_max: int
    base_price: float
    health_weight: float


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    if low > high:
        raise ValueError(f"invalid clamp range: low={low} > high={high}")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    return max(low, min(high, value))


def w_health(condition_score: float) -> float:
    """Health weight ``W = 0.65 + 0.50 * score / 100`` (score clamped 0..100)."""
    normalised = clamp(condition_score, 0.0, 100.0) / 100.0
    return HEALTH_WEIGHT_INTERCEPT + HEALTH_WEIGHT_SLOPE * normalised


def percentile(values: Sequence[float], pct: float) -> float:
    """Linear-interpolation percentile over an already unordered sample."""
    if not values:
        raise ValueError("cannot compute a percentile of an empty sample")
    if not 0.0 <= pct <= 100.0:
        raise ValueError(f"percentile must be in [0, 100], got {pct}")
    ordered = sorted(_finite(values))
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    if lower_index == upper_index:
        return ordered[lower_index]
    fraction = rank - lower_index
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


def filter_outliers_iqr(
    prices: Iterable[float], *, min_price: float = MIN_VALID_PRICE_EUR
) -> list[float]:
    """Drop non-finite/symbolic prices and IQR outliers, returning sorted values."""
    valid = sorted(price for price in _finite(prices) if price > min_price)
    if len(valid) < 4:
        return valid
    q1 = percentile(valid, 25.0)
    q3 = percentile(valid, 75.0)
    iqr = q3 - q1
    lower_fence = q1 - IQR_MULTIPLIER * iqr
    upper_fence = q3 + IQR_MULTIPLIER * iqr
    return [price for price in valid if lower_fence <= price <= upper_fence]


def compute_price_triplet(prices: Iterable[float], condition_score: float) -> PriceTriplet:
    """Compute ``P_min < P_avg < P_max`` exactly as specified in MOD-04 §2."""
    cleaned = filter_outliers_iqr(prices)
    if not cleaned:
        raise ValueError("cannot compute prices from an empty usable sample")

    base_price = statistics.median(cleaned)
    weight = w_health(condition_score)
    weighted_average = base_price * weight

    raw_min = min(percentile(cleaned, LOW_PERCENTILE), weighted_average * LIQUIDITY_DISCOUNT)
    raw_max = max(percentile(cleaned, HIGH_PERCENTILE), weighted_average * CEILING_PREMIUM)

    price_min, price_avg, price_max = enforce_price_triplet_invariant(
        raw_min, weighted_average, raw_max
    )
    return PriceTriplet(
        price_min=price_min,
        price_avg=price_avg,
        price_max=price_max,
        base_price=base_price,
        health_weight=weight,
    )


def enforce_price_triplet_invariant(
    p_min: float, p_avg: float, p_max: float
) -> tuple[int, int, int]:
    """Force ``0 < P_min < P_avg < P_max`` without ever returning 0 € or NaN."""
    safe_avg = max(MIN_AVERAGE_PRICE_EUR, _round_finite(p_avg))
    safe_min = min(safe_avg - 1, max(MIN_PRICE_FLOOR_EUR, _round_finite(p_min)))
    safe_max = max(safe_avg + 1, _round_finite(p_max))
    return safe_min, safe_avg, safe_max


def _round_finite(value: float) -> int:
    if not math.isfinite(value):
        raise ValueError("price inputs must be finite")
    return round(value)


def _finite(values: Iterable[float]) -> list[float]:
    return [float(value) for value in values if math.isfinite(value)]
