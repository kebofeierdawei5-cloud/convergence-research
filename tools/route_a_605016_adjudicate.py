from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from research.b2.company_evidence import (
    REQUIRED_COMPANY_FIELD_GROUPS,
    build_company_evidence_manifest,
    verify_raw_artifact,
)
from research.b2.evidence_contract import assert_pit, parse_temporal, validate_evidence_record

EXPECTED_BLOCKERS = (
    "EVIDENCE[605016-PRICE-CANDIDATE-20261009]:PIT:PIT_UNKNOWN: source availability/provenance is not established",
    "REQUIRED_FIELD_GROUPS_UNCOVERED:market_price",
)
EXPECTED_ADMITTED_GROUPS = {
    "security_identity",
    "corporate_disclosures",
    "business_reality",
    "financial_reality",
    "capital_structure",
    "trust_governance_events",
}


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}_UNREADABLE") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}_MUST_BE_OBJECT")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def adjudicate(input_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Run actual Attempt 10 raw bytes through the unchanged core-owned B2/PIT validator."""
    input_dir = input_dir.resolve(strict=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    intake_path = input_dir / "intake_manifest.json"
    receipt_path = input_dir / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json"
    verification_path = input_dir / "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json"

    intake_raw = intake_path.read_bytes()
    intake = _load_object(intake_path, "INTAKE_MANIFEST")
    receipt = _load_object(receipt_path, "INTAKE_RECEIPT")
    independent = _load_object(verification_path, "INDEPENDENT_VERIFICATION")

    if _sha256(intake_raw) != receipt.get("manifest_sha256"):
        raise ValueError("INTAKE_MANIFEST_SHA256_DOES_NOT_MATCH_CAPTURE_RECEIPT")
    if receipt.get("status") != "CAPTURED_NOT_ADMITTED":
        raise ValueError("EXPECTED_CAPTURE_ONLY_RECEIPT")
    if independent.get("manifest_sha256") != receipt.get("manifest_sha256"):
        raise ValueError("INDEPENDENT_VERIFIER_MANIFEST_BINDING_MISMATCH")
    if independent.get("raw_bytes_verified") != 12:
        raise ValueError("ATTEMPT10_RAW_BYTE_VERIFICATION_COUNT_MISMATCH")
    if independent.get("payload_contract_mismatches") != 0:
        raise ValueError("ATTEMPT10_PAYLOAD_CONTRACT_MISMATCH")
    if independent.get("source_origin_verified") is not False:
        raise ValueError("SOURCE_ORIGIN_MUST_NOT_BE_PROMOTED_BY_RAW_CAPTURE")
    if intake.get("case_id") != "RC-CN-A-605016-20261009":
        raise ValueError("CASE_ID_MISMATCH")
    if intake.get("symbol") != "605016" or intake.get("cutoff_date") != "2026-10-09":
        raise ValueError("SECURITY_OR_CUTOFF_MISMATCH")

    receipt_sources = receipt.get("sources")
    source_specs = intake.get("sources")
    if not isinstance(receipt_sources, list) or not isinstance(source_specs, list):
        raise ValueError("SOURCE_ROWS_REQUIRED")
    by_receipt = {
        str(row.get("source_id")): row for row in receipt_sources if isinstance(row, Mapping)
    }
    by_spec = {
        str(row.get("source_id")): row for row in source_specs if isinstance(row, Mapping)
    }
    if set(by_receipt) != set(by_spec) or len(by_receipt) != 12:
        raise ValueError("SOURCE_SPEC_RECEIPT_SET_MISMATCH")

    # Independently re-hash every captured source, including excluded candidates.
    raw_verification: list[dict[str, Any]] = []
    for source_id in sorted(by_spec):
        row = by_receipt[source_id]
        relative_path = str(row.get("raw_artifact_path") or "")
        declaration = {
            "evidence_id": source_id,
            "relative_path": relative_path,
            "expected_size_bytes": row.get("size_bytes"),
            "expected_sha256": row.get("sha256"),
        }
        result = verify_raw_artifact(input_dir, declaration)
        raw_verification.append({"source_id": source_id, **result})
        if result.get("status") != "PASS":
            raise ValueError(f"RAW_ARTIFACT_REVERIFICATION_FAILED:{source_id}:{result.get('reason')}")

    ledger_path = (
        Path(__file__).resolve().parents[1]
        / "evidence" / "real_cases" / "RC-CN-A-605016-20261009"
        / "SOURCE_ADJUDICATION_20261010.json"
    )
    ledger = _load_object(ledger_path, "SOURCE_ADJUDICATION_LEDGER")
    if ledger.get("capture_reference", {}).get("intake_manifest_sha256") != receipt.get("manifest_sha256"):
        raise ValueError("SOURCE_ADJUDICATION_LEDGER_NOT_BOUND_TO_ATTEMPT10")
    if ledger.get("case_id") != intake.get("case_id"):
        raise ValueError("SOURCE_ADJUDICATION_CASE_BINDING_MISMATCH")

    ledger_sources = ledger.get("sources")
    if not isinstance(ledger_sources, list) or len(ledger_sources) != 12:
        raise ValueError("SOURCE_ADJUDICATION_LEDGER_SOURCE_COUNT_MISMATCH")
    ledger_by_id = {
        str(row.get("source_id")): row for row in ledger_sources if isinstance(row, Mapping)
    }
    if set(ledger_by_id) != set(by_receipt):
        raise ValueError("SOURCE_ADJUDICATION_LEDGER_SOURCE_SET_MISMATCH")
    for source_id, ledger_row in ledger_by_id.items():
        receipt_row = by_receipt[source_id]
        if (
            str(ledger_row.get("raw_file")) != str(receipt_row.get("raw_artifact_path"))
            or str(ledger_row.get("sha256")) != str(receipt_row.get("sha256"))
            or str(ledger_row.get("source_url")) != str(by_spec[source_id].get("url") or "")
        ):
            raise ValueError(f"SOURCE_ADJUDICATION_LEDGER_RAW_BINDING_MISMATCH:{source_id}")

    candidates = ledger.get("evidence_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("EVIDENCE_CANDIDATES_REQUIRED")

    evidence: list[dict[str, Any]] = []
    raw_artifacts: list[dict[str, Any]] = []
    unknown_count = 0
    excluded_after_cutoff: list[dict[str, Any]] = []
    cutoff_instant = parse_temporal(str(ledger["cutoff_date"]), "cutoff_date")
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("EVIDENCE_CANDIDATE_MUST_BE_OBJECT")
        source_id = str(candidate.get("source_id") or "")
        source_spec = by_spec.get(source_id)
        source_receipt = by_receipt.get(source_id)
        if source_spec is None or source_receipt is None:
            raise ValueError(f"EVIDENCE_CANDIDATE_SOURCE_NOT_IN_ATTEMPT10:{source_id}")
        if source_receipt.get("capture_status") != "SUCCESS":
            raise ValueError(f"EVIDENCE_CANDIDATE_SOURCE_NOT_CAPTURED:{source_id}")

        evidence_id = str(candidate["evidence_id"])
        known_at_value = candidate.get("known_at")
        if known_at_value:
            try:
                if (
                    str(candidate.get("status")) == "ADMITTED"
                    and parse_temporal(known_at_value, "known_at") > cutoff_instant
                ):
                    excluded_after_cutoff.append({
                        "evidence_id": evidence_id,
                        "source_id": source_id,
                        "known_at": known_at_value,
                        "reason": "KNOWN_AT_AFTER_ORIGINAL_DATE_ONLY_CUTOFF",
                    })
                    continue
            except ValueError as exc:
                raise ValueError(f"INVALID_CANDIDATE_KNOWN_AT:{evidence_id}") from exc
        raw_path = str(source_receipt["raw_artifact_path"])
        raw_sha = str(source_receipt["sha256"])
        source_status = str(candidate["status"])
        if source_status == "UNKNOWN":
            unknown_count += 1

        record = {
            "evidence_id": evidence_id,
            "subject_id": str(intake["case_id"]),
            "field_id": str(candidate["field_id"]),
            "claim_type": str(candidate["claim_type"]),
            "value": candidate["value"],
            "unit": candidate.get("unit"),
            "basis": candidate.get("basis"),
            "observation_date": candidate.get("observation_date"),
            "known_at": candidate.get("known_at"),
            "published_at": candidate.get("published_at"),
            "known_at_basis": candidate.get("known_at_basis"),
            "retrieved_at": str(source_receipt.get("attempted_at") or receipt["captured_at"]),
            "source_ref": str(source_spec.get("url") or ""),
            "artifact_id": f"ROUTE-A-RAW:{source_id}:{raw_sha[:16]}",
            "content_sha256": raw_sha,
            "capture_sha256": raw_sha,
            "exact_bytes": True,
            "provenance_class": str(candidate["provenance_class"]),
            "status": source_status,
            "license_status": str(candidate["license_status"]),
            "source_locator": str(candidate["source_locator"]),
            "source_id": source_id,
            "first_public_time_precision": candidate.get("known_at_basis"),
            "source_origin_adjudication": next(
                (row.get("source_origin") for row in ledger["sources"] if row.get("source_id") == source_id),
                "NOT_REVIEWED",
            ),
            "parents": [],
            "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
            "quality_notes": list(candidate.get("quality_notes") or []),
        }
        # Exclude absent optional values, but never remove required UNKNOWN values such as known_at=None.
        record = {key: value for key, value in record.items() if value is not None}
        evidence.append(record)
        raw_artifacts.append({
            "evidence_id": evidence_id,
            "relative_path": raw_path,
            "expected_size_bytes": int(source_receipt["size_bytes"]),
            "expected_sha256": raw_sha,
        })

    manifest = build_company_evidence_manifest(
        case_id=str(intake["case_id"]),
        market=str(intake["market"]),
        symbol=str(intake["symbol"]),
        company=str(ledger["company"]),
        cutoff_date=str(ledger["cutoff_date"]),
        evidence=evidence,
        raw_artifacts=raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=input_dir,
    )
    errors = list(manifest.get("validation_errors") or [])
    actual_admitted_groups: set[str] = set()
    for item in evidence:
        if item.get("status") != "ADMITTED" or item.get("provenance_class") == "UNKNOWN":
            continue
        if validate_evidence_record(item):
            continue
        try:
            # The unchanged core contract treats a date-only cutoff as the
            # beginning of that local date. A 10/09 18:09:28 disclosure is
            # therefore outside a date-only 10/09 cutoff unless the governing
            # case contract explicitly supplies an end-of-day timestamp.
            assert_pit(item, str(ledger["cutoff_date"]))
        except ValueError:
            continue
        actual_admitted_groups.add(str(item["field_id"]).split(".", 1)[0])
    missing_groups = sorted(set(REQUIRED_COMPANY_FIELD_GROUPS) - actual_admitted_groups)

    # Expected outcome is a real fail-closed result, not overall PASS:
    # six groups have eligible source-adjudicated facts, while price remains
    # UNKNOWN. Same-day facts with known_at after the original date-only cutoff
    # are kept in the source ledger but excluded from the B2 candidate manifest.
    if manifest.get("status") != "BLOCKED":
        raise AssertionError(f"B2_MUST_REMAIN_BLOCKED_UNTIL_PRICE_ADMISSION:{manifest.get('status')}")
    if missing_groups != ["market_price"]:
        raise AssertionError(f"UNEXPECTED_MISSING_GROUPS:{missing_groups}")
    if len(excluded_after_cutoff) != 1 or excluded_after_cutoff[0]["evidence_id"] != "605016-MEETING-CB-RESOLUTIONS-20261008":
        raise AssertionError(f"UNEXPECTED_AFTER_CUTOFF_EXCLUSIONS:{excluded_after_cutoff}")
    if actual_admitted_groups != EXPECTED_ADMITTED_GROUPS:
        raise AssertionError(f"UNEXPECTED_ADMITTED_GROUPS:{sorted(actual_admitted_groups)}")
    if errors != list(EXPECTED_BLOCKERS):
        raise AssertionError(f"UNEXPECTED_B2_VALIDATION_ERRORS:{errors}")
    if unknown_count != 1:
        raise AssertionError(f"EXPECTED_ONE_UNADMITTED_PRICE_CANDIDATE:{unknown_count}")

    manifest_path = out_dir / "SOURCE_ADJUDICATED_B2_CANDIDATE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": "IIOS-ROUTE-A-SOURCE-ADJUDICATION-RUN-0.1",
        "case_id": intake["case_id"],
        "cutoff_date": intake["cutoff_date"],
        "capture_manifest_sha256": receipt["manifest_sha256"],
        "independently_reverified_raw_source_count": len(raw_verification),
        "raw_sources_hash_and_size_passed": len([row for row in raw_verification if row.get("status") == "PASS"]),
        "payload_contract_passed": independent["payload_contract_passes"],
        "source_adjudication_ledger_sha256": _sha256(ledger_path.read_bytes()),
        "fact_record_count": len(evidence),
        "admitted_fact_record_count": len([item for item in evidence if item.get("status") == "ADMITTED"]),
        "explicit_unknown_fact_record_count": unknown_count,
        "excluded_after_cutoff_fact_record_count": len(excluded_after_cutoff),
        "excluded_after_cutoff_fact_records": excluded_after_cutoff,
        "admitted_field_groups": sorted(actual_admitted_groups),
        "missing_required_field_groups": missing_groups,
        "core_b2_validator": "research.b2.company_evidence.build_company_evidence_manifest (unchanged)",
        "b2_manifest_status": manifest["status"],
        "evidence_admission": False,
        "pit_admission": False,
        "validation_errors": errors,
        "decision": "BLOCKED_AS_REQUIRED: market_price remains UNKNOWN; no valuation, Decision Revision, Publication, report or complete Run Receipt may be produced.",
        "cutoff_semantics_note": "The unchanged core parses date-only cutoff 2026-10-09 as the start of that day. The same-day 18:09:28+08 meeting resolution is retained in the source ledger but excluded from the admission manifest; a pre-cutoff 2026-09-11 official disclosure covers corporate_disclosures. No end-of-day reinterpretation was applied.",
        "raw_sources": raw_verification,
        "evidence_manifest_path": str(manifest_path.name),
        "non_claims": [
            "The source review does not convert an exchange archive date into an exact intraday first-public timestamp.",
            "The 2026-06-30 share count is historical, not asserted as the outstanding count on 2026-10-09.",
            "The H1 dividend proposal is not the actual implementation; the official 2026-09-22 implementation notice still needs to be captured and inspected.",
            "Convertible-bond admission covers procedural status only, not final registered terms or completed issuance.",
            "The 2026-10-09 market close remains UNKNOWN / NOT_ADMITTED despite the secondary CNY 20.28 candidate.",
            "Production Host deployment, genuine semantic reasoning, and full host-origin Run Receipt replay are outside this B2 evidence admission run."
        ]
    }
    report_path = out_dir / "SOURCE_ADJUDICATION_RUN_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-run-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    report = adjudicate(args.input_run_dir, args.out_dir)
    print(json.dumps({
        "case_id": report["case_id"],
        "b2_manifest_status": report["b2_manifest_status"],
        "admitted_field_groups": report["admitted_field_groups"],
        "missing_required_field_groups": report["missing_required_field_groups"],
        "validation_errors": report["validation_errors"],
        "evidence_admission": report["evidence_admission"],
        "pit_admission": report["pit_admission"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
