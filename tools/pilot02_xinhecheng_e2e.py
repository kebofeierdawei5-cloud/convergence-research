from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from iios_mvp.canonical_current_price import InMemoryCanonicalCurrentPriceRegistry
from iios_mvp.canonical_investment_admission_v01 import InMemoryCanonicalInvestmentAdmissionRegistry
from iios_mvp.canonical_independent_forecast import InMemoryCanonicalIndependentForecastRegistry
from iios_mvp.forecast_valuation_return_lineage_v01 import InMemoryCanonicalValuationOutputResolver
from iios_mvp.decision_admission import admit_canonical_decision
from iios_mvp.human_report import build_human_report, qa_human_report, write_human_report
from iios_mvp.investment_core_contract_v03 import calculate_return_metrics, decide_v03
from iios_mvp.machine_publication import write_machine_publication
from iios_mvp.market_model_identification import MarketValuationObservation
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)
from iios_mvp.store import (
    apply_monitoring_event,
    create_or_load_series,
    initialize_monitoring_state,
    replay_decision_lifecycle,
    write_decision_revision,
    write_monitoring_validation,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
)
from iios_mvp.engine import sha256_obj
from tests.b03b_upstream_authority_fixture import build_runtime_upstream_authority
from tests.b04b_return_lineage_fixture import bind_return_lineage

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "RC-CN-A-002001-20261007"
CUTOFF = date(2026, 10, 7)
PRICE_DATE = date(2026, 9, 30)
PRICE = Decimal("25.95")


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture() -> dict[str, Any]:
    path = ROOT / "examples/real_cases/RC-CN-A-002001-20261007_pilot02_input.json"
    payload = _load_json(path)
    if payload["case_id"] != CASE_ID:
        raise ValueError("PILOT-02 fixture case_id mismatch")
    if payload["cutoff_date"] != str(CUTOFF):
        raise ValueError("PILOT-02 fixture cutoff mismatch")
    if payload["research_weighting"] != {
        "cyclical": "0.70",
        "growth": "0.30",
        "financial_sector_inclusion": False,
        "classification": "USER_REQUESTED_RESEARCH_WEIGHTING_NOT_EVIDENCE",
    }:
        raise ValueError("PILOT-02 user weighting contract drift")
    if payload["security_classification"] != "NON_FINANCIAL":
        raise ValueError("PILOT-02 non-financial classification drift")
    return payload


def admit_price(price_path: Path, receipt: dict[str, Any]) -> tuple[InMemoryCanonicalCurrentPriceRegistry, dict[str, Any]]:
    raw = price_path.read_bytes()
    if _sha_file(price_path) != receipt["price_sha256"]:
        raise ValueError("price raw-byte SHA mismatch")
    if not receipt["price_exact_bytes"]:
        raise ValueError("price bytes not marked exact")
    payload = _load_json(price_path)
    try:
        node = payload["data"]["sz002001"]
        bars = node.get("day") or node.get("qfqday") or node.get("hfqday")
    except (KeyError, TypeError) as exc:
        raise ValueError("unexpected Tencent historical-price payload") from exc
    if not isinstance(bars, list):
        raise ValueError("Tencent historical-price bars missing")
    price_row = next((row for row in bars if row and str(row[0]).strip() == PRICE_DATE.isoformat()), None)
    if price_row is None:
        raise ValueError("no 2026-09-30 close in supplied market evidence")
    if len(price_row) < 3:
        raise ValueError("Tencent historical-price row missing close field")
    close = Decimal(str(price_row[2]))
    if close != PRICE:
        raise ValueError(f"unexpected 2026-09-30 close: {close}")

    registry = InMemoryCanonicalCurrentPriceRegistry()
    known_at = datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc)
    evidence = VerifiedMarketEvidence(
        evidence_id="E005",
        variable="market_price",
        unit="CNY/share",
        basis="Tencent Finance historical daily close for 2026-09-30, unadjusted K-line",
        observation_date=PRICE_DATE,
        known_at=known_at,
        source="TENCENT_FINANCE:HISTORICAL_KLINE",
        source_location=receipt["price_source_ref"],
        content_sha256=receipt["price_sha256"],
        exact_bytes=True,
        status=AdmissionStatus.ADMITTED,
        temporal_provenance=TemporalProvenance.CONTEMPORANEOUS_PUBLICATION,
        value=PRICE,
    )
    observation = MarketValuationObservation(
        observation_id="market-observation-002001-20260930",
        observation_date=PRICE_DATE,
        known_at=known_at,
        price=PRICE,
        shares_outstanding=Decimal("3073421680"),
        economic_variable="h1_net_profit",
        economic_value=Decimal("4010733454.55"),
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
        symbol="002001",
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=evidence,
        observed_at=datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    ).to_dict()
    return registry, ref


