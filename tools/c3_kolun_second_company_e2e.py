from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from iios_mvp.canonical_current_price import InMemoryCanonicalCurrentPriceRegistry
from iios_mvp.canonical_investment_admission_v01 import InMemoryCanonicalInvestmentAdmissionRegistry
from tests.b03b_upstream_authority_fixture import build_runtime_upstream_authority
from iios_mvp.forecast_valuation_return_lineage_v01 import InMemoryCanonicalValuationOutputResolver
from tests.b04b_return_lineage_fixture import bind_return_lineage
from iios_mvp.decision_admission import admit_canonical_decision
from iios_mvp.human_report import build_human_report, qa_human_report, write_human_report
from iios_mvp.investment_core_contract_v03 import calculate_return_metrics, decide_v03
from iios_mvp.machine_publication import build_machine_publication, write_machine_publication
from iios_mvp.market_model_identification import MarketValuationObservation
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)
from iios_mvp.store import (
    apply_monitoring_event,
    approve_revision,
    create_or_load_series,
    replay_decision_lifecycle,
    write_decision_revision,
    write_monitoring_validation,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
    initialize_monitoring_state,
)
from iios_mvp.engine import sha256_obj

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "examples/real_cases/RC-CN-A-002422-20261004_c3_input.json"
PRICE_CAPTURE_PATH = (
    ROOT
    / "evidence/real_cases/RC-CN-A-002422-20261004/c3_price_capture.txt"
)
CASE_ID = "RC-CN-A-002422-20261004"
CUTOFF = date(2026, 10, 4)
PRICE = Decimal("40.85")
PRICE_EVIDENCE_SHA = "b59d6844530261896569dcd071f2fecb670fc26ad162a6ecbf31ccca1f464d7f"
AUTHORITY_REGISTRY: InMemoryCanonicalInvestmentAdmissionRegistry | None = None
FORECAST_REGISTRY = None
VALUATION_ADMISSION_REGISTRY = InMemoryCanonicalInvestmentAdmissionRegistry()
VALUATION_OUTPUT_RESOLVER: InMemoryCanonicalValuationOutputResolver | None = None


def load_case_fixture() -> dict[str, Any]:
    payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    if payload["case_id"] != CASE_ID:
        raise ValueError("C3 fixture case_id mismatch")
    return payload


def admit_price() -> tuple[InMemoryCanonicalCurrentPriceRegistry, dict[str, Any]]:
    capture = PRICE_CAPTURE_PATH.read_bytes()
    if hashlib.sha256(capture).hexdigest() != PRICE_EVIDENCE_SHA:
        raise ValueError("C3 price evidence capture SHA mismatch")

    registry = InMemoryCanonicalCurrentPriceRegistry()
    known_at = datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc)
    price_evidence = VerifiedMarketEvidence(
        evidence_id="E005",
        variable="market_price",
        unit="CNY/share",
        basis="CFi historical quote capture for 2026-09-30",
        observation_date=date(2026, 9, 30),
        known_at=known_at,
        source="CFi:HISTORICAL_QUOTE",
        source_location="https://quote.cfi.cn/quote_002422.html",
        content_sha256=PRICE_EVIDENCE_SHA,
        exact_bytes=True,
        status=AdmissionStatus.ADMITTED,
        temporal_provenance=TemporalProvenance.CONTEMPORANEOUS_PUBLICATION,
        value=PRICE,
    )
    observation = MarketValuationObservation(
        observation_id="market-observation-002422-20260930",
        observation_date=date(2026, 9, 30),
        known_at=known_at,
        price=PRICE,
        shares_outstanding=Decimal("1590781208"),
        economic_variable="net_profit_h1",
        economic_value=Decimal("1127804000"),
        unit="CNY",
        basis="2026 H1 reported net profit attributable to parent",
        evidence_ids=("E005", "E002"),
        source="CNINFO:2026_H1_REPORT",
        net_debt=Decimal("0"),
    )
    admission = MarketObservationAdmission(
        status=AdmissionStatus.ADMITTED,
        observation=observation,
        evidence_ids=("E005", "E002"),
    )
    ref = registry.admit_current_price(
        case_id=CASE_ID,
        market="CN-A",
        symbol="002422",
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=price_evidence,
        observed_at=datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    ).to_dict()
    return registry, ref


