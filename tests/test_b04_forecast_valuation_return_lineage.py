from __future__ import annotations

from datetime import date
from copy import deepcopy

import pytest

from iios_mvp.canonical_independent_forecast import InMemoryCanonicalIndependentForecastRegistry
from iios_mvp.canonical_investment_admission_v01 import (
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)
from iios_mvp.forecast_valuation_return_lineage_v01 import (
    FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
    InMemoryCanonicalValuationOutputResolver,
    build_canonical_valuation_output,
    validate_forecast_valuation_return_lineage,
)
from iios_mvp.investment_core_contract_v03 import validate_case_v03


CASE_ID = "B04-CASE-001"
MARKET = "CN-A"
SYMBOL = "300750"
COMPANY = "CATL"
CUTOFF = date(2026, 10, 4)


def _forecast():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    ref = registry.admit_independent_forecast({
        "case_id": CASE_ID,
        "market": MARKET,
        "symbol": SYMBOL,
        "cutoff_date": CUTOFF.isoformat(),
        "forecast_id": "forecast-b04-001",
        "forecast_version": "B04-FORECAST-0.1",
        "model_version": "B04-MODEL-0.1",
        "variable_id": "forward_eps",
        "value": "20",
        "unit": "CNY/share",
        "basis": "2026A_to_2029E",
        "horizon_years": "3",
        "forecast_origin": "2026-10-04T12:00:00+00:00",
        "known_at": "2026-10-04T15:00:00+00:00",
        "prepared_without_current_price": True,
        "evidence_ids": ["b04-forecast-evidence"],
    })
    return registry, ref.to_dict()


def _valuation(forecast_ref):
    output = build_canonical_valuation_output({
        "valuation_id": "valuation-b04-001",
        "valuation_version": "B04-VALUATION-0.1",
        "case_id": CASE_ID,
        "market": MARKET,
        "symbol": SYMBOL,
        "company": COMPANY,
        "cutoff_date": CUTOFF.isoformat(),
        "forecast_ref": forecast_ref,
        "horizon_years": "3",
        "reference_value_per_share": "430",
        "scenarios": {
            "bear": {
                "probability": "0.25",
                "value_per_share": "280",
                "cash_distributions_per_share": "0",
            },
            "base": {
                "probability": "0.50",
                "value_per_share": "430",
                "cash_distributions_per_share": "10",
            },
            "bull": {
                "probability": "0.25",
                "value_per_share": "650",
                "cash_distributions_per_share": "15",
            },
        },
        "evidence_ids": ["b04-valuation-evidence"],
    })
    admission_registry = InMemoryCanonicalInvestmentAdmissionRegistry()
    admission = build_canonical_investment_admission(
        admission_id="valuation-admission-b04-001",
        domain="VALUATION",
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF.isoformat(),
        domain_status="PASS",
        source_record_id=output["valuation_id"],
        source_record_hash="a" * 64,
        output_hash=output["output_hash"],
        producer_version="B04-VALUATION-PRODUCER-0.1",
        evidence_ids=["b04-valuation-evidence"],
        admitted_at="2026-10-04T16:00:00+00:00",
    )
    ref = admission_registry.admit(admission).to_dict()
    resolver = InMemoryCanonicalValuationOutputResolver(admission_registry)
    resolver.register_output(
        valuation_reference=ref,
        valuation_output=output,
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF,
    )
    return resolver, ref, output


def _return_gate(forecast_ref, valuation_ref):
    return {
        "lineage_version": FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
        "canonical_forecast_ref": forecast_ref,
        "canonical_valuation_ref": valuation_ref,
        "entry_price": "291.11",
        "entry_value_reference": "430",
        "horizon_years": "3",
        "horizon_override": True,
        "horizon_override_basis": ["MAJOR_INDUSTRY_LEADER"],
        "horizon_selection_rationale": "B04 test horizon",
        "buy_entry_return_cushion_threshold": "0.15",
        "fundamental_target_annualized_return": "0.15",
        "required_return_annualized": "0.10",
        "scenarios": {
            "bear": {
                "probability": "0.25",
                "terminal_value_per_share": "280",
                "cash_distributions_per_share": "0",
                "probability_rationale": "canonical valuation",
            },
            "base": {
                "probability": "0.50",
                "terminal_value_per_share": "430",
                "cash_distributions_per_share": "10",
                "probability_rationale": "canonical valuation",
            },
            "bull": {
                "probability": "0.25",
                "terminal_value_per_share": "650",
                "cash_distributions_per_share": "15",
                "probability_rationale": "canonical valuation",
            },
        },
    }


def test_b04_lineage_accepts_canonical_forecast_and_valuation():
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    result = validate_forecast_valuation_return_lineage(
        return_gate=_return_gate(forecast_ref, valuation_ref),
        canonical_forecast_ref=forecast_ref,
        canonical_valuation_ref=valuation_ref,
        independent_forecast_resolver=forecast_registry,
        valuation_output_resolver=valuation_resolver,
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF,
    )
    assert result["status"] == "PASS"
    assert result["binding"] == "FORECAST_REF_EQUALITY_AND_CANONICAL_VALUATION_SCENARIO_EQUALITY"


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (("probability", "base", "0.75"), "is not canonical"),
        (("terminal_value_per_share", "base", "999"), "is not canonical"),
        (("cash_distributions_per_share", "bull", "999"), "is not canonical"),
    ],
)
def test_b04_return_gate_cannot_substitute_economic_inputs(mutation, expected):
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    gate = _return_gate(forecast_ref, valuation_ref)
    field, scenario, value = mutation
    gate["scenarios"][scenario][field] = value
    with pytest.raises(ValueError, match=expected):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=forecast_ref,
            canonical_valuation_ref=valuation_ref,
            independent_forecast_resolver=forecast_registry,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID,
            market=MARKET,
            symbol=SYMBOL,
            company=COMPANY,
            cutoff_date=CUTOFF,
        )