def build_case(fixture: dict[str, Any], price_ref: dict[str, Any]):
    quality = {
        "dimensions": [
            {
                "dimension": "competitive_advantage",
                "status": "PASS",
                "rationale": "Diversified nutrition, fragrance and new-material product platforms with large overseas revenue exposure are established in the H1 company report.",
                "evidence_ids": ["E002", "E003"],
            },
            {
                "dimension": "incremental_return_on_capital",
                "status": "CONDITIONAL",
                "rationale": "The pilot has sufficient economic anchors but does not contain a full PIT project-level incremental-ROIC bridge for the expansion program.",
                "evidence_ids": ["E002", "E004"],
            },
            {
                "dimension": "earnings_quality",
                "status": "PASS",
                "rationale": "H1 reported profit, adjusted profit and operating cash flow are all established from the same primary company report.",
                "evidence_ids": ["E002"],
            },
            {
                "dimension": "cash_flow_conversion",
                "status": "PASS",
                "rationale": "H1 operating cash flow grew 12.26% while reported profit grew 11.31%; this is supportive but not a full-cycle normalization proof.",
                "evidence_ids": ["E002"],
            },
            {
                "dimension": "balance_sheet_resilience",
                "status": "PASS",
                "rationale": "The H1 report records a 24.96% debt ratio, CNY 7.46bn cash and CNY 46.69bn total assets.",
                "evidence_ids": ["E004"],
            },
            {
                "dimension": "reinvestment_runway",
                "status": "PASS",
                "rationale": "The company has identifiable product and capacity expansion paths in new materials and nutrition-related businesses.",
                "evidence_ids": ["E003", "E004"],
            },
        ]
    }
    thesis = dict(fixture["thesis"])
    authority_registry, upstream = build_runtime_upstream_authority(
        case_id=CASE_ID,
        market="CN-A",
        symbol="002001",
        company="浙江新和成股份有限公司",
        cutoff_date=CUTOFF,
        reality={
            "status": "PASS",
            "economic_structure": fixture["economic_structure"],
            "evidence_ids": ["E001", "E002", "E003", "E004"],
        },
        quality=quality,
        value_driver={
            "status": "PASS",
            "drivers": thesis["key_driver_ids"],
            "evidence_ids": thesis["evidence_ids"],
        },
        valuation=fixture["valuation"],
        forecast={
            "status": "PASS",
            "forecast_assumptions": fixture["forecast_assumptions"],
            "evidence_ids": ["E002", "E003", "E004"],
        },
        thesis=thesis,
        declared_statuses={
            "REALITY": "PASS",
            "QUALITY": "CONDITIONAL",
            "VALUE_DRIVER": "PASS",
            "VALUATION": "PASS",
            "FORECAST": "PASS",
        },
    )

    payload = {
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "002001",
        "company": "浙江新和成股份有限公司",
        "as_of_date": "2026-10-07",
        "cutoff_date": "2026-10-07",
        "current_price_observation": {
            "price": "25.95",
            "price_observation_id": price_ref["price_observation_id"],
            "currency": "CNY",
            "observed_at": "2026-09-30T15:00:00+00:00",
            "known_at": "2026-09-30T23:59:00+00:00",
            "source": "TENCENT_FINANCE:HISTORICAL_KLINE",
            "adjustment_semantics": "UNADJUSTED",
            "price_observation_admission_hash": price_ref["admission_record_hash"],
            "as_of_note": "2026-10-07 is a non-trading day; 2026-09-30 is the latest tradable close.",
        },
        "company_evidence_manifest": {
            "manifest_id": "pilot02-xinhecheng-evidence-v0.1",
            "evidence_source_hierarchy": "CNINFO primary company evidence + reproducible public market price",
            "evidence_ids": [item["evidence_id"] for item in fixture["evidence"]],
        },
        "trust": {"status": "REVALIDATION"},
        "reality": {
            "status": "PASS",
            "economic_structure": fixture["economic_structure"],
            "evidence_ids": ["E001", "E002", "E003", "E004"],
        },
        "forecast": {
            "status": "PASS",
            "forecast_type": fixture["forecast_assumptions"]["method"],
            "assumption_classification": fixture["forecast_assumptions"]["classification"],
            "assumptions": fixture["forecast_assumptions"],
        },
        "valuation": fixture["valuation"],
        "risk": fixture["risk"],
        "portfolio": fixture["portfolio"],
        "thesis": thesis,
        "decision_upstream_admission": upstream,
        "return_gate": {
            "entry_price": "25.95",
            "entry_value_reference": "32.20",
            "horizon_years": "1",
            "horizon_override": False,
            "horizon_override_basis": [],
            "horizon_selection_rationale": "PILOT-02 uses the default 1Y decision horizon.",
            "buy_entry_return_cushion_threshold": "0.15",
            "fundamental_target_annualized_return": "0.15",
            "required_return_annualized": "0.10",
            "scenarios": {
                name: {
                    "probability": fixture["forecast_assumptions"]["scenarios"][name]["probability_weight"] if "probability_weight" in fixture["forecast_assumptions"]["scenarios"][name] else {"bear": "0.30", "base": "0.50", "bull": "0.20"}[name],
                    "terminal_value_per_share": fixture["forecast_assumptions"]["scenarios"][name]["value_per_share"],
                    "cash_distributions_per_share": "0",
                    "probability_rationale": fixture["forecast_assumptions"]["scenarios"][name]["rationale"],
                }
                for name in ("bear", "base", "bull")
            },
        },
    }
    payload, forecast_registry, valuation_resolver = bind_return_lineage(payload)
    return payload, authority_registry, forecast_registry, valuation_resolver


