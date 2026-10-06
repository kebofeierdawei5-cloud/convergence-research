from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

TRIGGER_CONTRACT_VERSION = "IIOS-TRIGGER-CONTRACT-0.1"
TRIGGER_EVENT_VERSION = "IIOS-TRIGGER-EVENT-0.1"

TRIGGER_ROLES = {"THESIS_BREAK", "MONITORING", "VALIDATION"}
TRIGGER_OPERATORS = {
    "LT", "LTE", "GT", "GTE", "EQ", "NE",
    "CHANGED", "UNCHANGED", "MISSING", "PRESENT",
}
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

def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value

def _date(value: Any, field: str) -> str:
    result = _text(value, field)
    try:
        datetime.strptime(result, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO date YYYY-MM-DD") from exc
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

def _scalar(value: Any, field: str) -> Any:
    if value is None or isinstance(value, (bool, str, int, float)):
        return value
    raise ValueError(f"{field} must be a scalar or null")

def _strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if not allow_empty and not value:
        raise ValueError(f"{field} must be a non-empty list")
    result = [_text(item, f"{field}[]") for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate items")
    return result

def _operator(value: Any) -> str:
    result = _text(value, "operator").upper()
    if result not in TRIGGER_OPERATORS:
        raise ValueError(f"operator has unsupported value: {result}")
    return result

def _parse_decimal(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError from exc
    if not parsed.is_finite():
        raise ValueError("numeric value must be finite")
    return parsed

def _same_scalar(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return _parse_decimal(left) == _parse_decimal(right)
    except ValueError:
        return type(left) is type(right) and left == right

def _evaluate(contract: Mapping[str, Any], value: Any, previous_value: Any) -> tuple[str, str]:
    operator = contract["operator"]
    target = contract["target"]
    if operator == "MISSING":
        return ("MATCHED", "value_is_missing") if value is None else ("NOT_MATCHED", "value_is_present")
    if operator == "PRESENT":
        return ("MATCHED", "value_is_present") if value is not None else ("NOT_MATCHED", "value_is_missing")
    if operator in {"CHANGED", "UNCHANGED"}:
        if previous_value is None:
            return "UNKNOWN", "previous_value_missing"
        changed = not _same_scalar(value, previous_value)
        matched = changed if operator == "CHANGED" else not changed
        return ("MATCHED" if matched else "NOT_MATCHED", "value_changed" if changed else "value_unchanged")
    if value is None:
        return "UNKNOWN", "current_value_missing"
    if operator in {"LT", "LTE", "GT", "GTE"}:
        try:
            current = _parse_decimal(value)
            threshold = _parse_decimal(target)
        except ValueError:
            return "UNKNOWN", "non_numeric_comparison_value"
        matched = {"LT": current < threshold, "LTE": current <= threshold, "GT": current > threshold, "GTE": current >= threshold}[operator]
        return ("MATCHED" if matched else "NOT_MATCHED", f"comparison_{operator.lower()}")
    if operator == "EQ":
        matched = _same_scalar(value, target)
    elif operator == "NE":
        matched = not _same_scalar(value, target)
    else:
        return "UNKNOWN", "unsupported_operator"
    return ("MATCHED" if matched else "NOT_MATCHED", f"comparison_{operator.lower()}")

def build_trigger_contract(*, trigger_id: str, decision_id: str, decision_series_id: str, revision: int, decision_revision_hash: str, case_id: str, decision_cutoff_date: str, role: str, metric_id: str, operator: str, target: Any = None, unit: str | None = None, evidence_ids: list[str] | None = None, enabled: bool = True) -> dict[str, Any]:
    trigger_id = _text(trigger_id, "trigger_id")
    decision_id = _text(decision_id, "decision_id")
    decision_series_id = _text(decision_series_id, "decision_series_id")
    revision = _positive_int(revision, "revision")
    decision_revision_hash = _text(decision_revision_hash, "decision_revision_hash")
    if len(decision_revision_hash) != 64 or any(c not in "0123456789abcdef" for c in decision_revision_hash):
        raise ValueError("decision_revision_hash must be a lowercase SHA-256")
    case_id = _text(case_id, "case_id")
    decision_cutoff_date = _date(decision_cutoff_date, "decision_cutoff_date")
    role = _text(role, "role").upper()
    if role not in TRIGGER_ROLES:
        raise ValueError(f"role has unsupported value: {role}")
    metric_id = _text(metric_id, "metric_id")
    operator = _operator(operator)
    target = _scalar(target, "target")
    unit = None if unit is None else _text(unit, "unit")
    evidence_ids = _strings([] if evidence_ids is None else evidence_ids, "evidence_ids", allow_empty=True)
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be boolean")
    if operator in {"CHANGED", "UNCHANGED", "MISSING", "PRESENT"}:
        target = None
    elif target is None:
        raise ValueError(f"target is required for operator {operator}")
    core = {
        "contract_version": TRIGGER_CONTRACT_VERSION,
        "trigger_id": trigger_id,
        "decision_id": decision_id,
        "decision_series_id": decision_series_id,
        "revision": revision,
        "decision_revision_hash": decision_revision_hash,
        "case_id": case_id,
        "decision_cutoff_date": decision_cutoff_date,
        "role": role,
        "metric_id": metric_id,
        "operator": operator,
        "target": target,
        "unit": unit,
        "evidence_ids": evidence_ids,
        "enabled": enabled,
        "policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
    }
    return {**core, "trigger_hash": _sha(core)}

def validate_trigger_contract(record: Any, *, decision_id: str | None = None) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("trigger_contract must be an object")
    required = {"contract_version", "trigger_id", "decision_id", "decision_series_id", "revision", "decision_revision_hash", "case_id", "decision_cutoff_date", "role", "metric_id", "operator", "target", "unit", "evidence_ids", "enabled", "policy_effect", "trigger_hash"}
    if set(record) != required:
        raise ValueError("trigger_contract fields are invalid")
    if record["contract_version"] != TRIGGER_CONTRACT_VERSION:
        raise ValueError("trigger_contract version mismatch")
    if decision_id is not None and record["decision_id"] != decision_id:
        raise ValueError("trigger_contract decision_id mismatch")
    rebuilt = build_trigger_contract(trigger_id=record["trigger_id"], decision_id=record["decision_id"], decision_series_id=record["decision_series_id"], revision=record["revision"], decision_revision_hash=record["decision_revision_hash"], case_id=record["case_id"], decision_cutoff_date=record["decision_cutoff_date"], role=record["role"], metric_id=record["metric_id"], operator=record["operator"], target=record["target"], unit=record["unit"], evidence_ids=record["evidence_ids"], enabled=record["enabled"])
    if rebuilt["trigger_hash"] != record["trigger_hash"]:
        raise ValueError("trigger_contract trigger hash mismatch")

def build_trigger_event(*, trigger_contract: Mapping[str, Any], trigger_event_id: str, evaluation_cutoff_at: str, observed_at: str, known_at: str, source_id: str, evidence_id: str, value: Any, previous_value: Any = None) -> dict[str, Any]:
    validate_trigger_contract(trigger_contract)
    trigger_event_id = _text(trigger_event_id, "trigger_event_id")
    evaluation_cutoff_at = _timestamp(evaluation_cutoff_at, "evaluation_cutoff_at")
    observed_at = _timestamp(observed_at, "observed_at")
    known_at = _timestamp(known_at, "known_at")
    cutoff_dt = datetime.fromisoformat(evaluation_cutoff_at.replace("Z", "+00:00"))
    observed_dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    known_dt = datetime.fromisoformat(known_at.replace("Z", "+00:00"))
    if observed_dt > known_dt:
        raise ValueError("observed_at cannot be later than known_at")
    if known_dt > cutoff_dt:
        raise ValueError("known_at cannot be later than evaluation_cutoff_at")
    source_id = _text(source_id, "source_id")
    evidence_id = _text(evidence_id, "evidence_id")
    value = _scalar(value, "value")
    previous_value = _scalar(previous_value, "previous_value")
    if not trigger_contract["enabled"]:
        trigger_state, reason = "NOT_MATCHED", "trigger_disabled"
    else:
        trigger_state, reason = _evaluate(trigger_contract, value, previous_value)
    core = {
        "event_version": TRIGGER_EVENT_VERSION,
        "trigger_event_id": trigger_event_id,
        "trigger_id": trigger_contract["trigger_id"],
        "trigger_hash": trigger_contract["trigger_hash"],
        "decision_id": trigger_contract["decision_id"],
        "decision_series_id": trigger_contract["decision_series_id"],
        "revision": trigger_contract["revision"],
        "decision_revision_hash": trigger_contract["decision_revision_hash"],
        "case_id": trigger_contract["case_id"],
        "evaluation_cutoff_at": evaluation_cutoff_at,
        "observed_at": observed_at,
        "known_at": known_at,
        "source_id": source_id,
        "evidence_id": evidence_id,
        "value": value,
        "previous_value": previous_value,
        "validation_status": "VALID",
        "trigger_state": trigger_state,
        "evaluation_reason": reason,
        "policy_effect": "NO_DIRECT_DECISION_PRECEDENCE_CHANGE",
    }
    return {**core, "trigger_event_hash": _sha(core)}

def validate_trigger_event(record: Any, *, trigger_contract: Mapping[str, Any]) -> None:
    validate_trigger_contract(trigger_contract)
    if not isinstance(record, Mapping):
        raise ValueError("trigger_event must be an object")
    required = {"event_version", "trigger_event_id", "trigger_id", "trigger_hash", "decision_id", "decision_series_id", "revision", "decision_revision_hash", "case_id", "evaluation_cutoff_at", "observed_at", "known_at", "source_id", "evidence_id", "value", "previous_value", "validation_status", "trigger_state", "evaluation_reason", "policy_effect", "trigger_event_hash"}
    if set(record) != required:
        raise ValueError("trigger_event fields are invalid")
    if record["event_version"] != TRIGGER_EVENT_VERSION:
        raise ValueError("trigger_event version mismatch")
    for field in ("trigger_id", "trigger_hash", "decision_id", "decision_series_id", "revision", "decision_revision_hash", "case_id"):
        if record[field] != trigger_contract[field]:
            raise ValueError(f"trigger_event {field} does not match trigger_contract")
    if record["validation_status"] != "VALID":
        raise ValueError("trigger_event validation_status invalid")
    if record["trigger_state"] not in TRIGGER_STATES:
        raise ValueError("trigger_event trigger_state invalid")
    if record["policy_effect"] != "NO_DIRECT_DECISION_PRECEDENCE_CHANGE":
        raise ValueError("trigger_event policy effect invalid")
    rebuilt = build_trigger_event(trigger_contract=trigger_contract, trigger_event_id=record["trigger_event_id"], evaluation_cutoff_at=record["evaluation_cutoff_at"], observed_at=record["observed_at"], known_at=record["known_at"], source_id=record["source_id"], evidence_id=record["evidence_id"], value=record["value"], previous_value=record["previous_value"])
    if rebuilt["trigger_state"] != record["trigger_state"] or rebuilt["evaluation_reason"] != record["evaluation_reason"]:
        raise ValueError("trigger_event evaluation drift")
    if rebuilt["trigger_event_hash"] != record["trigger_event_hash"]:
        raise ValueError("trigger_event hash mismatch")

__all__ = ["TRIGGER_CONTRACT_VERSION", "TRIGGER_EVENT_VERSION", "build_trigger_contract", "validate_trigger_contract", "build_trigger_event", "validate_trigger_event"]
