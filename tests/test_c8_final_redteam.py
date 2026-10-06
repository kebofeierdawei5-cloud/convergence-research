from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from iios_mvp.canonical_current_price import InMemoryCanonicalCurrentPriceRegistry
from iios_mvp.canonical_independent_forecast import InMemoryCanonicalIndependentForecastRegistry
from iios_mvp.decision_lifecycle_production import build_human_approval, validate_human_approval
from iios_mvp.decision_state_machine_v01 import DecisionStateInputs, evaluate_decision_state
from iios_mvp.execution_receipt_production import build_execution_receipt
from iios_mvp.human_report import build_human_report, qa_human_report, validate_human_report
from iios_mvp.market_model_identification import MarketValuationObservation
from iios_mvp.market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)
from iios_mvp.machine_publication import build_machine_publication, validate_machine_publication
from iios_mvp.semantic_expectation_gap import evaluate_expectation_gap
from iios_mvp.store import (
    apply_monitoring_event,
    create_or_load_series,
    initialize_monitoring_state,
    replay_monitoring_state,
    write_decision_revision,
    write_snapshot,
    write_trigger_event,
)
from tests.test_c7_full_lifecycle_e2e import make_snapshot, seed_c7


ROOT = Path(__file__).resolve().parents[1]
CATL_CASE = "RC-CN-A-300750-20261004"
KOLUN_CASE = "RC-CN-A-002422-20261004"
CUTOFF = date(2026, 10, 4)


def _sha(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _minimal_snapshot(*, case_id: str, symbol: str, company: str, action: str) -> dict:
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id,
            "market": "CN-A",
            "symbol": symbol,
            "company": company,
            "as_of_date": "2026-10-04",
            "cutoff_date": "2026-10-04",
        },
        "decision": {
            "action": action,
            "decision_status": "READY",
            "primary_reason": "C8 adversarial crafted snapshot",
            "gates": {
                "trust": "FAIL",
                "quality_gate": "UNKNOWN",
                "reality": "UNKNOWN",
                "valuation": "UNKNOWN",
                "forecast": "UNKNOWN",
                "new_capital_allowed": False,
            },
            "return_metrics": {
                "fundamental_target_pass": False,
                "required_return_pass": False,
                "risk_pass": False,
            },
        },
    }
    return {**core, "snapshot_hash": _sha(core)}


def _admitted_price(
    *,
    case_id: str,
    symbol: str,
    known_at: datetime,
) -> InMemoryCanonicalCurrentPriceRegistry:
    registry = InMemoryCanonicalCurrentPriceRegistry()
    evidence_id = f"C8-PRICE-{symbol}"
    evidence_sha = hashlib.sha256(f"{case_id}-{symbol}".encode("utf-8")).hexdigest()
    evidence = VerifiedMarketEvidence(
        evidence_id=evidence_id,
        variable="market_price",
        unit="CNY/share",
        basis="C8 historical test fixture",
        observation_date=date(2026, 9, 30),
        known_at=known_at,
        source="C8:TEST_EVIDENCE",
        source_location="C8 synthetic fixture",
        content_sha256=evidence_sha,
        exact_bytes=True,
        status=AdmissionStatus.ADMITTED,
        temporal_provenance=TemporalProvenance.SOURCE_VINTAGE,
        value=Decimal("40.85"),
    )
    observation = MarketValuationObservation(
        observation_id=f"c8-market-{symbol}",
        observation_date=date(2026, 9, 30),
        known_at=known_at,
        price=Decimal("40.85"),
        shares_outstanding=Decimal("1000000000"),
        economic_variable="net_profit",
        economic_value=Decimal("1000000000"),
        unit="CNY",
        basis="C8 synthetic",
        evidence_ids=(evidence_id,),
        source="C8:TEST_EVIDENCE",
        net_debt=Decimal("0"),
    )
    admission = MarketObservationAdmission(
        status=AdmissionStatus.ADMITTED,
        observation=observation,
        evidence_ids=(evidence_id,),
    )
    registry.admit_current_price(
        case_id=case_id,
        market="CN-A",
        symbol=symbol,
        cutoff_date=CUTOFF,
        admission=admission,
        price_evidence=evidence,
        observed_at=datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
    )
    return registry


