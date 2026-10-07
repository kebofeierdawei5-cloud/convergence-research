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
from tests.b04b_return_lineage_fixture import bind_return_lineage
from tests.test_core04_real_300750_upstream_gate_e2e import (
    _case,
    _inputs,
    _price_ref,
    UPSTREAM_AUTHORITY_REGISTRY,
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


def test_p0_01_caller_declared_upstream_status_is_blocked_without_canonical_domain_admissions():
    case, registry = _buyable_case()

    validation = validate_case_v03(case, current_price_resolver=registry)
    assert validation["status"] == "BLOCKED"
    assert any(
        "canonical upstream authority resolver is required for v0.2 upstream admission" in error["message"]
        for error in validation["errors"]
    )

    decision = decide_v03(case, current_price_resolver=registry)
    assert decision["action"] != "BUY"
    assert decision["gates"]["new_capital_allowed"] is False


def test_p0_02_return_gate_divergence_is_blocked_by_canonical_lineage():
    case, registry = _buyable_case()
    case, forecast_registry, valuation_resolver = bind_return_lineage(case)

    # B04-B attack: after canonical valuation is admitted, independently
    # substitute an optimistic Return Gate terminal value.
    # The canonical Valuation output remains unchanged and must win.
    case["return_gate"]["scenarios"]["base"]["terminal_value_per_share"] = "999"

    validation = validate_case_v03(
        case,
        current_price_resolver=registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        valuation_output_resolver=valuation_resolver,
    )
    assert validation["status"] == "BLOCKED", validation["errors"]
    assert any(
        error["code"] == "V03-RETURN-LINEAGE-CANONICAL"
        for error in validation["errors"]
    )

    decision = decide_v03(
        case,
        current_price_resolver=registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
        valuation_output_resolver=valuation_resolver,
    )

    assert decision["action"] != "BUY"
    assert decision["gates"]["new_capital_allowed"] is False


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
