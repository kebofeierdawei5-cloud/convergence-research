from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .canonical_run_authorization import verify_revision_write_authorization
from .decision_lifecycle_production import (
    validate_current_projection,
    validate_decision_revision,
    validate_human_approval,
)
from .engine import canonical_json, sha256_obj
from .monitoring_state import validate_monitoring_state
from .store import read_snapshot, snapshot_path
from .trigger_production import validate_trigger_contract
from .validation_replay import validate_validation_record

PUBLICATION_VERSION = "IIOS-MACHINE-PUBLICATION-0.1"


def _text(value: Any, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _timestamp(value: Any, field: str) -> str:
    text = _text(value, field)
    try:
        normalized = text.replace("Z", "+00:00")
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    return text


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def _decision_path(root: str | Path, decision_id: str) -> Path:
    return Path(root) / f"{decision_id}.decision.json"


def _approval_path(root: str | Path, decision_id: str) -> Path:
    return Path(root) / f"{decision_id}.approval.json"


def _series_path(root: str | Path, series_id: str) -> Path:
    return Path(root) / f"{series_id}.series.json"


def _current_path(root: str | Path, series_id: str) -> Path:
    return Path(root) / f"{series_id}.current.json"


def _trigger_contract_path(root: str | Path, trigger_id: str) -> Path:
    return Path(root) / f"{trigger_id}.trigger.json"


def _monitoring_state_path(root: str | Path, trigger_id: str) -> Path:
    return Path(root) / f"{trigger_id}.monitor.json"


def _validation_path(root: str | Path, validation_id: str) -> Path:
    return Path(root) / f"{validation_id}.validation.json"


def _load_revision(root: str | Path, decision_id: str) -> dict[str, Any]:
    record = _load_json(_decision_path(root, decision_id))
    if not record:
        raise ValueError("decision revision not found")
    validate_decision_revision(
        record,
        case_id=record["case_id"],
        cutoff_date=record["cutoff_date"],
    )
    return record


def _load_bound_snapshot(root: str | Path, revision: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = read_snapshot(snapshot_path(root, revision["snapshot_hash"]))
    if snapshot["snapshot_hash"] != revision["snapshot_hash"]:
        raise ValueError("decision revision snapshot binding mismatch")
    return snapshot


def _load_approval(root: str | Path, revision: Mapping[str, Any]) -> dict[str, Any] | None:
    path = _approval_path(root, revision["decision_id"])
    if not path.exists():
        return None
    record = _load_json(path)
    validate_human_approval(record, decision_revision=revision)
    return record


def _load_current_projection(
    root: str | Path,
    revision: Mapping[str, Any],
) -> dict[str, Any] | None:
    path = _current_path(root, revision["decision_series_id"])
    if not path.exists():
        return None
    record = _load_json(path)
    validate_current_projection(record)
    return record


def _load_trigger_refs(
    root: str | Path,
    *,
    decision_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    root_path = Path(root)
    trigger_refs: list[dict[str, Any]] = []
    monitoring_refs: list[dict[str, Any]] = []
    validation_refs: list[dict[str, Any]] = []

    for path in sorted(root_path.glob("*.trigger.json")):
        trigger = _load_json(path)
        if not trigger or trigger.get("decision_id") != decision_id:
            continue
        validate_trigger_contract(trigger)
        if trigger["decision_id"] != decision_id:
            raise ValueError("trigger contract decision binding mismatch")

        trigger_refs.append(
            {
                "trigger_id": trigger["trigger_id"],
                "trigger_hash": trigger["trigger_hash"],
                "role": trigger["role"],
                "metric_id": trigger["metric_id"],
                "enabled": trigger["enabled"],
                "revision": trigger["revision"],
                "decision_revision_hash": trigger["decision_revision_hash"],
            }
        )

        monitoring_path = _monitoring_state_path(root, trigger["trigger_id"])
        if monitoring_path.exists():
            state = _load_json(monitoring_path)
            validate_monitoring_state(state, trigger_contract=trigger)
            if state["decision_id"] != decision_id or state["revision"] != trigger["revision"]:
                raise ValueError("monitoring state decision binding mismatch")
            monitoring_refs.append(
                {
                    "monitor_id": state["monitor_id"],
                    "trigger_id": state["trigger_id"],
                    "state_hash": state["state_hash"],
                    "lifecycle_status": state["lifecycle_status"],
                    "evaluation_status": state["evaluation_status"],
                    "due_state": state["due_state"],
                    "last_event_id": state["last_event_id"],
                    "next_due_at": state["next_due_at"],
                }
            )

        candidate_validations: list[dict[str, Any]] = []
        for validation_path in sorted(root_path.glob("*.validation.json")):
            record = _load_json(validation_path)
            if not record or record.get("trigger_id") != trigger["trigger_id"]:
                continue
            validate_validation_record(record)
            if (record["decision_id"] != decision_id or
                record["revision"] != trigger["revision"] or
                record["trigger_id"] != trigger["trigger_id"] or
                record["trigger_hash"] != trigger["trigger_hash"]):
                raise ValueError("validation record decision/trigger binding mismatch")
            candidate_validations.append(
                {
                    "validation_id": record["validation_id"],
                    "validation_status": record["validation_status"],
                    "validation_cutoff_at": record["validation_cutoff_at"],
                    "validation_hash": record["validation_hash"],
                    "event_count": record["event_count"],
                }
            )
        if candidate_validations:
            candidate_validations.sort(
                key=lambda item: (item["validation_cutoff_at"], item["validation_id"])
            )
            validation_refs.append(candidate_validations[-1])

    trigger_refs.sort(key=lambda item: item["trigger_id"])
    monitoring_refs.sort(key=lambda item: item["trigger_id"])
    validation_refs.sort(key=lambda item: item["validation_id"])
    return trigger_refs, monitoring_refs, validation_refs


def build_machine_publication(
    *,
    root: str | Path,
    decision_id: str,
    published_at: str,
) -> dict[str, Any]:
    published_at = _timestamp(published_at, "published_at")
    revision = _load_revision(root, decision_id)
    verify_revision_write_authorization(root, revision)
    snapshot = _load_bound_snapshot(root, revision)
    approval = _load_approval(root, revision)
    current_projection = _load_current_projection(root, revision)
    trigger_refs, monitoring_refs, validation_refs = _load_trigger_refs(
        root,
        decision_id=decision_id,
    )

    source_decision = snapshot["decision"]
    if not isinstance(source_decision, Mapping):
        raise ValueError("snapshot decision must be an object")
    nested_decision = source_decision.get("decision")
    if isinstance(nested_decision, Mapping):
        ai_decision = nested_decision
    elif "action" in source_decision:
        ai_decision = source_decision
    else:
        raise ValueError("snapshot decision must expose action or nested decision")

    human_approval: dict[str, Any]
    if approval is None:
        human_approval = {
            "approval_status": "PENDING",
            "approved": None,
            "decision_id": decision_id,
            "revision": revision["revision"],
            "revision_hash": revision["revision_hash"],
            "snapshot_hash": revision["snapshot_hash"],
            "approval_hash": None,
        }
    else:
        human_approval = {
            "approval_status": approval["approval_status"],
            "approved": approval["approved"],
            "decision_id": approval["decision_id"],
            "revision": approval["revision"],
            "revision_hash": approval["revision_hash"],
            "snapshot_hash": approval["snapshot_hash"],
            "approval_hash": approval["approval_hash"],
            "note": approval["note"],
        }

    if current_projection is None:
        currentness = "NO_CURRENT_PROJECTION"
    elif current_projection.get("current_decision_id") == decision_id:
        currentness = "CURRENT"
    elif current_projection.get("current_revision", 0) > revision["revision"]:
        currentness = "SUPERSEDED"
    else:
        currentness = "NOT_CURRENT"

    core = {
        "publication_version": PUBLICATION_VERSION,
        "published_at": published_at,
        "decision_ref": {
            "decision_id": revision["decision_id"],
            "decision_series_id": revision["decision_series_id"],
            "revision": revision["revision"],
            "run_id": revision["run_id"],
            "case_id": revision["case_id"],
            "as_of_date": revision["as_of_date"],
            "cutoff_date": revision["cutoff_date"],
            "snapshot_hash": revision["snapshot_hash"],
            "revision_hash": revision["revision_hash"],
            "engine_version": revision["engine_version"],
            "contract_version": revision["contract_version"],
        },
        "case": {
            "case_id": snapshot["input"].get("case_id"),
            "market": snapshot["input"].get("market"),
            "symbol": snapshot["input"].get("symbol"),
            "company": snapshot["input"].get("company"),
            "as_of_date": snapshot["input"].get("as_of_date", revision["as_of_date"]),
            "cutoff_date": snapshot["input"].get("cutoff_date", revision["cutoff_date"]),
        },
        "ai_decision": deepcopy(dict(ai_decision)),
        "decision_payload": deepcopy(dict(source_decision)),
        "human_approval": human_approval,
        "current_projection": {
            "status": currentness,
            "current_decision_id": (
                current_projection.get("current_decision_id")
                if current_projection is not None
                else None
            ),
            "current_revision": (
                current_projection.get("current_revision")
                if current_projection is not None
                else None
            ),
            "projection_hash": (
                current_projection.get("projection_hash")
                if current_projection is not None
                else None
            ),
        },
        "lifecycle_refs": {
            "trigger_contracts": trigger_refs,
            "monitoring_states": monitoring_refs,
            "validation_records": validation_refs,
        },
        "integrity": {
            "snapshot_hash": revision["snapshot_hash"],
            "revision_hash": revision["revision_hash"],
            "approval_hash": human_approval["approval_hash"],
            "trigger_hashes": [item["trigger_hash"] for item in trigger_refs],
            "monitoring_state_hashes": [item["state_hash"] for item in monitoring_refs],
            "validation_hashes": [item["validation_hash"] for item in validation_refs],
        },
    }
    publication_hash = sha256_obj(core)
    return {
        **core,
        "publication_id": f"{decision_id}-pub-{publication_hash[:16]}",
        "publication_hash": publication_hash,
    }


def validate_machine_publication(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("machine_publication must be an object")
    required = {
        "publication_version",
        "published_at",
        "decision_ref",
        "case",
        "ai_decision",
        "decision_payload",
        "human_approval",
        "current_projection",
        "lifecycle_refs",
        "integrity",
        "publication_id",
        "publication_hash",
    }
    if set(record) != required:
        raise ValueError("machine_publication fields are invalid")
    if record["publication_version"] != PUBLICATION_VERSION:
        raise ValueError("machine_publication version mismatch")
    _timestamp(record["published_at"], "published_at")

    decision_ref = record["decision_ref"]
    if not isinstance(decision_ref, Mapping):
        raise ValueError("machine_publication decision_ref invalid")
    ref_required = {
        "decision_id",
        "decision_series_id",
        "revision",
        "run_id",
        "case_id",
        "as_of_date",
        "cutoff_date",
        "snapshot_hash",
        "revision_hash",
        "engine_version",
        "contract_version",
    }
    if set(decision_ref) != ref_required:
        raise ValueError("machine_publication decision_ref fields are invalid")
    for field in ("snapshot_hash", "revision_hash"):
        value = decision_ref[field]
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"machine_publication {field} invalid")
    if not isinstance(decision_ref["revision"], int) or decision_ref["revision"] < 1:
        raise ValueError("machine_publication revision invalid")

    for field in ("case", "ai_decision", "decision_payload", "human_approval", "current_projection", "lifecycle_refs", "integrity"):
        if not isinstance(record[field], Mapping):
            raise ValueError(f"machine_publication {field} must be an object")

    approval = record["human_approval"]
    if approval["approval_status"] not in {"PENDING", "HUMAN_APPROVED", "HUMAN_REJECTED"}:
        raise ValueError("machine_publication approval status invalid")
    if approval["approval_status"] == "PENDING":
        if approval["approved"] is not None or approval["approval_hash"] is not None:
            raise ValueError("pending publication approval must be null")
    else:
        if not isinstance(approval["approved"], bool) or len(str(approval["approval_hash"])) != 64:
            raise ValueError("materialized publication approval is invalid")
        if approval["decision_id"] != decision_ref["decision_id"]:
            raise ValueError("publication approval decision binding mismatch")
        if approval["revision"] != decision_ref["revision"]:
            raise ValueError("publication approval revision binding mismatch")
        if approval["snapshot_hash"] != decision_ref["snapshot_hash"]:
            raise ValueError("publication approval snapshot binding mismatch")

    lifecycle = record["lifecycle_refs"]
    for key in ("trigger_contracts", "monitoring_states", "validation_records"):
        if key not in lifecycle:
            raise ValueError(f"machine_publication lifecycle list missing: {key}")
        if not isinstance(lifecycle[key], list):
            raise ValueError(f"machine_publication lifecycle list invalid: {key}")

    integrity = record["integrity"]
    for key in ("trigger_hashes", "monitoring_state_hashes", "validation_hashes"):
        if not isinstance(integrity[key], list):
            raise ValueError(f"machine_publication integrity list invalid: {key}")
        if not all(isinstance(value, str) and len(value) == 64 for value in integrity[key]):
            raise ValueError(f"machine_publication integrity hashes invalid: {key}")

    expected_trigger_hashes = [item.get("trigger_hash") for item in lifecycle["trigger_contracts"]]
    expected_monitor_hashes = [item.get("state_hash") for item in lifecycle["monitoring_states"]]
    expected_validation_hashes = [item.get("validation_hash") for item in lifecycle["validation_records"]]
    if integrity["trigger_hashes"] != expected_trigger_hashes:
        raise ValueError("machine_publication trigger integrity list mismatch")
    if integrity["monitoring_state_hashes"] != expected_monitor_hashes:
        raise ValueError("machine_publication monitoring integrity list mismatch")
    if integrity["validation_hashes"] != expected_validation_hashes:
        raise ValueError("machine_publication validation integrity list mismatch")

    decision_ref = record["decision_ref"]
    approval = record["human_approval"]
    if approval["decision_id"] != decision_ref["decision_id"] or approval["revision"] != decision_ref["revision"]:
        raise ValueError("machine_publication approval decision reference mismatch")
    if approval["revision_hash"] != decision_ref["revision_hash"] or approval["snapshot_hash"] != decision_ref["snapshot_hash"]:
        raise ValueError("machine_publication approval source hash mismatch")

    current = record["current_projection"]
    if current["status"] == "CURRENT" and current["current_decision_id"] != decision_ref["decision_id"]:
        raise ValueError("machine_publication current projection mismatch")

    core = {k: record[k] for k in required if k not in {"publication_id", "publication_hash"}}
    expected_hash = sha256_obj(core)
    if record["publication_hash"] != expected_hash:
        raise ValueError("machine_publication hash mismatch")
    expected_id = f'{decision_ref["decision_id"]}-pub-{expected_hash[:16]}'
    if record["publication_id"] != expected_id:
        raise ValueError("machine_publication id mismatch")


def publication_path(root: str | Path, publication_hash: str) -> Path:
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{publication_hash}.publication.json"


def write_machine_publication(
    root: str | Path,
    *,
    decision_id: str,
    published_at: str,
) -> Path:
    record = build_machine_publication(
        root=root,
        decision_id=decision_id,
        published_at=published_at,
    )
    validate_machine_publication(record)
    path = publication_path(root, record["publication_hash"])
    if path.exists():
        existing = _load_json(path)
        validate_machine_publication(existing)
        if canonical_json(existing) != canonical_json(record):
            raise ValueError("machine publication hash collision or attempted overwrite")
        return path
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


__all__ = [
    "PUBLICATION_VERSION",
    "build_machine_publication",
    "validate_machine_publication",
    "publication_path",
    "write_machine_publication",
]
