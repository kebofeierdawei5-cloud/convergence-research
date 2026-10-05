from __future__ import annotations

import pytest

from iios_mvp.semantic_expectation_gap import (
    ComparisonDirection,
    ExpectationGapStatus,
    evaluate_expectation_gap,
)


def _independent(**overrides):
    value = {
        "variable_id": "eps_cagr",
        "value": "0.20",
        "unit": "ratio",
        "basis": "2026A_to_2029E",
        "horizon_years": "3",
    }
    value.update(overrides)
    return value


def _market(**overrides):
    value = {
        "resolution_state": "UNIQUE_MODEL",
        "qualification": "DECISION_GRADE",
        "variable_id": "eps_cagr",
        "value": "0.15",
        "unit": "ratio",
        "basis": "2026A_to_2029E",
        "horizon_years": "3",
    }
    value.update(overrides)
    return value


def test_compatible_expectations_produce_gap():
    result = evaluate_expectation_gap(
        independent_expectation=_independent(),
        market_expectation=_market(),
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER.value,
    )
    assert result["status"] == ExpectationGapStatus.PASS.value
    assert result["gap_absolute"] == pytest.approx(0.05)
    assert result["gap_relative"] == pytest.approx(1 / 3)


@pytest.mark.parametrize("field,value", [
    ("variable_id", "revenue_cagr"),
    ("unit", "CNY/share"),
    ("basis", "2027E_to_2029E"),
    ("horizon_years", "2"),
])
def test_incompatible_semantics_never_force_a_gap(field, value):
    market = _market(**{field: value})
    result = evaluate_expectation_gap(
        independent_expectation=_independent(),
        market_expectation=market,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER.value,
    )
    assert result["status"] == ExpectationGapStatus.INCOMPATIBLE.value
    assert result["gap_absolute"] is None


def test_ambiguous_mie_fails_closed():
    result = evaluate_expectation_gap(
        independent_expectation=_independent(),
        market_expectation=_market(resolution_state="AMBIGUOUS"),
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER.value,
    )
    assert result["status"] == ExpectationGapStatus.AMBIGUOUS.value
    assert result["gap_absolute"] is None


def test_blocked_mie_fails_closed():
    result = evaluate_expectation_gap(
        independent_expectation=_independent(),
        market_expectation=_market(qualification="BLOCKED", resolution_state="INSUFFICIENT_EVIDENCE"),
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER.value,
    )
    assert result["status"] == ExpectationGapStatus.BLOCKED.value
    assert result["gap_absolute"] is None


def test_lower_is_better_reverses_gap_direction():
    result = evaluate_expectation_gap(
        independent_expectation=_independent(value="0.10"),
        market_expectation=_market(value="0.15"),
        comparison_direction=ComparisonDirection.LOWER_IS_BETTER.value,
    )
    assert result["status"] == ExpectationGapStatus.PASS.value
    assert result["gap_absolute"] == pytest.approx(0.05)


def test_zero_market_requirement_is_rejected_for_relative_gap():
    with pytest.raises(ValueError, match="cannot be zero"):
        evaluate_expectation_gap(
            independent_expectation=_independent(value="0.10"),
            market_expectation=_market(value="0"),
            comparison_direction=ComparisonDirection.HIGHER_IS_BETTER.value,
        )
