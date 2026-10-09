from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

# Direct script execution sets sys.path[0] to tools/. Add the repository root
# explicitly so the canonical research.b2 package is found on GitHub runners.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from research.b2.company_evidence import (
    REQUIRED_COMPANY_FIELD_GROUPS,
    build_company_evidence_manifest,
)
from tools.verify_company_evidence_intake import verify_intake

PREFLIGHT_SCHEMA = "IIOS-ROUTE-A-B2-PREFLIGHT-0.1"
B2_MANIFEST_FILENAME = "B2_COMPANY_EVIDENCE_MANIFEST.json"
REPORT_FILENAME = "ROUTE_A_B2_PREFLIGHT.json"


class RouteAB2PreflightError(ValueError):
    """The preflight could not safely bind the raw intake receipt to B2."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteAB2PreflightError("PREFLIGHT_INPUT_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise RouteAB2PreflightError("PREFLIGHT_INPUT_JSON_MUST_BE_OBJECT")
    return value


def _b2_cutoff_end_of_day(value: Any) -> str:
    """Convert a date-only Route A cutoff to the normative +08:00 end of day."""
    if not isinstance(value, str) or not value.strip():
        raise RouteAB2PreflightError("CASE_CUTOFF_REQUIRED")
    raw = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            date.fromisoformat(raw)
        except ValueError as exc:
            raise RouteAB2PreflightError("CASE_CUTOFF_INVALID") from exc
        return f"{raw}T23:59:59+08:00"
    # An already-qualified B2 timestamp must remain explicit and timezone-aware.
    try:
        from datetime import datetime
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RouteAB2PreflightError("CASE_CUTOFF_INVALID") from exc
    if parsed.tzinfo is None:
        raise RouteAB2PreflightError("CASE_CUTOFF_TIMEZONE_REQUIRED")
    return parsed.isoformat()


def _source_evidence_record(
    *,
    case_id: str,
    source_spec: Mapping[str, Any],
    receipt_row: Mapping[str, Any],
) -> dict[str, Any]:
    """Create an artifact-level UNKNOWN record; never turn capture into fact admission."""
    source_id = str(receipt_row.get("source_id") or "").strip()
    digest = receipt_row.get("sha256")
    raw_path = receipt_row.get("raw_artifact_path")
    retrieved_at = receipt_row.get("retrieved_at")
    source_ref = str(receipt_row.get("source_ref") or "").strip()
    source_url = receipt_row.get("source_url")
    field_group = str(receipt_row.get("field_group") or "").strip()
    if (
        not source_id
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or not isinstance(raw_path, str)
        or not raw_path.startswith("raw/")
        or not isinstance(retrieved_at, str)
        or not retrieved_at.strip()
        or not source_ref
        or not isinstance(field_group, str)
    ):
        raise RouteAB2PreflightError("CAPTURED_SOURCE_METADATA_INCOMPLETE")
    if field_group not in REQUIRED_COMPANY_FIELD_GROUPS:
        raise RouteAB2PreflightError("CAPTURED_SOURCE_FIELD_GROUP_INVALID")

    declared_known_at = source_spec.get("known_at")
    declared_basis = source_spec.get("known_at_basis")
    declared_license = source_spec.get("license_status")
    declared_class = source_spec.get("source_class")
    notes = [
        "ROUTE_A_CAPTURE_ONLY_NOT_FACT_EXTRACTION",
        "SOURCE_ORIGIN_NOT_INDEPENDENTLY_VERIFIED",
        "KNOWN_AT_NOT_ADMITTED_BY_ROUTE_A_PREFLIGHT",
        f"DECLARED_SOURCE_CLASS={declared_class or 'UNKNOWN'}",
        f"DECLARED_LICENSE_STATUS={declared_license or 'UNKNOWN'}",
    ]
    if declared_known_at not in (None, ""):
        notes.append(f"DECLARED_KNOWN_AT_NOT_ADMITTED={declared_known_at}")
    else:
        notes.append("DECLARED_KNOWN_AT=UNKNOWN")
    if declared_basis not in (None, ""):
        notes.append("DECLARED_KNOWN_AT_BASIS_NOT_VERIFIED=" + str(declared_basis)[:1000])
    else:
        notes.append("DECLARED_KNOWN_AT_BASIS=UNKNOWN")

    return {
        "evidence_id": "ROUTEA-SOURCE-" + source_id,
        "subject_id": case_id,
        "field_id": field_group + ".source_artifact",
        "claim_type": "SOURCE_ARTIFACT_CAPTURE_RECORD",
        "value": {
            "source_id": source_id,
            "capture_status": "SUCCESS",
            "size_bytes": receipt_row.get("size_bytes"),
        },
        "observation_date": None,
        "period": None,
        "published_at": None,
        "known_at": None,
        "retrieved_at": retrieved_at,
        "effective_from": None,
        "effective_to": None,
        "source_ref": source_ref,
        "source_version": None,
        "source_locator": source_url,
        "artifact_id": f"ROUTE-A-RAW:{source_id}:{digest[:16]}",
        "content_sha256": digest,
        "capture_sha256": digest,
        "exact_bytes": True,
        "provenance_class": "UNKNOWN",
        "status": "UNKNOWN",
        "transformation": {
            "type": "DIRECT",
            "code_ref": None,
            "code_sha256": None,
            "formula_id": None,
        },
        "parents": [],
        "quality_notes": notes,
        "license_status": "UNKNOWN",
    }


def run_route_a_b2_preflight(
    root: str | Path,
    *,
    company: str | None = None,
) -> dict[str, Any]:
    """Verify Route A bytes, then test them against existing B2 without admission."""
    root_path = Path(root).resolve()
    receipt_path = root_path / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json"
    manifest_path = root_path / "intake_manifest.json"
    if not receipt_path.is_file() or not manifest_path.is_file():
        raise RouteAB2PreflightError("ROUTE_A_RECEIPT_OR_MANIFEST_MISSING")

    integrity = verify_intake(root_path)
    if integrity.get("status") != "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION":
        raise RouteAB2PreflightError("RAW_BYTE_INTEGRITY_VERIFICATION_NOT_PASS")

    receipt = _read_json(receipt_path)
    intake_manifest = _read_json(manifest_path)
    specs = {
        item.get("source_id"): item
        for item in intake_manifest.get("sources", [])
        if isinstance(item, dict)
    }
    rows = receipt.get("sources")
    if not isinstance(rows, list) or not rows:
        raise RouteAB2PreflightError("ROUTE_A_RECEIPT_SOURCE_SET_INVALID")
    if len(rows) != len(specs):
        raise RouteAB2PreflightError("ROUTE_A_RECEIPT_SOURCE_SET_SIZE_MISMATCH")

    case_id = str(receipt.get("case_id") or "").strip()
    if not case_id or case_id != intake_manifest.get("case_id"):
        raise RouteAB2PreflightError("ROUTE_A_CASE_ID_BINDING_MISMATCH")
    cutoff = _b2_cutoff_end_of_day(intake_manifest.get("cutoff_date"))
    b2_company = (company or "").strip() or f"{receipt.get('market')} {receipt.get('symbol')}"

    evidence_records = []
    raw_artifacts = []
    source_rows = []
    raw_groups = set()
    uncaptured_count = 0

    for row in rows:
        if not isinstance(row, dict):
            raise RouteAB2PreflightError("ROUTE_A_RECEIPT_SOURCE_ROW_INVALID")
        source_id = row.get("source_id")
        spec = specs.get(source_id)
        if spec is None:
            raise RouteAB2PreflightError("ROUTE_A_SOURCE_SPEC_NOT_FOUND")
        capture_status = row.get("capture_status")
        if capture_status == "SUCCESS":
            evidence = _source_evidence_record(
                case_id=case_id,
                source_spec=spec,
                receipt_row=row,
            )
            evidence_records.append(evidence)
            raw_artifacts.append({
                "evidence_id": evidence["evidence_id"],
                "relative_path": row["raw_artifact_path"],
                "expected_size_bytes": row["size_bytes"],
                "expected_sha256": row["sha256"],
            })
            raw_groups.add(str(row["field_group"]))
            b2_evidence_status = "UNKNOWN"
        elif capture_status == "FAILED":
            uncaptured_count += 1
            b2_evidence_status = "NO_RECORD_NO_RAW_BYTES"
        else:
            raise RouteAB2PreflightError("ROUTE_A_CAPTURE_STATUS_INVALID")
        source_rows.append({
            "source_id": source_id,
            "field_group": row.get("field_group"),
            "capture_status": capture_status,
            "raw_artifact_path": row.get("raw_artifact_path"),
            "size_bytes": row.get("size_bytes"),
            "sha256": row.get("sha256"),
            "error_code": row.get("error_code"),
            "b2_evidence_status": b2_evidence_status,
            "declared_known_at": spec.get("known_at") or None,
            "declared_known_at_basis": spec.get("known_at_basis") or None,
            "source_origin_verified": False,
        })

    b2_manifest = None
    b2_validation_errors = []
    if evidence_records:
        b2_manifest = build_company_evidence_manifest(
            case_id=case_id,
            market=receipt["market"],
            symbol=receipt["symbol"],
            company=b2_company,
            cutoff_date=cutoff,
            evidence=evidence_records,
            raw_artifacts=raw_artifacts,
            required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
            raw_root=root_path,
        )
        if b2_manifest.get("status") != "BLOCKED":
            # Capture-only artifact records are intentionally UNKNOWN and must
            # never yield a passing company evidence manifest.
            raise RouteAB2PreflightError("CAPTURE_ONLY_SOURCES_UNEXPECTEDLY_PASSED_B2")
        b2_validation_errors = list(b2_manifest.get("validation_errors", []))
        (root_path / B2_MANIFEST_FILENAME).write_text(
            json.dumps(b2_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        b2_manifest_status = "BLOCKED"
        b2_manifest_sha256 = b2_manifest["audit"]["manifest_sha256"]
        preflight_status = "BLOCKED_NOT_ADMITTED"
    else:
        # No raw bytes means no Evidence Records can safely be constructed.
        b2_manifest_status = "NOT_BUILT_NO_RAW_BYTES"
        b2_manifest_sha256 = None
        b2_validation_errors = ["NO_CAPTURED_RAW_BYTES"]
        preflight_status = "BLOCKED_NO_RAW_BYTES"

    missing_groups = sorted(REQUIRED_COMPANY_FIELD_GROUPS)
    for item in b2_validation_errors:
        if item.startswith("REQUIRED_FIELD_GROUPS_UNCOVERED:"):
            missing_groups = item.split(":", 1)[1].split(",") if item.split(":", 1)[1] else []
            break

    report = {
        "schema_version": PREFLIGHT_SCHEMA,
        "status": preflight_status,
        "case_id": case_id,
        "market": receipt["market"],
        "symbol": receipt["symbol"],
        "cutoff_date": cutoff,
        "intake_receipt_status": receipt.get("status"),
        "raw_integrity_status": integrity["status"],
        "receipt_manifest_sha256": receipt.get("manifest_sha256"),
        "raw_bytes_verified": integrity["raw_bytes_verified"],
        "declared_source_count": len(rows),
        "captured_source_count": len(evidence_records),
        "uncaptured_source_count": uncaptured_count,
        "groups_with_raw_bytes": sorted(raw_groups),
        "admitted_field_groups": [],
        "missing_required_field_groups": missing_groups,
        "b2_manifest_status": b2_manifest_status,
        "b2_manifest_sha256": b2_manifest_sha256,
        "source_origin_verified": False,
        "evidence_admission": False,
        "pit_admission": False,
        "llm_provider_required": False,
        "b2_validation_errors": b2_validation_errors,
        "sources": source_rows,
        "contract": {
            "raw_capture_does_not_equal_fact_admission": True,
            "declared_known_at_is_never_promoted_by_this_preflight": True,
            "only_admitted_pit_qualified_records_cover_required_groups": True,
            "not_an_investment_decision": True,
        },
    }
    (root_path / REPORT_FILENAME).write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Route A raw-byte verification through the existing B2 Evidence/PIT contract; do not admit source facts."
    )
    parser.add_argument("--root", required=True, help="Route A capture output directory")
    parser.add_argument("--company", help="Optional display label; does not affect source or PIT status")
    args = parser.parse_args()
    try:
        report = run_route_a_b2_preflight(args.root, company=args.company)
    except Exception as exc:
        code = str(exc) if isinstance(exc, RouteAB2PreflightError) else type(exc).__name__
        print(json.dumps({
            "status": "ROUTE_A_B2_PREFLIGHT_FAILED_CLOSED",
            "error_code": code,
            "evidence_admission": False,
            "pit_admission": False,
        }, sort_keys=True))
        return 1
    print(json.dumps({
        "status": report["status"],
        "case_id": report["case_id"],
        "raw_integrity_status": report["raw_integrity_status"],
        "captured_source_count": report["captured_source_count"],
        "uncaptured_source_count": report["uncaptured_source_count"],
        "b2_manifest_status": report["b2_manifest_status"],
        "missing_required_field_groups": report["missing_required_field_groups"],
        "evidence_admission": report["evidence_admission"],
        "pit_admission": report["pit_admission"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
