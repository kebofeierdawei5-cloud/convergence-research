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


def write_human_approval(root: str | Path, snapshot: dict[str, Any], approved: bool, note: str) -> Path:
    payload = {
        "approval_schema": "IIOS-MVP-HUMAN-APPROVAL-0.1",
        "snapshot_hash": snapshot["snapshot_hash"],
        "approved": bool(approved),
        "note": note,
    }
    payload["approval_hash"] = sha256_obj(payload)
    path = store_root(root) / f"{snapshot['snapshot_hash']}.human-approval.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if canonical_json(existing) != canonical_json(payload):
            raise ValueError("human approval already exists with different content")
        return path
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
