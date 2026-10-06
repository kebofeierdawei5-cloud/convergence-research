from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

MONITORING_STATE_VERSION = "IIOS-MONITORING-STATE-0.1"
LIFECYCLE_STATES = {"ACTIVE", "DISABLED", "RETIRED"}
EVALUATION_STATUSES = {"NEVER_EVALUATED", "VALID", "UNKNOWN"}
DUE_STATES = {"UNSCHEDULED", "NOT_DUE", "DUE", "OVERDUE"}
TRIGGER_STATES = {"MATCHED", "NOT_MATCHED", "UNKNOWN"}


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


def _due_state(next_due_at: str | None, reference_at: str) -> str:
    if next_due_at is None:
        return "UNSCHEDULED"
    due = datetime.fromisoformat(_timestamp(next_due_at, "next_due_at").replace("Z", "+00:00"))
    reference = datetime.fromisoformat(_timestamp(reference_at, "reference_at").replace("Z", "+00:00"))
    return "DUE" if due == reference else ("OVERDUE" if due < reference else "NOT_DUE")


def build_monitoring_state(
    *,
    monitor_id: str,
    trigger_contract: Mapping[str, Any],
    lifecycle_status: str,
    next_due_at: str | None = None,
    evaluation_reference_at: str | None = None,
) -> dict[str, Any]:
    from .trigger_production import validate_trigger_contract

    validate_trigger_contract(trigger_contract)
    monitor_id = _text(monitor_id, "monitor_id")
    lifecycle_status = _text(lifecycle_status, "lifecycle_status").upper()
    if lifecycle_status not in LIFECYCLE_STATES:
        raise ValueError(f"lifecycle_status has unsupported value: {lifecycle_status}")
    if next_due_at is not None:
        next_due_at = _timestamp(next_due_at, "next_due_at")
    if evaluation_reference_at is None:
        evaluation_reference_at = next_due_at or trigger_contract["decision_cutoff_date"] + "T00:00:00+00:00"
    evaluation_reference_at = _timestamp(evaluation_reference_at, "evaluation_reference_at")

    core = {
        "state_version": MONITORING_STATE_VERSION,
        "monitor_id": monitor_id,
        "trigger_id": trigger_contract["trigger_id"],
        "trigger_hash": trigger_contract["trigger_hash"],
        "decision_id": trigger_contract["decision_id"],
        "decision_series_id": trigger_contract["decision_series_id"],
        "revision": trigger_contract["revision"],
        "decision_revision_hash": trigger_contract["decision_revision_hash"],
        "case_id": trigger_contract["case_id"],
        "lifecycle_status": lifecycle_status,
        "evaluation_status": "NEVER_EVALUATED",
        "last_trigger_state": None,
        "last_event_id": None,
        "last_known_at": None,
        "last_evaluation_cutoff_at": None,
        "next_due_at": next_due_at,
        "due_state": _due_state(next_due_at, evaluation_reference_at),
        "policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
    }
    return {**core, "state_hash": _sha(core)}


