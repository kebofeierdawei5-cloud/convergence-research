from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from iios_mvp.canonical_current_price import InMemoryCanonicalCurrentPriceRegistry
from iios_mvp.investment_core_contract_v03 import decide_v03
from iios_mvp.decision_upstream_admission_v03 import build_decision_upstream_admission
from iios_mvp.market_model_identification import MarketValuationObservation
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)

ROOT = Path(__file__).resolve().parents[1]
CORE03_PATH = ROOT / "examples/real_cases/RC-CN-A-300750-20261004_core03_input.json"
CASE_ID = "RC-CN-A-300750-20261004"
CUTOFF = date(2026, 10, 4)
PRICE_DATE = date(2026, 9, 30)
PRICE = Decimal("291.11")
PRICE_EVIDENCE_SHA = "349b422f6f9c95d5ea8787aa664e8cd913f9aac3b056914e68f3826567cd6ea2"


def _inputs():
    data = json.loads(CORE03_PATH.read_text(encoding="utf-8"))
    return data, data["core02_input"]


def _price_ref():
    registry = InMemoryCanonicalCurrentPriceRegistry()
    known_at = datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc)
    evidence = VerifiedMarketEvidence(
        evidence_id="E011",
        variable="market_price",
        unit="CNY/share",
        basis="Official SZSE EOD snapshot for 2026-09-30",
        observation_date=PRICE_DATE,
        known_at=known_at,
        source="SZSE:MARKET_DATA",
        source_location="SZSE primary EOD snapshot for 2026-09-30",
        content_sha256=PRICE_EVIDENCE_SHA,
        exact_bytes=True,
        status=AdmissionStatus.ADMITTED,
        temporal_provenance=TemporalProvenance.SOURCE_VINTAGE,
        value=PRICE,
    )
    observation = MarketValuationObservation(
        observation_id="market-observation-300750-20260930",
        observation_date=PRICE_DATE,
        known_at=known_at,
        price=PRICE,
        shares_outstanding=Decimal("4380630342"),
        economic_variable="ebitda",
        economic_value=Decimal("119197217000"),
        unit="CNY",
        basis="FY2025 completed fiscal-year EBITDA",
        evidence_ids=("E011", "E008", "E009"),
        source="SZSE:MARKET_DATA",
        net_debt=Decimal("-276904623000"),
    )
    admission = MarketObservationAdmission(
        status=AdmissionStatus.ADMITTED,
        observation=observation,
        evidence_ids=("E011", "E008", "E009"),
    )
    return registry, registry.admit_current_price(
        case_id=CASE_ID,
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=evidence,
        observed_at=datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    ).to_dict()


def _thesis():
    return {
        "status": "INTACT",
        "statement": "CATL can convert global battery-system scale, unit economics and disciplined reinvestment into durable economic profit.",
        "mechanism": "Volume and product mix drive revenue and margins; reinvestment must convert into adequate incremental ROIC and sustained FCF.",
        "key_driver_ids": ["D1", "D2", "D3"],
        "falsifiers": [
            "persistent unit-margin deterioration",
            "incremental ROIC remains below required return",
            "structural FCF conversion failure",
            "material governance or shareholder-treatment deterioration",
        ],
        "monitoring_triggers": [
            "quarterly margin and mix",
            "FCF conversion",
            "incremental ROIC",
            "capacity utilization and new-capacity returns",
        ],
        "evidence_ids": ["E004", "E005", "E009", "E010"],
        "known_at": "2026-10-04T12:00:00+00:00",
        "prepared_without_current_price": True,
    }


