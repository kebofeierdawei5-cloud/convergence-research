from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from iios_mvp.canonical_entry_evaluation import (
    CANONICAL_ENTRY_EVALUATION_VERSION,
    DECISION_ADMISSION_VERSION,
    admit_decision,
    build_canonical_entry_evaluation,
    replay_canonical_entry_evaluation,
    replay_decision_admission,
)
from iios_mvp.engine import decide
from iios_mvp.p2_1_canonical_price_response import PRICE_RESPONSE_VERSION
from iios_mvp.price_dependent_expectation_gap import (
    P2_PRICE_GAP_REVALIDATION_VERSION,
    revalidate_expectation_gap_at_price,
)
from tests.test_investment_core_v03 import (
    EVIDENCE_ROOT_REGISTRY,
    CURRENT_PRICE_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    case,
)


def _decision_case(*, price: str = "100", position_pct: str = "0") -> dict:
    c = case(price=price, price_observation_id=f"price-{price}")
    c["expectation_gap"]["price"] = price
    c["return_gate"]["entry_price"] = price
    c["portfolio"]["position_pct"] = position_pct
    c["return_gate"]["entry_value_reference"] = "160"
    c["return_gate"]["scenarios"] = {
        "bear": {
            "probability": "0.2",
            "terminal_value_per_share": "160",
            "cash_distributions_per_share": "0",
            "probability_rationale": "P2.2 bear",
        },
        "base": {
            "probability": "0.5",
            "terminal_value_per_share": "220",
            "cash_distributions_per_share": "0",
            "probability_rationale": "P2.2 base",
        },
        "bull": {
            "probability": "0.3",
            "terminal_value_per_share": "280",
            "cash_distributions_per_share": "0",
            "probability_rationale": "P2.2 bull",
        },
    }
    return c


def _canonical_p2_1_response(
    *,
    candidate: str = "139",
    reference: str = "100",
    boundary: str = "120",
    qualification: str = "DECISION_GRADE",
) -> dict:
    return {
        "response_version": PRICE_RESPONSE_VERSION,
        "response_id": "p21-fixture-response",
        "candidate_price": candidate,
        "reference_price": reference,
        "snapshot_hash": "a" * 64,
        "model_id": "forward_ev_ebitda",
        "expectation_id": "mie-fixture",
        "qualification": qualification,
        "status": "NON_POSITIVE",
        "comparison_direction": "HIGHER_IS_BETTER",
        "expectation_gap_price_boundary": boundary,
        "price_constraint_type": "UPPER_BOUND_STRICT",
    }


def _evaluation(
    *,
    current_price: str = "100",
    response: dict | None = None,
) -> dict:
    return build_canonical_entry_evaluation(
        current_price=current_price,
        return_target_entry_price="139",
        price_response=response or _canonical_p2_1_response(),
        price_response_source="P2.1_CANONICAL",
        entry_reference_source="EXPECTATION_GAP",
        market_expectation_id="mie-fixture",
        independent_forecast_ref={"forecast_id": "forecast-fixture"},
    )


def test_canonical_entry_evaluation_is_decision_grade_and_price_admissible():
    evaluation = _evaluation()
    assert evaluation["status"] == "PASS"
    assert evaluation["qualification"] == "DECISION_GRADE"
    assert Decimal(evaluation["effective_target_entry_price"]) == Decimal("120")
    assert evaluation["current_price_eligible"] is True
    assert evaluation["price_constraint_type"] == "UPPER_BOUND_STRICT"
    assert evaluation["evaluation_version"] == CANONICAL_ENTRY_EVALUATION_VERSION
    assert evaluation["price_response_source"] == "P2.1_CANONICAL"


def test_decision_admission_downgrades_buy_when_canonical_entry_rejects_price():
    admission = admit_decision(
        pre_admission_action="BUY",
        pre_admission_status="READY",
        pre_admission_reason="BUY",
        pre_admission_capital_effect="INCREASE",
        position_pct="0",
        entry_evaluation={
            "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
            "evaluation_id": "fixture",
            "status": "PASS",
            "qualification": "DECISION_GRADE",
            "current_price_eligible": False,
        },
    )
    assert admission["status"] == "BLOCKED"
    assert admission["action"] == "WATCH"
    assert admission["rule_id"] == "DA40_NEW_CAPITAL_PRICE_INELIGIBLE"


