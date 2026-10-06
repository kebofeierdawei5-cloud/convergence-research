import pytest
from json import load
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.trigger_production import (
    TRIGGER_CONTRACT_VERSION, TRIGGER_EVENT_VERSION,
    build_trigger_contract, build_trigger_event,
    validate_trigger_contract, validate_trigger_event,
)

DECISION = "CN-A-300750-r001"
SERIES = "CN-A-300750"
REVISION_HASH = "a" * 64
CASE = "RC-CN-A-300750-20261004"
CUTOFF = "2026-10-04"

def contract(**overrides):
    payload = {
        "trigger_id": "tr-price-1", "decision_id": DECISION, "decision_series_id": SERIES,
        "revision": 1, "decision_revision_hash": REVISION_HASH, "case_id": CASE,
        "decision_cutoff_date": CUTOFF, "role": "MONITORING", "metric_id": "market_price",
        "operator": "LTE", "target": "350", "unit": "CNY/share", "evidence_ids": [],
        "enabled": True,
    }
    payload.update(overrides)
    return build_trigger_contract(**payload)

def event(c, **overrides):
    payload = {
        "trigger_contract": c, "trigger_event_id": "evt-1",
        "evaluation_cutoff_at": "2026-10-06T00:00:00+00:00",
        "observed_at": "2026-10-05T10:00:00+00:00",
        "known_at": "2026-10-05T10:05:00+00:00", "source_id": "szse",
        "evidence_id": "evt-e1", "value": "349.5",
    }
    payload.update(overrides)
    return build_trigger_event(**payload)

def test_contract_is_deterministic_and_versioned():
    a, b = contract(), contract()
    assert a == b
    assert a["contract_version"] == TRIGGER_CONTRACT_VERSION
    assert len(a["trigger_hash"]) == 64
    validate_trigger_contract(a, decision_id=DECISION)

def test_contract_rejects_unsupported_and_ambiguous_rules():
    with pytest.raises(ValueError, match="unsupported value"):
        contract(operator="EXEC")
    with pytest.raises(ValueError, match="target is required"):
        contract(operator="LTE", target=None)
    x = contract(operator="PRESENT", target="ignored")
    assert x["target"] is None

def test_contract_tampering_is_blocked():
    x = contract()
    x["decision_revision_hash"] = "b" * 64
    with pytest.raises(ValueError, match="trigger hash mismatch"):
        validate_trigger_contract(x)

def test_numeric_match_and_nonmatch():
    c = contract()
    assert event(c, value="349.5")["trigger_state"] == "MATCHED"
    assert event(c, value="350.1")["trigger_state"] == "NOT_MATCHED"

def test_bad_numeric_is_unknown_not_false():
    e = event(contract(), value="not-a-number")
    assert e["trigger_state"] == "UNKNOWN"
    assert e["evaluation_reason"] == "non_numeric_comparison_value"

@pytest.mark.parametrize("operator,value,previous,expected", [
    ("CHANGED", "101", "100", "MATCHED"),
    ("UNCHANGED", "100", "100", "MATCHED"),
    ("MISSING", None, None, "MATCHED"),
    ("PRESENT", "x", None, "MATCHED"),
])
def test_state_operators(operator, value, previous, expected):
    c = contract(operator=operator, target="ignored")
    e = event(c, trigger_event_id=f"evt-{operator}", value=value, previous_value=previous)
    assert e["trigger_state"] == expected

def test_changed_without_previous_is_unknown():
    e = event(contract(operator="CHANGED", target=None), value="101")
    assert e["trigger_state"] == "UNKNOWN"
    assert e["evaluation_reason"] == "previous_value_missing"

def test_pit_ordering_is_strict():
    c = contract()
    with pytest.raises(ValueError, match="known_at cannot be later"):
        event(c, evaluation_cutoff_at="2026-10-05T10:00:00+00:00", known_at="2026-10-05T10:01:00+00:00")
    with pytest.raises(ValueError, match="observed_at cannot"):
        event(c, observed_at="2026-10-05T10:06:00+00:00", known_at="2026-10-05T10:05:00+00:00")

