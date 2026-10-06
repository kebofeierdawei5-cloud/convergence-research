from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

VALIDATION_VERSION = "IIOS-VALIDATION-0.1"
MONITORING_INITIALIZATION_VERSION = "IIOS-MONITORING-INITIALIZATION-0.1"
MONITORING_EVALUATION_VERSION = "IIOS-MONITORING-EVALUATION-0.1"

VALIDATION_STATUSES = {"PASS", "FAIL"}
CHECK_STATUSES = {"PASS", "FAIL"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _timestamp(value: Any, field: str) -> str:
    result = _text(value, field)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return result


def build_monitoring_initialization_record(
    *,
    trigger_contract: Mapping[str, Any],
    initial_state: Mapping[str, Any],
) -> dict[str, Any]:
    from .monitoring_state import validate_monitoring_state
    from .trigger_production import validate_trigger_contract

    validate_trigger_contract(trigger_contract)
    validate_monitoring_state(initial_state, trigger_contract=trigger_contract)
    core = {
        "initialization_version": MONITORING_INITIALIZATION_VERSION,
        "initialization_id": f'{initial_state["monitor_id"]}-initial',
        "trigger_id": trigger_contract["trigger_id"],
        "trigger_hash": trigger_contract["trigger_hash"],
        "decision_id": trigger_contract["decision_id"],
        "decision_series_id": trigger_contract["decision_series_id"],
        "revision": trigger_contract["revision"],
        "decision_revision_hash": trigger_contract["decision_revision_hash"],
        "case_id": trigger_contract["case_id"],
        "monitor_id": initial_state["monitor_id"],
        "initial_state_hash": initial_state["state_hash"],
        "initial_state": dict(initial_state),
    }
    return {**core, "initialization_hash": _sha(core)}


def validate_monitoring_initialization_record(
    record: Any,
    *,
    trigger_contract: Mapping[str, Any],
) -> None:
    from .monitoring_state import validate_monitoring_state
    from .trigger_production import validate_trigger_contract

    validate_trigger_contract(trigger_contract)
    if not isinstance(record, Mapping):
        raise ValueError("monitoring_initialization must be an object")
    required = {
        "initialization_version",
        "initialization_id",
        "trigger_id",
        "trigger_hash",
        "decision_id",
        "decision_series_id",
        "revision",
        "decision_revision_hash",
        "case_id",
        "monitor_id",
        "initial_state_hash",
        "initial_state",
        "initialization_hash",
    }
    if set(record) != required:
        raise ValueError("monitoring_initialization fields are invalid")
    if record["initialization_version"] != MONITORING_INITIALIZATION_VERSION:
        raise ValueError("monitoring_initialization version mismatch")
    for field in (
        "trigger_id",
        "trigger_hash",
        "decision_id",
        "decision_series_id",
        "revision",
        "decision_revision_hash",
        "case_id",
    ):
        if record[field] != trigger_contract[field]:
            raise ValueError(f"monitoring_initialization {field} does not match trigger_contract")
    validate_monitoring_state(record["initial_state"], trigger_contract=trigger_contract)
    if record["initial_state"]["monitor_id"] != record["monitor_id"]:
        raise ValueError("monitoring_initialization monitor_id mismatch")
    if record["initial_state_hash"] != record["initial_state"]["state_hash"]:
        raise ValueError("monitoring_initialization initial_state_hash mismatch")
    core = {k: record[k] for k in required if k != "initialization_hash"}
    if record["initialization_hash"] != _sha(core):
        raise ValueError("monitoring_initialization hash mismatch")


def build_monitoring_evaluation_record(
    *,
    trigger_contract: Mapping[str, Any],
    trigger_event: Mapping[str, Any],
    previous_state: Mapping[str, Any],
    resulting_state: Mapping[str, Any],
) -> dict[str, Any]:
    from .monitoring_state import validate_monitoring_state
    from .trigger_production import validate_trigger_contract, validate_trigger_event

    validate_trigger_contract(trigger_contract)
    validate_trigger_event(trigger_event, trigger_contract=trigger_contract)
    validate_monitoring_state(previous_state, trigger_contract=trigger_contract)
    validate_monitoring_state(resulting_state, trigger_contract=trigger_contract)
    core = {
        "evaluation_version": MONITORING_EVALUATION_VERSION,
        "evaluation_id": f'{trigger_event["trigger_event_id"]}-evaluation',
        "trigger_event_id": trigger_event["trigger_event_id"],
        "trigger_id": trigger_contract["trigger_id"],
        "trigger_hash": trigger_contract["trigger_hash"],
        "decision_id": trigger_contract["decision_id"],
        "decision_series_id": trigger_contract["decision_series_id"],
        "revision": trigger_contract["revision"],
        "decision_revision_hash": trigger_contract["decision_revision_hash"],
        "case_id": trigger_contract["case_id"],
        "previous_state_hash": previous_state["state_hash"],
        "resulting_state_hash": resulting_state["state_hash"],
        "previous_next_due_at": previous_state["next_due_at"],
        "resulting_next_due_at": resulting_state["next_due_at"],
        "event_known_at": trigger_event["known_at"],
        "evaluation_cutoff_at": trigger_event["evaluation_cutoff_at"],
        "evaluation_status": resulting_state["evaluation_status"],
    }
    return {**core, "evaluation_hash": _sha(core)}


def validate_monitoring_evaluation_record(
    record: Any,
    *,
    trigger_contract: Mapping[str, Any],
    trigger_event: Mapping[str, Any],
    previous_state: Mapping[str, Any],
    resulting_state: Mapping[str, Any],
) -> None:
    from .monitoring_state import validate_monitoring_state
    from .trigger_production import validate_trigger_contract, validate_trigger_event

    expected = build_monitoring_evaluation_record(
        trigger_contract=trigger_contract,
        trigger_event=trigger_event,
        previous_state=previous_state,
        resulting_state=resulting_state,
    )
    if not isinstance(record, Mapping):
        raise ValueError("monitoring_evaluation must be an object")
    required = set(expected)
    if set(record) != required:
        raise ValueError("monitoring_evaluation fields are invalid")
    validate_trigger_contract(trigger_contract)
    validate_trigger_event(trigger_event, trigger_contract=trigger_contract)
    validate_monitoring_state(previous_state, trigger_contract=trigger_contract)
    validate_monitoring_state(resulting_state, trigger_contract=trigger_contract)
    if dict(record) != expected:
        raise ValueError("monitoring_evaluation content or hash mismatch")


def build_validation_record(
    *,
    validation_id: str,
    trigger_contract: Mapping[str, Any],
    monitor_id: str,
    validation_cutoff_at: str,
    checks: Mapping[str, str],
    checked_event_ids: list[str],
    initial_state_hash: str,
    replayed_state_hash: str | None,
    persisted_state_hash: str | None,
    history_head_hash: str,
    issues: list[str],
) -> dict[str, Any]:
    from .trigger_production import validate_trigger_contract

    validate_trigger_contract(trigger_contract)
    validation_id = _text(validation_id, "validation_id")
    validation_cutoff_at = _timestamp(validation_cutoff_at, "validation_cutoff_at")
    required_checks = {
        "decision_revision_replay",
        "trigger_contract_binding",
        "trigger_event_pit",
        "monitoring_state_integrity",
        "transition_history",
        "monitoring_replay",
    }
    if set(checks) != required_checks:
        raise ValueError("validation checks are incomplete")
    if any(value not in CHECK_STATUSES for value in checks.values()):
        raise ValueError("validation check status is invalid")
    if not all(isinstance(item, str) and item for item in checked_event_ids):
        raise ValueError("checked_event_ids must contain non-empty strings")
    if any(len(value) != 64 for value in (initial_state_hash, history_head_hash) if value is not None):
        raise ValueError("validation hashes must be SHA-256")
    if replayed_state_hash is not None and len(replayed_state_hash) != 64:
        raise ValueError("replayed_state_hash must be SHA-256")
    if persisted_state_hash is not None and len(persisted_state_hash) != 64:
        raise ValueError("persisted_state_hash must be SHA-256")
    normalized_issues = [str(item) for item in issues]
    core = {
        "validation_version": VALIDATION_VERSION,
        "validation_id": validation_id,
        "validation_scope": "MONITORING_REPLAY",
        "decision_id": trigger_contract["decision_id"],
        "decision_series_id": trigger_contract["decision_series_id"],
        "revision": trigger_contract["revision"],
        "decision_revision_hash": trigger_contract["decision_revision_hash"],
        "case_id": trigger_contract["case_id"],
        "decision_cutoff_date": trigger_contract["decision_cutoff_date"],
        "trigger_id": trigger_contract["trigger_id"],
        "trigger_hash": trigger_contract["trigger_hash"],
        "monitor_id": monitor_id,
        "validation_cutoff_at": validation_cutoff_at,
        "validation_status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "checks": dict(checks),
        "event_count": len(checked_event_ids),
        "checked_event_ids": list(checked_event_ids),
        "initial_state_hash": initial_state_hash,
        "replayed_state_hash": replayed_state_hash,
        "persisted_state_hash": persisted_state_hash,
        "history_head_hash": history_head_hash,
        "issues": normalized_issues,
        "policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
    }
    return {**core, "validation_hash": _sha(core)}


def validate_validation_record(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("validation_record must be an object")
    required = {
        "validation_version",
        "validation_id",
        "validation_scope",
        "decision_id",
        "decision_series_id",
        "revision",
        "decision_revision_hash",
        "case_id",
        "decision_cutoff_date",
        "trigger_id",
        "trigger_hash",
        "monitor_id",
        "validation_cutoff_at",
        "validation_status",
        "checks",
        "event_count",
        "checked_event_ids",
        "initial_state_hash",
        "replayed_state_hash",
        "persisted_state_hash",
        "history_head_hash",
        "issues",
        "policy_effect",
        "validation_hash",
    }
    if set(record) != required:
        raise ValueError("validation_record fields are invalid")
    if record["validation_version"] != VALIDATION_VERSION:
        raise ValueError("validation_record version mismatch")
    if record["validation_scope"] != "MONITORING_REPLAY":
        raise ValueError("validation_record scope invalid")
    if record["validation_status"] not in VALIDATION_STATUSES:
        raise ValueError("validation_record status invalid")
    if not isinstance(record["checks"], Mapping) or set(record["checks"]) != {
        "decision_revision_replay",
        "trigger_contract_binding",
        "trigger_event_pit",
        "monitoring_state_integrity",
        "transition_history",
        "monitoring_replay",
    }:
        raise ValueError("validation_record checks invalid")
    if any(value not in CHECK_STATUSES for value in record["checks"].values()):
        raise ValueError("validation_record check status invalid")
    expected_status = "PASS" if all(value == "PASS" for value in record["checks"].values()) else "FAIL"
    if record["validation_status"] != expected_status:
        raise ValueError("validation_record status does not match checks")
    if not isinstance(record["event_count"], int) or isinstance(record["event_count"], bool) or record["event_count"] < 0:
        raise ValueError("validation_record event_count invalid")
    if not isinstance(record["checked_event_ids"], list) or len(record["checked_event_ids"]) != record["event_count"]:
        raise ValueError("validation_record event list invalid")
    _timestamp(record["validation_cutoff_at"], "validation_cutoff_at")
    for field in ("initial_state_hash", "replayed_state_hash", "persisted_state_hash", "history_head_hash"):
        value = record[field]
        if value is not None and (not isinstance(value, str) or len(value) != 64):
            raise ValueError(f"validation_record {field} invalid")
    if not isinstance(record["issues"], list) or not all(isinstance(item, str) for item in record["issues"]):
        raise ValueError("validation_record issues invalid")
    if record["policy_effect"] != "NO_DIRECT_DECISION_PRECEDENCE_CHANGE":
        raise ValueError("validation_record policy effect invalid")
    core = {k: record[k] for k in required if k != "validation_hash"}
    if record["validation_hash"] != _sha(core):
        raise ValueError("validation_record hash mismatch")


__all__ = [
    "VALIDATION_VERSION",
    "MONITORING_INITIALIZATION_VERSION",
    "MONITORING_EVALUATION_VERSION",
    "build_monitoring_initialization_record",
    "validate_monitoring_initialization_record",
    "build_monitoring_evaluation_record",
    "validate_monitoring_evaluation_record",
    "build_validation_record",
    "validate_validation_record",
]