def run(*, report_path: Path, price_path: Path, receipt_path: Path, out_dir: Path) -> dict[str, Any]:
    fixture = load_fixture()
    receipt = _load_json(receipt_path)

    if receipt["case_id"] != CASE_ID:
        raise ValueError("receipt case mismatch")
    if receipt["cutoff_date"] != str(CUTOFF):
        raise ValueError("receipt cutoff mismatch")
    if receipt["report_exact_bytes"] is not True:
        raise ValueError("report exact-byte flag missing")
    if _sha_file(report_path) != receipt["report_sha256"]:
        raise ValueError("report raw-byte SHA mismatch")
    if receipt["latest_tradable_date"] != "2026-09-30":
        raise ValueError("latest tradable date mismatch")
    if receipt["price"] != "25.95":
        raise ValueError("price receipt mismatch")

    registry, price_ref = admit_price(price_path, receipt)
    case, authority_registry, forecast_registry, valuation_resolver = build_case(fixture, price_ref)

    decision = decide_v03(
        case,
        current_price_resolver=registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=authority_registry,
        valuation_output_resolver=valuation_resolver,
    )
    metrics = calculate_return_metrics(case["return_gate"], max_loss_pct=case["risk"]["max_loss_pct"])

    if decision["action"] != "REVIEW_REQUIRED":
        raise AssertionError("PILOT-02 expected REVIEW_REQUIRED from Trust REVALIDATION / Quality CONDITIONAL")
    if decision["gates"]["new_capital_allowed"] is not False:
        raise AssertionError("PILOT-02 must not admit new capital")
    if metrics["fundamental_target_pass"] is not True or metrics["required_return_pass"] is not True:
        raise AssertionError("PILOT-02 model test did not clear expected return gates")
    if metrics["risk_pass"] is not True:
        raise AssertionError("PILOT-02 bear-case risk test failed")

    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="iios-pilot02-xhc-") as tmp:
        root = Path(tmp)
        series = create_or_load_series(
            root,
            "CN-A",
            "002001",
            "浙江新和成股份有限公司",
            "2026-10-07T10:00:00+08:00",
        )
        snapshot = {
            "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
            "engine_version": "0.3.0",
            "input": {
                "case_id": CASE_ID,
                "market": "CN-A",
                "symbol": "002001",
                "company": "浙江新和成股份有限公司",
                "as_of_date": "2026-10-07",
                "cutoff_date": "2026-10-07",
                "research_weighting": fixture["research_weighting"],
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
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=authority_registry,
            valuation_output_resolver=valuation_resolver,
        )
        decision_path = write_decision_revision(
            root,
            series["decision_series_id"],
            1,
            snapshot,
            "run-pilot02-xhc-001",
            decision_admission=decision_admission,
        )
        decision_record = json.loads(decision_path.read_text(encoding="utf-8"))

        trigger = {
            "trigger_id": "tr-pilot02-002001-01",
            "decision_id": decision_record["decision_id"],
            "decision_series_id": decision_record["decision_series_id"],
            "revision": decision_record["revision"],
            "decision_revision_hash": decision_record["revision_hash"],
            "case_id": CASE_ID,
            "decision_cutoff_date": "2026-10-07",
            "role": "MONITORING",
            "metric_id": "nutrition_product_cycle",
            "operator": "EQ",
            "target": "PASS",
            "unit": "status",
            "evidence_ids": ["E002", "E003"],
            "enabled": True,
        }
        trigger_record = json.loads(write_trigger_contract(root, decision_record["decision_id"], trigger).read_text(encoding="utf-8"))
        event_record = json.loads(
            write_trigger_event(
                root,
                {
                    "trigger_id": trigger_record["trigger_id"],
                    "trigger_event_id": "evt-pilot02-002001-01",
                    "evaluation_cutoff_at": "2026-10-07T10:00:00+08:00",
                    "observed_at": "2026-06-30T00:00:00+00:00",
                    "known_at": "2026-08-20T00:00:00+08:00",
                    "source_id": "CNINFO:2026_H1_REPORT",
                    "evidence_id": "E002",
                    "value": "PASS",
                    "previous_value": "PASS",
                },
            ).read_text(encoding="utf-8")
        )
        if event_record["trigger_state"] != "MATCHED":
            raise AssertionError("PILOT-02 monitoring event did not match")

        monitor_path = initialize_monitoring_state(
            root,
            trigger_record["trigger_id"],
            "monitor-pilot02-002001-01",
            lifecycle_status="ACTIVE",
            next_due_at="2026-11-07T00:00:00+08:00",
            evaluation_reference_at="2026-10-07T10:00:00+08:00",
        )
        apply_monitoring_event(root, event_record["trigger_event_id"], next_due_at="2026-11-07T00:00:00+08:00")
        monitor = json.loads(monitor_path.read_text(encoding="utf-8"))

        validation = json.loads(
            write_monitoring_validation(
                root,
                trigger_record["trigger_id"],
                "2026-10-07T10:30:00+08:00",
                validation_id="validation-pilot02-002001-01",
            ).read_text(encoding="utf-8")
        )
        if validation["validation_status"] != "PASS":
            raise AssertionError(f"PILOT-02 validation failed: {validation}")

        replay = replay_decision_lifecycle(root, decision_record["decision_id"])
        if replay["replay_status"] != "PASS":
            raise AssertionError("PILOT-02 lifecycle replay failed")

        publication_path = write_machine_publication(
            root,
            decision_id=decision_record["decision_id"],
            published_at="2026-10-07T10:00:00+08:00",
        )
        publication = json.loads(publication_path.read_text(encoding="utf-8"))
        if publication["case"]["symbol"] != "002001":
            raise AssertionError("PILOT-02 publication symbol binding failed")
        if publication["decision_ref"]["revision_hash"] != decision_record["revision_hash"]:
            raise AssertionError("PILOT-02 publication decision binding failed")

        report = build_human_report(
            publication=publication,
            generated_at="2026-10-07T10:05:00+08:00",
        )
        qa = qa_human_report(publication=publication, report=report)
        if qa["qa_status"] != "PASS":
            raise AssertionError(f"PILOT-02 report QA failed: {qa}")
        if build_human_report(publication=publication, generated_at="2026-10-07T10:05:00+08:00") != report:
            raise AssertionError("PILOT-02 human report replay mismatch")

        report_path_out, qa_path = write_human_report(
            root,
            publication_path=publication_path,
            generated_at="2026-10-07T10:05:00+08:00",
        )
        # Persist only derived test artifacts, never raw authority state.
        for source in (
            publication_path,
            report_path_out,
            qa_path,
            decision_path,
        ):
            target = out_dir / source.name
            target.write_bytes(source.read_bytes())

        result = {
            "pilot": "PILOT-02",
            "case_id": CASE_ID,
            "company": "浙江新和成股份有限公司",
            "symbol": "002001",
            "cutoff_date": str(CUTOFF),
            "latest_tradable_date": "2026-09-30",
            "current_price": str(PRICE),
            "security_classification": "NON_FINANCIAL",
            "research_weighting": fixture["research_weighting"],
            "quality_gate_status": decision["gates"]["quality_gate"],
            "trust_status": case["trust"]["status"],
            "return_metrics": {
                "entry_return_cushion": str(metrics["entry_return_cushion"]),
                "margin_of_safety": str(metrics["margin_of_safety"]),
                "expected_total_return": str(metrics["expected_total_return"]),
                "expected_annualized_return": str(metrics["expected_annualized_return"]),
                "fundamental_target_pass": metrics["fundamental_target_pass"],
                "required_return_pass": metrics["required_return_pass"],
                "risk_pass": metrics["risk_pass"],
                "target_entry_price": str(metrics["target_entry_price"]),
            },
            "decision": {
                "action": decision["action"],
                "decision_status": decision["decision_status"],
                "primary_reason": decision["primary_reason"],
                "new_capital_allowed": decision["gates"]["new_capital_allowed"],
                "human_approval_required": decision["human_approval_required"],
                "auto_execution": decision["auto_execution"],
            },
            "lifecycle": {
                "decision_revision": decision_record["revision"],
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
            "evidence": {
                "report_sha256": receipt["report_sha256"],
                "price_sha256": receipt["price_sha256"],
                "report_exact_bytes": receipt["report_exact_bytes"],
                "price_exact_bytes": receipt["price_exact_bytes"],
            },
        }
        (out_dir / "PILOT-02_XINHECHENG_RESULT.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        # Print the actual human report for operator review in CI logs.
        print("\n===== PILOT-02 HUMAN REPORT =====")
        print((out_dir / report_path_out.name).read_text(encoding="utf-8"))
        print("===== PILOT-02 RESULT =====")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--price", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(
        report_path=args.report,
        price_path=args.price,
        receipt_path=args.receipt,
        out_dir=args.out,
    )


if __name__ == "__main__":
    main()
