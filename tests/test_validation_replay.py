import hashlib
import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from tests.decision_admission_fixture import build_fixture_admission_receipt
from tests.canonical_run_authorization_fixture import authorize_test_run
from iios_mvp.monitoring_state import build_monitoring_state
from iios_mvp.trigger_production import build_trigger_contract, build_trigger_event
from iios_mvp.validation_replay import (
    build_monitoring_evaluation_record,
    build_monitoring_initialization_record,
    validate_monitoring_evaluation_record,
    validate_monitoring_initialization_record,
    validate_validation_record,
)
from iios_mvp.store import (
    apply_monitoring_event,
    create_or_load_series,
    initialize_monitoring_state,
    replay_monitoring_state,
    replay_monitoring_validation,
    write_decision_revision,
    write_monitoring_validation,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
)


CASE = "RC-CN-A-300750-20261004"
CUTOFF = "2026-10-04"


def contract(**overrides):
    payload = {
        "trigger_id": "tr-validation",
        "decision_id": "CN-A-300750-r001",
        "decision_series_id": "CN-A-300750",
        "revision": 1,
        "decision_revision_hash": "a" * 64,
        "case_id": CASE,
        "decision_cutoff_date": CUTOFF,
        "role": "MONITORING",
        "metric_id": "market_price",
        "operator": "LTE",
        "target": "350",
        "unit": "CNY/share",
        "evidence_ids": [],
        "enabled": True,
    }
    payload.update(overrides)
    return build_trigger_contract(**payload)


def event(c, event_id, known, cutoff, value="349"):
    return build_trigger_event(
        trigger_contract=c,
        trigger_event_id=event_id,
        evaluation_cutoff_at=cutoff,
        observed_at=known.replace(":05+00:00", ":00+00:00"),
        known_at=known,
        source_id="szse",
        evidence_id=f"ev-{event_id}",
        value=value,
    )


def seed_store(tmp_path):
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": CASE,
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "as_of_date": CUTOFF,
            "cutoff_date": CUTOFF,
        },
        "decision": {"action": "HOLD"},
    }
    snapshot_hash = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    snapshot = {**core, "snapshot_hash": snapshot_hash}
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(
        tmp_path, "CN-A", "300750", "CATL", "2026-10-04T00:00:00Z"
    )
    admission = build_fixture_admission_receipt(snapshot=snapshot, canonical_decision=snapshot["decision"])
    authorize_test_run(tmp_path, snapshot=snapshot, decision_admission=admission, run_id="run-1")
    write_decision_revision(
        tmp_path,
        series["decision_series_id"],
        1,
        snapshot,
        "run-1",
        decision_admission=admission,
    )
    revision = json.loads(
        (tmp_path / "CN-A-300750-r001.decision.json").read_text()
    )
    c = write_trigger_contract(
        tmp_path,
        "CN-A-300750-r001",
        {
            "trigger_id": "tr-validation",
            "decision_id": "CN-A-300750-r001",
            "decision_series_id": "CN-A-300750",
            "revision": 1,
            "decision_revision_hash": revision["revision_hash"],
            "case_id": CASE,
            "decision_cutoff_date": CUTOFF,
            "role": "MONITORING",
            "metric_id": "market_price",
            "operator": "LTE",
            "target": "350",
            "unit": "CNY/share",
            "evidence_ids": [],
            "enabled": True,
        },
    )
    initialize_monitoring_state(
        tmp_path,
        "tr-validation",
        "monitor-1",
        next_due_at="2026-10-08T00:00:00+00:00",
        evaluation_reference_at="2026-10-04T00:00:00+00:00",
    )
    return tmp_path, c, revision


def test_initialization_record_is_immutable_and_self_hash_protected():
    c = contract()
    state = build_monitoring_state(
        monitor_id="m1",
        trigger_contract=c,
        lifecycle_status="ACTIVE",
    )
    record = build_monitoring_initialization_record(
        trigger_contract=c,
        initial_state=state,
    )
    validate_monitoring_initialization_record(record, trigger_contract=c)
    tampered = dict(record)
    tampered["initial_state"] = dict(record["initial_state"])
    tampered["initial_state"]["lifecycle_status"] = "DISABLED"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_monitoring_initialization_record(tampered, trigger_contract=c)


