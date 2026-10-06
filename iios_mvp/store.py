from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .decision_lifecycle_production import (
    build_decision_revision,
    build_human_approval,
    project_current_approval,
    validate_current_projection,
    validate_decision_revision,
    validate_human_approval,
)
from .engine import canonical_json, replay, sha256_obj
from .trigger_production import (
    build_trigger_contract,
    build_trigger_event,
    validate_trigger_contract,
    validate_trigger_event,
)
from .monitoring_state import (
    apply_trigger_event,
    build_monitoring_state,
    validate_monitoring_state,
)


def store_root(root: str | Path = "runs") -> Path:
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshot_path(root: str | Path, snapshot_hash: str) -> Path:
    return store_root(root) / f"{snapshot_hash}.json"


def write_snapshot(root: str | Path, snapshot: dict[str, Any]) -> Path:
    path = snapshot_path(root, snapshot["snapshot_hash"])
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if canonical_json(existing) != canonical_json(snapshot):
            raise ValueError("snapshot hash collision or attempted overwrite")
        return path
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def read_snapshot(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or "snapshot_hash" not in value:
        raise ValueError("invalid IIOS snapshot")
    expected = sha256_obj({
        "snapshot_schema": value["snapshot_schema"],
        "engine_version": value["engine_version"],
        "input": value["input"],
        "decision": value["decision"],
    })
    if expected != value["snapshot_hash"]:
        raise ValueError("snapshot integrity check failed")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def _atomic_create(path: Path, payload: dict[str, Any]) -> Path:
    if path.exists():
        existing = _load_json(path)
        if canonical_json(existing) != canonical_json(payload):
            raise ValueError(f"immutable object already exists with different content: {path.name}")
        return path
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)
    return path


def _atomic_replace(path: Path, payload: dict[str, Any]) -> Path:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)
    return path


def decision_series_id(market: str, symbol: str) -> str:
    return f"{market.upper()}-{symbol.upper()}"


def load_series(root: str | Path, series_id: str) -> dict[str, Any]:
    return _load_json(store_root(root) / f"{series_id}.series.json")


def create_or_load_series(
    root: str | Path,
    market: str,
    symbol: str,
    company: str,
    created_at: str,
) -> dict[str, Any]:
    sid = decision_series_id(market, symbol)
    payload = {
        "decision_series_id": sid,
        "company_id": sid,
        "market": market.upper(),
        "symbol": symbol.upper(),
        "company_name": company,
        "created_at": created_at,
        "schema_version": "IIOS-SERIES-1.0",
    }
    series = _load_json(
        _atomic_create(store_root(root) / f"{sid}.series.json", payload)
    )
    index_path = store_root(root) / f"{sid}.index.json"
    if not index_path.exists():
        _atomic_create(index_path, {"next_revision": 1})
    return series


def _index_path(root: str | Path, series_id: str) -> Path:
    return store_root(root) / f"{series_id}.index.json"


def next_revision(root: str | Path, series_id: str) -> int:
    index = _load_json(_index_path(root, series_id))
    value = index.get("next_revision", 1)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("revision index next_revision must be a positive integer")
    return value


def _decision_path(root: str | Path, decision_id: str) -> Path:
    return store_root(root) / f"{decision_id}.decision.json"


def _approval_path(root: str | Path, decision_id: str) -> Path:
    return store_root(root) / f"{decision_id}.approval.json"


def _current_path(root: str | Path, series_id: str) -> Path:
    return store_root(root) / f"{series_id}.current.json"


def _load_revision(root: str | Path, decision_id: str) -> dict[str, Any]:
    record = _load_json(_decision_path(root, decision_id))
    if not record:
        raise ValueError("decision revision not found")
    return record


def write_decision_revision(
    root: str | Path,
    series_id: str,
    revision: int,
    snapshot: dict[str, Any],
    run_id: str,
    trigger_event_id: str | None = None,
) -> Path:
    expected_revision = next_revision(root, series_id)
    payload = build_decision_revision(
        decision_series_id=series_id,
        revision=revision,
        snapshot=snapshot,
        run_id=run_id,
        trigger_event_id=trigger_event_id,
    )
    path = _decision_path(root, payload["decision_id"])

    if path.exists():
        existing = _load_revision(root, payload["decision_id"])
        validate_decision_revision(
            existing,
            case_id=payload["case_id"],
            cutoff_date=payload["cutoff_date"],
        )
        if canonical_json(existing) != canonical_json(payload):
            raise ValueError("immutable decision revision already exists with different content")
    else:
        if revision != expected_revision:
            raise ValueError(
                f"revision {revision} is not the next canonical revision; expected {expected_revision}"
            )
        _atomic_create(path, payload)

    next_value = max(expected_revision, revision + 1)
    _atomic_replace(_index_path(root, series_id), {"next_revision": next_value})
    return path


