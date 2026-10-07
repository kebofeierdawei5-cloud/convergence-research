#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_000906_SHA256 = "f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984"
EXPECTED_000906_SIZE = 169984

REQUIRED_STATES = [
    "2023-06", "2023-12", "2024-06", "2024-12",
    "2025-06", "2025-12", "2026-06",
]
REQUIRED_B_DOMAINS = [
    "identity", "listing_delisting", "common_equity",
    "st_history", "industry_history", "source_vintages",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "DELIVERY_MANIFEST.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_terminal_000906(root: Path) -> list[Path]:
    return sorted(
        p for p in (root / "A_CSI800_RAW").rglob("*")
        if p.is_file() and p.name.lower() == "000906cons.xls"
    )


def verify_terminal_a(root: Path, findings: list[str]) -> dict[str, Any]:
    candidates = find_terminal_000906(root)
    if not candidates:
        findings.append("A terminal 000906cons.xls is absent")
        return {"status": "BLOCKED", "present": False}
    matches = []
    for p in candidates:
        size = p.stat().st_size
        digest = sha256_file(p)
        matches.append({
            "path": str(p.relative_to(root)),
            "size_bytes": size,
            "sha256": digest,
            "size_match": size == EXPECTED_000906_SIZE,
            "sha256_match": digest == EXPECTED_000906_SHA256,
        })
    passed = [x for x in matches if x["size_match"] and x["sha256_match"]]
    if not passed:
        findings.append("A terminal 000906cons.xls exists but does not match the frozen validation target")
        return {"status": "BLOCKED", "present": True, "candidates": matches}
    return {"status": "PASS", "present": True, "match": passed[0], "candidates": matches}


def verify_states(root: Path, manifest: dict[str, Any], findings: list[str]) -> dict[str, Any]:
    rows = manifest.get("a_membership_states", [])
    by_state = {str(x.get("state_id")): x for x in rows if isinstance(x, dict)}
    missing = []
    invalid = []
    for state in REQUIRED_STATES:
        row = by_state.get(state)
        if not row:
            missing.append(state)
            continue
        raw_path = row.get("raw_path")
        if not raw_path or not (root / raw_path).is_file():
            invalid.append({"state": state, "reason": "raw_path_missing"})
        for k in ("source_ref", "publication_basis", "effective_date"):
            if not row.get(k):
                invalid.append({"state": state, "reason": f"missing_{k}"})
    if missing:
        findings.append("A historical membership states missing: " + ",".join(missing))
    if invalid:
        findings.append("A membership state metadata/raw references incomplete")
    status = "PASS" if not missing and not invalid else "BLOCKED"
    return {"status": status, "missing_states": missing, "invalid": invalid}


def verify_b(root: Path, manifest: dict[str, Any], findings: list[str]) -> dict[str, Any]:
    rows = manifest.get("b_domain_records", [])
    by_domain = {str(x.get("domain")): x for x in rows if isinstance(x, dict)}
    missing = []
    invalid = []
    for domain in REQUIRED_B_DOMAINS:
        row = by_domain.get(domain)
        if not row:
            missing.append(domain)
            continue
        raw_paths = row.get("raw_paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            invalid.append({"domain": domain, "reason": "raw_paths_missing"})
            continue
        absent = [p for p in raw_paths if not isinstance(p, str) or not (root / p).is_file()]
        if absent:
            invalid.append({"domain": domain, "reason": "raw_file_missing", "paths": absent})
        for k in ("source_ref", "known_at_basis", "license_redistribution_status"):
            if not row.get(k):
                invalid.append({"domain": domain, "reason": f"missing_{k}"})
    if missing:
        findings.append("B domains missing: " + ",".join(missing))
    if invalid:
        findings.append("B domain metadata/raw references incomplete")
    status = "PASS" if not missing and not invalid else "BLOCKED"
    return {"status": status, "missing_domains": missing, "invalid": invalid}


def run(root: Path, strict: bool) -> int:
    findings: list[str] = []
    try:
        manifest = load_manifest(root)
    except Exception as exc:
        findings.append(str(exc))
        manifest = {}

    a = verify_terminal_a(root, findings)
    states = verify_states(root, manifest, findings)
    b = verify_b(root, manifest, findings)

    raw_complete = a["status"] == "PASS" and states["status"] == "PASS" and b["status"] == "PASS"
    result = {
        "schema_version": "IIOS-A02-DATA-01-INDEPENDENT-RAW-PREFLIGHT-0.1",
        "status": "PASS_RAW_COMPLETE" if raw_complete else "BLOCKED",
        "admission_status": "NOT_ADMISSION",
        "terminal_a": a,
        "a_membership_states": states,
        "b_domains": b,
        "findings": findings,
        "rules": {
            "current_to_historical_substitution": "FORBIDDEN",
            "retrieved_at_to_known_at_substitution": "FORBIDDEN",
            "checksum_without_bytes": "FORBIDDEN",
            "self_authored_receipt_as_admission": "FORBIDDEN",
        },
    }
    out = root / "A02_DATA01_INDEPENDENT_RAW_PREFLIGHT.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if strict and not raw_complete:
        return 4
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    return run(args.root.resolve(), args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