def test_c8_real_company_fixture_set_contains_catl_and_kolun():
    catl = json.loads(
        (ROOT / "examples/real_cases/RC-CN-A-300750-20261004_core03_input.json").read_text(encoding="utf-8")
    )
    kolun = json.loads(
        (ROOT / "examples/real_cases/RC-CN-A-002422-20261004_c3_input.json").read_text(encoding="utf-8")
    )
    assert catl["case_id"] == CATL_CASE
    assert kolun["case_id"] == KOLUN_CASE


def test_c8_current_price_pit_leak_is_rejected():
    with pytest.raises(ValueError):
        _admitted_price(
            case_id=KOLUN_CASE,
            symbol="002422",
            known_at=datetime(2026, 10, 5, 0, 1, tzinfo=timezone.utc),
        )


def test_c8_independent_forecast_pit_leak_is_rejected():
    registry = InMemoryCanonicalIndependentForecastRegistry()
    payload = {
        "case_id": KOLUN_CASE,
        "market": "CN-A",
        "symbol": "002422",
        "cutoff_date": "2026-10-04",
        "forecast_id": "c8-pit-leak",
        "forecast_version": "C8-TEST-0.1",
        "model_version": "C8-TEST-MODEL",
        "variable_id": "net_profit",
        "value": "100",
        "unit": "CNY_bn",
        "basis": "FY2027E",
        "horizon_years": "1",
        "forecast_origin": "2026-09-20T00:00:00+00:00",
        "known_at": "2026-10-05T00:00:00+00:00",
        "prepared_without_current_price": True,
        "evidence_ids": ["C8-E1"],
    }
    with pytest.raises(ValueError):
        registry.admit_independent_forecast(payload)


def test_c8_expectation_gap_unit_mismatch_refuses_scalar_gap():
    result = evaluate_expectation_gap(
        independent_expectation={
            "variable_id": "net_profit",
            "value": "120",
            "unit": "CNY_bn",
            "basis": "FY2027E",
            "horizon_years": "1",
        },
        market_expectation={
            "qualification": "DECISION_GRADE",
            "resolution_state": "UNIQUE_MODEL",
            "variable_id": "net_profit",
            "value": "100",
            "unit": "USD_bn",
            "basis": "FY2027E",
            "horizon_years": "1",
        },
        comparison_direction="HIGHER_IS_BETTER",
    )
    assert result["status"] == "INCOMPATIBLE"
    assert result["gap_relative"] is None


def test_c8_mie_non_unique_refuses_scalar_gap():
    result = evaluate_expectation_gap(
        independent_expectation={
            "variable_id": "net_profit",
            "value": "120",
            "unit": "CNY_bn",
            "basis": "FY2027E",
            "horizon_years": "1",
        },
        market_expectation={
            "qualification": "DECISION_GRADE",
            "resolution_state": "AMBIGUOUS",
            "variable_id": "net_profit",
            "value": "100",
            "unit": "CNY_bn",
            "basis": "FY2027E",
            "horizon_years": "1",
        },
        comparison_direction="HIGHER_IS_BETTER",
    )
    assert result["status"] == "AMBIGUOUS"
    assert result["gap_relative"] is None


def test_c8_return_and_required_return_fail_closed():
    state = evaluate_decision_state(
        DecisionStateInputs(
            validation_pass=True,
            trust_status="PASS",
            thesis_status="INTACT",
            reality_status="PASS",
            quality_gate_status="PASS",
            value_driver_status="PASS",
            valuation_status="PASS",
            forecast_status="PASS",
            thesis_admission_status="ADMITTED",
            risk_status="PASS",
            portfolio_status="PASS",
            position_pct=Decimal("0"),
            gap_status="PASS",
            gap_positive=True,
            expected_annualized_return=Decimal("0.10"),
            return_gate_pass=False,
            risk_gate_pass=True,
            can_add=True,
            package_complete=True,
            return_metrics_ready=True,
        )
    )
    assert state["new_capital_allowed"] is False
    assert state["action"] in {"WATCH", "REVIEW_REQUIRED", "NO-BUY"}


