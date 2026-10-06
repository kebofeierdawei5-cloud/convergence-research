from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from iios_mvp.canonical_current_price import InMemoryCanonicalCurrentPriceRegistry
from iios_mvp.canonical_independent_forecast import InMemoryCanonicalIndependentForecastRegistry
from iios_mvp.canonical_investment_admission_v01 import (
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)
from iios_mvp.decision_upstream_admission_v03 import build_decision_upstream_admission
from iios_mvp.forecast_valuation_return_lineage_v01 import (
    FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
    InMemoryCanonicalValuationOutputResolver,
    build_canonical_valuation_output,
)
from iios_mvp.investment_core_contract_v03 import validate_case_v03
from iios_mvp.market_model_identification import MarketValuationObservation
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)


CASE_ID = "B04-CORE-001"
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
        "forecast_id": "b04-core-forecast-001",
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
        "evidence_ids": ["b04-core-forecast-evidence"],
    })
    return registry, ref.to_dict()


def _valuation(forecast_ref):
    output = build_canonical_valuation_output({
        "valuation_id": "b04-core-valuation-001",
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
            "bear": {"probability": "0.25", "value_per_share": "280", "cash_distributions_per_share": "0"},
            "base": {"probability": "0.50", "value_per_share": "430", "cash_distributions_per_share": "10"},
            "bull": {"probability": "0.25", "value_per_share": "650", "cash_distributions_per_share": "15"},
        },
        "evidence_ids": ["b04-core-valuation-evidence"],
    })
    admissions = InMemoryCanonicalInvestmentAdmissionRegistry()
    admission = build_canonical_investment_admission(
        admission_id="b04-core-valuation-admission-001",
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
        evidence_ids=["b04-core-valuation-evidence"],
        admitted_at="2026-10-04T16:00:00+00:00",
    )
    valuation_ref = admissions.admit(admission).to_dict()
    resolver = InMemoryCanonicalValuationOutputResolver(admissions)
    resolver.register_output(
        valuation_reference=valuation_ref,
        valuation_output=output,
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        company=COMPANY,
        cutoff_date=CUTOFF,
    )
    return resolver, valuation_ref


def _price():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    known_at = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
    evidence = VerifiedMarketEvidence(
        evidence_id="b04-core-price-evidence",
        variable="market_price",
        unit="CNY/share",
        basis="B04 price",
        observation_date=CUTOFF,
        known_at=known_at,
        source="fixture",
        source_location="fixture://b04-price",
        content_sha256="b" * 64,
        exact_bytes=True,
        status=AdmissionStatus.ADMITTED,
        temporal_provenance=TemporalProvenance.SOURCE_VINTAGE,
        value=Decimal("291.11"),
    )
    observation = MarketValuationObservation(
        observation_id="b04-core-market-observation",
        observation_date=CUTOFF,
        known_at=known_at,
        price=Decimal("291.11"),
        shares_outstanding=Decimal("1000000000"),
        economic_variable="ebitda",
        economic_value=Decimal("100000000000"),
        unit="CNY",
        basis="B04 fixture",
        evidence_ids=("b04-core-price-evidence",),
        source="fixture",
        net_debt=Decimal("0"),
    )
    admission = MarketObservationAdmission(
        status=AdmissionStatus.ADMITTED,
        observation=observation,
        evidence_ids=("b04-core-price-evidence",),
    )
    ref = registry.admit_current_price(
        case_id=CASE_ID,
        market=MARKET,
        symbol=SYMBOL,
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=evidence,
        observed_at=known_at,
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    )
    return registry, ref.to_dict()


