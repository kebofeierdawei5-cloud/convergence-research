from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from driver_series import DriverSeriesError, load_ndjson, validate_records

ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_dataset(dataset_path: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path or (ROOT / "dataset_manifest.json")
    manifest = load_json(manifest_path)
    records = load_ndjson(dataset_path) if dataset_path.exists() else []
    findings = validate_records(records)

    record_ids = [r.get("record_id") for r in records]
    if len(record_ids) != len(set(record_ids)):
        findings.append({"record_id": None, "code": "DATASET-001", "message": "record_id must be unique"})

    expected_security = manifest["security_id"]
    expected_drivers = set(manifest["drivers"])
    unexpected = [r.get("record_id") for r in records if r.get("security_id") != expected_security or r.get("driver_id") not in expected_drivers]
    if unexpected:
        findings.append({"record_id": ",".join(map(str, unexpected)), "code": "DATASET-002", "message": "record falls outside manifest security/driver scope"})

    if manifest["coverage_target"]["expected_quarters"] != 22:
        findings.append({"record_id": None, "code": "DATASET-003", "message": "current CATL target must remain 22 quarters"})

    if not manifest["data_status"]["exact_source_snapshot_present"]:
        status = "BLOCKED_DATA_INGRESS"
        block_reason = "Exact M1.1 historical source snapshot is not present; no numeric CATL values may be fabricated or inferred as a substitute."
    elif findings:
        status = "FAIL"
        block_reason = None
    else:
        status = "PASS"
        block_reason = None

    return {
        "schema_version": "IIOS-FM01-ADMISSION-RESULT-0.1",
        "status": status,
        "manifest_id": manifest["manifest_id"],
        "dataset_path": str(dataset_path),
        "record_count": len(records),
        "validation_findings": findings,
        "data_gate": {
            "exact_source_snapshot_present": manifest["data_status"]["exact_source_snapshot_present"],
            "coverage_target": manifest["coverage_target"],
            "block_reason": block_reason,
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate an IIOS FM-01 DriverSeries dataset")
    parser.add_argument("dataset")
    parser.add_argument("--manifest", default=str(ROOT / "dataset_manifest.json"))
    args = parser.parse_args()
    result = validate_dataset(Path(args.dataset), Path(args.manifest))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"PASS", "BLOCKED_DATA_INGRESS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
