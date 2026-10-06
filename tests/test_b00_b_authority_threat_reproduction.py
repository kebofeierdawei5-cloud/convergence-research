from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from iios_mvp.decision_lifecycle_production import (
    build_decision_revision,
    build_human_approval,
)
from iios_mvp.execution_receipt_production import (
    build_execution_receipt,
    validate_execution_receipt,
)
from iios_mvp.investment_core_contract_v03 import decide_v03, validate_case_v03

from tests.decision_admission_fixture import build_fixture_admission_receipt
from tests.test_core04_real_300750_upstream_gate_e2e import (
    _case,
    _inputs,
    _price_ref,
)
from tests.test_decision_lifecycle_production import snapshot


def _all_pass_quality(core02: dict) -> dict:
    quality = deepcopy(core02["quality"])
    for row in quality["dimensions"]:
        row["status"] = "PASS"
        row["rationale"] = "B00-B adversarial reproduction fixture: caller asserts PASS."
    return quality


def _buyable_case() -> tuple[dict, object]:
    core03, core02 = _inputs()
    core02 = deepcopy(core02)
    core02["quality"] = _all_pass_quality(core02)
    registry, price_ref = _price_ref()
    case = _case(
        core03=core03,
        core02=core02,
        price_ref=price_ref,
        trust_status="PASS",
    )

    # Keep expectation-gap/MIE absent so this exercises the non-MIE decision
    # path and isolates the upstream status/return lineage boundaries.
    assert "expectation_gap" not in case
    assert "target_entry_price_reference" not in case

    # Make Return Gate independently satisfy the 15% annualized hurdle.
    case["return_gate"]["scenarios"] = {
        "bear": {
            "probability": "0.25",
            "terminal_value_per_share": "420",
            "cash_distributions_per_share": "0",
            "probability_rationale": "B00-B adversarial fixture.",
        },
        "base": {
            "probability": "0.50",
            "terminal_value_per_share": "520",
            "cash_distributions_per_share": "0",
            "probability_rationale": "B00-B adversarial fixture.",
        },
        "bull": {
            "probability": "0.25",
            "terminal_value_per_share": "680",
            "cash_distributions_per_share": "0",
            "probability_rationale": "B00-B adversarial fixture.",
        },
    }
    return case, registry


def test_p0_01_caller_declared_upstream_status_can_reach_buy_without_canonical_domain_admissions():
    case, registry = _buyable_case()

    validation = validate_case_v03(case, current_price_resolver=registry)
    assert validation["status"] == "PASS", validation["errors"]

    upstream = case["decision_upstream_admission"]
    assert upstream["reality_status"] == "PASS"
    assert upstream["value_driver_status"] == "PASS"
    assert upstream["valuation_status"] == "PASS"
    assert upstream["forecast_status"] == "PASS"

    # No domain-owned canonical admission references are required by the
    # current v0.3 upstream admission contract for these caller-declared states.
    assert "reality_admission_ref" not in upstream
    assert "value_driver_admission_ref" not in upstream
    assert "valuation_admission_ref" not in upstream
    assert "independent_forecast_ref" not in upstream

    decision = decide_v03(case, current_price_resolver=registry)

    assert decision["action"] == "BUY"
    assert decision["gates"]["new_capital_allowed"] is True


def test_p0_02_return_gate_can_diverge_from_forecast_and_valuation_and_still_reach_buy():
    case, registry = _buyable_case()

    # Deliberately make the supplied Valuation and Forecast economically
    # incompatible with the separately supplied Return Gate while keeping all
    # individually checked structural contracts valid.
    case["valuation"]["probability_weighted_value_per_share"] = "50"
    case["forecast"]["scenarios"]["base"]["fcf_proxy_bn_cny"] = ["1", "1", "1"]
    case["forecast"]["scenarios"]["bull"]["fcf_proxy_bn_cny"] = ["2", "2", "2"]
    case["forecast"]["scenarios"]["bear"]["fcf_proxy_bn_cny"] = ["0.5", "0.5", "0.5"]

    validation = validate_case_v03(case, current_price_resolver=registry)
    assert validation["status"] == "PASS", validation["errors"]

    decision = decide_v03(case, current_price_resolver=registry)

    assert decision["action"] == "BUY"
    assert decision["gates"]["new_capital_allowed"] is True
    assert decision["gates"]["valuation"] == "PASS"
    assert decision["gates"]["forecast"] == "PASS"
    assert Decimal(decision["return_metrics"]["expected_annualized_return"]) > Decimal("0.15")


def test_p1_03_execution_receipt_accepts_action_scope_mismatch_as_record_only_evidence():
    # This reproduces the execution-scope observation without treating it as
    # an execution-authority bypass: C6 is explicitly record-only.
    s = snapshot("HOLD")
    revision = build_decision_revision(
        decision_series_id="CN-A-300750",
        revision=1,
        snapshot=s,
        run_id="b00-b-p1-03",
        decision_admission=build_fixture_admission_receipt(
            snapshot=s,
            canonical_decision=s["decision"],
        ),
    )
    approval = build_human_approval(
        decision_revision=revision,
        approved=True,
        note="B00-B scope mismatch reproduction",
        actor_identity="human:b00-b",
    )
    receipt = build_execution_receipt(
        execution_receipt_id="b00-b-hold-positive-execution",
        decision_revision=revision,
        human_approval=approval,
        executed_at="2026-10-06T15:30:00+00:00",
        execution_status="EXECUTED",
        executed_quantity="100",
        executed_position_pct="25",
        executed_price="100",
        actor_identity="human:b00-b",
    )
    validate_execution_receipt(receipt)

    assert receipt["approved_action"] == "HOLD"
    assert receipt["execution_status"] == "EXECUTED"
    assert receipt["executed_position_pct"] == "25"
    assert receipt["auto_execution"] is False
    assert receipt["policy_effect"] == "POST_APPROVAL_RECORD_ONLY_NO_DECISION_MUTATION"
