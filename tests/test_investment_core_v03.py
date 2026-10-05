from __future__ import annotations

import json
from pathlib import Path

from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal

from iios_mvp.canonical_expectation_gap import CANONICAL_EXPECTATION_GAP_VERSION
from iios_mvp.engine import decide, replay, run_case, validate_case
from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEEconomicRequirement,
    MIEObservationBasis,
    MIEQualification,
    MIERepresentation,
    MarketImpliedExpectation,
)
from iios_mvp.market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState
from iios_mvp.multi_model_market_implied_expectation_set import (
    MIEModelEvaluation,
    build_multi_model_market_implied_expectation_set,
)
from iios_mvp.p4f_mie_snapshot import P4FProvenanceRecord, build_p4f_snapshot
from iios_mvp.investment_core_contract_v03 import calculate_return_metrics, validate_case_v03


def market_implied_expectation_snapshot() -> dict:
    cutoff = date(2026, 10, 4)
    created = datetime(2026, 10, 4, 17, 10, tzinfo=timezone.utc)
    requirement = MIEEconomicRequirement(
        economic_variable="forward_eps",
        unit="CNY/share",
        basis="2026A_to_2028E",
        period="2028E",
        horizon="24M",
        accounting_basis="reported",
        role="IMPLIED_PRIMARY",
        value=Decimal("10"),
        evidence_ids=("req-pe-1",),
    )
    coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis="fixture-candidate-set",
        candidate_model_ids=("pe-1",),
        evidence_ids=("cov-pe-1",),
        rationale="The fixture has one admitted market-model candidate.",
    )
    sufficiency = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState.SUFFICIENT,
        rationale="Fixture MIE evidence is complete.",
        evidence_ids=("suff-pe-1",),
    )
    mie = MarketImpliedExpectation(
        expectation_id="mie-pe-1",
        model_id="pe-1",
        market_model=MarketModelFamily.FORWARD_PE,
        identifiability=IdentifiabilityState.IDENTIFIABLE,
        stability=StabilityState.STABLE,
        candidate_coverage=coverage,
        representation=MIERepresentation.IMPLIED_POINT,
        economic_requirements=(requirement,),
        observation_basis=MIEObservationBasis(
            price_observation_id="price-1",
            observation_date=cutoff,
            cutoff_date=cutoff,
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
        ),
        assumption_set=(),
        evidence_sufficiency=sufficiency,
        evidence_ids=("req-pe-1", "cov-pe-1", "suff-pe-1"),
        qualification=MIEQualification.DECISION_GRADE,
        qualification_rationale="Fixture MIE is decision-grade.",
    )
    model_evaluation = MIEModelEvaluation.from_expectation(mie)
    mie_set = build_multi_model_market_implied_expectation_set(
        set_id="set-v03-001",
        candidate_coverage=coverage,
        evidence_sufficiency=sufficiency,
        model_evaluations=(model_evaluation,),
        qualification_rationale="Fixture set resolves uniquely.",
        evidence_ids=("req-pe-1", "cov-pe-1", "suff-pe-1"),
    )
    evidence_ids = sorted({
        "req-pe-1", "cov-pe-1", "suff-pe-1",
        "price-1",
    })
    provenance = []
    for evidence_id in evidence_ids:
        is_price = evidence_id == "price-1"
        provenance.append(
            P4FProvenanceRecord(
                evidence_id=evidence_id,
                variable="market_price" if is_price else "fixture_variable",
                unit="CNY" if is_price else "CNY/share",
                basis="fixture",
                observation_date=cutoff,
                known_at=datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc),
                source="fixture-source",
                source_location=f"fixture://{evidence_id}",
                content_sha256="a" * 64,
                captured_at=created,
            )
        )
    return build_p4f_snapshot(
        case_id="V03-001",
        cutoff_date=cutoff,
        created_at=created,
        mie_set=mie_set,
        provenance_records=provenance,
    )


