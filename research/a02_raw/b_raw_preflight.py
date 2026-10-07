#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_ORIGINS = [
    "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4",
    "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1",
]
REQUIRED_DOMAINS = [
    "identity", "listing_delisting", "common_equity",
    "st_history", "industry_history", "source_vintages",
]
ALLOWED_KNOWLEDGE_CLASSES = {
    "SOURCE_VINTAGE_VERIFIED",
    "EVENT_PUBLICATION_VERIFIED",
    "VENDOR_PIT_QUERY",
    "DERIVED_FROM_ADMITTED_RAW",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(root: Path) -> dict:
    manifest_path = root / "DELIVERY_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("missing DELIVERY_MANIFEST.json")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def run(root: Path) -> dict:
    findings: list[str] = []
    try:
        manifest = load_manifest(root)
    except Exception as exc:
        return {
            "schema_version": "IIOS-A02-DATA01-B-INDEPENDENT-RAW-PREFLIGHT-0.1",
            "status": "BLOCKED",
            "admission_status": "NOT_ADMISSION",
            "independent_from_collector": True,
            "b_domains": {
                "status": "BLOCKED",
                "missing_domains": REQUIRED_DOMAINS,
            },
            "findings": [str(exc)],
        }

    if manifest.get("schema_version") != "IIOS-A02-DATA-01-DELIVERY-MANIFEST-0.1":
        findings.append("invalid delivery manifest schema_version")
    if manifest.get("universe_id") != "OU-M12-A02-CSI800-NONFIN-PIT-001":
        findings.append("invalid universe_id")
    if manifest.get("required_origins") != REQUIRED_ORIGINS:
        findings.append("required_origins mismatch")
    if manifest.get("required_b_domains") != REQUIRED_DOMAINS:
        findings.append("required_b_domains mismatch")

    rows = manifest.get("b_domain_records", [])
    by_domain = {row.get("domain"): row for row in rows if isinstance(row, dict)}
    missing: list[str] = []
    invalid: list[dict] = []

    for domain in REQUIRED_DOMAINS:
        row = by_domain.get(domain)
        if not row:
            missing.append(domain)
            continue

        raw_paths = row.get("raw_paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            invalid.append({"domain": domain, "reason": "raw_paths_missing"})
            continue

        absent = [
            path for path in raw_paths
            if not isinstance(path, str) or not (root / path).is_file()
        ]
        if absent:
            invalid.append({
                "domain": domain,
                "reason": "raw_file_missing",
                "paths": absent,
            })

        if row.get("origin_periods") != REQUIRED_ORIGINS:
            invalid.append({"domain": domain, "reason": "origin_coverage_mismatch"})

        for key in (
            "source_ref",
            "license_redistribution_status",
            "known_at_basis",
            "knowledge_evidence_class",
        ):
            if not row.get(key):
                invalid.append({"domain": domain, "reason": f"missing_{key}"})

        if row.get("knowledge_evidence_class") not in ALLOWED_KNOWLEDGE_CLASSES:
            invalid.append({
                "domain": domain,
                "reason": "knowledge_evidence_not_historical_capable",
            })

        if (
            row.get("known_at_basis") == "retrieved_at"
            or row.get("known_at_basis") == row.get("retrieved_at")
        ):
            invalid.append({
                "domain": domain,
                "reason": "retrieved_at_used_as_known_at",
            })

        if row.get("exact_bytes") is not True:
            invalid.append({"domain": domain, "reason": "exact_bytes_not_true"})

        declared_hashes = row.get("raw_sha256_by_path")
        if not isinstance(declared_hashes, dict):
            invalid.append({
                "domain": domain,
                "reason": "raw_sha256_by_path_missing",
            })
            continue

        for raw_path in raw_paths:
            path = root / raw_path
            if not path.is_file():
                continue
            actual = sha256_file(path)
            if str(declared_hashes.get(raw_path, "")).lower() != actual:
                invalid.append({
                    "domain": domain,
                    "reason": "raw_sha256_mismatch",
                    "path": raw_path,
                })

    status = (
        "PASS_RAW_B_COMPLETE"
        if not missing and not invalid and not findings
        else "BLOCKED"
    )
    return {
        "schema_version": "IIOS-A02-DATA01-B-INDEPENDENT-RAW-PREFLIGHT-0.1",
        "status": status,
        "admission_status": "NOT_ADMISSION",
        "independent_from_collector": True,
        "required_origins": REQUIRED_ORIGINS,
        "required_domains": REQUIRED_DOMAINS,
        "b_domains": {
            "status": status,
            "missing_domains": missing,
            "invalid": invalid,
        },
        "findings": findings,
        "rules": {
            "exact_bytes_required": True,
            "retrieved_at_as_known_at_forbidden": True,
            "current_snapshot_as_historical_forbidden": True,
            "checksum_without_bytes_forbidden": True,
            "secondary_source_as_normative_without_role_basis_forbidden": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = run(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and result["status"] != "PASS_RAW_B_COMPLETE":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
