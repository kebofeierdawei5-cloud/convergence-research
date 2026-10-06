from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from iios_mvp.engine import canonical_json
from iios_mvp.human_report import (
    build_human_report,
    qa_human_report,
    validate_human_report,
)
from iios_mvp.machine_publication import (
    build_machine_publication,
    validate_machine_publication,
)
from iios_mvp.decision_admission import build_test_admission_receipt
from iios_mvp.store import (
    apply_monitoring_event,
    approve_revision,
    create_or_load_series,
    initialize_monitoring_state,
    replay_decision_lifecycle,
    replay_monitoring_state,
    replay_monitoring_validation,
    write_decision_revision,
    write_execution_receipt,
    write_monitoring_validation,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
)


def make_snapshot(
    *,
    case_id: str,
    cutoff_date: str,
    action: str,
    reason: str,
) -> dict:
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id,
            "cutoff_date": cutoff_date,
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "as_of_date": cutoff_date,
        },
        "decision": {
            "action": action,
            "primary_reason": reason,
            "decision_status": "AI_PROPOSED",
        },
    }
    core["snapshot_hash"] = hashlib.sha256(
        canonical_json({k: v for k, v in core.items() if k != "snapshot_hash"}).encode(
            "utf-8"
        )
    ).hexdigest()
    return core


def seed_c7(tmp_path):
    case_id = "RC-CN-A-300750-20261004"
    cutoff = "2026-10-04"
    series = create_or_load_series(
        tmp_path,
        "CN-A",
        "300750",
        "CATL",
        "2026-10-04T00:00:00Z",
    )
    s1 = make_snapshot(
        case_id=case_id,
        cutoff_date=cutoff,
        action="BUY",
        reason="initial canonical proposal",
    )
    write_snapshot(tmp_path, s1)
    admission1 = build_test_admission_receipt(snapshot=s1, canonical_decision=s1["decision"])
    r1_path = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        s1,
        "run-c7-001",
        decision_admission=admission1,
    )
    revision1 = json.loads(r1_path.read_text(encoding="utf-8"))

    approval1 = approve_revision(
        tmp_path,
        "CN-A-300750-r001",
        s1,
        True,
        "human approved initial action",
        actor_identity="human:owner",
    )

    trigger_path = write_trigger_contract(
        tmp_path,
        "CN-A-300750-r001",
        {
            "trigger_id": "tr-c7-price",
            "decision_id": "CN-A-300750-r001",
            "decision_series_id": series["decision_series_id"],
            "revision": 1,
            "decision_revision_hash": revision1["revision_hash"],
            "case_id": case_id,
            "decision_cutoff_date": cutoff,
            "role": "MONITORING",
            "metric_id": "market_price",
            "operator": "LTE",
            "target": "350",
            "unit": "CNY/share",
            "evidence_ids": ["ev-c7-contract"],
            "enabled": True,
        },
    )
    initialize_monitoring_state(
        tmp_path,
        "tr-c7-price",
        "monitor-c7",
        next_due_at="2026-10-08T00:00:00+00:00",
        evaluation_reference_at="2026-10-04T00:00:00+00:00",
    )
    return series, s1, r1_path, approval1, trigger_path


