import hashlib
import json
from argparse import Namespace
from pathlib import Path

import pytest

from iios_mvp.decision_lifecycle_production import build_human_approval
from iios_mvp.engine import canonical_json
from iios_mvp.store import (
    approve_revision,
    create_or_load_series,
    next_revision,
    replay_decision_lifecycle,
    write_decision_revision,
    write_snapshot,
)
from iios_mvp import cli


def make_snapshot(case_id="V03-DR02", cutoff="2026-10-05", action="REVIEW_REQUIRED"):
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {"case_id": case_id, "cutoff_date": cutoff},
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


def test_revision_persistence_is_canonical_and_advances_index(tmp_path):
    snapshot = make_snapshot()
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    assert next_revision(tmp_path, series["decision_series_id"]) == 1

    path = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        run_id="run-001",
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["contract_version"] == "IIOS-DECISION-LIFECYCLE-0.1"
    assert record["decision_status"] == "AI_PROPOSED"
    assert record["snapshot_hash"] == snapshot["snapshot_hash"]
    assert next_revision(tmp_path, series["decision_series_id"]) == 2

    # Retry of the exact same revision is idempotent.
    same = write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        run_id="run-001",
    )
    assert same == path


def test_out_of_order_revision_is_rejected(tmp_path):
    snapshot = make_snapshot()
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    with pytest.raises(ValueError, match="next canonical revision"):
        write_decision_revision(
            tmp_path,
            series["decision_series_id"],
            2,
            snapshot,
            run_id="run-002",
        )


def test_approval_persists_and_only_approved_revision_updates_current(tmp_path):
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    s1 = make_snapshot(action="HOLD")
    write_snapshot(tmp_path, s1)
    write_decision_revision(tmp_path, series["decision_series_id"], 1, s1, "run-001")

    rejected = approve_revision(tmp_path, "CN-A-300750-r001", s1, False, "reject")
    assert rejected["status"] == "HUMAN_REJECTED"
    assert rejected["current"] is False
    assert not (Path(tmp_path) / "CN-A-300750.current.json").exists()
    assert (Path(tmp_path) / "CN-A-300750-r001.approval.json").exists()

    s2 = make_snapshot(action="BUY")
    write_snapshot(tmp_path, s2)
    write_decision_revision(tmp_path, series["decision_series_id"], 2, s2, "run-002")
    approved = approve_revision(tmp_path, "CN-A-300750-r002", s2, True, "approve")
    assert approved["status"] == "HUMAN_APPROVED"
    assert approved["current"] is True

    current = json.loads((Path(tmp_path) / "CN-A-300750.current.json").read_text(encoding="utf-8"))
    assert current["current_revision"] == 2
    assert current["current_decision_id"] == "CN-A-300750-r002"
    assert len(current["projection_hash"]) == 64


def test_wrong_snapshot_cannot_be_approved(tmp_path):
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    s1 = make_snapshot(action="HOLD")
    s2 = make_snapshot(case_id="V03-DR02-OTHER", action="BUY")
    write_snapshot(tmp_path, s1)
    write_snapshot(tmp_path, s2)
    write_decision_revision(tmp_path, series["decision_series_id"], 1, s1, "run-001")
    with pytest.raises(ValueError, match="same snapshot"):
        approve_revision(tmp_path, "CN-A-300750-r001", s2, True, "wrong snapshot")


def test_lifecycle_replay_reconstructs_current_projection(tmp_path):
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    for revision, action, cutoff in ((1, "HOLD", "2026-10-05"), (2, "BUY", "2026-10-06")):
        snapshot = make_snapshot(cutoff=cutoff, action=action)
        write_snapshot(tmp_path, snapshot)
        write_decision_revision(tmp_path, series["decision_series_id"], revision, snapshot, f"run-{revision:03d}")
        approve_revision(
            tmp_path,
            f"CN-A-300750-r{revision:03d}",
            snapshot,
            True,
            f"approve r{revision}",
        )

    result = replay_decision_lifecycle(tmp_path, "CN-A-300750-r001")
    assert result["replay_status"] == "PASS"
    assert result["current_revision"] == 2
    assert result["current_decision_id"] == "CN-A-300750-r002"


def test_cli_exposes_lifecycle_replay(tmp_path):
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    snapshot = make_snapshot()
    write_snapshot(tmp_path, snapshot)
    write_decision_revision(tmp_path, series["decision_series_id"], 1, snapshot, "run-001")
    approve_revision(tmp_path, "CN-A-300750-r001", snapshot, True, "approve")

    args = Namespace(out=str(tmp_path), decision_id="CN-A-300750-r001")
    assert cli.cmd_lifecycle_replay(args) == 0


def test_persisted_revision_tampering_is_detected(tmp_path):
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-05T00:00:00Z")
    snapshot = make_snapshot()
    write_snapshot(tmp_path, snapshot)
    path = write_decision_revision(tmp_path, series["decision_series_id"], 1, snapshot, "run-001")
    record = json.loads(path.read_text(encoding="utf-8"))
    record["ai_action"] = "BUY"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="revision hash mismatch"):
        replay_decision_lifecycle(tmp_path, "CN-A-300750-r001")
