from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .decision_lifecycle_production import (
    DECISION_ACTIONS,
    validate_decision_revision,
    validate_human_approval,
)

C6_EXECUTION_RECEIPT_VERSION = "IIOS-C6-EXECUTION-RECEIPT-0.1"
C6_POLICY_EFFECT = "POST_APPROVAL_RECORD_ONLY_NO_DECISION_MUTATION"
EXECUTION_STATUSES = {"EXECUTED", "PARTIALLY_EXECUTED", "NOT_EXECUTED", "CANCELLED"}
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _decimal_or_none(value: Any, field: str) -> str | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} must be finite and >= 0")
    return str(result)


def _datetime(value: Any, field: str) -> str:
    try:
        result = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result.isoformat()


def _id(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _ID_RE.fullmatch(result):
        raise ValueError(f"{field} has invalid identifier characters")
    return result


def build_execution_receipt(
    *,
    execution_receipt_id: str,
    decision_revision: Mapping[str, Any],
    human_approval: Mapping[str, Any],
    executed_at: str,
    execution_status: str,
    executed_quantity: Any = None,
    executed_position_pct: Any = None,
    executed_price: Any = None,
    actor_identity: str,
) -> dict[str, Any]:
    validate_decision_revision(
        decision_revision,
        case_id=decision_revision["case_id"],
        cutoff_date=decision_revision["cutoff_date"],
    )
    validate_human_approval(human_approval, decision_revision=decision_revision)

    receipt_id = _id(execution_receipt_id, "execution_receipt_id")
    status = _text(execution_status, "execution_status").upper()
    if status not in EXECUTION_STATUSES:
        raise ValueError(f"unsupported execution_status: {status}")
    if human_approval["approval_status"] != "HUMAN_APPROVED" or human_approval["approved"] is not True:
        raise ValueError("execution receipt requires HUMAN_APPROVED approval")

    quantity = _decimal_or_none(executed_quantity, "executed_quantity")
    position_pct = _decimal_or_none(executed_position_pct, "executed_position_pct")
    price = _decimal_or_none(executed_price, "executed_price")

    if status in {"EXECUTED", "PARTIALLY_EXECUTED"} and quantity is None and position_pct is None:
        raise ValueError("executed or partially executed receipt requires quantity or position")
    if position_pct is not None and Decimal(position_pct) > Decimal("100"):
        raise ValueError("executed_position_pct must be <= 100")

    core = {
        "receipt_version": C6_EXECUTION_RECEIPT_VERSION,
        "execution_receipt_id": receipt_id,
        "decision_id": decision_revision["decision_id"],
        "decision_series_id": decision_revision["decision_series_id"],
        "revision": decision_revision["revision"],
        "run_id": decision_revision["run_id"],
        "case_id": decision_revision["case_id"],
        "cutoff_date": decision_revision["cutoff_date"],
        "snapshot_hash": decision_revision["snapshot_hash"],
        "revision_hash": decision_revision["revision_hash"],
        "approval_hash": human_approval["approval_hash"],
        "approval_status": human_approval["approval_status"],
        "approved_action": decision_revision["ai_action"],
        "executed_at": _datetime(executed_at, "executed_at"),
        "execution_status": status,
        "executed_quantity": quantity,
        "executed_position_pct": position_pct,
        "executed_price": price,
        "actor_identity": _text(actor_identity, "actor_identity"),
        "policy_effect": C6_POLICY_EFFECT,
        "auto_execution": False,
    }
    return {**core, "receipt_hash": _sha(core)}


def validate_execution_receipt(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("execution_receipt must be an object")
    required = {
        "receipt_version",
        "execution_receipt_id",
        "decision_id",
        "decision_series_id",
        "revision",
        "run_id",
        "case_id",
        "cutoff_date",
        "snapshot_hash",
        "revision_hash",
        "approval_hash",
        "approval_status",
        "approved_action",
        "executed_at",
        "execution_status",
        "executed_quantity",
        "executed_position_pct",
        "executed_price",
        "actor_identity",
        "policy_effect",
        "auto_execution",
        "receipt_hash",
    }
    if set(record) != required:
        raise ValueError("execution_receipt fields are invalid")
    if record["receipt_version"] != C6_EXECUTION_RECEIPT_VERSION:
        raise ValueError("execution_receipt version mismatch")
    if not _ID_RE.fullmatch(str(record["execution_receipt_id"])):
        raise ValueError("execution_receipt_id invalid")
    if record["approval_status"] != "HUMAN_APPROVED":
        raise ValueError("execution_receipt approval status invalid")
    if record["approved_action"] not in DECISION_ACTIONS:
        raise ValueError("execution_receipt approved action invalid")
    if record["execution_status"] not in EXECUTION_STATUSES:
        raise ValueError("execution_receipt execution status invalid")
    if record["auto_execution"] is not False:
        raise ValueError("execution_receipt auto_execution must be false")
    if not str(record["actor_identity"]).strip():
        raise ValueError("execution_receipt actor_identity is required")
    for field in ("snapshot_hash", "revision_hash", "approval_hash", "receipt_hash"):
        if not _HASH_RE.fullmatch(str(record[field])):
            raise ValueError(f"{field} must be lowercase SHA-256")
    _datetime(record["executed_at"], "executed_at")
    for field in ("executed_quantity", "executed_position_pct", "executed_price"):
        if record[field] is not None:
            _decimal_or_none(record[field], field)
    if record["executed_position_pct"] is not None and Decimal(str(record["executed_position_pct"])) > Decimal("100"):
        raise ValueError("executed_position_pct must be <= 100")
    if record["execution_status"] in {"EXECUTED", "PARTIALLY_EXECUTED"}:
        if record["executed_quantity"] is None and record["executed_position_pct"] is None:
            raise ValueError("executed status requires quantity or position")
    core = {k: record[k] for k in required if k != "receipt_hash"}
    if record["receipt_hash"] != _sha(core):
        raise ValueError("execution_receipt receipt hash mismatch")


def replay_execution_receipt(
    record: Mapping[str, Any],
    *,
    decision_revision: Mapping[str, Any],
    human_approval: Mapping[str, Any],
) -> dict[str, Any]:
    validate_execution_receipt(record)
    expected = build_execution_receipt(
        execution_receipt_id=record["execution_receipt_id"],
        decision_revision=decision_revision,
        human_approval=human_approval,
        executed_at=record["executed_at"],
        execution_status=record["execution_status"],
        executed_quantity=record["executed_quantity"],
        executed_position_pct=record["executed_position_pct"],
        executed_price=record["executed_price"],
        actor_identity=record["actor_identity"],
    )
    deterministic = _canonical(expected) == _canonical(dict(record))
    return {
        "replay_status": "PASS" if deterministic else "FAIL",
        "deterministic_replay": deterministic,
        "receipt_hash": record["receipt_hash"],
        "replay_hash": expected["receipt_hash"],
    }


def execution_receipt_path(root: str | Path, execution_receipt_id: str) -> Path:
    return Path(root) / f"{_id(execution_receipt_id, 'execution_receipt_id')}.execution-receipt.json"


__all__ = [
    "C6_EXECUTION_RECEIPT_VERSION",
    "C6_POLICY_EFFECT",
    "EXECUTION_STATUSES",
    "build_execution_receipt",
    "validate_execution_receipt",
    "replay_execution_receipt",
    "execution_receipt_path",
]