def test_evaluation_record_captures_due_at_transition():
    c = contract()
    previous = build_monitoring_state(
        monitor_id="m1",
        trigger_contract=c,
        lifecycle_status="ACTIVE",
    )
    e = event(
        c,
        "evt-1",
        "2026-10-05T10:05:00+00:00",
        "2026-10-05T10:06:00+00:00",
    )
    from iios_mvp.monitoring_state import apply_trigger_event

    resulting = apply_trigger_event(
        previous_state=previous,
        trigger_contract=c,
        trigger_event=e,
        next_due_at="2026-10-07T00:00:00+00:00",
    )
    record = build_monitoring_evaluation_record(
        trigger_contract=c,
        trigger_event=e,
        previous_state=previous,
        resulting_state=resulting,
    )
    assert record["previous_next_due_at"] is None
    assert record["resulting_next_due_at"] == "2026-10-07T00:00:00+00:00"
    validate_monitoring_evaluation_record(
        record,
        trigger_contract=c,
        trigger_event=e,
        previous_state=previous,
        resulting_state=resulting,
    )


def test_replay_reconstructs_historical_next_due_mutations(tmp_path):
    root, _, _ = seed_store(tmp_path)
    for event_id, known, cutoff, due in [
        (
            "evt-1",
            "2026-10-05T10:05:00+00:00",
            "2026-10-05T10:06:00+00:00",
            "2026-10-07T00:00:00+00:00",
        ),
        (
            "evt-2",
            "2026-10-06T10:05:00+00:00",
            "2026-10-06T10:06:00+00:00",
            "2026-10-09T00:00:00+00:00",
        ),
    ]:
        write_trigger_event(
            root,
            {
                "trigger_id": "tr-validation",
                "trigger_event_id": event_id,
                "evaluation_cutoff_at": cutoff,
                "observed_at": known.replace("10:05", "10:00"),
                "known_at": known,
                "source_id": "szse",
                "evidence_id": f"ev-{event_id}",
                "value": "349",
                "previous_value": None,
            },
        )
        apply_monitoring_event(root, event_id, next_due_at=due)

    result = replay_monitoring_state(root, "tr-validation")
    assert result["replay_status"] == "PASS"
    assert result["event_count"] == 2
    assert result["due_state"] == "NOT_DUE"

    final_state = json.loads(
        (root / "tr-validation.monitor.json").read_text()
    )
    assert final_state["next_due_at"] == "2026-10-09T00:00:00+00:00"


def test_replay_detects_tampered_historical_due_transition(tmp_path):
    root, _, _ = seed_store(tmp_path)
    write_trigger_event(
        root,
        {
            "trigger_id": "tr-validation",
            "trigger_event_id": "evt-1",
            "evaluation_cutoff_at": "2026-10-05T10:06:00+00:00",
            "observed_at": "2026-10-05T10:00:00+00:00",
            "known_at": "2026-10-05T10:05:00+00:00",
            "source_id": "szse",
            "evidence_id": "ev-evt-1",
            "value": "349",
            "previous_value": None,
        },
    )
    apply_monitoring_event(
        root,
        "evt-1",
        next_due_at="2026-10-07T00:00:00+00:00",
    )
    path = root / "evt-1.evaluation.json"
    record = json.loads(path.read_text())
    record["resulting_next_due_at"] = "2026-10-08T00:00:00+00:00"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    with pytest.raises(ValueError):
        replay_monitoring_state(root, "tr-validation")


