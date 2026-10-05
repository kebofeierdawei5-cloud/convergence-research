from decimal import Decimal

from iios_mvp.decision_kernel_v03 import (
    DECISION_KERNEL_POLICY_VERSION,
    DECISION_KERNEL_VERSION,
    evaluate_production_decision,
)


def _inputs(**overrides):
    values = dict(
        validation_pass=True,
        trust_status="PASS",
        thesis_status="INTACT",
        reality_status="PASS",
        quality_gate_status="PASS",
        value_driver_status="PASS",
        valuation_status="PASS",
        forecast_status="PASS",
        thesis_admission_status="ADMITTED",
        risk_status="PASS",
        portfolio_status="PASS",
        position_pct=Decimal("0"),
        gap_status="UNKNOWN",
        gap_positive=False,
        expected_annualized_return=Decimal("0.20"),
        return_gate_pass=True,
        risk_gate_pass=True,
        can_add=True,
        package_complete=True,
        return_metrics_ready=True,
        mie_policy="OPTIONAL_EXPLANATORY",
        mie_material_contradiction=False,
    )
    values.update(overrides)
    return values


def test_core04_missing_mie_can_produce_buy_when_independent_gates_pass():
    result = evaluate_production_decision(**_inputs())
    assert result["action"] == "BUY"
    assert result["new_capital_allowed"] is True
    assert result["investability_status"] == "INVESTABLE"
    assert result["mie_policy"] == "OPTIONAL_EXPLANATORY"


def test_core04_mie_unknown_cannot_create_buy_without_return_gate():
    result = evaluate_production_decision(
        **_inputs(return_gate_pass=False, expected_annualized_return=Decimal("0.10"))
    )
    assert result["action"] == "WATCH"
    assert result["new_capital_allowed"] is False


def test_core04_portfolio_block_precedes_company_value_for_new_capital():
    result = evaluate_production_decision(
        **_inputs(portfolio_status="BLOCKED")
    )
    assert result["action"] == "NO-BUY"
    assert result["precedence_rule_id"] == "NP11_PORTFOLIO_BLOCKED"


def test_core04_trust_failure_precedes_all_investment_actions():
    result = evaluate_production_decision(
        **_inputs(trust_status="FAIL", thesis_status="BROKEN")
    )
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "T00_TRUST_NOT_PASS"


def test_core04_versioned_identity_is_present():
    result = evaluate_production_decision(**_inputs())
    assert result["decision_kernel_version"] == DECISION_KERNEL_VERSION
    assert result["decision_policy_version"] == DECISION_KERNEL_POLICY_VERSION


def test_core04_quality_conditional_requires_review_even_when_returns_pass():
    result = evaluate_production_decision(
        **_inputs(quality_gate_status="CONDITIONAL")
    )
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["new_capital_allowed"] is False
    assert result["precedence_rule_id"] == "NP47_QUALITY_UNRESOLVED"


def test_core04_quality_blocked_denies_new_capital():
    result = evaluate_production_decision(
        **_inputs(quality_gate_status="BLOCKED")
    )
    assert result["action"] == "NO-BUY"
    assert result["new_capital_allowed"] is False
    assert result["precedence_rule_id"] == "NP46_QUALITY_HARD_FAIL"


def test_core04_thesis_admission_is_required_for_new_capital():
    result = evaluate_production_decision(
        **_inputs(thesis_admission_status="UNKNOWN")
    )
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["new_capital_allowed"] is False
    assert result["precedence_rule_id"] == "NP51_THESIS_ADMISSION_NOT_VALID"


def test_core04_quality_failure_reduces_existing_position_after_stronger_protection():
    result = evaluate_production_decision(
        **_inputs(
            position_pct=Decimal("5"),
            quality_gate_status="BLOCKED",
        )
    )
    assert result["action"] == "REDUCE"
    assert result["new_capital_allowed"] is False
    assert result["precedence_rule_id"] == "EP42_QUALITY_HARD_FAIL"


def test_core04_existing_broken_thesis_still_exits_before_quality_review():
    result = evaluate_production_decision(
        **_inputs(
            position_pct=Decimal("5"),
            thesis_status="BROKEN",
            quality_gate_status="BLOCKED",
        )
    )
    assert result["action"] == "EXIT"
    assert result["precedence_rule_id"] == "EP10_THESIS_BROKEN"