def test_c7_full_operating_loop(tmp_path):
    series, s1, r1_path, approval1, trigger_path = seed_c7(tmp_path)
    case_id = "RC-CN-A-300750-20261004"
    cutoff = "2026-10-04"
    revision1_bytes = r1_path.read_bytes()
    approval1_path = tmp_path / "CN-A-300750-r001.approval.json"
    approval1_bytes = approval1_path.read_bytes()

    assert trigger_path.exists()
    assert approval1["status"] == "HUMAN_APPROVED"

    write_trigger_event(
        tmp_path,
        {
            "trigger_id": "tr-c7-price",
            "trigger_event_id": "evt-c7-match",
            "evaluation_cutoff_at": "2026-10-05T10:06:00+00:00",
            "observed_at": "2026-10-05T10:00:00+00:00",
            "known_at": "2026-10-05T10:05:00+00:00",
            "source_id": "szse",
            "evidence_id": "ev-c7-price",
            "value": "349",
            "previous_value": "355",
        },
    )
    apply_monitoring_event(
        tmp_path,
        "evt-c7-match",
        next_due_at="2026-10-07T00:00:00+00:00",
    )

    validation_path = write_monitoring_validation(
        tmp_path,
        "tr-c7-price",
        "2026-10-06T00:00:00+00:00",
        validation_id="validation-c7-001",
    )
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation["validation_status"] == "PASS"

    assert replay_monitoring_state(tmp_path, "tr-c7-price")["replay_status"] == "PASS"
    assert replay_monitoring_validation(tmp_path, "validation-c7-001")["validation_replay_status"] == "PASS"
    assert replay_decision_lifecycle(tmp_path, "CN-A-300750-r001")["replay_status"] == "PASS"

    receipt_path = write_execution_receipt(
        tmp_path,
        "exec-c7-001",
        "CN-A-300750-r001",
        s1,
        "2026-10-06T09:30:00+08:00",
        "EXECUTED",
        "human:owner",
        executed_quantity="100",
        executed_position_pct="2",
        executed_price="349",
    )
    assert receipt_path.exists()

    assert r1_path.read_bytes() == revision1_bytes
    assert approval1_path.read_bytes() == approval1_bytes

    s2 = make_snapshot(
        case_id=case_id,
        cutoff_date=cutoff,
        action="REDUCE",
        reason="monitoring event invalidated the prior sizing thesis",
    )
    write_snapshot(tmp_path, s2)
    admission2 = build_test_admission_receipt(snapshot=s2, canonical_decision=s2["decision"])
    r2_path = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        2,
        s2,
        "run-c7-002",
        trigger_event_id="evt-c7-match",
        decision_admission=admission2,
    )
    revision2 = json.loads(r2_path.read_text(encoding="utf-8"))
    assert revision2["revision"] == 2
    assert revision2["run_id"] == "run-c7-002"
    assert revision2["trigger_event_id"] == "evt-c7-match"
    assert revision2["revision_hash"] != json.loads(r1_path.read_text(encoding="utf-8"))["revision_hash"]

    approval2 = approve_revision(
        tmp_path,
        "CN-A-300750-r002",
        s2,
        True,
        "human approved revised action",
        actor_identity="human:owner",
    )
    assert approval2["status"] == "HUMAN_APPROVED"
    assert json.loads(r1_path.read_text(encoding="utf-8"))["ai_action"] == "BUY"
    assert json.loads(r2_path.read_text(encoding="utf-8"))["ai_action"] == "REDUCE"

    publication = build_machine_publication(
        root=tmp_path,
        decision_id="CN-A-300750-r002",
        published_at="2026-10-06T10:05:00+08:00",
    )
    validate_machine_publication(publication)
    assert publication["decision_ref"]["decision_id"] == "CN-A-300750-r002"
    assert publication["ai_decision"]["action"] == "REDUCE"

    report = build_human_report(
        publication=publication,
        generated_at="2026-10-06T10:05:00+08:00",
    )
    validate_human_report(report)
    qa = qa_human_report(publication=publication, report=report)
    assert qa["qa_status"] == "PASS"
    assert qa["policy_effect"] == "REPORT_ONLY_PROJECTION"

    assert json.loads(r1_path.read_text(encoding="utf-8"))["revision"] == 1
    assert json.loads(r2_path.read_text(encoding="utf-8"))["revision"] == 2


def test_c7_monitoring_cannot_mutate_decision_revision(tmp_path):
    _, s1, r1_path, _, _ = seed_c7(tmp_path)
    before = r1_path.read_bytes()

    write_trigger_event(
        tmp_path,
        {
            "trigger_id": "tr-c7-price",
            "trigger_event_id": "evt-c7-noop",
            "evaluation_cutoff_at": "2026-10-05T11:06:00+00:00",
            "observed_at": "2026-10-05T11:00:00+00:00",
            "known_at": "2026-10-05T11:05:00+00:00",
            "source_id": "szse",
            "evidence_id": "ev-c7-noop",
            "value": "351",
            "previous_value": "350",
        },
    )
    apply_monitoring_event(tmp_path, "evt-c7-noop")
    assert r1_path.read_bytes() == before
    assert json.loads(r1_path.read_text(encoding="utf-8"))["snapshot_hash"] == s1["snapshot_hash"]


def test_c7_changed_decision_requires_new_run_and_revision(tmp_path):
    series, _, r1_path, _, _ = seed_c7(tmp_path)
    s2 = make_snapshot(
        case_id="RC-CN-A-300750-20261004",
        cutoff_date="2026-10-04",
        action="HOLD",
        reason="changed proposal requires independent revision",
    )
    write_snapshot(tmp_path, s2)
    admission2 = build_test_admission_receipt(snapshot=s2, canonical_decision=s2["decision"])
    r2_path = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        2,
        s2,
        "run-c7-003",
        decision_admission=admission2,
    )
    r1 = json.loads(r1_path.read_text(encoding="utf-8"))
    r2 = json.loads(r2_path.read_text(encoding="utf-8"))
    assert r1["revision"] == 1
    assert r2["revision"] == 2
    assert r1["run_id"] != r2["run_id"]
    assert r1["revision_hash"] != r2["revision_hash"]
    assert r1["ai_action"] == "BUY"
    assert r2["ai_action"] == "HOLD"


def test_c7_publication_and_report_are_projections(tmp_path):
    _, s1, r1_path, _, _ = seed_c7(tmp_path)
    publication = build_machine_publication(
        root=tmp_path,
        decision_id="CN-A-300750-r001",
        published_at="2026-10-06T11:00:00+08:00",
    )
    validate_machine_publication(publication)
    report = build_human_report(
        publication=publication,
        generated_at="2026-10-06T11:00:00+08:00",
    )
    validate_human_report(report)
    qa = qa_human_report(publication=publication, report=report)
    assert qa["qa_status"] == "PASS"

    decision_before = r1_path.read_bytes()
    projected = deepcopy(report)
    projected["markdown"] += "\nProjection-only edit"
    assert projected["markdown"] != report["markdown"]
    assert r1_path.read_bytes() == decision_before
    assert s1["decision"]["action"] == "BUY"
