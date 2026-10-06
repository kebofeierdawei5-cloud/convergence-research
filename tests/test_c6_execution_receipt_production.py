import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.engine import canonical_json
from iios_mvp.execution_receipt_production import (
    C6_EXECUTION_RECEIPT_VERSION,
    C6_POLICY_EFFECT,
    build_execution_receipt,
    execution_receipt_path,
    replay_execution_receipt,
    validate_execution_receipt,
)
from iios_mvp.store import (
    approve_revision,
    create_or_load_series,
    read_execution_receipt,
    replay_persisted_execution_receipt,
    write_decision_revision,
    write_execution_receipt,
    write_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]


def make_snapshot(case_id="V03-C6", cutoff="2026-10-06", action="BUY"):
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id,
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "cutoff_date": cutoff,
        },
        "decision": {"action": action},
    }
    core["snapshot_hash"] = hashlib.sha256(
        canonical_json({
            "snapshot_schema": core["snapshot_schema"],
            "engine_version": core["engine_version"],
            "input": core["input"],
            "decision": core["decision"],
        }).encode("utf-8")
    ).hexdigest()
    return core


def setup_approved_revision(tmp_path, action="BUY"):
    series = create_or_load_series(
        tmp_path,
        "CN-A",
        "300750",
        "CATL",
        "2026-10-06T00:00:00Z",
    )
    snapshot = make_snapshot(action=action)
    write_snapshot_path = write_snapshot(tmp_path, snapshot)
    from tests.decision_admission_fixture import build_fixture_admission_receipt
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    revision_path = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        "run-c6-001",
        decision_admission=admission,
    )
    approval = approve_revision(
        tmp_path,
        "CN-A-300750-r001",
        snapshot,
        True,
        "human approval for C6 test",
        actor_identity="human:owner",
    )
    return series, snapshot, revision_path, write_snapshot_path, approval


def test_c6_receipt_binds_exact_approved_revision_and_action():
    rev = {
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.2",
        "decision_id": "CN-A-300750-r001",
        "decision_series_id": "CN-A-300750",
        "revision": 1,
        "run_id": "run-c6-001",
        "trigger_event_id": None,
        "case_id": "V03-C6",
        "as_of_date": "2026-10-06",
        "cutoff_date": "2026-10-06",
        "snapshot_hash": "a" * 64,
        "ai_action": "BUY",
        "decision_status": "AI_PROPOSED",
        "engine_version": "0.3.0",
        "human_approval_required": True,
        "auto_execution": False,
        "decision_admission": {
            "schema_version": "IIOS-DECISION-ADMISSION-0.1",
            "status": "ADMITTED",
            "admission_method": "CANONICAL_DECIDE_V03_REEXECUTED",
            "contract_version": "IIOS-INVESTMENT-CORE-0.3",
            "engine_version": "0.3.0",
            "case_id": "V03-C6",
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "cutoff_date": "2026-10-06",
            "snapshot_hash": "a" * 64,
            "canonical_decision_keys": ["action"],
            "canonical_decision_hash": "95ac255afa82bcec8609c7492bd56f8ed201e3cf4624ddbbabfd28f8ff77c5cc",
            "canonical_decision_projection": {"action": "BUY"},
            "canonical_action": "BUY",
            "canonical_decision_status": "READY",
            "canonical_new_capital_allowed": False,
            "admission_record_hash": "8766d70fe40167ba81688c5ace4b8e7eac3596d79f36af4a7bb5e612d8f34dd6",
        },
    }
    rev["revision_hash"] = hashlib.sha256(
        canonical_json({k: rev[k] for k in rev if k != "revision_hash"}).encode()
    ).hexdigest()
    from iios_mvp.decision_lifecycle_production import build_human_approval
    approval = build_human_approval(decision_revision=rev, approved=True, note="approved", actor_identity="human:test")
    receipt = build_execution_receipt(
        execution_receipt_id="exec-c6-001",
        decision_revision=rev,
        human_approval=approval,
        executed_at="2026-10-06T12:00:00+08:00",
        execution_status="PARTIALLY_EXECUTED",
        executed_quantity="100",
        executed_position_pct="1.25",
        executed_price="285",
        actor_identity="human:owner",
    )
    assert receipt["receipt_version"] == C6_EXECUTION_RECEIPT_VERSION
    assert receipt["decision_id"] == rev["decision_id"]
    assert receipt["revision_hash"] == rev["revision_hash"]
    assert receipt["approval_hash"] == approval["approval_hash"]
    assert receipt["approved_action"] == "BUY"
    assert receipt["auto_execution"] is False
    assert receipt["policy_effect"] == C6_POLICY_EFFECT
    validate_execution_receipt(receipt)
    replay = replay_execution_receipt(
        receipt,
        decision_revision=rev,
        human_approval=approval,
    )
    assert replay["replay_status"] == "PASS"
    assert replay["deterministic_replay"] is True


