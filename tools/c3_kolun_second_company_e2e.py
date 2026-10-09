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

    with tempfile.TemporaryDirectory(prefix="iios-c3-002422-") as tmp:
        root = Path(tmp)
        series = create_or_load_series(
            root, "CN-A", "002422", "四川科伦药业股份有限公司", "2026-10-06T10:00:00+08:00"
        )
        snapshot = {
            "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
            "engine_version": "0.3.0",
            "input": {
                "case_id": CASE_ID,
                "market": "CN-A",
                "symbol": "002422",
                "company": "四川科伦药业股份有限公司",
                "as_of_date": "2026-10-04",
                "cutoff_date": "2026-10-04",
            },
            "decision": {
                **decision,
                "economic_structure": fixture["economic_structure"],
                "forecast": fixture["forecast_assumptions"],
                "valuation": fixture["valuation"],
                "risk": fixture["risk"],
                "thesis": fixture["thesis"],
                "monitoring": fixture["monitoring"],
                "evidence_chain": fixture["evidence"],
            },
        }
        snapshot["snapshot_hash"] = sha256_obj({
            "snapshot_schema": snapshot["snapshot_schema"],
            "engine_version": snapshot["engine_version"],
            "input": snapshot["input"],
            "decision": snapshot["decision"],
        })
        snapshot_path = write_snapshot(root, snapshot)
        decision_admission = admit_canonical_decision(
            case=case,
            snapshot=snapshot,
            current_price_resolver=registry,
            independent_forecast_resolver=FORECAST_REGISTRY,
            upstream_authority_resolver=AUTHORITY_REGISTRY,
            valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
        )
        try:
            decision_path = write_decision_revision(
                root,
                series["decision_series_id"],
                1,
                snapshot,
                "run-c3-kolun-001",
                decision_admission=decision_admission,
            )
        except ValueError as exc:
            if "CANONICAL_RUN_AUTHORIZATION_BLOCKED" not in str(exc):
                raise
            # This runner uses fixture-bound upstream producers. Until a real
            # canonical orchestrator receipt is supplied, it may report the
            # kernel proposal for diagnostics but must not create a formal
            # Decision Revision, Publication, or Investor Report.
            return {
                "status": "BLOCKED_NON_CANONICAL",
                "block_reason": "CANONICAL_RUN_AUTHORIZATION_BLOCKED",
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
                "formal_artifacts_written": False,
                "authority_boundary": {
                    "human_approval_required": True,
                    "auto_execution": False,
                    "report_policy_effect": "NOT_RUN_NON_CANONICAL",
                    "validation_policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
                },
            }
        decision_record = json.loads(decision_path.read_text(encoding="utf-8"))

        trigger = {
            "trigger_id": "tr-c3-002422-01",
            "decision_id": decision_record["decision_id"],
            "decision_series_id": decision_record["decision_series_id"],
            "revision": decision_record["revision"],
            "decision_revision_hash": decision_record["revision_hash"],
            "case_id": CASE_ID,
            "decision_cutoff_date": "2026-10-04",
            "role": "MONITORING",
            "metric_id": "core_pharma_cash_flow_conversion",
            "operator": "EQ",
            "target": "PASS",
            "unit": "status",
            "evidence_ids": ["E002"],
            "enabled": True,
        }
        trigger_path = write_trigger_contract(root, decision_record["decision_id"], trigger)
        trigger_record = json.loads(trigger_path.read_text(encoding="utf-8"))

        event_path = write_trigger_event(
            root,
            {
                "trigger_id": trigger_record["trigger_id"],
                "trigger_event_id": "evt-c3-002422-01",
                "evaluation_cutoff_at": "2026-10-06T10:00:00+08:00",
                "observed_at": "2026-06-30T00:00:00+00:00",
                "known_at": "2026-08-27T00:00:00+00:00",
                "source_id": "CNINFO:2026_H1_REPORT",
                "evidence_id": "E002",
                "value": "PASS",
                "previous_value": "PASS",
            },
        )
        event_record = json.loads(event_path.read_text(encoding="utf-8"))
        if event_record["trigger_state"] != "MATCHED":
            raise AssertionError("C3 monitoring event did not match")

        monitor_path = initialize_monitoring_state(
            root,
            trigger_record["trigger_id"],
            "monitor-c3-002422-01",
            lifecycle_status="ACTIVE",
            next_due_at="2026-11-04T00:00:00+00:00",
            evaluation_reference_at="2026-10-06T10:00:00+08:00",
        )
        apply_monitoring_event(
            root,
            event_record["trigger_event_id"],
            next_due_at="2026-11-04T00:00:00+08:00",
        )
        monitor = json.loads(monitor_path.read_text(encoding="utf-8"))
        validation_path = write_monitoring_validation(
            root,
            trigger_record["trigger_id"],
            "2026-10-06T10:30:00+08:00",
            validation_id="validation-c3-002422-01",
        )
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        if validation["validation_status"] != "PASS":
            raise AssertionError(f"C3 TR-03 validation did not pass: {validation}")

        replay = replay_decision_lifecycle(root, decision_record["decision_id"])
        if replay["replay_status"] != "PASS":
            raise AssertionError("C3 decision lifecycle replay failed")

        publication_path = write_machine_publication(
            root,
            decision_id=decision_record["decision_id"],
            published_at="2026-10-06T10:00:00+08:00",
        )
        publication = json.loads(publication_path.read_text(encoding="utf-8"))
        if publication["case"]["symbol"] != "002422":
            raise AssertionError("C3 publication case binding failed")
        if publication["decision_ref"]["revision_hash"] != decision_record["revision_hash"]:
            raise AssertionError("C3 publication revision binding failed")
        if len(publication["lifecycle_refs"]["trigger_contracts"]) != 1:
            raise AssertionError("C3 publication trigger reference missing")
        if len(publication["lifecycle_refs"]["monitoring_states"]) != 1:
            raise AssertionError("C3 publication monitoring reference missing")
        if len(publication["lifecycle_refs"]["validation_records"]) != 1:
            raise AssertionError("C3 publication validation reference missing")

        report = build_human_report(
            publication=publication,
            generated_at="2026-10-06T10:05:00+08:00",
        )
        qa = qa_human_report(publication=publication, report=report)
        if qa["qa_status"] != "PASS":
            raise AssertionError(f"C3 report QA failed: {qa}")
        replay_report = build_human_report(
            publication=publication,
            generated_at="2026-10-06T10:05:00+08:00",
        )
        if replay_report != report:
            raise AssertionError("C3 human report deterministic replay failed")

        report_path, qa_path = write_human_report(
            root,
            publication_path=publication_path,
            generated_at="2026-10-06T10:05:00+08:00",
        )
        if report_path.exists() is not True or qa_path.exists() is not True:
            raise AssertionError("C3 immutable report artifacts were not persisted")

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
                "decision_revision": decision_record["revision"],
                "trigger_state": event_record["trigger_state"],
                "monitoring_evaluation_status": monitor["evaluation_status"],
                "validation_status": validation["validation_status"],
                "decision_replay_status": replay["replay_status"],
            },
            "publication": {
                "publication_hash": publication["publication_hash"],
                "report_hash": report["report_hash"],
                "qa_status": qa["qa_status"],
                "qa_hash": qa["qa_hash"],
                "report_deterministic_replay": True,
            },
            "authority_boundary": {
                "human_approval_required": decision["human_approval_required"],
                "auto_execution": decision["auto_execution"],
                "report_policy_effect": qa["policy_effect"],
                "validation_policy_effect": validation["policy_effect"],
            },
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
