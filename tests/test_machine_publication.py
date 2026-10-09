import json
from argparse import Namespace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.engine import canonical_json, sha256_obj
from iios_mvp.machine_publication import (
    PUBLICATION_VERSION,
    build_machine_publication,
    validate_machine_publication,
    write_machine_publication,
)
from iios_mvp import cli
from iios_mvp.store import (
    approve_revision,
    create_or_load_series,
    initialize_monitoring_state,
    write_decision_revision,
    write_monitoring_validation,
    write_snapshot,
)
from iios_mvp.trigger_production import build_trigger_contract, validate_trigger_contract
from iios_mvp.store import write_trigger_contract


SCHEMA = Path("schemas/machine_publication_v0.1.schema.json")


def make_snapshot(case_id="C1-001", cutoff="2026-10-06", action="REVIEW_REQUIRED"):
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case_id,
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "as_of_date": cutoff,
            "cutoff_date": cutoff,
        },
        "decision": {
            "engine_version": "0.3.0",
            "case_id": case_id,
            "symbol": "300750",
            "company": "CATL",
            "cutoff_date": cutoff,
            "action": action,
            "decision_status": "REVIEW_REQUIRED",
            "investability_status": "REVIEW_REQUIRED",
            "primary_reason": "TEST",
            "human_approval_required": True,
            "auto_execution": False,
            "gates": {"trust": "PASS"},
            "return_metrics": {"expected_annualized_return": "0.14"},
            "monitoring": [],
        },
    }
    core["snapshot_hash"] = sha256_obj({
        "snapshot_schema": core["snapshot_schema"],
        "engine_version": core["engine_version"],
        "input": core["input"],
        "decision": core["decision"],
    })
    return core


def persist_revision(tmp_path, *, action="REVIEW_REQUIRED"):
    series = create_or_load_series(
        tmp_path,
        "CN-A",
        "300750",
        "CATL",
        "2026-10-06T00:00:00+00:00",
    )
    snapshot = make_snapshot(action=action)
    write_snapshot(tmp_path, snapshot)
    from tests.decision_admission_fixture import build_fixture_admission_receipt, prepare_authorized_test_run
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    decision_id = "CN-A-300750-r001"
    prepare_authorized_test_run(root=str(tmp_path), run_id="run-c1-001", snapshot=snapshot, decision_admission=admission)
    write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        "run-c1-001",
        decision_admission=admission,
    )
    return series, snapshot, decision_id


def test_machine_publication_is_external_readable_and_content_addressed(tmp_path):
    _, _, decision_id = persist_revision(tmp_path)
    record = build_machine_publication(
        root=tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    validate_machine_publication(record)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(record)

    assert record["publication_version"] == PUBLICATION_VERSION
    assert record["decision_ref"]["decision_id"] == decision_id
    assert record["ai_decision"]["action"] == "REVIEW_REQUIRED"
    assert record["human_approval"]["approval_status"] == "PENDING"
    assert record["current_projection"]["status"] == "NO_CURRENT_PROJECTION"
    assert record["integrity"]["approval_hash"] is None

    path1 = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    path2 = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    assert path1 == path2
    assert path1.name == f"{record['publication_hash']}.publication.json"


def test_machine_publication_separates_human_approval_and_lifecycle_refs(tmp_path):
    series, snapshot, decision_id = persist_revision(tmp_path, action="HOLD")
    approved = approve_revision(
        tmp_path,
        decision_id,
        snapshot,
        True,
        "human approval for C1 publication fixture",
        actor_identity="human:owner",
    )
    assert approved["current"] is True

    revision_path = tmp_path / f"{decision_id}.decision.json"
    revision = json.loads(revision_path.read_text(encoding="utf-8"))

    trigger = build_trigger_contract(
        trigger_id="TR-C1-001",
        decision_id=decision_id,
        decision_series_id=series["decision_series_id"],
        revision=revision["revision"],
        decision_revision_hash=revision["revision_hash"],
        case_id=revision["case_id"],
        decision_cutoff_date=revision["cutoff_date"],
        role="MONITORING",
        metric_id="quality_gate",
        operator="EQ",
        target="PASS",
        unit=None,
        evidence_ids=["E-C1-001"],
        enabled=True,
    )
    validate_trigger_contract(trigger)
    trigger_input = dict(trigger)
    trigger_input.pop("contract_version")
    trigger_input.pop("trigger_hash")
    trigger_input.pop("policy_effect")
    write_trigger_contract(tmp_path, decision_id, trigger_input)

    initialize_monitoring_state(
        tmp_path,
        "TR-C1-001",
        "MON-C1-001",
        lifecycle_status="ACTIVE",
    )
    validation_path = write_monitoring_validation(
        tmp_path,
        "TR-C1-001",
        "2026-10-06T02:00:00+00:00",
        validation_id="VAL-C1-001",
    )
    assert validation_path.exists()

    record = build_machine_publication(
        root=tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T03:00:00+00:00",
    )
    validate_machine_publication(record)

    assert record["human_approval"]["approval_status"] == "HUMAN_APPROVED"
    assert record["human_approval"]["approved"] is True
    assert record["current_projection"]["status"] == "CURRENT"
    assert len(record["lifecycle_refs"]["trigger_contracts"]) == 1
    assert len(record["lifecycle_refs"]["monitoring_states"]) == 1
    assert record["lifecycle_refs"]["validation_records"][0]["validation_id"] == "VAL-C1-001"
    assert record["integrity"]["trigger_hashes"]
    assert record["integrity"]["monitoring_state_hashes"]
    assert record["integrity"]["validation_hashes"]


def test_machine_publication_old_bytes_remain_valid_after_new_publication(tmp_path):
    _, _, decision_id = persist_revision(tmp_path)
    first = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    first_bytes = first.read_bytes()

    second = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T04:00:00+00:00",
    )
    assert second != first
    assert first.read_bytes() == first_bytes
    validate_machine_publication(json.loads(first.read_text(encoding="utf-8")))
    validate_machine_publication(json.loads(second.read_text(encoding="utf-8")))


def test_machine_publication_fails_closed_on_source_revision_tampering(tmp_path):
    _, _, decision_id = persist_revision(tmp_path)
    publication = write_machine_publication(
        tmp_path,
        decision_id=decision_id,
        published_at="2026-10-06T01:00:00+00:00",
    )
    original = publication.read_bytes()

    revision_path = tmp_path / f"{decision_id}.decision.json"
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    revision["ai_action"] = "BUY"
    revision_path.write_text(
        json.dumps(revision, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decision admission action binding mismatch"):
        build_machine_publication(
            root=tmp_path,
            decision_id=decision_id,
            published_at="2026-10-06T05:00:00+00:00",
        )

    assert publication.read_bytes() == original


def test_cli_publish_exposes_machine_publication(tmp_path, capsys):
    _, _, decision_id = persist_revision(tmp_path)
    args = Namespace(
        out=str(tmp_path),
        decision_id=decision_id,
        published_at="2026-10-06T06:00:00+00:00",
    )
    assert cli.cmd_publish(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "PUBLISHED"
    assert output["decision_id"] == decision_id
    assert output["publication_hash"]