def test_c6_rejected_approval_cannot_create_execution_receipt(tmp_path):
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-06T00:00:00Z")
    snapshot = make_snapshot()
    write_snapshot(tmp_path, snapshot)
    from tests.decision_admission_fixture import build_fixture_admission_receipt
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        "run-c6-reject",
        decision_admission=admission,
    )
    approve_revision(
        tmp_path,
        "CN-A-300750-r001",
        snapshot,
        False,
        "rejected",
        actor_identity="human:owner",
    )
    with pytest.raises(ValueError, match="HUMAN_APPROVED"):
        write_execution_receipt(
            tmp_path,
            "exec-c6-rejected",
            "CN-A-300750-r001",
            snapshot,
            "2026-10-06T12:00:00+08:00",
            "EXECUTED",
            "human:owner",
            executed_quantity="100",
            executed_price="285",
        )


def test_c6_persisted_receipt_is_immutable_and_does_not_mutate_lifecycle(tmp_path):
    _, snapshot, revision_path, _, approval = setup_approved_revision(tmp_path)
    revision_before = revision_path.read_text(encoding="utf-8")
    current_before = (Path(tmp_path) / "CN-A-300750.current.json").read_text(encoding="utf-8")

    receipt_path = write_execution_receipt(
        tmp_path,
        "exec-c6-immutable",
        "CN-A-300750-r001",
        snapshot,
        "2026-10-06T12:05:00+08:00",
        "EXECUTED",
        "human:owner",
        executed_quantity="200",
        executed_position_pct="2.5",
        executed_price="286",
    )
    assert receipt_path == execution_receipt_path(tmp_path, "exec-c6-immutable")
    assert revision_path.read_text(encoding="utf-8") == revision_before
    assert (Path(tmp_path) / "CN-A-300750.current.json").read_text(encoding="utf-8") == current_before

    existing = json.loads(receipt_path.read_text(encoding="utf-8"))
    same = write_execution_receipt(
        tmp_path,
        "exec-c6-immutable",
        "CN-A-300750-r001",
        snapshot,
        "2026-10-06T12:05:00+08:00",
        "EXECUTED",
        "human:owner",
        executed_quantity="200",
        executed_position_pct="2.5",
        executed_price="286",
    )
    assert same == receipt_path

    with pytest.raises(ValueError, match="immutable object already exists"):
        write_execution_receipt(
            tmp_path,
            "exec-c6-immutable",
            "CN-A-300750-r001",
            snapshot,
            "2026-10-06T12:06:00+08:00",
            "EXECUTED",
            "human:owner",
            executed_quantity="201",
            executed_position_pct="2.5",
            executed_price="286",
        )
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == existing
    assert approval["current"] is True


def test_c6_receipt_tampering_is_detected():
    rev = {
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.2",
        "decision_id": "CN-A-300750-r001",
        "decision_series_id": "CN-A-300750",
        "revision": 1,
        "run_id": "run-c6-002",
        "trigger_event_id": None,
        "case_id": "V03-C6",
        "as_of_date": "2026-10-06",
        "cutoff_date": "2026-10-06",
        "snapshot_hash": "b" * 64,
        "ai_action": "REDUCE",
        "decision_status": "AI_PROPOSED",
        "engine_version": "0.3.0",
        "human_approval_required": True,
        "auto_execution": False,
        "decision_admission": {
            "schema_version": "IIOS-DECISION-ADMISSION-0.1",
            "status": "ADMITTED",
            "admission_method": "CANONICAL_DECIDE_V03_REEXECUTED",
            "contract_version": "IIOS-INVESTMENT-CORE-0.3",
            "engine_version": "0.3.0",
            "case_id": "V03-C6",
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "cutoff_date": "2026-10-06",
            "snapshot_hash": "b" * 64,
            "canonical_decision_keys": ["action"],
            "canonical_decision_hash": "e714c245ceee121baa0bd5ad719ce0f0e12a22b0f1662d8f361beb0582d664ba",
            "canonical_decision_projection": {"action": "REDUCE"},
            "canonical_action": "REDUCE",
            "canonical_decision_status": "READY",
            "canonical_new_capital_allowed": False,
            "admission_record_hash": "6518d5599053e55328e3eb0dcb53340ad780a44d179985d8af07688484a40eb4",
        },
    }
    rev["revision_hash"] = hashlib.sha256(
        canonical_json({k: rev[k] for k in rev if k != "revision_hash"}).encode()
    ).hexdigest()
    from iios_mvp.decision_lifecycle_production import build_human_approval
    approval = build_human_approval(decision_revision=rev, approved=True, note="approved", actor_identity="human:test")
    receipt = build_execution_receipt(
        execution_receipt_id="exec-c6-tamper",
        decision_revision=rev,
        human_approval=approval,
        executed_at="2026-10-06T13:00:00+08:00",
        execution_status="EXECUTED",
        executed_position_pct="2",
        actor_identity="human:owner",
    )
    tampered = deepcopy(receipt)
    tampered["executed_position_pct"] = "3"
    with pytest.raises(ValueError, match="receipt hash mismatch"):
        validate_execution_receipt(tampered)