def test_c8_revision_overwrite_is_rejected(tmp_path):
    series, _, revision_path, _, _ = seed_c7(tmp_path)
    original = revision_path.read_bytes()
    forged = make_snapshot(
        case_id=CATL_CASE,
        cutoff_date="2026-10-04",
        action="EXIT",
        reason="overwrite attempt",
    )
    with pytest.raises(ValueError):
        write_decision_revision(
            tmp_path,
            series["decision_series_id"],
            1,
            forged,
            "c8-overwrite",
        )
    assert revision_path.read_bytes() == original


def test_c8_approval_cross_revision_mismatch_is_rejected(tmp_path):
    _, snapshot, revision_path, _, _ = seed_c7(tmp_path)
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    bad = {
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.1",
        "decision_id": revision["decision_id"],
        "revision": revision["revision"],
        "revision_hash": "0" * 64,
        "snapshot_hash": snapshot["snapshot_hash"],
        "approved": True,
        "approval_status": "HUMAN_APPROVED",
        "note": "forged approval",
        "approval_hash": "0" * 64,
    }
    with pytest.raises(ValueError):
        validate_human_approval(bad, decision_revision=revision)


def test_c8_monitoring_history_tamper_is_detected(tmp_path):
    _, _, _, _, trigger_path = seed_c7(tmp_path)
    trigger = json.loads(trigger_path.read_text(encoding="utf-8"))
    initialize_monitoring_state(
        tmp_path,
        trigger["trigger_id"],
        "c8-monitor",
        next_due_at="2026-10-08T00:00:00+00:00",
        evaluation_reference_at="2026-10-04T00:00:00+00:00",
    )
    write_trigger_event(
        tmp_path,
        {
            "trigger_id": trigger["trigger_id"],
            "trigger_event_id": "c8-event",
            "evaluation_cutoff_at": "2026-10-06T10:00:00+00:00",
            "observed_at": "2026-10-05T10:00:00+00:00",
            "known_at": "2026-10-05T10:05:00+00:00",
            "source_id": "C8:TEST",
            "evidence_id": "C8-EVENT",
            "value": "349",
            "previous_value": "355",
        },
    )
    apply_monitoring_event(tmp_path, "c8-event")
    event_path = tmp_path / "c8-event.event.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["value"] = "999"
    event_path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        replay_monitoring_state(tmp_path, trigger["trigger_id"])


def test_c8_publication_report_drift_is_detected(tmp_path):
    _, snapshot, revision_path, approval, _ = seed_c7(tmp_path)
    assert approval["status"] == "HUMAN_APPROVED"
    publication = build_machine_publication(
        root=tmp_path,
        decision_id="CN-A-300750-r001",
        published_at="2026-10-06T11:00:00+00:00",
    )
    report = build_human_report(
        publication=publication,
        generated_at="2026-10-06T11:00:00+00:00",
    )
    validate_human_report(report)
    assert qa_human_report(publication=publication, report=report)["qa_status"] == "PASS"

    drifted = deepcopy(report)
    drifted["markdown"] += "\nC8 drift"
    with pytest.raises(ValueError):
        validate_human_report(drifted)
    assert revision_path.exists()
    assert snapshot["snapshot_hash"] == publication["decision_ref"]["snapshot_hash"]


