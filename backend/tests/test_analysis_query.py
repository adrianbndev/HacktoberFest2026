"""Generic brand/model cleanup for `/analyze` (never applied to `/valuate`)."""

from __future__ import annotations

import pytest
from app.mcp.analysis_query import (
    build_analysis_query,
    build_relevance_query,
    clean_brand,
    clean_model,
    normalize_query,
)


def test_analysis_query_comes_from_the_name_only() -> None:
    assert build_analysis_query("Silla de madera") == "Silla madera"
    assert build_analysis_query("Nintendo Switch OLED 64GB Blanca") == (
        "Nintendo Switch OLED 64GB Blanca"
    )


@pytest.mark.parametrize(
    "value",
    ["Sin marca", "sin  marca", "Genérica", "GENERICA", "N/A", "na", "-", "unknown", "No aplica"],
)
def test_generic_brands_are_treated_as_absent(value: str) -> None:
    assert clean_brand(value) is None


@pytest.mark.parametrize("value", ["Apple", "Nintendo", "IKEA", "  Bosch  "])
def test_real_brands_are_kept_and_trimmed(value: str) -> None:
    assert clean_brand(value) == value.strip()


@pytest.mark.parametrize("value", ["Genérico", "generica", "N/A", "-", "   "])
def test_generic_models_are_treated_as_absent(value: str) -> None:
    assert clean_model(value, name="Silla de madera") is None


def test_model_that_repeats_the_name_is_treated_as_absent() -> None:
    assert clean_model("Silla de madera", name="Silla de madera") is None
    assert clean_model("silla de  MADERA", name="Silla de madera") is None
    assert clean_model("Switch OLED", name="Nintendo Switch OLED") == "Switch OLED"


def test_relevance_query_skips_generic_identity_and_falls_back_to_the_name() -> None:
    assert build_relevance_query("Silla de madera", "Sin marca", "Silla de madera") == (
        "Silla madera"
    )
    assert build_relevance_query("iPhone 13 128GB", "Apple", "iPhone 13") == (
        "Apple iPhone 13"
    )
    assert build_relevance_query("iPhone 13 128GB", "Generica", "N/A") == "iPhone 13 128GB"
    assert build_relevance_query("iPhone 13", "Apple", "iPhone 13") == "iPhone 13"


def test_valuate_normalisation_is_untouched() -> None:
    # Regression guard: generic cleanup lives only in the analysis helpers.
    assert normalize_query("Silla de madera", brand="Sin marca", model="Silla de madera") == (
        "marca Silla madera"
    )
