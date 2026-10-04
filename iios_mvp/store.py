from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import canonical_json, sha256_obj


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
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
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
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)
    return path


def decision_series_id(market: str, symbol: str) -> str:
    return f"{market.upper()}-{symbol.upper()}"


def load_series(root: str | Path, series_id: str) -> dict[str, Any]:
    return _load_json(store_root(root) / f"{series_id}.series.json")


def create_or_load_series(root: str | Path, market: str, symbol: str, company: str, created_at: str) -> dict[str, Any]:
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
    return _load_json(_atomic_create(store_root(root) / f"{sid}.series.json", payload))


def next_revision(root: str | Path, series_id: str) -> int:
    index = _load_json(store_root(root) / f"{series_id}.index.json")
    return int(index.get("next_revision", 1))


def write_decision_revision(
    root: str | Path,
    series_id: str,
    revision: int,
    snapshot: dict[str, Any],
    run_id: str,
    trigger_event_id: str | None = None,
) -> Path:
    decision_id = f"{series_id}-r{revision:03d}"
    payload = {
        "decision_schema_version": "IIOS-DECISION-1.0",
        "decision_id": decision_id,
        "decision_series_id": series_id,
        "revision": revision,
        "run_id": run_id,
        "trigger_event_id": trigger_event_id,
        "as_of_date": snapshot["input"]["cutoff_date"],
        "cutoff_date": snapshot["input"]["cutoff_date"],
        "snapshot_hash": snapshot["snapshot_hash"],
        "ai_decision": snapshot["decision"]["decision"],
        "decision_status": "AI_PROPOSED",
        "engine_version": snapshot["engine_version"],
    }
    return _atomic_create(store_root(root) / f"{decision_id}.decision.json", payload)


def write_human_approval(
    root: str | Path,
    snapshot: dict[str, Any],
    approved: bool,
    note: str,
    decision_id: str | None = None,
) -> Path:
    payload = {
        "approval_schema": "IIOS-MVP-HUMAN-APPROVAL-0.1.1",
        "snapshot_hash": snapshot["snapshot_hash"],
        "decision_id": decision_id,
        "approved": bool(approved),
        "note": note,
    }
    payload["approval_hash"] = sha256_obj(payload)
    path = store_root(root) / f"{snapshot['snapshot_hash']}.human-approval.json"
    return _atomic_create(path, payload)


def approve_revision(root: str | Path, decision_id: str, snapshot: dict[str, Any], approved: bool, note: str) -> dict[str, Any]:
    if not approved:
        write_human_approval(root, snapshot, False, note, decision_id)
        return {"decision_id": decision_id, "status": "HUMAN_REJECTED", "current": False}
    write_human_approval(root, snapshot, True, note, decision_id)
    path = store_root(root) / f"{decision_id}.decision.json"
    decision = _load_json(path)
    if not decision:
        raise ValueError("decision revision not found")
    if decision.get("snapshot_hash") != snapshot.get("snapshot_hash"):
        raise ValueError("decision revision and snapshot are not bound to the same snapshot")
    _atomic_create(store_root(root) / f"{decision_id}.approved.json", {
        "decision_id": decision_id,
        "approval_hash": _load_json(store_root(root) / f"{snapshot['snapshot_hash']}.human-approval.json")["approval_hash"],
    })
    current_path = store_root(root) / f"{decision['decision_series_id']}.current.json"
    current = _load_json(current_path)
    current["decision_series_id"] = decision["decision_series_id"]
    current["company_id"] = decision["decision_series_id"]
    current["current_approved_decision_id"] = decision_id
    current["current_decision_updated_at"] = snapshot["input"]["cutoff_date"]
    _atomic_create(current_path, current)
    # Keep the revision immutable: publish a separate current projection rather than editing the revision.
    return {"decision_id": decision_id, "status": "HUMAN_APPROVED", "current": True}


def write_trigger_contract(root: str | Path, decision_id: str, contract: dict[str, Any]) -> Path:
    payload = dict(contract)
    payload["decision_id"] = decision_id
    payload.setdefault("trigger_schema_version", "IIOS-TRIGGER-1.0")
    payload.setdefault("enabled", True)
    payload["trigger_hash"] = sha256_obj(payload)
    return _atomic_create(store_root(root) / f"{payload['trigger_id']}.trigger.json", payload)


def write_trigger_event(root: str | Path, event: dict[str, Any]) -> Path:
    payload = dict(event)
    payload.setdefault("trigger_schema_version", "IIOS-TRIGGER-1.0")
    payload["trigger_event_hash"] = sha256_obj(payload)
    return _atomic_create(store_root(root) / f"{payload['trigger_event_id']}.event.json", payload)