def case() -> dict:
    return {
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "case_id": "V03-001",
        "market": "CN-A",
        "symbol": "300750",
        "company": "CATL",
        "as_of_date": "2026-10-04",
        "cutoff_date": "2026-10-04",
        "current_price_observation": {
            "price": "100", "price_observation_id": "price-1", "currency": "CNY",
            "observed_at": "2026-10-04T15:00:00+08:00",
            "known_at": "2026-10-04T15:00:00+08:00",
            "source": "test", "adjustment_semantics": "UNADJUSTED",
        },
        "company_evidence_manifest": {"manifest_id": "company-v03-001"},
        "trust": {"status": "PASS"},
        "reality": {"status": "PASS"},
        "forecast": {"status": "PASS"},
        "valuation": {"status": "PASS", "primary_model": "DCF"},
        "risk": {"status": "PASS", "max_loss_pct": "25"},
        "portfolio": {
            "position_pct": "0",
            "constraint_status": "PASS",
            "can_add": True,
            "buy_add_package": {
                "entry_zone": ["95", "100"],
                "initial_position_pct": "5",
                "target_position_pct": "10",
                "max_position_pct": "10",
                "thesis_break_triggers": ["driver deterioration"],
                "monitoring_triggers": ["quarterly results"],
            },
        },
        "thesis": {"status": "INTACT"},
        "market_implied_expectation_snapshot": market_implied_expectation_snapshot(),
        "expectation_gap": {
            "gap_id": "gap-v01-001",
            "evaluator_version": CANONICAL_EXPECTATION_GAP_VERSION,
            "price": "100",
            "price_observation_id": "price-1",
            "cutoff_date": "2026-10-04",
            "mie_snapshot_hash": market_implied_expectation_snapshot()["snapshot_hash"],
            "market_expectation_id": "mie-pe-1",
            "comparison_direction": "HIGHER_IS_BETTER",
            "independent_expectation": {
                "variable_id": "forward_eps",
                "value": "12",
                "unit": "CNY/share",
                "basis": "2026A_to_2028E",
                "horizon_years": "2",
                "evidence_ids": ["ev-forecast"],
            },
        },
        "return_gate": {
            "entry_price": "100",
            "entry_value_reference": "115",
            "horizon_years": "2",
            "horizon_override": False,
            "horizon_override_basis": [],
            "horizon_selection_rationale": "Two-year case-specific evaluation horizon for a test fixture.",
            "buy_entry_return_cushion_threshold": "0.15",
            "fundamental_target_annualized_return": "0.15",
            "required_return_annualized": "0.10",
            "scenarios": {
                "bear": {"probability": "0.2", "terminal_value_per_share": "90", "cash_distributions_per_share": "0", "probability_rationale": "test bear"},
                "base": {"probability": "0.5", "terminal_value_per_share": "140", "cash_distributions_per_share": "0", "probability_rationale": "test base"},
                "bull": {"probability": "0.3", "terminal_value_per_share": "180", "cash_distributions_per_share": "0", "probability_rationale": "test bull"},
            },
        },
    }


def test_v03_return_math_separates_the_two_15_percent_policies():
    metrics = calculate_return_metrics(case()["return_gate"])
    assert metrics["entry_return_cushion"] == Decimal("0.15")
    assert metrics["fundamental_target_pass"] is True
    assert metrics["required_return_pass"] is True
    assert metrics["return_gate_pass"] is True
    assert metrics["expected_total_return"] == Decimal("0.42")
    assert abs(metrics["expected_annualized_return"] - (Decimal("1.42").sqrt() - Decimal("1"))) < Decimal("0.000001")
    assert abs(metrics["margin_of_safety"] - (Decimal("15")/Decimal("115"))) < Decimal("0.000001")


def test_v03_mie_is_required_for_canonical_gap():
    c = case()
    assert validate_case_v03(c)["status"] == "PASS"
    assert not any(x.startswith("V03-MIE") for x in [e["code"] for e in validate_case_v03(c)["errors"]])


def test_v03_forged_positive_gap_is_blocked():
    c = case()
    c["expectation_gap"]["gap_relative"] = "0.10"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-EXPECTATION-GAP-CANONICAL" in x for x in result["validation"]["blockers"])


def test_v03_snapshot_tampering_is_blocked():
    c = case()
    c["market_implied_expectation_snapshot"]["mie_set"]["model_evaluations"][0]["expectation"]["economic_requirements"][0]["value"] = "11"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("invalid canonical P4-F MIE snapshot" in x for x in result["validation"]["blockers"])


def test_v03_expectation_gap_horizon_must_match_decision_horizon():
    c = case()
    c["expectation_gap"]["independent_expectation"]["horizon_years"] = "3"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-EXPECTATION-GAP-HORIZON" in x for x in result["validation"]["blockers"])


def test_v03_buy_requires_all_three_return_conditions():
    result = decide(case())
    assert result["decision"]["action"] == "BUY"
    assert result["decision"]["decision_status"] == "READY"
    assert result["decision"]["investability_status"] == "INVESTABLE"
    assert result["decision"]["human_approval_required"] is True
    assert result["decision"]["auto_execution"] is False


