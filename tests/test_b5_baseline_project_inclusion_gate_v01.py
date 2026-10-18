from __future__ import annotations

from iios_mvp.local_investment_pilot_v01 import _build_valuation_model_consistency


def _evaluate(
    *,
    selected_family: str = "EPS_MULTIPLE",
    calculated_family: str = "EPS_MULTIPLE",
    model_name: str = "Synthetic EPS x PE",
    rationale: str = "Explicit EPS and multiple valuation basis for a regression fixture.",
    scope: str = "PROJECT_INCREMENTAL",
    transmission_status: str = "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
    baseline_includes_project: bool | None = True,
) -> dict:
    return _build_valuation_model_consistency(
        operator_model_family=selected_family,
        forecast_model_family=calculated_family,
        model_name=model_name,
        model_rationale=rationale,
        operating_driver_forecast={"scope": scope},
        valuation_transmission={
            "status": transmission_status,
            "baseline_includes_project": baseline_includes_project,
        },
    )


def test_confirmed_project_in_baseline_keeps_primary_model_eligible_when_b5_counterfactual_is_incomplete() -> None:
    result = _evaluate(
        scope="PROJECT_INCREMENTAL",
        transmission_status="NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
        baseline_includes_project=True,
    )

    assert result["primary_model_price_calculation_eligible"] is True
    assert result["scenario_values_role"] == "PRIMARY_MODEL"
    assert result["status"] == "MATCH_BASELINE_PROJECT_INCLUDED_B5_DIAGNOSTIC_ONLY"
    assert "B5_NOT_APPLIED_BASELINE_CONFIRMED_PROJECT_INCLUDED" in result["issues"]


def test_unconfirmed_project_baseline_still_fails_closed_when_b5_is_incomplete() -> None:
    result = _evaluate(
        scope="PROJECT_INCREMENTAL",
        transmission_status="NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
        baseline_includes_project=None,
    )

    assert result["primary_model_price_calculation_eligible"] is False
    assert result["status"] == "OPERATING_SCOPE_OR_B5_TRANSMISSION_NOT_RESOLVED"
    assert "B5_TRANSMISSION_NOT_ACCEPTED_OUTSIDE_EXPLICIT_COMPANY_WIDE_SCOPE" in result["issues"]


def test_primary_model_identity_mismatch_still_blocks_even_when_project_is_in_baseline() -> None:
    result = _evaluate(
        selected_family="EPS_MULTIPLE",
        calculated_family="FCF_DCF",
        model_name="Discounted Cash Flow DCF",
        scope="PROJECT_INCREMENTAL",
        transmission_status="NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
        baseline_includes_project=True,
    )

    assert result["primary_model_price_calculation_eligible"] is False
    assert result["status"] == "MODEL_FAMILY_MISMATCH"