def test_c6_not_executed_receipt_can_be_recorded_without_fake_quantity(tmp_path):
    _, snapshot, _, _, _ = setup_approved_revision(tmp_path, action="HOLD")
    path = write_execution_receipt(
        tmp_path,
        "exec-c6-none",
        "CN-A-300750-r001",
        snapshot,
        "2026-10-06T14:00:00+08:00",
        "NOT_EXECUTED",
        "human:owner",
    )
    record = read_execution_receipt(path)
    assert record["execution_status"] == "NOT_EXECUTED"
    assert record["executed_quantity"] is None
    assert record["executed_position_pct"] is None
    assert record["approved_action"] == "HOLD"
    validate_execution_receipt(record)


def test_c6_persisted_replay_reconstructs_receipt(tmp_path):
    _, snapshot, _, _, _ = setup_approved_revision(tmp_path)
    write_execution_receipt(
        tmp_path,
        "exec-c6-replay",
        "CN-A-300750-r001",
        snapshot,
        "2026-10-06T15:00:00+08:00",
        "EXECUTED",
        "human:owner",
        executed_quantity="50",
        executed_price="287",
    )
    result = replay_persisted_execution_receipt(tmp_path, "exec-c6-replay")
    assert result["replay_status"] == "PASS"
    assert result["deterministic_replay"] is True


def test_c6_schema_accepts_receipt():
    rev = {
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.2",
        "decision_id": "CN-A-300750-r001",
        "decision_series_id": "CN-A-300750",
        "revision": 1,
        "run_id": "run-c6-schema",
        "trigger_event_id": None,
        "case_id": "V03-C6",
        "as_of_date": "2026-10-06",
        "cutoff_date": "2026-10-06",
        "snapshot_hash": "c" * 64,
        "ai_action": "ADD",
        "decision_status": "AI_PROPOSED",
        "engine_version": "0.3.0",
        "human_approval_required": True,
        "auto_execution": False,
        "decision_admission": {
            "schema_version": "IIOS-DECISION-ADMISSION-0.1",
            "status": "ADMITTED",
            "admission_method": "CANONICAL_DECIDE_V03_REEXECUTED",
            "contract_version": "IIOS-INVESTMENT-CORE-0.3",
            "engine_version": "0.3.0",
            "case_id": "V03-C6",
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "cutoff_date": "2026-10-06",
            "snapshot_hash": "c" * 64,
            "canonical_decision_keys": ["action"],
            "canonical_decision_hash": "f68b6fac1c0f9c5957a60408673cf603242d9588fcc4bd2a08271ff1233dc59d",
            "canonical_decision_projection": {"action": "ADD"},
            "canonical_action": "ADD",
            "canonical_decision_status": "READY",
            "canonical_new_capital_allowed": False,
            "admission_record_hash": "83eb69bd63ea8c43d4a9643125fb3c7de16aaa5971bafe7adf0c4a8b5028325f",
        },
    }
    rev["revision_hash"] = hashlib.sha256(
        canonical_json({k: rev[k] for k in rev if k != "revision_hash"}).encode()
    ).hexdigest()
    from iios_mvp.decision_lifecycle_production import build_human_approval
    approval = build_human_approval(decision_revision=rev, approved=True, note="approved", actor_identity="human:test")
    receipt = build_execution_receipt(
        execution_receipt_id="exec-c6-schema",
        decision_revision=rev,
        human_approval=approval,
        executed_at="2026-10-06T16:00:00+08:00",
        execution_status="EXECUTED",
        executed_quantity="100",
        actor_identity="human:owner",
    )
    schema = json.loads(
        (ROOT / "schemas/execution_receipt_v0.1.schema.json").read_text(encoding="utf-8")
    )
    assert list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(receipt)
    ) == []


def test_c6_invalid_execution_timestamp_or_negative_amount_fails_closed(tmp_path):
    _, snapshot, _, _, _ = setup_approved_revision(tmp_path)
    with pytest.raises(ValueError, match="timezone-aware"):
        write_execution_receipt(
            tmp_path,
            "exec-c6-bad-time",
            "CN-A-300750-r001",
            snapshot,
            "2026-10-06T12:00:00",
            "EXECUTED",
            "human:owner",
            executed_quantity="1",
        )

    with pytest.raises(ValueError, match="finite and >= 0"):
        write_execution_receipt(
            tmp_path,
            "exec-c6-negative",
            "CN-A-300750-r001",
            snapshot,
            "2026-10-06T12:00:00+08:00",
            "EXECUTED",
            "human:owner",
            executed_quantity="-1",
        )