def test_v03_target_entry_price_solver_returns_binding_price_cap():
    metrics = calculate_return_metrics(case()["return_gate"], max_loss_pct="25")
    # For this fixture, the 15% entry cushion is the tightest constraint:
    # 115 / 1.15 = 100.
    assert metrics["target_entry_price_for_entry_cushion"] == Decimal("100")
    assert metrics["target_entry_price"] == Decimal("100")
    assert metrics["risk_pass"] is True


def test_v03_current_price_mismatch_blocks_decision():
    c = case()
    c["return_gate"]["entry_price"] = "90"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-CURRENT-PRICE-BIND" in x for x in result["validation"]["blockers"])


def test_v03_missing_expectation_gap_blocks_new_capital_decision():
    c = case()
    del c["expectation_gap"]
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert result["decision"]["primary_reason"] == "POSITIVE_EXPECTATION_GAP_UNRESOLVED"
    assert result["validation"]["status"] == "PASS"


def test_v03_blocked_expectation_gap_requires_review_for_new_position():
    c = case()
    c["market_implied_expectation"]["identifiability"] = "UNIDENTIFIABLE"
    c["market_implied_expectation"]["qualification"] = "BLOCKED"
    c["expectation_gap"]["market_expectation_hash"] = market_implied_expectation_content_hash(
        c["market_implied_expectation"]
    )
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"



def test_v03_missing_expectation_gap_does_not_block_existing_hold():
    c = case()
    c["portfolio"]["position_pct"] = "5"
    del c["expectation_gap"]
    result = decide(c)
    assert result["decision"]["action"] == "HOLD"


def test_v03_missing_expectation_gap_does_not_block_thesis_broken_exit():
    c = case()
    c["portfolio"]["position_pct"] = "5"
    c["thesis"]["status"] = "BROKEN"
    del c["expectation_gap"]
    result = decide(c)
    assert result["decision"]["action"] == "EXIT"


def test_v03_negative_expectation_gap_is_no_buy():
    c = case()
    c["expectation_gap"]["independent_expectation"]["value"] = "8"
    result = decide(c)
    assert result["decision"]["action"] == "NO-BUY"
    assert result["decision"]["primary_reason"] == "NO_POSITIVE_EXPECTATION_GAP"


def test_v03_positive_gap_and_price_qualified_produces_buy():
    c = case()
    c["current_price_observation"]["price"] = "99"
    c["return_gate"]["entry_price"] = "99"
    c["expectation_gap"]["price"] = "99"
    result = decide(c)
    assert result["decision"]["action"] == "BUY"
    assert Decimal(result["decision"]["target_entry_price"]) >= Decimal("99")


def test_v03_positive_gap_but_price_above_target_is_watch_price():
    c = case()
    c["current_price_observation"]["price"] = "101"
    c["return_gate"]["entry_price"] = "101"
    c["expectation_gap"]["price"] = "101"
    result = decide(c)
    assert result["decision"]["action"] == "WATCH"
    assert result["decision"]["primary_reason"] == "CURRENT_PRICE_ABOVE_TARGET_ENTRY_PRICE"
    assert Decimal(result["decision"]["target_entry_price"]) < Decimal("101")



def test_v03_missing_mie_snapshot_with_gap_fails_closed():
    c = case()
    del c["market_implied_expectation_snapshot"]
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("market_implied_expectation_snapshot is required" in x for x in result["validation"]["blockers"])


def test_v03_mie_snapshot_hash_binding_fails_closed():
    c = case()
    c["expectation_gap"]["mie_snapshot_hash"] = "0" * 64
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("mie_snapshot_hash" in x for x in result["validation"]["blockers"])


def test_v03_mie_id_tampering_fails_closed():
    c = case()
    c["expectation_gap"]["market_expectation_id"] = "mie-forged"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("market_expectation_id" in x for x in result["validation"]["blockers"])


def test_v03_inline_market_expectation_is_rejected_by_canonical_boundary():
    c = case()
    c["expectation_gap"]["market_expectation"] = {"value": "999"}
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("unsupported fields" in x for x in result["validation"]["blockers"])

def test_v03_price_observation_id_is_required():
    c = case()
    del c["current_price_observation"]["price_observation_id"]
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-PRICE-OBSERVATION-ID" in x for x in result["validation"]["blockers"])

def test_v03_expectation_gap_price_binding_requires_revalidation():
    c = case()
    c["current_price_observation"]["price"] = "99"
    c["return_gate"]["entry_price"] = "99"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-EXPECTATION-GAP-PRICE" in x for x in result["validation"]["blockers"])


def test_v03_target_entry_price_is_conditional_and_requires_gap_revalidation():
    result = decide(case())
    assert result["decision"]["target_entry_price_semantics"] == (
        "CONDITIONAL_THRESHOLD_REQUIRES_EXPECTATION_GAP_REVALIDATION"
    )
    assert result["decision"]["target_entry_price_requires_gap_revalidation"] is True
    assert result["gates"]["target_entry_price"] == result["decision"]["target_entry_price"]