def write_human_approval(
    root: str | Path,
    snapshot: dict[str, Any],
    approved: bool,
    note: str,
    decision_id: str | None = None,
) -> Path:
    if not decision_id:
        raise ValueError("decision_id is required")
    revision = _load_revision(root, decision_id)
    if revision["snapshot_hash"] != snapshot.get("snapshot_hash"):
        raise ValueError("decision revision and snapshot are not bound to the same snapshot")
    approval = build_human_approval(
        decision_revision=revision,
        approved=approved,
        note=note,
    )
    return _atomic_create(_approval_path(root, decision_id), approval)


def approve_revision(
    root: str | Path,
    decision_id: str,
    snapshot: dict[str, Any],
    approved: bool,
    note: str,
) -> dict[str, Any]:
    revision = _load_revision(root, decision_id)
    if revision["snapshot_hash"] != snapshot.get("snapshot_hash"):
        raise ValueError("decision revision and snapshot are not bound to the same snapshot")
    approval_path = write_human_approval(root, snapshot, approved, note, decision_id)
    approval = _load_json(approval_path)
    validate_human_approval(approval, decision_revision=revision)

    current_path = _current_path(root, revision["decision_series_id"])
    current = _load_json(current_path) if current_path.exists() else None
    projected = project_current_approval(
        previous=current,
        decision_revision=revision,
        approval=approval,
    )

    if projected.get("projection_status") == "CURRENT":
        _atomic_replace(current_path, projected)
        return {
            "decision_id": decision_id,
            "status": "HUMAN_APPROVED",
            "current": True,
            "approval": str(approval_path),
            "current_projection": str(current_path),
        }

    return {
        "decision_id": decision_id,
        "status": "HUMAN_REJECTED" if not approved else "HUMAN_APPROVED",
        "current": bool(
            current and current.get("current_decision_id") == decision_id
        ),
        "approval": str(approval_path),
        "current_projection": str(current_path) if current_path.exists() else None,
    }


def replay_decision_lifecycle(
    root: str | Path,
    decision_id: str,
) -> dict[str, Any]:
    revision = _load_revision(root, decision_id)
    validate_decision_revision(
        revision,
        case_id=revision["case_id"],
        cutoff_date=revision["cutoff_date"],
    )

    snapshot = read_snapshot(
        snapshot_path(root, revision["snapshot_hash"])
    )
    expected_revision = build_decision_revision(
        decision_series_id=revision["decision_series_id"],
        revision=revision["revision"],
        snapshot=snapshot,
        run_id=revision["run_id"],
        trigger_event_id=revision["trigger_event_id"],
    )
    if canonical_json(expected_revision) != canonical_json(revision):
        raise ValueError("decision revision replay mismatch")

    series_prefix = revision["decision_series_id"] + "-r"
    revision_files = sorted(
        store_root(root).glob(f"{series_prefix}*.decision.json"),
        key=lambda p: int(
            p.name.removesuffix(".decision.json").rsplit("-r", 1)[1]
        ),
    )
    if not revision_files:
        raise ValueError("decision revision history is empty")
    records = []
    for path in revision_files:
        record = _load_json(path)
        if record["case_id"] != revision["case_id"]:
            raise ValueError("decision revision history contains a different case_id")
        validate_decision_revision(
            record,
            case_id=record["case_id"],
            cutoff_date=record["cutoff_date"],
        )
        historical_snapshot = read_snapshot(
            snapshot_path(root, record["snapshot_hash"])
        )
        expected_historical_revision = build_decision_revision(
            decision_series_id=record["decision_series_id"],
            revision=record["revision"],
            snapshot=historical_snapshot,
            run_id=record["run_id"],
            trigger_event_id=record["trigger_event_id"],
        )
        if canonical_json(expected_historical_revision) != canonical_json(record):
            raise ValueError(
                f"decision revision replay mismatch: {record['decision_id']}"
            )
        records.append(record)

    numbers = [record["revision"] for record in records]
    if numbers != list(range(1, max(numbers) + 1)):
        raise ValueError("decision revision history is not contiguous")

    current: dict[str, Any] | None = None
    approval_status = "PENDING"
    for record in records:
        approval_path = _approval_path(root, record["decision_id"])
        if not approval_path.exists():
            continue
        approval = _load_json(approval_path)
        validate_human_approval(approval, decision_revision=record)
        if record["decision_id"] == decision_id:
            approval_status = approval["approval_status"]
        projected = project_current_approval(
            previous=current,
            decision_revision=record,
            approval=approval,
        )
        if projected.get("projection_status") == "CURRENT":
            current = projected

    current_exists = _current_path(root, revision["decision_series_id"]).exists()
    persisted_current = (
        _load_json(_current_path(root, revision["decision_series_id"]))
        if current_exists
        else None
    )
    if persisted_current is not None:
        validate_current_projection(persisted_current)
        if current is None or canonical_json(persisted_current) != canonical_json(current):
            raise ValueError("current projection replay mismatch")
    elif current is not None:
        raise ValueError("current projection is missing from persistent store")

    return {
        "replay_status": "PASS",
        "decision_id": decision_id,
        "decision_revision": revision["revision"],
        "approval_status": approval_status,
        "current_decision_id": current["current_decision_id"] if current else None,
        "current_revision": current["current_revision"] if current else None,
        "snapshot_hash": revision["snapshot_hash"],
    }