def test_b04_return_gate_reference_value_and_horizon_are_bound():
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)

    gate = _return_gate(forecast_ref, valuation_ref)
    gate["entry_value_reference"] = "500"
    with pytest.raises(ValueError, match="reference value"):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=forecast_ref,
            canonical_valuation_ref=valuation_ref,
            independent_forecast_resolver=forecast_registry,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID,
            market=MARKET,
            symbol=SYMBOL,
            company=COMPANY,
            cutoff_date=CUTOFF,
        )

    gate = _return_gate(forecast_ref, valuation_ref)
    gate["horizon_years"] = "2"
    with pytest.raises(ValueError, match="horizon"):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=forecast_ref,
            canonical_valuation_ref=valuation_ref,
            independent_forecast_resolver=forecast_registry,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID,
            market=MARKET,
            symbol=SYMBOL,
            company=COMPANY,
            cutoff_date=CUTOFF,
        )


def test_b04_forecast_to_valuation_binding_is_strict():
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, valuation = _valuation(forecast_ref)
    unrelated_registry, unrelated_ref = _forecast()
    _ = unrelated_registry
    gate = _return_gate(unrelated_ref, valuation_ref)
    with pytest.raises(ValueError, match="valuation.forecast_ref"):
        validate_forecast_valuation_return_lineage(
            return_gate=gate,
            canonical_forecast_ref=unrelated_ref,
            canonical_valuation_ref=valuation_ref,
            independent_forecast_resolver=forecast_registry,
            valuation_output_resolver=valuation_resolver,
            case_id=CASE_ID,
            market=MARKET,
            symbol=SYMBOL,
            company=COMPANY,
            cutoff_date=CUTOFF,
        )


def _core_case(return_gate):
    return {
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "case_id": CASE_ID,
        "market": MARKET,
        "symbol": SYMBOL,
        "company": COMPANY,
        "as_of_date": CUTOFF.isoformat(),
        "cutoff_date": CUTOFF.isoformat(),
        "current_price_observation": {
            "price": "291.11",
            "price_observation_id": "b04-price-001",
            "price_observation_admission_hash": "b" * 64,
            "currency": "CNY",
            "observed_at": "2026-10-04T15:00:00+00:00",
            "known_at": "2026-10-04T15:00:00+00:00",
            "source": "fixture",
            "adjustment_semantics": "UNADJUSTED",
        },
        "company_evidence_manifest": {"manifest_id": "b04-company"},
        "trust": {"status": "PASS"},
        "reality": {"status": "PASS"},
        "forecast": {"status": "PASS"},
        "valuation": {"status": "PASS"},
        "risk": {
            "status": "PASS",
            "max_loss_pct": "25",
            "thesis_breaks": ["forecast failure"],
            "evidence_ids": ["b04-risk"],
        },
        "portfolio": {
            "position_pct": "0",
            "constraint_status": "PASS",
            "can_add": True,
            "buy_add_package": {
                "entry_zone": ["280", "291.11"],
                "initial_position_pct": "5",
                "target_position_pct": "10",
                "max_position_pct": "10",
                "thesis_break_triggers": ["forecast failure"],
                "monitoring_triggers": ["quarterly review"],
            },
        },
        "thesis": {"status": "INTACT"},
        "decision_upstream_admission": {
            "schema_version": "IIOS-CORE-04-UPSTREAM-ADMISSION-0.1",
            "policy_version": "IIOS-DECISION-UPSTREAM-POLICY-0.1",
            "case_id": CASE_ID,
            "cutoff_date": CUTOFF.isoformat(),
            "reality_status": "PASS",
            "quality_gate_status": "PASS",
            "value_driver_status": "PASS",
            "valuation_status": "PASS",
            "forecast_status": "PASS",
            "thesis_status": "INTACT",
            "thesis_admission_status": "ADMITTED",
            "capital_admission_ready": True,
            "quality_gate": {"status": "PASS", "case_id": CASE_ID, "cutoff_date": CUTOFF.isoformat(), "dimensions": []},
            "thesis_admission": {"status": "INTACT", "admission_status": "ADMITTED", "case_id": CASE_ID, "cutoff_date": CUTOFF.isoformat(), "evidence_ids": ["b04-risk"]},
            "evidence_ids": ["b04-risk"],
            "admission_record_hash": "invalid-placeholder",
        },
        "return_gate": return_gate,
    }


def test_b04_core_validation_rejects_lineage_tampering_before_decision_runtime():
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref, _ = _valuation(forecast_ref)
    gate = _return_gate(forecast_ref, valuation_ref)
    gate["scenarios"]["bear"]["terminal_value_per_share"] = "999"
    result = validate_case_v03(
        _core_case(gate),
        independent_forecast_resolver=forecast_registry,
        valuation_output_resolver=valuation_resolver,
    )
    assert result["status"] == "BLOCKED"
    assert any(error["code"] == "V03-RETURN-LINEAGE-CANONICAL" for error in result["errors"])