def test_v03_risk_cap_enters_target_entry_price_solver():
    c = case()
    c["risk"]["max_loss_pct"] = "5"
    metrics = calculate_return_metrics(c["return_gate"], max_loss_pct="5")
    assert metrics["risk_pass"] is False
    assert abs(
        metrics["target_entry_price_for_risk"] - Decimal("90") / Decimal("0.95")
    ) < Decimal("0.0000000001")
    assert metrics["target_entry_price"] == metrics["target_entry_price_for_risk"]



def test_v03_missing_risk_budget_fails_closed():
    c = case()
    del c["risk"]["max_loss_pct"]
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-RISK-MAX-LOSS-REQUIRED" in x for x in result["validation"]["blockers"])


def test_v03_exact_15_annualized_target_is_inclusive():
    c = case()
    # Equal scenario wealth makes expected wealth exactly 132.25 over H=2.
    # sqrt(1.3225) - 1 = 15%, so the target comparison must pass at equality.
    c["return_gate"]["scenarios"] = {
        "bear": {"probability": "0.2", "terminal_value_per_share": "132.25", "cash_distributions_per_share": "0", "probability_rationale": "exact boundary"},
        "base": {"probability": "0.5", "terminal_value_per_share": "132.25", "cash_distributions_per_share": "0", "probability_rationale": "exact boundary"},
        "bull": {"probability": "0.3", "terminal_value_per_share": "132.25", "cash_distributions_per_share": "0", "probability_rationale": "exact boundary"},
    }
    metrics = calculate_return_metrics(c["return_gate"])
    assert metrics["expected_total_return"] == Decimal("0.3225")
    assert abs(metrics["expected_annualized_return"] - Decimal("0.15")) < Decimal("0.000001")
    assert metrics["fundamental_target_pass"] is True


def test_v03_watch_when_target_passes_but_entry_cushion_fails():
    c = case()
    c["current_price_observation"]["price"] = "110"
    c["return_gate"]["entry_price"] = "110"
    c["expectation_gap"]["price"] = "110"
    c["return_gate"]["entry_value_reference"] = "115"
    c["return_gate"]["scenarios"] = {
        "bear": {"probability": "0.2", "terminal_value_per_share": "140", "cash_distributions_per_share": "0", "probability_rationale": "watch bear"},
        "base": {"probability": "0.5", "terminal_value_per_share": "160", "cash_distributions_per_share": "0", "probability_rationale": "watch base"},
        "bull": {"probability": "0.3", "terminal_value_per_share": "180", "cash_distributions_per_share": "0", "probability_rationale": "watch bull"},
    }
    result = decide(c)
    assert result["decision"]["action"] == "WATCH"
    assert result["decision"]["investability_status"] == "WATCH"


def test_v03_watch_price_when_expected_annualized_return_below_target():
    c = case()
    c["return_gate"]["scenarios"] = {
        "bear": {"probability": "0.2", "terminal_value_per_share": "80", "cash_distributions_per_share": "0", "probability_rationale": "low"},
        "base": {"probability": "0.5", "terminal_value_per_share": "125", "cash_distributions_per_share": "0", "probability_rationale": "base"},
        "bull": {"probability": "0.3", "terminal_value_per_share": "140", "cash_distributions_per_share": "0", "probability_rationale": "high"},
    }
    result = decide(c)
    assert result["decision"]["action"] == "WATCH"
    assert result["decision"]["target_entry_price"] is not None


def test_v03_unknown_never_becomes_hold():
    c = case()
    c["trust"]["status"] = "UNKNOWN"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    c["portfolio"]["position_pct"] = "5"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"


def test_v03_trust_fail_does_not_auto_exit():
    c = case()
    c["portfolio"]["position_pct"] = "5"
    c["trust"]["status"] = "FAIL"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"


def test_v03_portfolio_block_can_reduce_existing_position():
    c = case()
    c["portfolio"]["position_pct"] = "15"
    c["portfolio"]["constraint_status"] = "BLOCKED"
    result = decide(c)
    assert result["decision"]["action"] == "REDUCE"


def test_v03_thesis_broken_exits_existing_position():
    c = case()
    c["portfolio"]["position_pct"] = "5"
    c["thesis"]["status"] = "BROKEN"
    result = decide(c)
    assert result["decision"]["action"] == "EXIT"


def test_v03_add_existing_position():
    c = case()
    c["portfolio"]["position_pct"] = "5"
    result = decide(c)
    assert result["decision"]["action"] == "ADD"


