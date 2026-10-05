from decimal import Decimal

from iios_mvp.decision_state_machine_v01 import (
    CANONICAL_DECISION_PRECEDENCE,
    DECISION_PRECEDENCE_VERSION,
    DecisionStateInputs,
    decision_precedence_table,
    evaluate_decision_state,
)


def base(**overrides):
    values = dict(
        validation_pass=True,
        trust_status="PASS",
        thesis_status="INTACT",
        risk_status="PASS",
        portfolio_status="PASS",
        position_pct=Decimal("0"),
        gap_status="PASS",
        gap_positive=True,
        expected_annualized_return=Decimal("0.20"),
        return_gate_pass=True,
        risk_gate_pass=True,
        can_add=True,
        package_complete=True,
        return_metrics_ready=True,
    )
    values.update(overrides)
    return DecisionStateInputs(**values)


def test_precedence_table_is_unique_and_versioned():
    ids = [rule.rule_id for rule in CANONICAL_DECISION_PRECEDENCE]
    assert len(ids) == len(set(ids))
    assert DECISION_PRECEDENCE_VERSION == "IIOS-DECISION-PRECEDENCE-0.1"
    table = decision_precedence_table()
    assert [row["rule_id"] for row in table] == ids



def test_every_canonical_rule_has_executable_predicate():
    neutral = base()
    for rule in CANONICAL_DECISION_PRECEDENCE:
        # _matches is intentionally private: this is a structural invariant
        # ensuring the audit table and executable predicate map cannot drift.
        from iios_mvp.decision_state_machine_v01 import _matches
        result = _matches(rule, neutral)
        assert isinstance(result, bool), rule.rule_id

def test_validation_precedes_trust():
    result = evaluate_decision_state(
        base(validation_pass=False, trust_status="FAIL", thesis_status="BROKEN")
    )
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "V00_VALIDATION_UNRESOLVED"


def test_trust_precedes_all_actions():
    result = evaluate_decision_state(
        base(trust_status="FAIL", thesis_status="BROKEN", portfolio_status="BLOCKED", risk_status="FAIL")
    )
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "T00_TRUST_NOT_PASS"


def test_existing_broken_thesis_beats_portfolio_block():
    result = evaluate_decision_state(
        base(position_pct=Decimal("5"), thesis_status="BROKEN", portfolio_status="BLOCKED")
    )
    assert result["action"] == "EXIT"
    assert result["precedence_rule_id"] == "EP10_THESIS_BROKEN"


def test_existing_risk_failure_beats_portfolio_block():
    result = evaluate_decision_state(
        base(position_pct=Decimal("5"), portfolio_status="BLOCKED", risk_gate_pass=False)
    )
    assert result["action"] == "REDUCE"
    assert result["precedence_rule_id"] == "EP20_RISK_HARD_FAIL"


def test_existing_portfolio_block_reduces_when_thesis_and_risk_are_clear():
    result = evaluate_decision_state(
        base(position_pct=Decimal("5"), portfolio_status="BLOCKED")
    )
    assert result["action"] == "REDUCE"
    assert result["precedence_rule_id"] == "EP31_PORTFOLIO_BLOCKED"


def test_new_capital_portfolio_block_beats_thesis_and_risk():
    result = evaluate_decision_state(
        base(portfolio_status="BLOCKED", thesis_status="BROKEN", risk_gate_pass=False)
    )
    assert result["action"] == "NO-BUY"
    assert result["precedence_rule_id"] == "NP11_PORTFOLIO_BLOCKED"


def test_new_capital_portfolio_unknown_requires_review():
    result = evaluate_decision_state(base(portfolio_status="UNKNOWN"))
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "NP10_PORTFOLIO_UNKNOWN"


def test_thesis_unknown_existing_never_silently_becomes_hold():
    result = evaluate_decision_state(base(position_pct=Decimal("5"), thesis_status="UNKNOWN"))
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "EP11_THESIS_UNKNOWN"


def test_risk_unknown_existing_requires_review_after_thesis_is_clear():
    result = evaluate_decision_state(base(position_pct=Decimal("5"), risk_status="UNKNOWN"))
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "EP15_RISK_UNKNOWN"


def test_negative_long_term_return_precedes_unresolved_expectation_gap():
    result = evaluate_decision_state(
        base(
            expected_annualized_return=Decimal("-0.10"),
            return_gate_pass=False,
            gap_status="UNKNOWN",
            gap_positive=False,
        )
    )
    assert result["action"] == "NO-BUY"
    assert result["precedence_rule_id"] == "NP40_EXPECTED_RETURN_NEGATIVE"


