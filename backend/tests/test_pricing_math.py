"""Property and unit tests for the pure pricing mathematics (brief §7.2)."""

from __future__ import annotations

import pytest
from app.mcp.pricing_math import (
    clamp,
    compute_price_triplet,
    enforce_price_triplet_invariant,
    filter_outliers_iqr,
    percentile,
    w_health,
)
from hypothesis import given
from hypothesis import strategies as st

PRICE_LISTS = st.lists(
    st.floats(min_value=1.01, max_value=5000.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=60,
)
SCORES = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)


@given(prices=PRICE_LISTS, score=SCORES)
def test_triplet_invariant_always_holds(prices: list[float], score: float) -> None:
    triplet = compute_price_triplet(prices, score)

    assert triplet.price_min > 0
    assert triplet.price_min < triplet.price_avg < triplet.price_max
    assert isinstance(triplet.price_min, int)
    assert isinstance(triplet.price_avg, int)
    assert isinstance(triplet.price_max, int)


def test_invariant_holds_for_every_integer_score() -> None:
    sample = [120.0, 140.0, 150.0, 160.0, 175.0, 190.0, 210.0, 260.0]

    for score in range(101):
        triplet = compute_price_triplet(sample, score)
        assert 0 < triplet.price_min < triplet.price_avg < triplet.price_max


@given(prices=PRICE_LISTS, low=SCORES, high=SCORES)
def test_average_is_monotonic_non_decreasing_with_score(
    prices: list[float], low: float, high: float
) -> None:
    ordered_low, ordered_high = sorted((low, high))
    cheap = compute_price_triplet(prices, ordered_low)
    expensive = compute_price_triplet(prices, ordered_high)

    assert cheap.price_avg <= expensive.price_avg


def test_identical_prices_still_yield_a_strict_triplet() -> None:
    for score in range(101):
        triplet = compute_price_triplet([200.0] * 12, score)
        assert 0 < triplet.price_min < triplet.price_avg < triplet.price_max


def test_single_price_sample_is_safe() -> None:
    triplet = compute_price_triplet([2.0], 0)

    assert (triplet.price_min, triplet.price_avg, triplet.price_max) == (1, 5, 6)


def test_formula_is_exact_for_a_known_sample() -> None:
    triplet = compute_price_triplet([300.0] * 10, 80)

    assert triplet.health_weight == pytest.approx(1.05)
    assert triplet.base_price == pytest.approx(300.0)
    assert triplet.price_avg == 315
    assert triplet.price_min == 258
    assert triplet.price_max == 391


def test_computation_is_deterministic() -> None:
    sample = [99.0, 150.0, 175.0, 180.0, 210.0, 260.0, 400.0]

    assert compute_price_triplet(sample, 63) == compute_price_triplet(sample, 63)


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0, 0.65), (70, 1.0), (100, 1.15), (-20, 0.65), (140, 1.15)],
)
def test_health_weight_formula_and_clamping(score: float, expected: float) -> None:
    assert w_health(score) == pytest.approx(expected)


def test_clamp_rejects_bad_ranges_and_non_finite_values() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(50, 0, 10) == 10

    with pytest.raises(ValueError):
        clamp(1, 10, 0)
    with pytest.raises(ValueError):
        clamp(float("nan"), 0, 10)


def test_percentile_uses_linear_interpolation() -> None:
    assert percentile([50, 10, 20, 30, 40], 0) == 10
    assert percentile([50, 10, 20, 30, 40], 100) == 50
    assert percentile([10, 20, 30, 40, 50], 20) == pytest.approx(18.0)
    assert percentile([10, 20, 30, 40, 50], 85) == pytest.approx(44.0)


def test_percentile_rejects_empty_samples() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)


def test_iqr_filter_removes_symbolic_and_absurd_outliers() -> None:
    filtered = filter_outliers_iqr([1, 175, 180, 190, 195, 200, 210, 220, 9999])

    assert filtered == [175.0, 180.0, 190.0, 195.0, 200.0, 210.0, 220.0]


def test_iqr_filter_keeps_small_samples_and_drops_non_finite() -> None:
    assert filter_outliers_iqr([float("nan"), 10, 12, 0.5]) == [10.0, 12.0]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ((0, 0, 0), (1, 5, 6)),
        ((100, 120, 150), (100, 120, 150)),
        ((200, 120, 130), (119, 120, 130)),
        ((100, 120, 100), (100, 120, 121)),
        ((1, 1, 1), (1, 5, 6)),
    ],
)
def test_invariant_guard_repairs_invalid_triplets(
    raw: tuple[int, int, int], expected: tuple[int, int, int]
) -> None:
    assert enforce_price_triplet_invariant(*raw) == expected


def test_invariant_guard_rejects_non_finite_prices() -> None:
    with pytest.raises(ValueError):
        enforce_price_triplet_invariant(float("nan"), 100, 120)
    with pytest.raises(ValueError):
        enforce_price_triplet_invariant(100, 100, float("inf"))


def test_empty_sample_is_a_typed_error() -> None:
    with pytest.raises(ValueError):
        compute_price_triplet([], 80)