def test_decision_admission_downgrades_add_when_canonical_entry_rejects_price():
    admission = admit_decision(
        pre_admission_action="ADD",
        pre_admission_status="READY",
        pre_admission_reason="ADD",
        pre_admission_capital_effect="INCREASE",
        position_pct="5",
        entry_evaluation={
            "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
            "evaluation_id": "fixture",
            "status": "PASS",
            "qualification": "DECISION_GRADE",
            "current_price_eligible": False,
        },
    )
    assert admission["status"] == "BLOCKED"
    assert admission["action"] == "HOLD"
    assert admission["rule_id"] == "DA41_EXISTING_POSITION_PRICE_INELIGIBLE"


def test_investment_core_formally_admits_buy_through_canonical_entry_evaluation():
    c = _decision_case(price="125")
    result = decide(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert result["decision"]["action"] == "BUY"
    assert result["decision"]["decision_admission_version"] == DECISION_ADMISSION_VERSION
    assert result["decision"]["decision_admission_rule_id"] == "DA50_CANONICAL_ENTRY_ADMITTED"
    assert result["decision"]["decision_pre_admission_action"] == "BUY"
    assert result["decision"]["decision_status"] == "READY"
    assert result["decision"]["capital_effect"] == "INCREASE"
    assert result["decision"]["canonical_entry_evaluation"]["qualification"] == "DECISION_GRADE"
    assert result["decision"]["canonical_entry_evaluation"]["price_response_source"] == "P2_LEGACY_COMPAT"
    assert result["decision"]["canonical_entry_evaluation"]["current_price_eligible"] is True


def test_investment_core_formally_admits_add_through_canonical_entry_evaluation():
    c = _decision_case(price="125", position_pct="5")
    result = decide(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert result["decision"]["action"] == "ADD"
    assert result["decision"]["decision_admission_rule_id"] == "DA50_CANONICAL_ENTRY_ADMITTED"
    assert result["decision"]["decision_pre_admission_action"] == "ADD"


def test_entry_evaluation_rejects_current_price_mismatch_with_price_response_reference():
    try:
        _evaluation(current_price="101")
    except ValueError as exc:
        assert "must equal price-response reference_price" in str(exc)
    else:
        raise AssertionError(
            "current/price-response reference mismatch must fail closed"
        )


def test_missing_entry_evaluation_fails_closed_for_buy_add():
    admission = admit_decision(
        pre_admission_action="BUY",
        pre_admission_status="READY",
        pre_admission_reason="BUY",
        pre_admission_capital_effect="INCREASE",
        position_pct="0",
        entry_evaluation=None,
    )
    assert admission["status"] == "REVIEW_REQUIRED"
    assert admission["action"] == "REVIEW_REQUIRED"
    assert admission["rule_id"] == "DA10_ENTRY_EVALUATION_MISSING"


def test_conditional_only_price_boundary_cannot_become_admission_gate():
    admission = admit_decision(
        pre_admission_action="BUY",
        pre_admission_status="READY",
        pre_admission_reason="BUY",
        pre_admission_capital_effect="INCREASE",
        position_pct="0",
        entry_evaluation={
            "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
            "evaluation_id": "fixture",
            "status": "CONDITIONAL_ONLY",
            "qualification": "CONDITIONAL_ONLY",
            "current_price_eligible": None,
        },
    )
    assert admission["status"] == "PASS_ADVISORY_ONLY"
    assert admission["action"] == "BUY"
    assert admission["new_capital_allowed"] is True


def test_non_increasing_actions_are_not_mutated():
    evaluation = {
        "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
        "evaluation_id": "fixture",
        "status": "REVIEW_REQUIRED",
        "qualification": "UNKNOWN",
        "current_price_eligible": False,
    }
    for action in (
        "HOLD",
        "WATCH",
        "REDUCE",
        "EXIT",
        "NO-BUY",
        "REVIEW_REQUIRED",
    ):
        admission = admit_decision(
            pre_admission_action=action,
            pre_admission_status="READY",
            pre_admission_reason="BASE",
            pre_admission_capital_effect="UNCHANGED",
            position_pct="5",
            entry_evaluation=evaluation,
        )
        assert admission["action"] == action


def test_canonical_entry_evaluation_supports_explicit_legacy_p2_compatibility():
    c = _decision_case()
    snapshot = EVIDENCE_ROOT_REGISTRY.resolve_p4f_snapshot(
        c["market_implied_expectation_snapshot_ref"],
        case_id=c["case_id"],
        cutoff_date=__import__("datetime").date.fromisoformat(c["cutoff_date"]),
    )
    legacy = revalidate_expectation_gap_at_price(
        market_implied_expectation_snapshot=snapshot,
        current_price_observation=c["current_price_observation"],
        candidate_price="139",
        cutoff_date=c["cutoff_date"],
        case_id=c["case_id"],
        market=c["market"],
        symbol=c["symbol"],
        market_expectation_id=c["expectation_gap"]["market_expectation_id"],
        independent_forecast_ref=c["expectation_gap"]["independent_forecast_ref"],
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    evaluation = build_canonical_entry_evaluation(
        current_price="100",
        return_target_entry_price="139",
        price_response=legacy,
        price_response_source="P2_LEGACY_COMPAT",
        entry_reference_source="EXPECTATION_GAP",
        market_expectation_id=c["expectation_gap"]["market_expectation_id"],
        independent_forecast_ref=c["expectation_gap"]["independent_forecast_ref"],
    )
    assert evaluation["status"] == "PASS"
    assert evaluation["qualification"] == "DECISION_GRADE"
    assert evaluation["price_response_source"] == "P2_LEGACY_COMPAT"
    assert evaluation["price_response_version"] == P2_PRICE_GAP_REVALIDATION_VERSION


def test_canonical_entry_evaluation_replay_is_exact_and_tamper_sensitive():
    evaluation = _evaluation()
    assert replay_canonical_entry_evaluation(
        evaluation=evaluation,
        current_price="100",
        return_target_entry_price="139",
        price_response=_canonical_p2_1_response(),
        price_response_source="P2.1_CANONICAL",
        entry_reference_source="EXPECTATION_GAP",
        market_expectation_id="mie-fixture",
        independent_forecast_ref={"forecast_id": "forecast-fixture"},
    )["replay_status"] == "PASS"

    tampered = deepcopy(evaluation)
    tampered["effective_target_entry_price"] = "121"
    assert replay_canonical_entry_evaluation(
        evaluation=tampered,
        current_price="100",
        return_target_entry_price="139",
        price_response=_canonical_p2_1_response(),
        price_response_source="P2.1_CANONICAL",
        entry_reference_source="EXPECTATION_GAP",
        market_expectation_id="mie-fixture",
        independent_forecast_ref={"forecast_id": "forecast-fixture"},
    )["replay_status"] == "FAIL"


def test_decision_admission_replay_is_exact():
    admission = admit_decision(
        pre_admission_action="BUY",
        pre_admission_status="READY",
        pre_admission_reason="BUY",
        pre_admission_capital_effect="INCREASE",
        position_pct="0",
        entry_evaluation={
            "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
            "evaluation_id": "fixture",
            "status": "PASS",
            "qualification": "DECISION_GRADE",
            "current_price_eligible": True,
        },
    )
    assert replay_decision_admission(
        admission=admission,
        pre_admission_action="BUY",
        pre_admission_status="READY",
        pre_admission_reason="BUY",
        pre_admission_capital_effect="INCREASE",
        position_pct="0",
        entry_evaluation={
            "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
            "evaluation_id": "fixture",
            "status": "PASS",
            "qualification": "DECISION_GRADE",
            "current_price_eligible": True,
        },
    )["replay_status"] == "PASS"


def test_entry_schema_accepts_canonical_evaluation():
    evaluation = _evaluation()
    schema = json.loads(
        Path("schemas/canonical_entry_evaluation_v0.1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(evaluation)
