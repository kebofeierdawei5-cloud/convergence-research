from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from iios_mvp.investment_core_contract_v03 import calculate_return_metrics


FIXTURE = Path("examples/real_cases/RC-CN-A-002001-20261007_pilot02_input.json")


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_pilot02_bear_case_is_not_backsolved_into_risk_pass() -> None:
    """
    Regression discipline for the PILOT-02 finding:
    the Bear value must be independently supplied by the scenario, and the
    canonical Risk gate may only evaluate it. This test does not mutate or
    reinterpret the production risk semantics.
    """
    case = _fixture()
    max_loss_pct = Decimal(str(case["risk"]["max_loss_pct"]))
    scenarios = case["forecast_assumptions"]["scenarios"]

    bear = Decimal(scenarios["bear"]["value_per_share"])
    entry = Decimal("25.95")
    bear_loss = Decimal("1") - (bear / entry)

    assert bear_loss <= max_loss_pct / Decimal("100")

    gate = {
        "entry_price": str(entry),
        "entry_value_reference": str(case["valuation"]["scenario_values_per_share"]["base"]),
        "horizon_years": "1",
        "horizon_override": False,
        "horizon_override_basis": [],
        "horizon_selection_rationale": "PILOT-03 fixture regression",
        "buy_entry_return_cushion_threshold": "0.15",
        "fundamental_target_annualized_return": "0.15",
        "required_return_annualized": "0.10",
        "lineage_version": "IIOS-FV-RETURN-LINEAGE-0.1",
        "canonical_forecast_ref": {},
        "canonical_valuation_ref": {},
        "scenarios": {
            name: {
                "probability": {"bear": "0.30", "base": "0.50", "bull": "0.20"}[name],
                "terminal_value_per_share": str(scenarios[name]["value_per_share"]),
                "cash_distributions_per_share": "0",
                "probability_rationale": scenarios[name]["rationale"],
            }
            for name in ("bear", "base", "bull")
        },
    }

    metrics = calculate_return_metrics(gate, max_loss_pct=max_loss_pct)
    assert metrics["risk_pass"] is True
    assert metrics["target_entry_price_for_risk"] == bear / (Decimal("1") - max_loss_pct / Decimal("100"))


def test_pilot02_fixture_does_not_change_production_risk_semantics() -> None:
    case = _fixture()
    assert case["risk"]["max_loss_pct"] == "25"
    assert case["valuation"]["primary_model"] == "FORWARD_PE"
    assert case["valuation"]["scenario_values_per_share"]["bear"] == "19.95"
    assert case["forecast_assumptions"]["scenarios"]["bear"]["value_per_share"] == "19.95"