def _trigger_contract_path(root: str | Path, trigger_id: str) -> Path:
    return store_root(root) / f"{trigger_id}.trigger.json"


def _trigger_event_path(root: str | Path, trigger_event_id: str) -> Path:
    return store_root(root) / f"{trigger_event_id}.event.json"


def _validate_trigger_revision_binding(
    root: str | Path,
    *,
    decision_id: str,
    decision_series_id: str,
    revision: int,
    decision_revision_hash: str,
    case_id: str,
    decision_cutoff_date: str,
) -> None:
    revision_record = _load_revision(root, decision_id)
    validate_decision_revision(
        revision_record,
        case_id=revision_record["case_id"],
        cutoff_date=revision_record["cutoff_date"],
    )
    expected = {
        "decision_id": revision_record["decision_id"],
        "decision_series_id": revision_record["decision_series_id"],
        "revision": revision_record["revision"],
        "decision_revision_hash": revision_record["revision_hash"],
        "case_id": revision_record["case_id"],
        "decision_cutoff_date": revision_record["cutoff_date"],
    }
    actual = {
        "decision_id": decision_id,
        "decision_series_id": decision_series_id,
        "revision": revision,
        "decision_revision_hash": decision_revision_hash,
        "case_id": case_id,
        "decision_cutoff_date": decision_cutoff_date,
    }
    if actual != expected:
        raise ValueError("trigger contract is not bound to the persisted decision revision")


def _load_trigger_contract(root: str | Path, trigger_id: str) -> dict[str, Any]:
    record = _load_json(_trigger_contract_path(root, trigger_id))
    if not record:
        raise ValueError("trigger contract not found")
    validate_trigger_contract(record)
    _validate_trigger_revision_binding(
        root,
        decision_id=record["decision_id"],
        decision_series_id=record["decision_series_id"],
        revision=record["revision"],
        decision_revision_hash=record["decision_revision_hash"],
        case_id=record["case_id"],
        decision_cutoff_date=record["decision_cutoff_date"],
    )
    return record


def write_trigger_contract(root: str | Path, decision_id: str, contract: dict[str, Any]) -> Path:
    payload = dict(contract)
    payload["decision_id"] = decision_id
    payload.pop("contract_version", None)
    payload.pop("trigger_hash", None)
    fields = {
        "trigger_id",
        "decision_id",
        "decision_series_id",
        "revision",
        "decision_revision_hash",
        "case_id",
        "decision_cutoff_date",
        "role",
        "metric_id",
        "operator",
        "target",
        "unit",
        "evidence_ids",
        "enabled",
    }
    if set(payload) != fields:
        raise ValueError("trigger contract input fields are invalid")
    canonical = build_trigger_contract(**payload)
    _validate_trigger_revision_binding(
        root,
        decision_id=canonical["decision_id"],
        decision_series_id=canonical["decision_series_id"],
        revision=canonical["revision"],
        decision_revision_hash=canonical["decision_revision_hash"],
        case_id=canonical["case_id"],
        decision_cutoff_date=canonical["decision_cutoff_date"],
    )
    path = _trigger_contract_path(root, canonical["trigger_id"])
    return _atomic_create(path, canonical)


