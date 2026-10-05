from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from iios_mvp.canonical_current_price import InMemoryCanonicalCurrentPriceRegistry
from iios_mvp.investment_core_contract_v03 import calculate_return_metrics, decide_v03
from iios_mvp.market_model_identification import MarketValuationObservation
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)


ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "RC-CN-A-300750-20261004"
CUTOFF = date(2026, 10, 4)
PRICE_DATE = date(2026, 9, 30)
PRICE = Decimal("291.11")
PRICE_EVIDENCE_SHA = "349b422f6f9c95d5ea8787aa664e8cd913f9aac3b056914e68f3826567cd6ea2"


def _load_case_inputs() -> tuple[dict, dict]:
    core03 = json.loads(
        (ROOT / "examples/real_cases/RC-CN-A-300750-20261004_core03_input.json").read_text(
            encoding="utf-8"
        )
    )
    core02 = core03["core02_input"]
    return core03, core02


def _admit_price(registry: InMemoryCanonicalCurrentPriceRegistry) -> dict:
    observed_at = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
    known_at = datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc)

    price_evidence = VerifiedMarketEvidence(
        evidence_id="E011",
        variable="market_price",
        unit="CNY/share",
        basis="Official SZSE EOD snapshot for 2026-09-30",
        observation_date=PRICE_DATE,
        known_at=known_at,
        source="SZSE:MARKET_DATA",
        source_location=(
            "https://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx"
            "&CATALOGID=1815_stock_snapshot&TABKEY=tab1"
            "&txtBeginDate=2026-09-30&txtEndDate=2026-09-30"
            "&archiveDate=2026-10-01&random=0.20261005"
        ),
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
        basis="FY2025 completed-fiscal-year EBITDA",
        evidence_ids=("E011", "E008", "E009"),
        source="SZSE:MARKET_DATA",
        net_debt=Decimal("-276904623000"),
    )
    admission = MarketObservationAdmission(
        status=AdmissionStatus.ADMITTED,
        observation=observation,
        evidence_ids=("E011", "E008", "E009"),
    )

    ref = registry.admit_current_price(
        case_id=CASE_ID,
        market="CN-A",
        symbol="300750",
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=price_evidence,
        observed_at=observed_at,
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    )
    return ref.to_dict()