def test_c8_execution_receipt_requires_human_approved():
    revision = {
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.1",
        "decision_id": "CN-A-300750-r001",
        "decision_series_id": "CN-A-300750",
        "revision": 1,
        "run_id": "c8",
        "trigger_event_id": None,
        "case_id": CATL_CASE,
        "as_of_date": "2026-10-04",
        "cutoff_date": "2026-10-04",
        "snapshot_hash": "0" * 64,
        "ai_action": "BUY",
        "decision_status": "AI_PROPOSED",
        "engine_version": "0.3.0",
        "human_approval_required": True,
        "auto_execution": False,
    }
    from iios_mvp.decision_lifecycle_production import _sha
    revision["revision_hash"] = _sha({k: revision[k] for k in revision if k != "revision_hash"})
    approval = {
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.1",
        "decision_id": revision["decision_id"],
        "revision": 1,
        "revision_hash": revision["revision_hash"],
        "snapshot_hash": revision["snapshot_hash"],
        "approved": False,
        "approval_status": "HUMAN_REJECTED",
        "note": "not approved",
    }
    approval["approval_hash"] = _sha({k: approval[k] for k in approval if k != "approval_hash"})
    with pytest.raises(ValueError):
        build_execution_receipt(
            execution_receipt_id="c8-execution",
            decision_revision=revision,
            human_approval=approval,
            executed_at="2026-10-06T10:00:00+00:00",
            execution_status="EXECUTED",
            actor_identity="human:c8",
            executed_quantity="1",
            executed_position_pct="1",
            executed_price="1",
        )


def test_c8_crafted_revision_can_bypass_kernel():
    with TemporaryDirectory(prefix="iios-c8-authority-") as tmp:
        root = Path(tmp)
        series = create_or_load_series(root, "CN-A", "300750", "宁德时代", "2026-10-06T00:00:00+00:00")
        forged = _minimal_snapshot(case_id=CATL_CASE, symbol="300750", company="宁德时代", action="BUY")
        write_snapshot(root, forged)
        path = write_decision_revision(root, series["decision_series_id"], 1, forged, "c8-forged-buy")
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["ai_action"] == "BUY"
        assert forged["decision"]["gates"]["trust"] == "FAIL"
        assert forged["decision"]["return_metrics"]["fundamental_target_pass"] is False
        publication = build_machine_publication(
            root=root,
            decision_id=record["decision_id"],
            published_at="2026-10-06T11:00:00+00:00",
        )
        validate_machine_publication(publication)
        assert publication["ai_decision"]["action"] == "BUY"


def test_c8_cross_company_revision_coupling_can_bypass_identity():
    with TemporaryDirectory(prefix="iios-c8-cross-company-") as tmp:
        root = Path(tmp)
        series = create_or_load_series(
            root,
            "CN-A",
            "002422",
            "四川科伦药业股份有限公司",
            "2026-10-06T00:00:00+00:00",
        )
        catl_snapshot = _minimal_snapshot(
            case_id=CATL_CASE,
            symbol="300750",
            company="宁德时代",
            action="REVIEW_REQUIRED",
        )
        write_snapshot(root, catl_snapshot)
        path = write_decision_revision(
            root,
            series["decision_series_id"],
            1,
            catl_snapshot,
            "c8-cross-company",
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["decision_id"] == "CN-A-002422-r001"
        assert catl_snapshot["input"]["symbol"] == "300750"
        assert catl_snapshot["input"]["company"] == "宁德时代"
        publication = build_machine_publication(
            root=root,
            decision_id=record["decision_id"],
            published_at="2026-10-06T11:00:00+00:00",
        )
        validate_machine_publication(publication)
        assert publication["decision_ref"]["decision_series_id"] == "CN-A-002422"
        assert publication["case"]["symbol"] == "300750"
        assert publication["case"]["company"] == "宁德时代"


def test_c8_human_approval_has_no_actor_identity_boundary(tmp_path):
    _, _, revision_path, _, _ = seed_c7(tmp_path)
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    approval = build_human_approval(
        decision_revision=revision,
        approved=True,
        note="C8 boundary review",
    )
    assert "actor_identity" not in approval
    assert approval["decision_id"] == revision["decision_id"]