def write_trigger_event(root: str | Path, event: dict[str, Any]) -> Path:
    payload = dict(event)
    trigger_id = payload.get("trigger_id")
    if not isinstance(trigger_id, str) or not trigger_id.strip():
        raise ValueError("trigger_id is required for trigger event")
    contract = _load_trigger_contract(root, trigger_id)
    payload.pop("trigger_id", None)
    fields = {
        "trigger_event_id",
        "evaluation_cutoff_at",
        "observed_at",
        "known_at",
        "source_id",
        "evidence_id",
        "value",
        "previous_value",
    }
    if set(payload) != fields:
        raise ValueError("trigger event input fields are invalid")
    canonical = build_trigger_event(trigger_contract=contract, **payload)
    path = _trigger_event_path(root, canonical["trigger_event_id"])
    existing = _load_json(path) if path.exists() else None
    if existing is not None:
        validate_trigger_event(existing, trigger_contract=contract)
    return _atomic_create(path, canonical)


def _monitoring_state_path(root: str | Path, trigger_id: str) -> Path:
    return store_root(root) / f"{trigger_id}.monitor.json"


def initialize_monitoring_state(
    root: str | Path,
    trigger_id: str,
    monitor_id: str,
    lifecycle_status: str = "ACTIVE",
    next_due_at: str | None = None,
    evaluation_reference_at: str | None = None,
) -> Path:
    contract = _load_trigger_contract(root, trigger_id)
    state = build_monitoring_state(
        monitor_id=monitor_id,
        trigger_contract=contract,
        lifecycle_status=lifecycle_status,
        next_due_at=next_due_at,
        evaluation_reference_at=evaluation_reference_at,
    )
    return _atomic_create(_monitoring_state_path(root, trigger_id), state)


def apply_monitoring_event(
    root: str | Path,
    trigger_event_id: str,
    next_due_at: str | None = None,
) -> Path:
    event_path = _trigger_event_path(root, trigger_event_id)
    event = _load_json(event_path)
    if not event:
        raise ValueError("trigger event not found")
    trigger_id = event.get("trigger_id")
    if not isinstance(trigger_id, str) or not trigger_id.strip():
        raise ValueError("trigger event trigger_id is required")
    contract = _load_trigger_contract(root, trigger_id)
    state_path = _monitoring_state_path(root, trigger_id)
    previous = _load_json(state_path)
    if not previous:
        raise ValueError("monitoring state not initialized")
    validate_monitoring_state(previous, trigger_contract=contract)
    validate_trigger_event(event, trigger_contract=contract)
    updated = apply_trigger_event(
        previous_state=previous,
        trigger_contract=contract,
        trigger_event=event,
        next_due_at=next_due_at,
    )
    return _atomic_replace(state_path, updated)


def replay_monitoring_state(root: str | Path, trigger_id: str) -> dict[str, Any]:
    contract = _load_trigger_contract(root, trigger_id)
    state_path = _monitoring_state_path(root, trigger_id)
    persisted = _load_json(state_path)
    if not persisted:
        raise ValueError("monitoring state not initialized")
    validate_monitoring_state(persisted, trigger_contract=contract)

    replayed = build_monitoring_state(
        monitor_id=persisted["monitor_id"],
        trigger_contract=contract,
        lifecycle_status=persisted["lifecycle_status"],
        next_due_at=persisted["next_due_at"],
        evaluation_reference_at=persisted["due_reference_at"],
    )
    event_files = []
    for path in store_root(root).glob("*.event.json"):
        record = _load_json(path)
        if record.get("trigger_id") == trigger_id:
            event_files.append(path)
    event_files.sort(
        key=lambda p: (
            _load_json(p)["known_at"],
            _load_json(p)["trigger_event_id"],
        )
    )
    for path in event_files:
        event = _load_json(path)
        validate_trigger_event(event, trigger_contract=contract)
        replayed = apply_trigger_event(
            previous_state=replayed,
            trigger_contract=contract,
            trigger_event=event,
        )
    validate_monitoring_state(replayed, trigger_contract=contract)
    if canonical_json(replayed) != canonical_json(persisted):
        raise ValueError("monitoring state replay mismatch")
    return {
        "replay_status": "PASS",
        "trigger_id": trigger_id,
        "monitor_id": persisted["monitor_id"],
        "last_event_id": persisted["last_event_id"],
        "evaluation_status": persisted["evaluation_status"],
        "last_trigger_state": persisted["last_trigger_state"],
        "due_state": persisted["due_state"],
        "state_hash": persisted["state_hash"],
    }