def _make_case(
    *,
    price_ref: dict,
    core03: dict,
    core02: dict,
    trust_status: str,
    thesis_status: str,
) -> dict:
    reality = deepcopy(core02.get("reality", {}))
    reality["quality_assessment"] = deepcopy(core02.get("quality", {}))
    reality["value_core"] = deepcopy(core02.get("value_core", {}))
    reality["value_driver_ranking"] = deepcopy(core02.get("value_driver_ranking", []))

    return {
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "300750",
        "company": "宁德时代",
        "as_of_date": "2026-10-04",
        "cutoff_date": "2026-10-04",
        "current_price_observation": {
            "price": str(PRICE),
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
        "trust": {
            "status": trust_status,
            "basis": "Derived from the current Core-02 Trust assessment; conditional dimensions require revalidation before capital admission.",
        },
        "reality": reality,
        "forecast": deepcopy(core03["forecast"]),
        "valuation": {
            "status": "CONDITIONAL",
            "primary_model": "DCF",
            "valuation_basis": "CORE-03 human-selected DCF; no broker consensus",
            "bear_value_per_share": "258.32",
            "base_value_per_share": "418.49",
            "bull_value_per_share": "638.97",
            "probability_weighted_value_per_share": "433.5675",
            "evidence_ids": ["E004", "E005", "E009", "E010"],
        },
        "risk": {
            "status": "PASS",
            "max_loss_pct": "25",
            "basis": "E2E policy parameter; not a market-data observation.",
        },
        "portfolio": {
            "position_pct": "0",
            "constraint_status": "PASS",
            "can_add": True,
            "buy_add_package": {
                "entry_zone": ["300", "345"],
                "initial_position_pct": "5",
                "target_position_pct": "10",
                "max_position_pct": "10",
                "thesis_break_triggers": [
                    "incremental ROIC deteriorates materially",
                    "FCF conversion remains structurally weak",
                    "battery/storage demand or utilization thesis breaks",
                ],
                "monitoring_triggers": [
                    "quarterly revenue / margin / cash-flow conversion",
                    "capacity utilization and new-capacity returns",
                ],
            },
        },
        "thesis": {
            "status": thesis_status,
            "basis": "Formal thesis state is not yet separately admitted by an upstream machine contract; UNKNOWN is therefore fail-closed.",
        },
        "return_gate": {
            "entry_price": "291.11",
            "entry_value_reference": "433.5675",
            "horizon_years": "3",
            "horizon_override": True,
            "horizon_override_basis": [
                "MAJOR_INDUSTRY_LEADER",
                "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX",
            ],
            "horizon_selection_rationale": (
                "Explicit 3Y override for CATL because it is a major industry leader "
                "and is in a major capacity / capital-expenditure cycle; IIOS default remains 1Y."
            ),
            "buy_entry_return_cushion_threshold": "0.15",
            "fundamental_target_annualized_return": "0.15",
            "required_return_annualized": "0.10",
            "scenarios": {
                "bear": {
                    "probability": "0.25",
                    "terminal_value_per_share": "258.32",
                    "cash_distributions_per_share": "0",
                    "probability_rationale": "Reuse the admitted CORE-03 Bear DCF scenario.",
                },
                "base": {
                    "probability": "0.50",
                    "terminal_value_per_share": "418.49",
                    "cash_distributions_per_share": "0",
                    "probability_rationale": "Reuse the admitted CORE-03 Base DCF scenario.",
                },
                "bull": {
                    "probability": "0.25",
                    "terminal_value_per_share": "638.97",
                    "cash_distributions_per_share": "0",
                    "probability_rationale": "Reuse the admitted CORE-03 Bull DCF scenario.",
                },
            },
        },
    }


def run() -> dict:
    core03, core02 = _load_case_inputs()
    registry = InMemoryCanonicalCurrentPriceRegistry()
    price_ref = _admit_price(registry)

    strict_case = _make_case(
        price_ref=price_ref,
        core03=core03,
        core02=core02,
        trust_status="REVALIDATION",
        thesis_status="UNKNOWN",
    )
    metrics = calculate_return_metrics(strict_case["return_gate"], max_loss_pct="25")
    strict_result = decide_v03(
        strict_case,
        current_price_resolver=registry,
    )

    diagnostic_case = deepcopy(strict_case)
    diagnostic_case["trust"]["status"] = "PASS"
    diagnostic_case["thesis"]["status"] = "INTACT"
    diagnostic_result = decide_v03(
        diagnostic_case,
        current_price_resolver=registry,
    )

    assert metrics["horizon_years"] == "3"
    assert metrics["horizon_override"] is True
    assert metrics["entry_return_cushion"] >= Decimal("0.15")
    assert metrics["fundamental_target_pass"] is False
    assert metrics["required_return_pass"] is True
    assert metrics["risk_pass"] is True
    assert abs(
        metrics["expected_annualized_return"] - Decimal("0.1420011256785252039")
    ) < Decimal("0.000000000000000001")

    # Strict real-case result: unresolved Trust must dominate and no new capital is admitted.
    assert strict_result["action"] == "REVIEW_REQUIRED"
    assert strict_result["investability_status"] == "UNKNOWN"
    assert strict_result["gates"]["new_capital_allowed"] is False
    assert strict_result["current_price"] == "291.11"

    # Gate-normalized diagnostic isolates the return decision without manufacturing MIE.
    assert diagnostic_result["action"] == "WATCH"
    assert diagnostic_result["gates"]["new_capital_allowed"] is False
    assert diagnostic_result["mie_policy"] == "OPTIONAL_EXPLANATORY"
    assert diagnostic_result["gates"]["expectation_gap_required_for_buy_add"] is False

    return {
        "case_id": CASE_ID,
        "cutoff_date": "2026-10-04",
        "current_price": str(PRICE),
        "current_price_reference": price_ref,
        "horizon": {
            "years": metrics["horizon_years"],
            "override": metrics["horizon_override"],
            "override_basis": metrics["horizon_override_basis"],
        },
        "return_metrics": {
            "entry_return_cushion": str(metrics["entry_return_cushion"]),
            "margin_of_safety": str(metrics["margin_of_safety"]),
            "expected_terminal_wealth": str(metrics["expected_terminal_wealth"]),
            "expected_total_return": str(metrics["expected_total_return"]),
            "expected_annualized_return": str(metrics["expected_annualized_return"]),
            "fundamental_target_pass": metrics["fundamental_target_pass"],
            "required_return_pass": metrics["required_return_pass"],
            "bear_return": str(metrics["bear_return"]),
            "risk_pass": metrics["risk_pass"],
            "target_entry_price": str(metrics["target_entry_price"]),
            "target_entry_price_binding": metrics["target_entry_price_binding"],
        },
        "strict_real_case": {
            "trust_status": strict_case["trust"]["status"],
            "thesis_status": strict_case["thesis"]["status"],
            "action": strict_result["action"],
            "decision_status": strict_result["decision_status"],
            "primary_reason": strict_result["primary_reason"],
            "capital_admitted": strict_result["gates"]["new_capital_allowed"],
            "mie_policy": strict_result["mie_policy"],
        },
        "gate_normalized_diagnostic": {
            "trust_status": diagnostic_case["trust"]["status"],
            "thesis_status": diagnostic_case["thesis"]["status"],
            "action": diagnostic_result["action"],
            "decision_status": diagnostic_result["decision_status"],
            "primary_reason": diagnostic_result["primary_reason"],
            "capital_admitted": diagnostic_result["gates"]["new_capital_allowed"],
            "mie_policy": diagnostic_result["mie_policy"],
        },
        "integration_findings": [
            "Current Core-02 Trust assessment is conditional and is not safe to coerce to PASS.",
            "Formal Thesis admission is not yet a dedicated upstream machine contract; UNKNOWN is retained fail-closed.",
            "Quality/value-driver data are carried inside Reality for this E2E but are not explicit Decision Kernel inputs.",
            "MIE is OPTIONAL_EXPLANATORY in CORE-04 v0.3 and is not required to reach the return/risk decision path.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