def _upstream():
    return build_decision_upstream_admission(
        case_id=CASE_ID,
        cutoff_date=CUTOFF.isoformat(),
        reality_status="PASS",
        quality={
            "dimensions": [
                {"dimension": "competitive_advantage", "status": "PASS", "rationale": "B04", "evidence_ids": ["b04-core-risk"]},
                {"dimension": "incremental_return_on_capital", "status": "PASS", "rationale": "B04", "evidence_ids": ["b04-core-risk"]},
                {"dimension": "earnings_quality", "status": "PASS", "rationale": "B04", "evidence_ids": ["b04-core-risk"]},
                {"dimension": "cash_flow_conversion", "status": "PASS", "rationale": "B04", "evidence_ids": ["b04-core-risk"]},
                {"dimension": "balance_sheet_resilience", "status": "PASS", "rationale": "B04", "evidence_ids": ["b04-core-risk"]},
                {"dimension": "reinvestment_runway", "status": "PASS", "rationale": "B04", "evidence_ids": ["b04-core-risk"]},
            ]
        },
        value_driver_status="PASS",
        valuation_status="PASS",
        forecast_status="PASS",
        thesis={
            "status": "INTACT",
            "statement": "B04 fixture thesis",
            "mechanism": "B04 fixture mechanism",
            "key_driver_ids": ["D1"],
            "falsifiers": ["forecast failure"],
            "monitoring_triggers": ["quarterly review"],
            "evidence_ids": ["b04-core-risk"],
            "known_at": "2026-10-04T12:00:00+00:00",
            "prepared_without_current_price": True,
        },
    )


def _case(return_gate, price_ref):
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
            "price_observation_id": price_ref["price_observation_id"],
            "price_observation_admission_hash": price_ref["admission_record_hash"],
            "currency": "CNY",
            "observed_at": "2026-10-04T15:00:00+00:00",
            "known_at": "2026-10-04T15:00:00+00:00",
            "source": "fixture",
            "adjustment_semantics": "UNADJUSTED",
        },
        "company_evidence_manifest": {"manifest_id": "b04-core-company"},
        "trust": {"status": "PASS"},
        "reality": {"status": "PASS"},
        "forecast": {"status": "PASS"},
        "valuation": {"status": "PASS"},
        "risk": {
            "status": "PASS",
            "max_loss_pct": "25",
            "thesis_breaks": ["forecast failure"],
            "evidence_ids": ["b04-core-risk"],
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
        "decision_upstream_admission": _upstream(),
        "return_gate": return_gate,
    }


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
        "horizon_selection_rationale": "B04 core integration test",
        "buy_entry_return_cushion_threshold": "0.15",
        "fundamental_target_annualized_return": "0.15",
        "required_return_annualized": "0.10",
        "scenarios": {
            "bear": {"probability": "0.25", "terminal_value_per_share": "280", "cash_distributions_per_share": "0", "probability_rationale": "canonical"},
            "base": {"probability": "0.50", "terminal_value_per_share": "430", "cash_distributions_per_share": "10", "probability_rationale": "canonical"},
            "bull": {"probability": "0.25", "terminal_value_per_share": "650", "cash_distributions_per_share": "15", "probability_rationale": "canonical"},
        },
    }


def test_b04_core_accepts_canonical_lineage():
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref = _valuation(forecast_ref)
    price_registry, price_ref = _price()
    result = validate_case_v03(
        _case(_return_gate(forecast_ref, valuation_ref), price_ref),
        current_price_resolver=price_registry,
        independent_forecast_resolver=forecast_registry,
        valuation_output_resolver=valuation_resolver,
    )
    assert result["status"] == "PASS"


def test_b04_core_blocks_modified_probability_before_return_calculation():
    forecast_registry, forecast_ref = _forecast()
    valuation_resolver, valuation_ref = _valuation(forecast_ref)
    price_registry, price_ref = _price()
    gate = _return_gate(forecast_ref, valuation_ref)
    gate["scenarios"]["base"]["probability"] = "0.99"
    result = validate_case_v03(
        _case(gate, price_ref),
        current_price_resolver=price_registry,
        independent_forecast_resolver=forecast_registry,
        valuation_output_resolver=valuation_resolver,
    )
    assert result["status"] == "BLOCKED"
    assert any(error["code"] == "V03-RETURN-LINEAGE-CANONICAL" for error in result["errors"])