def test_monitoring_validation_passes_and_replays_from_source(tmp_path):
    root, _, _ = seed_store(tmp_path)
    write_trigger_event(
        root,
        {
            "trigger_id": "tr-validation",
            "trigger_event_id": "evt-1",
            "evaluation_cutoff_at": "2026-10-05T10:06:00+00:00",
            "observed_at": "2026-10-05T10:00:00+00:00",
            "known_at": "2026-10-05T10:05:00+00:00",
            "source_id": "szse",
            "evidence_id": "ev-evt-1",
            "value": "349",
            "previous_value": None,
        },
    )
    apply_monitoring_event(root, "evt-1", next_due_at="2026-10-07T00:00:00+00:00")
    validation_path = write_monitoring_validation(
        root,
        "tr-validation",
        "2026-10-06T00:00:00+00:00",
        validation_id="validation-001",
    )
    record = json.loads(validation_path.read_text())
    assert record["validation_status"] == "PASS"
    assert record["event_count"] == 1
    validate_validation_record(record)
    replay = replay_monitoring_validation(root, "validation-001")
    assert replay["validation_replay_status"] == "PASS"


def test_validation_fails_closed_on_future_event(tmp_path):
    root, _, _ = seed_store(tmp_path)
    write_trigger_event(
        root,
        {
            "trigger_id": "tr-validation",
            "trigger_event_id": "evt-future",
            "evaluation_cutoff_at": "2026-10-08T10:06:00+00:00",
            "observed_at": "2026-10-08T10:00:00+00:00",
            "known_at": "2026-10-08T10:05:00+00:00",
            "source_id": "szse",
            "evidence_id": "ev-future",
            "value": "349",
            "previous_value": None,
        },
    )
    apply_monitoring_event(root, "evt-future")
    record_path = write_monitoring_validation(
        root,
        "tr-validation",
        "2026-10-07T00:00:00+00:00",
        validation_id="validation-future",
    )
    record = json.loads(record_path.read_text())
    assert record["validation_status"] == "FAIL"
    assert record["checks"]["trigger_event_pit"] == "FAIL"
    assert record["policy_effect"] == "NO_DIRECT_DECISION_PRECEDENCE_CHANGE"


def test_validation_schema_accepts_pass_record(tmp_path):
    root, _, _ = seed_store(tmp_path)
    path = write_monitoring_validation(
        root,
        "tr-validation",
        "2026-10-05T00:00:00+00:00",
        validation_id="validation-schema",
    )
    record = json.loads(path.read_text())
    schema = json.loads(
        (tmp_path.parent.parent / "schemas/validation_record_v0.1.schema.json").read_text()
    ) if (tmp_path.parent.parent / "schemas/validation_record_v0.1.schema.json").exists() else json.loads(
        __import__("pathlib").Path("schemas/validation_record_v0.1.schema.json").read_text()
    )
    assert list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)
    ) == []


def test_validation_id_cannot_overwrite_different_content(tmp_path):
    root, _, _ = seed_store(tmp_path)
    first = write_monitoring_validation(
        root, "tr-validation", "2026-10-05T00:00:00+00:00", validation_id="same-id"
    )
    record = json.loads(first.read_text())
    record["issues"] = ["tampered"]
    record["validation_hash"] = "b" * 64
    first.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    with pytest.raises(ValueError):
        write_monitoring_validation(
            root, "tr-validation", "2026-10-05T00:00:00+00:00", validation_id="same-id"
        )


def test_store_preserves_idempotent_event_application(tmp_path):
    root, _, _ = seed_store(tmp_path)
    write_trigger_event(
        root,
        {
            "trigger_id": "tr-validation",
            "trigger_event_id": "evt-idempotent",
            "evaluation_cutoff_at": "2026-10-05T10:06:00+00:00",
            "observed_at": "2026-10-05T10:00:00+00:00",
            "known_at": "2026-10-05T10:05:00+00:00",
            "source_id": "szse",
            "evidence_id": "ev-idempotent",
            "value": "349",
            "previous_value": None,
        },
    )
    first = apply_monitoring_event(
        root,
        "evt-idempotent",
        next_due_at="2026-10-07T00:00:00+00:00",
    )
    state_before = json.loads(first.read_text())
    second = apply_monitoring_event(
        root,
        "evt-idempotent",
        next_due_at="2026-10-07T00:00:00+00:00",
    )
    state_after = json.loads(second.read_text())
    assert state_after == state_before
    assert json.loads((root / "evt-idempotent.evaluation.json").read_text())["previous_state_hash"] != state_after["state_hash"]