def test_event_binds_exact_trigger_and_recomputes_state():
    c1, c2 = contract(), contract(trigger_id="tr-price-2")
    e = event(c1)
    tampered = dict(e); tampered["trigger_hash"] = c2["trigger_hash"]
    with pytest.raises(ValueError, match="trigger_hash"):
        validate_trigger_event(tampered, trigger_contract=c1)
    drift = dict(e); drift["trigger_state"] = "MATCHED"; drift["value"] = "999"
    with pytest.raises(ValueError, match="evaluation drift"):
        validate_trigger_event(drift, trigger_contract=c1)

def test_disabled_trigger_never_matches():
    e = event(contract(enabled=False), value="1")
    assert e["trigger_state"] == "NOT_MATCHED"
    assert e["evaluation_reason"] == "trigger_disabled"

def test_event_schema():
    schema = load("schemas/trigger_event_v0.1.schema.json")
    e = event(contract())
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(e)) == []

def test_contract_schema():
    schema = load("schemas/trigger_contract_v0.1.schema.json")
    c = contract()
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(c)) == []

def test_event_is_versioned_and_validates():
    c = contract()
    e = event(c)
    assert e["event_version"] == TRIGGER_EVENT_VERSION
    assert e["validation_status"] == "VALID"
    validate_trigger_event(e, trigger_contract=c)

def test_event_requires_timezone():
    with pytest.raises(ValueError, match="include timezone"):
        event(contract(), evaluation_cutoff_at="2026-10-06T00:00:00", observed_at="2026-10-05T10:00:00", known_at="2026-10-05T10:05:00")

def test_store_persists_only_canonical_trigger_objects(tmp_path):
    from iios_mvp.store import create_or_load_series, next_revision, write_decision_revision, write_snapshot, write_trigger_contract, write_trigger_event
    import hashlib
    import json

    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {"case_id": CASE, "cutoff_date": CUTOFF},
        "decision": {"action": "HOLD"},
    }
    snapshot_hash = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    snapshot = {**core, "snapshot_hash": snapshot_hash}
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(tmp_path, "CN-A", "300750", "CATL", "2026-10-04T00:00:00Z")
    write_decision_revision(tmp_path, series["decision_series_id"], 1, snapshot, "run-1")
    revision = json.loads((tmp_path / f"{DECISION}.decision.json").read_text())

    raw_contract = {
        "trigger_id": "tr-store-1",
        "decision_id": DECISION,
        "decision_series_id": SERIES,
        "revision": 1,
        "decision_revision_hash": revision["revision_hash"],
        "case_id": CASE,
        "decision_cutoff_date": CUTOFF,
        "role": "THESIS_BREAK",
        "metric_id": "market_price",
        "operator": "LTE",
        "target": "300",
        "unit": "CNY/share",
        "evidence_ids": [],
        "enabled": True,
    }
    cp = write_trigger_contract(tmp_path, DECISION, raw_contract)
    stored_contract = __import__("json").loads(cp.read_text())
    assert stored_contract["contract_version"] == TRIGGER_CONTRACT_VERSION
    assert stored_contract["decision_revision_hash"] == revision["revision_hash"]

    ep = write_trigger_event(tmp_path, {
        "trigger_id": "tr-store-1",
        "trigger_event_id": "evt-store-1",
        "evaluation_cutoff_at": "2026-10-06T00:00:00+00:00",
        "observed_at": "2026-10-05T10:00:00+00:00",
        "known_at": "2026-10-05T10:05:00+00:00",
        "source_id": "szse",
        "evidence_id": "ev-store-1",
        "value": "299",
        "previous_value": None,
    })
    stored_event = __import__("json").loads(ep.read_text())
    assert stored_event["trigger_state"] == "MATCHED"
    validate_trigger_event(stored_event, trigger_contract=stored_contract)


def test_store_rejects_orphan_or_mismatched_revision_binding(tmp_path):
    from iios_mvp.store import write_trigger_contract
    raw = {
        "trigger_id": "tr-orphan",
        "decision_id": DECISION,
        "decision_series_id": SERIES,
        "revision": 1,
        "decision_revision_hash": REVISION_HASH,
        "case_id": CASE,
        "decision_cutoff_date": CUTOFF,
        "role": "VALIDATION",
        "metric_id": "market_price",
        "operator": "LTE",
        "target": "300",
        "unit": None,
        "evidence_ids": [],
        "enabled": True,
    }
    with pytest.raises(ValueError, match="decision revision"):
        write_trigger_contract(tmp_path, DECISION, raw)