def build_case(fixture: dict[str, Any], price_ref: dict[str, Any]) -> dict[str, Any]:
    global AUTHORITY_REGISTRY, FORECAST_REGISTRY, VALUATION_OUTPUT_RESOLVER
    quality = {
        "dimensions": [
            {
                "dimension": "competitive_advantage",
                "status": "PASS",
                "rationale": "Mature pharmaceutical manufacturing scale and an established product platform are supported by the 2026 H1 company report.",
                "evidence_ids": ["E002", "E003"],
            },
            {
                "dimension": "incremental_return_on_capital",
                "status": "CONDITIONAL",
                "rationale": "The case has sufficient operating anchors for analysis, but a full PIT incremental-ROIC bridge remains incomplete.",
                "evidence_ids": ["E002", "E004"],
            },
            {
                "dimension": "earnings_quality",
                "status": "PASS",
                "rationale": "2026 H1 accounting earnings and operating cash flow are established from the same primary report; no cross-source substitution is used in the C3 case.",
                "evidence_ids": ["E002"],
            },
            {
                "dimension": "cash_flow_conversion",
                "status": "PASS",
                "rationale": "2026 H1 operating cash flow of approximately CNY 2.34bn is an admitted company-report anchor.",
                "evidence_ids": ["E002"],
            },
            {
                "dimension": "balance_sheet_resilience",
                "status": "PASS",
                "rationale": "The company report establishes a substantial consolidated asset and liquidity base for this case-level acceptance.",
                "evidence_ids": ["E002"],
            },
            {
                "dimension": "reinvestment_runway",
                "status": "PASS",
                "rationale": "The mature business plus the controlled biotechnology platform provides an identifiable reinvestment path that differs structurally from CATL.",
                "evidence_ids": ["E003", "E004"],
            },
        ]
    }
    thesis = dict(fixture["thesis"])
    authority_registry, upstream = build_runtime_upstream_authority(
        case_id=CASE_ID,
        market="CN-A",
        symbol="002422",
        company="四川科伦药业股份有限公司",
        cutoff_date=CUTOFF,
        reality={"status": "PASS", "economic_structure": fixture["economic_structure"], "evidence_ids": ["E001", "E002", "E003", "E004"]},
        quality=quality,
        value_driver={"status": "PASS", "drivers": thesis["key_driver_ids"], "evidence_ids": thesis["evidence_ids"]},
        valuation=fixture["valuation"],
        forecast={"status": "PASS", "forecast_assumptions": fixture["forecast_assumptions"], "evidence_ids": ["E002", "E003", "E004"]},
        thesis=thesis,
        declared_statuses={
            "REALITY": "PASS",
            "QUALITY": "CONDITIONAL",
            "VALUE_DRIVER": "PASS",
            "VALUATION": "PASS",
            "FORECAST": "PASS",
        },
    )
    AUTHORITY_REGISTRY = authority_registry
    payload = {
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "002422",
        "company": "四川科伦药业股份有限公司",
        "as_of_date": "2026-10-04",
        "cutoff_date": "2026-10-04",
        "current_price_observation": {
            "price": "40.85",
            "price_observation_id": price_ref["price_observation_id"],
            "currency": "CNY",
            "observed_at": "2026-09-30T15:00:00+00:00",
            "known_at": "2026-09-30T23:59:00+00:00",
            "source": "CFi:HISTORICAL_QUOTE",
            "adjustment_semantics": "UNADJUSTED",
            "price_observation_admission_hash": price_ref["admission_record_hash"],
        },
        "company_evidence_manifest": {
            "manifest_id": "c3-kolun-evidence-v0.1",
            "evidence_source_hierarchy": "CNINFO primary company evidence + separately captured public market price",
            "evidence_ids": [item["evidence_id"] for item in fixture["evidence"]],
        },
        "trust": {"status": "PASS"},
        "reality": {
            "status": "PASS",
            "economic_structure": fixture["economic_structure"],
            "evidence_ids": ["E001", "E002", "E003", "E004"],
        },
        "forecast": {
            "status": "PASS",
            "forecast_type": "C3_SCENARIO_FORECAST",
            "assumption_classification": "EXPLICIT_MODEL_ASSUMPTION_NOT_EVIDENCE",
            "assumptions": fixture["forecast_assumptions"],
        },
        "valuation": fixture["valuation"],
        "risk": fixture["risk"],
        "portfolio": {
            "position_pct": "0",
            "constraint_status": "PASS",
            "can_add": True,
            "buy_add_package": {
                "entry_zone": ["38", "42"],
                "initial_position_pct": "5",
                "target_position_pct": "10",
                "max_position_pct": "10",
                "thesis_break_triggers": fixture["thesis"]["falsifiers"],
                "monitoring_triggers": [item["metric"] for item in fixture["monitoring"]],
            },
        },
        "thesis": thesis,
        "decision_upstream_admission": upstream,
        "return_gate": {
            "entry_price": "40.85",
            "entry_value_reference": "58",
            "horizon_years": "1",
            "horizon_override": False,
            "horizon_override_basis": [],
            "horizon_selection_rationale": "C3 uses the default 1Y decision horizon; the case does not invoke a 3Y exception.",
            "buy_entry_return_cushion_threshold": "0.15",
            "fundamental_target_annualized_return": "0.15",
            "required_return_annualized": "0.10",
            "scenarios": {
                "bear": {
                    "probability": "0.30",
                    "terminal_value_per_share": "37",
                    "cash_distributions_per_share": "0",
                    "probability_rationale": "Core pharmaceutical risk and lower biotechnology option realization.",
                },
                "base": {
                    "probability": "0.50",
                    "terminal_value_per_share": "58",
                    "cash_distributions_per_share": "0",
                    "probability_rationale": "Core pharmaceutical stabilization plus medium realization of controlled-biotech option value.",
                },
                "bull": {
                    "probability": "0.20",
                    "terminal_value_per_share": "88",
                    "cash_distributions_per_share": "0",
                    "probability_rationale": "Core business growth plus high realization of biotechnology platform value.",
                },
            },
        },
    }
    payload, FORECAST_REGISTRY, VALUATION_OUTPUT_RESOLVER = bind_return_lineage(
        payload,
        valuation_admission_registry=VALUATION_ADMISSION_REGISTRY,
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
    )
    return payload