def test_new_unresolved_gap_requires_review_after_hard_gates_clear():
    result = evaluate_decision_state(base(gap_status="UNKNOWN", gap_positive=False))
    assert result["action"] == "REVIEW_REQUIRED"
    assert result["precedence_rule_id"] == "G00_GAP_UNRESOLVED_NEW"


def test_existing_unresolved_gap_blocks_add_only():
    result = evaluate_decision_state(
        base(position_pct=Decimal("5"), gap_status="UNKNOWN", gap_positive=False)
    )
    assert result["action"] == "HOLD"
    assert result["precedence_rule_id"] == "EP50_GAP_UNRESOLVED"


def test_nonpositive_gap_blocks_new_buy_but_not_existing_hold():
    new_result = evaluate_decision_state(base(gap_status="PASS", gap_positive=False))
    assert new_result["action"] == "NO-BUY"
    assert new_result["precedence_rule_id"] == "G10_GAP_NONPOSITIVE_NEW"

    existing_result = evaluate_decision_state(
        base(position_pct=Decimal("5"), gap_status="PASS", gap_positive=False)
    )
    assert existing_result["action"] == "HOLD"
    assert existing_result["precedence_rule_id"] == "EP70_GAP_NONPOSITIVE"


def test_positive_gap_and_return_pass_produces_buy_or_add():
    buy = evaluate_decision_state(base())
    assert buy["action"] == "BUY"
    assert buy["capital_effect"] == "INCREASE"
    assert buy["new_capital_allowed"] is True

    add = evaluate_decision_state(base(position_pct=Decimal("5")))
    assert add["action"] == "ADD"
    assert add["capital_effect"] == "INCREASE"


def test_package_missing_fails_closed_after_buy_add_eligibility():
    buy = evaluate_decision_state(base(package_complete=False))
    assert buy["action"] == "REVIEW_REQUIRED"
    assert buy["precedence_rule_id"] == "R00_RETURN_QUALIFIED_NEW_PACKAGE_MISSING"

    add = evaluate_decision_state(
        base(position_pct=Decimal("5"), package_complete=False)
    )
    assert add["action"] == "REVIEW_REQUIRED"
    assert add["precedence_rule_id"] == "R30_RETURN_QUALIFIED_EXISTING_PACKAGE_MISSING"


def test_existing_can_add_false_keeps_hold():
    result = evaluate_decision_state(
        base(position_pct=Decimal("5"), can_add=False)
    )
    assert result["action"] == "HOLD"
    assert result["precedence_rule_id"] == "R60_EXISTING_DEFAULT_HOLD"


def test_positive_gap_but_return_gate_failure_is_watch_or_hold():
    new_result = evaluate_decision_state(
        base(return_gate_pass=False)
    )
    assert new_result["action"] == "WATCH"
    assert new_result["precedence_rule_id"] == "R20_RETURN_NOT_QUALIFIED_NEW"

    existing_result = evaluate_decision_state(
        base(position_pct=Decimal("5"), return_gate_pass=False)
    )
    assert existing_result["action"] == "HOLD"
    assert existing_result["precedence_rule_id"] == "R50_RETURN_NOT_QUALIFIED_EXISTING"


def test_repeated_evaluation_is_byte_level_equivalent():
    inputs = base(position_pct=Decimal("5"))
    first = evaluate_decision_state(inputs)
    second = evaluate_decision_state(inputs)
    assert first == second
    assert first["precedence_version"] == DECISION_PRECEDENCE_VERSION



def test_optional_mie_policy_does_not_block_new_capital_on_unknown_gap():
    result = evaluate_decision_state(
        base(
            gap_status="UNKNOWN",
            gap_positive=False,
            mie_policy="OPTIONAL_EXPLANATORY",
        )
    )
    assert result["action"] == "BUY"


def test_optional_mie_policy_does_not_block_new_capital_on_nonpositive_advisory_gap():
    result = evaluate_decision_state(
        base(
            gap_status="PASS",
            gap_positive=False,
            mie_policy="OPTIONAL_EXPLANATORY",
        )
    )
    assert result["action"] == "BUY"


def test_explicit_material_mie_contradiction_can_block_optional_policy():
    result = evaluate_decision_state(
        base(
            gap_status="PASS",
            gap_positive=False,
            mie_policy="OPTIONAL_EXPLANATORY",
            mie_material_contradiction=True,
        )
    )
    assert result["action"] == "NO-BUY"
    assert result["precedence_rule_id"] == "G10_GAP_NONPOSITIVE_NEW"