def validate_monitoring_state(record: Any, *, trigger_contract: Mapping[str, Any]) -> None:
    from .trigger_production import validate_trigger_contract

    validate_trigger_contract(trigger_contract)
    if not isinstance(record, Mapping):
        raise ValueError("monitoring_state must be an object")
    required = {
        "state_version", "monitor_id", "trigger_id", "trigger_hash", "decision_id",
        "decision_series_id", "revision", "decision_revision_hash", "case_id",
        "lifecycle_status", "evaluation_status", "last_trigger_state", "last_event_id",
        "last_known_at", "last_evaluation_cutoff_at", "next_due_at", "due_state",
        "policy_effect", "state_hash",
    }
    if set(record) != required:
        raise ValueError("monitoring_state fields are invalid")
    if record["state_version"] != MONITORING_STATE_VERSION:
        raise ValueError("monitoring_state version mismatch")
    for field in ("trigger_id", "trigger_hash", "decision_id", "decision_series_id", "revision", "decision_revision_hash", "case_id"):
        if record[field] != trigger_contract[field]:
            raise ValueError(f"monitoring_state {field} does not match trigger_contract")
    if record["lifecycle_status"] not in LIFECYCLE_STATES:
        raise ValueError("monitoring_state lifecycle_status invalid")
    if record["evaluation_status"] not in EVALUATION_STATUSES:
        raise ValueError("monitoring_state evaluation_status invalid")
    if record["last_trigger_state"] not in TRIGGER_STATES | {None}:
        raise ValueError("monitoring_state last_trigger_state invalid")
    for field in ("last_known_at", "last_evaluation_cutoff_at", "next_due_at"):
        if record[field] is not None:
            _timestamp(record[field], field)
    if record["last_event_id"] is None:
        if record["evaluation_status"] != "NEVER_EVALUATED" or record["last_trigger_state"] is not None:
            raise ValueError("monitoring_state initial evaluation fields are inconsistent")
    elif record["evaluation_status"] == "NEVER_EVALUATED":
        raise ValueError("monitoring_state evaluated state cannot be NEVER_EVALUATED")
    if record["due_state"] not in DUE_STATES:
        raise ValueError("monitoring_state due_state invalid")
    if record["policy_effect"] != "NO_DIRECT_DECISION_PRECEDENCE_CHANGE":
        raise ValueError("monitoring_state policy effect invalid")
    core = {k: record[k] for k in required if k != "state_hash"}
    if record["state_hash"] != _sha(core):
        raise ValueError("monitoring_state hash mismatch")


def apply_trigger_event(
    *,
    previous_state: Mapping[str, Any],
    trigger_contract: Mapping[str, Any],
    trigger_event: Mapping[str, Any],
    next_due_at: str | None = None,
) -> dict[str, Any]:
    from .trigger_production import validate_trigger_event

    validate_monitoring_state(previous_state, trigger_contract=trigger_contract)
    validate_trigger_event(trigger_event, trigger_contract=trigger_contract)
    if trigger_event["trigger_event_id"] == previous_state.get("last_event_id"):
        if next_due_at is None or next_due_at == previous_state.get("next_due_at"):
            return dict(previous_state)
        raise ValueError("idempotent event cannot change next_due_at")
    if previous_state["last_known_at"] is not None:
        old = datetime.fromisoformat(previous_state["last_known_at"].replace("Z", "+00:00"))
        new = datetime.fromisoformat(trigger_event["known_at"].replace("Z", "+00:00"))
        if new <= old:
            raise ValueError("trigger event known_at is not strictly later than monitoring state")
    if next_due_at is not None:
        next_due_at = _timestamp(next_due_at, "next_due_at")
    last_state = trigger_event["trigger_state"]
    evaluation_status = "VALID"
    reference_at = trigger_event["evaluation_cutoff_at"]
    core = {
        "state_version": MONITORING_STATE_VERSION,
        "monitor_id": previous_state["monitor_id"],
        "trigger_id": trigger_contract["trigger_id"],
        "trigger_hash": trigger_contract["trigger_hash"],
        "decision_id": trigger_contract["decision_id"],
        "decision_series_id": trigger_contract["decision_series_id"],
        "revision": trigger_contract["revision"],
        "decision_revision_hash": trigger_contract["decision_revision_hash"],
        "case_id": trigger_contract["case_id"],
        "lifecycle_status": previous_state["lifecycle_status"],
        "evaluation_status": evaluation_status,
        "last_trigger_state": last_state,
        "last_event_id": trigger_event["trigger_event_id"],
        "last_known_at": trigger_event["known_at"],
        "last_evaluation_cutoff_at": trigger_event["evaluation_cutoff_at"],
        "next_due_at": previous_state["next_due_at"] if next_due_at is None else next_due_at,
        "due_state": _due_state(previous_state["next_due_at"] if next_due_at is None else next_due_at, reference_at),
        "policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
    }
    return {**core, "state_hash": _sha(core)}


__all__ = [
    "MONITORING_STATE_VERSION",
    "build_monitoring_state",
    "validate_monitoring_state",
    "apply_trigger_event",
]