def _case(*, core03, core02, price_ref, trust_status):
    upstream = build_decision_upstream_admission(
        case_id=CASE_ID,
        cutoff_date="2026-10-04",
        reality_status="PASS",
        quality=core02["quality"],
        value_driver_status="PASS",
        valuation_status="PASS",
        forecast_status="PASS",
        thesis=_thesis(),
    )
    return {
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "300750",
        "company": "宁德时代",
        "as_of_date": "2026-10-04",
        "cutoff_date": "2026-10-04",
        "current_price_observation": {
            "price": "291.11",
            "price_observation_id": price_ref["price_observation_id"],
            "currency": "CNY",
            "observed_at": "2026-09-30T15:00:00+00:00",
            "known_at": "2026-09-30T23:59:00+00:00",
            "source": "SZSE:MARKET_DATA",
            "adjustment_semantics": "UNADJUSTED",
            "price_observation_admission_hash": price_ref["admission_record_hash"],
        },
        "company_evidence_manifest": {
            "manifest_id": "b2_company_evidence_manifest_v0.1"
        },
        "trust": {"status": trust_status},
        "reality": core02["reality"],
        "quality": core02["quality"],
        "forecast": core03["forecast"],
        "valuation": {
            "status": "PASS",
            "primary_model": "DCF",
            "probability_weighted_value_per_share": "433.5675",
        },
        "risk": {"status": "PASS", "max_loss_pct": "25"},
        "portfolio": {
            "position_pct": "0",
            "constraint_status": "PASS",
            "can_add": True,
            "buy_add_package": {
                "entry_zone": ["285", "291.11"],
                "initial_position_pct": "5",
                "target_position_pct": "10",
                "max_position_pct": "10",
                "thesis_break_triggers": ["incremental ROIC failure", "FCF conversion failure"],
                "monitoring_triggers": ["quarterly operating review"],
            },
        },
        "thesis": {
            **_thesis(),
        },
        "decision_upstream_admission": upstream,
        "return_gate": {
            "entry_price": "291.11",
            "entry_value_reference": "433.5675",
            "horizon_years": "3",
            "horizon_override": True,
            "horizon_override_basis": ["MAJOR_INDUSTRY_LEADER", "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX"],
            "horizon_selection_rationale": "Explicit 3Y override for major industry leadership and capital-cycle characteristics; default remains 1Y.",
            "buy_entry_return_cushion_threshold": "0.15",
            "fundamental_target_annualized_return": "0.15",
            "required_return_annualized": "0.10",
            "scenarios": {
                "bear": {"probability": "0.25", "terminal_value_per_share": "258.32", "cash_distributions_per_share": "0", "probability_rationale": "CORE-03 admitted Bear scenario."},
                "base": {"probability": "0.50", "terminal_value_per_share": "418.49", "cash_distributions_per_share": "0", "probability_rationale": "CORE-03 admitted Base scenario."},
                "bull": {"probability": "0.25", "terminal_value_per_share": "638.97", "cash_distributions_per_share": "0", "probability_rationale": "CORE-03 admitted Bull scenario."},
            },
        },
    }


def test_real_300750_quality_gate_is_explicitly_propagated_to_kernel():
    core03, core02 = _inputs()
    registry, price_ref = _price_ref()
    case = _case(core03=core03, core02=core02, price_ref=price_ref, trust_status="PASS")

    result = decide_v03(case, current_price_resolver=registry)

    assert result["validation"]["status"] == "PASS"
    assert result["gates"]["reality"] == "PASS"
    assert result["gates"]["quality_gate"] == "CONDITIONAL"
    assert result["gates"]["value_driver"] == "PASS"
    assert result["gates"]["valuation"] == "PASS"
    assert result["gates"]["forecast"] == "PASS"
    assert result["gates"]["thesis_admission"] == "ADMITTED"
    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert result["decision"]["primary_reason"] == "QUALITY_GATE_UNRESOLVED"
    assert result["decision"]["gates"]["new_capital_allowed"] is False
    assert result["decision"]["mie_policy"] == "OPTIONAL_EXPLANATORY"


def test_real_300750_strict_trust_still_precedes_quality_gate():
    core03, core02 = _inputs()
    registry, price_ref = _price_ref()
    case = _case(core03=core03, core02=core02, price_ref=price_ref, trust_status="REVALIDATION")

    result = decide_v03(case, current_price_resolver=registry)

    assert result["decision"]["action"] == "REVIEW_REQUIRED"
    assert result["decision"]["primary_reason"] == "TRUST_NOT_PASS_REQUIRES_REVIEW"
    assert result["decision"]["gates"]["new_capital_allowed"] is False