def run() -> dict[str, Any]:
    fixture = load_case_fixture()
    registry, price_ref = admit_price()
    case = build_case(fixture, price_ref)

    decision = decide_v03(case, current_price_resolver=registry, independent_forecast_resolver=FORECAST_REGISTRY, upstream_authority_resolver=AUTHORITY_REGISTRY, valuation_output_resolver=VALUATION_OUTPUT_RESOLVER)
    if decision["action"] != "REVIEW_REQUIRED":
        raise AssertionError("C3 expected a review-required result from conditional quality")
    if decision["gates"]["new_capital_allowed"] is not False:
        raise AssertionError("C3 must not admit new capital")

    metrics = calculate_return_metrics(case["return_gate"], max_loss_pct=case["risk"]["max_loss_pct"])
    if metrics["fundamental_target_pass"] is not True:
        raise AssertionError("C3 scenario should clear the 15% annualized target on this test input")
    if metrics["required_return_pass"] is not True:
        raise AssertionError("C3 scenario should clear Required Return")
    if metrics["risk_pass"] is not True:
        raise AssertionError("C3 scenario should clear risk cap")

    # The fixture currently has source-capture anchors and a separately
    # admitted price observation, but no complete B2 company Evidence Manifest
    # with independently verified raw bytes/PIT for all required field groups.
    # Keep the economic calculation inspectable, but block all formal persistence
    # rather than promoting this legacy fixture as a canonical Run Envelope.
    return {
        "case_id": CASE_ID,
        "company": case["company"],
        "symbol": case["symbol"],
        "economic_structure": fixture["economic_structure"]["type"],
        "valuation_primary_model": fixture["valuation"]["primary_model"],
        "forecast_assumption_version": fixture["forecast_assumptions"]["version"],
        "current_price": str(PRICE),
        "decision": {
            "action": decision["action"],
            "primary_reason": decision["primary_reason"],
            "decision_status": decision["decision_status"],
            "new_capital_allowed": decision["gates"]["new_capital_allowed"],
        },
        "return_metrics": {
            "expected_annualized_return": str(metrics["expected_annualized_return"]),
            "fundamental_target_pass": metrics["fundamental_target_pass"],
            "required_return_pass": metrics["required_return_pass"],
            "risk_pass": metrics["risk_pass"],
        },
        "lifecycle": {
            "status": "BLOCKED_NOT_ADMITTED",
            "blocking_gate": "B2_EVIDENCE_PIT_ADMISSION_REQUIRED",
            "formal_decision_revision_created": False,
            "trigger_state": "NOT_RUN",
            "monitoring_evaluation_status": "NOT_RUN",
            "validation_status": "NOT_RUN",
            "decision_replay_status": "NOT_RUN",
        },
        "publication": {
            "status": "BLOCKED_NOT_ADMITTED",
            "qa_status": "BLOCKED_NOT_ADMITTED",
            "report_deterministic_replay": False,
            "publication_hash": None,
            "report_hash": None,
            "qa_hash": None,
        },
        "authority_boundary": {
            "human_approval_required": True,
            "auto_execution": False,
            "report_policy_effect": "REPORT_ONLY_PROJECTION",
            "validation_policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
