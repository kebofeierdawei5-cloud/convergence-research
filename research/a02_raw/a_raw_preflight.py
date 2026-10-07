#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_SIZE = 169984
EXPECTED_SHA256 = "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984"
REQUIRED_STATES = [
    "2023-06", "2023-12", "2024-06", "2024-12",
    "2025-06", "2025-12", "2026-06",
]
SCHEMA = "IIOS-A02-DATA-01-DELIVERY-MANIFEST-0.1"
UNIVERSE = "OU-M12-A02-CSI800-NONFIN-PIT-001"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(root: Path) -> dict[str, Any]:
    p = root / "DELIVERY_MANIFEST.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def terminal_candidates(root: Path) -> list[Path]:
    base = root / "A_CSI800_RAW"
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file() and p.name.lower() == "000906cons.xls")


def verify_terminal(root: Path, findings: list[str]) -> dict[str, Any]:
    candidates = terminal_candidates(root)
    if not candidates:
        findings.append("A terminal 000906cons.xls bytes are absent")
        return {"status": "BLOCKED", "present": False, "candidates": []}
    rows = []
    for p in candidates:
        size = p.stat().st_size
        digest = sha256_file(p)
        rows.append({
            "path": str(p.relative_to(root)),
            "size_bytes": size,
            "sha256": digest,
            "size_match": size == EXPECTED_SIZE,
            "sha256_match": digest == EXPECTED_SHA256,
        })
    exact = [x for x in rows if x["size_match"] and x["sha256_match"]]
    if not exact:
        findings.append("A terminal bytes are present but none match the frozen size/hash target")
        return {"status": "BLOCKED", "present": True, "candidates": rows}
    return {"status": "PASS", "present": True, "match": exact[0], "candidates": rows}


def verify_manifest_and_states(root: Path, manifest: dict[str, Any], findings: list[str]) -> dict[str, Any]:
    identity_ok = (
        manifest.get("schema_version") == SCHEMA
        and manifest.get("universe_id") == UNIVERSE
        and manifest.get("required_membership_states") == REQUIRED_STATES
    )
    if not identity_ok:
        findings.append("delivery manifest identity or required membership states are invalid")
    rows = manifest.get("a_membership_states", [])
    by_state = {str(x.get("state_id")): x for x in rows if isinstance(x, dict)}
    missing, invalid = [], []
    for state in REQUIRED_STATES:
        row = by_state.get(state)
        if not row:
            missing.append(state)
            continue
        raw_path = row.get("raw_path")
        if not isinstance(raw_path, str) or not (root / raw_path).is_file():
            invalid.append({"state": state, "reason": "raw_bytes_missing"})
            continue
        for key in ("source_ref", "publication_basis", "effective_date", "known_at_basis"):
            if not row.get(key):
                invalid.append({"state": state, "reason": f"missing_{key}"})
        declared = row.get("raw_sha256")
        if not declared:
            invalid.append({"state": state, "reason": "missing_raw_sha256"})
        elif sha256_file(root / raw_path) != str(declared).lower():
            invalid.append({"state": state, "reason": "raw_sha256_mismatch"})
    if missing:
        findings.append("historical membership states missing: " + ",".join(missing))
    if invalid:
        findings.append("historical membership raw/provenance entries are incomplete")
    return {
        "identity_status": "PASS" if identity_ok else "BLOCKED",
        "states_status": "PASS" if not missing and not invalid else "BLOCKED",
        "missing_states": missing,
        "invalid": invalid,
    }


def run(root: Path, strict: bool) -> int:
    findings: list[str] = []
    try:
        manifest = load_manifest(root)
    except Exception as exc:
        manifest = {}
        findings.append(str(exc))
    terminal = verify_terminal(root, findings)
    states = verify_manifest_and_states(root, manifest, findings) if manifest else {
        "identity_status": "BLOCKED",
        "states_status": "BLOCKED",
        "missing_states": REQUIRED_STATES,
        "invalid": [],
    }
    raw_complete = (
        terminal["status"] == "PASS"
        and states["identity_status"] == "PASS"
        and states["states_status"] == "PASS"
    )
    result = {
        "schema_version": "IIOS-A02-DATA01-A-INDEPENDENT-RAW-PREFLIGHT-0.1",
        "status": "PASS_RAW_COMPLETE" if raw_complete else "BLOCKED",
        "admission_status": "NOT_ADMISSION",
        "independent_from_collector": True,
        "terminal_a": terminal,
        "historical_membership_states": states,
        "findings": findings,
        "rules": {
            "checksum_without_bytes": "FORBIDDEN",
            "current_to_historical_substitution": "FORBIDDEN",
            "retrieved_at_to_known_at_substitution": "FORBIDDEN",
            "collector_receipt_as_proof": "FORBIDDEN",
        },
    }
    out = root / "A02_DATA01_A_INDEPENDENT_RAW_PREFLIGHT.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 4 if strict and not raw_complete else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    return run(args.root.resolve(), args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