def test_v03_hold_existing_when_return_is_positive_but_gate_fails():
    c = case()
    c["portfolio"]["position_pct"] = "5"
    c["current_price_observation"]["price"] = "130"
    c["return_gate"]["entry_price"] = "130"
    c["expectation_gap"]["price"] = "130"
    c["return_gate"]["entry_value_reference"] = "115"
    result = decide(c)
    assert result["decision"]["action"] == "HOLD"


def test_v03_review_required_on_unresolved_return_input():
    c = case()
    del c["return_gate"]["required_return_annualized"]
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"


def test_v03_pit_leak_blocks_decision():
    c = case()
    c["current_price_observation"]["known_at"] = "2026-10-05T09:00:00+08:00"
    result = decide(c)
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert any("V03-PIT-PRICE-KNOWN-AT" in x for x in result["validation"]["blockers"])


def test_v03_replay_is_deterministic():
    snap, digest = run_case(case())
    assert digest == snap["snapshot_hash"]
    replay_result = replay(snap)
    assert replay_result["replay_status"] == "PASS"
    assert replay_result["integrity_status"] == "PASS"


def test_legacy_v02_contract_remains_supported_through_legacy_validator():
    from tests.test_investment_core_contract import valid_case
    c = valid_case()
    assert validate_case(c) == []


def test_v03_schema_contract_is_explicitly_versioned():
    c = case()
    assert c["contract_version"] == "IIOS-INVESTMENT-CORE-0.3"

def test_v03_jsonschema_accepts_valid_case():
    import jsonschema
    schema = json.loads(Path("schemas/investment_core_case_v0.3.schema.json").read_text())
    jsonschema.validate(case(), schema)


def test_v03_jsonschema_rejects_incomplete_buy_add_package():
    import jsonschema
    schema = json.loads(Path("schemas/investment_core_case_v0.3.schema.json").read_text())
    invalid = case()
    invalid["portfolio"]["buy_add_package"].pop("monitoring_triggers")
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, schema)

def test_v03_default_horizon_is_one_year_and_not_an_implicit_three_year():
    c = case()
    del c["expectation_gap"]
    c["return_gate"]["horizon_years"] = "1"
    c["return_gate"]["horizon_override"] = False
    c["return_gate"]["horizon_override_basis"] = []
    c["return_gate"]["horizon_selection_rationale"] = "Use the IIOS default one-year decision horizon."
    assert validate_case_v03(c)["status"] == "PASS"
    metrics = calculate_return_metrics(c["return_gate"])
    assert metrics["horizon_years"] == "1"
    assert metrics["horizon_override"] is False


def test_v03_three_year_requires_explicit_override_and_qualifying_basis():
    c = case()
    del c["expectation_gap"]
    c["return_gate"]["horizon_years"] = "3"
    c["return_gate"]["horizon_override"] = True
    c["return_gate"]["horizon_override_basis"] = [
        "MAJOR_INDUSTRY_LEADER",
        "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX",
    ]
    c["return_gate"]["horizon_selection_rationale"] = "Three-year horizon is justified by major industry leadership and a major investment cycle."
    assert validate_case_v03(c)["status"] == "PASS"


def test_v03_three_year_without_override_fails_closed():
    c = case()
    c["return_gate"]["horizon_years"] = "3"
    c["return_gate"]["horizon_override"] = False
    c["return_gate"]["horizon_override_basis"] = []
    c["return_gate"]["horizon_selection_rationale"] = "Attempted three-year horizon without exception."
    result = validate_case_v03(c)
    assert result["status"] == "BLOCKED"
    assert any("horizon_override" in e["message"] for e in result["errors"])


def test_v03_three_year_with_unqualified_basis_fails_closed():
    c = case()
    c["return_gate"]["horizon_years"] = "3"
    c["return_gate"]["horizon_override"] = True
    c["return_gate"]["horizon_override_basis"] = ["OTHER"]
    c["return_gate"]["horizon_selection_rationale"] = "Attempted three-year horizon with unsupported reason."
    result = validate_case_v03(c)
    assert result["status"] == "BLOCKED"


def test_v03_two_year_override_is_not_treated_as_a_three_year_exception():
    c = case()
    c["return_gate"]["horizon_years"] = "2"
    c["return_gate"]["horizon_override"] = True
    c["return_gate"]["horizon_override_basis"] = ["MAJOR_INDUSTRY_LEADER"]
    c["return_gate"]["horizon_selection_rationale"] = "Attempted two-year override."
    result = validate_case_v03(c)
    assert result["status"] == "BLOCKED"
