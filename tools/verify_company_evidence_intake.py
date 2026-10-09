from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

RECEIPT_SCHEMA = "IIOS-COMPANY-EVIDENCE-INTAKE-RECEIPT-0.1"
MANIFEST_SCHEMA = "IIOS-COMPANY-EVIDENCE-INTAKE-MANIFEST-0.1"
UTC_PLUS_8 = timezone(timedelta(hours=8))


class IndependentVerificationError(ValueError):
    """Raised when captured raw bytes or their manifest binding cannot be verified."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IndependentVerificationError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndependentVerificationError("INVALID_OR_UNAVAILABLE_JSON") from exc


def _known_at_pit_status(source: Mapping[str, Any], cutoff_raw: str) -> str:
    known_raw = source.get("known_at")
    basis = source.get("known_at_basis")
    if not isinstance(known_raw, str) or not known_raw.strip():
        return "UNKNOWN_NO_KNOWN_AT"
    if not isinstance(basis, str) or not basis.strip():
        return "UNKNOWN_NO_KNOWN_AT_BASIS"
    try:
        cutoff = date.fromisoformat(cutoff_raw)
    except ValueError as exc:
        raise IndependentVerificationError("INVALID_CUTOFF_DATE") from exc
    if len(known_raw.strip()) == 10:
        try:
            known = date.fromisoformat(known_raw)
        except ValueError as exc:
            raise IndependentVerificationError("INVALID_KNOWN_AT_DATE") from exc
        return "PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW" if known <= cutoff else "BLOCKED_KNOWN_AFTER_CUTOFF"
    try:
        known_dt = datetime.fromisoformat(known_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndependentVerificationError("INVALID_KNOWN_AT_DATETIME") from exc
    if known_dt.tzinfo is None:
        raise IndependentVerificationError("KNOWN_AT_TIMEZONE_MISSING")
    cutoff_end = datetime.combine(cutoff + timedelta(days=1), time.min, tzinfo=UTC_PLUS_8)
    if known_dt.astimezone(timezone.utc) >= cutoff_end.astimezone(timezone.utc):
        return "BLOCKED_KNOWN_AFTER_CUTOFF"
    return "PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW"


def _contained_file(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative.startswith("raw/"):
        raise IndependentVerificationError("RAW_PATH_INVALID")
    candidate = (root / relative).resolve()
    raw_root = (root / "raw").resolve()
    if candidate == raw_root or raw_root not in candidate.parents or not candidate.is_file():
        raise IndependentVerificationError("RAW_PATH_ESCAPES_ROOT_OR_FILE_MISSING")
    return candidate


def verify_intake(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    receipt_path = root_path / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json"
    manifest_path = root_path / "intake_manifest.json"
    receipt = _load_json(receipt_path)
    manifest = _load_json(manifest_path)
    if not isinstance(receipt, dict) or not isinstance(manifest, dict):
        raise IndependentVerificationError("RECEIPT_AND_MANIFEST_MUST_BE_OBJECTS")
    if receipt.get("schema_version") != RECEIPT_SCHEMA or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise IndependentVerificationError("SCHEMA_VERSION_MISMATCH")
    if receipt.get("admission_status") != "NOT_ADMITTED":
        raise IndependentVerificationError("INTAKE_RECEIPT_MUST_NOT_CLAIM_ADMISSION")
    if receipt.get("status") not in {"CAPTURED_NOT_ADMITTED", "PARTIAL_CAPTURE_NOT_ADMITTED"}:
        raise IndependentVerificationError("RECEIPT_STATUS_IS_NOT_A_CAPTURE_ONLY_STATUS")
    manifest_bytes = manifest_path.read_bytes()
    if _sha256(manifest_bytes) != receipt.get("manifest_sha256"):
        raise IndependentVerificationError("MANIFEST_SHA256_MISMATCH")
    for field in ("case_id", "market", "symbol", "cutoff_date"):
        if receipt.get(field) != manifest.get(field):
            raise IndependentVerificationError("CASE_IDENTITY_BINDING_MISMATCH")
    if manifest.get("case_id") == "" or not isinstance(manifest.get("sources"), list) or not manifest["sources"]:
        raise IndependentVerificationError("MANIFEST_SOURCE_SET_INVALID")
    sources_by_id = {}
    for source in manifest["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            raise IndependentVerificationError("MANIFEST_SOURCE_SPEC_INVALID")
        if source["source_id"] in sources_by_id:
            raise IndependentVerificationError("DUPLICATE_MANIFEST_SOURCE_ID")
        sources_by_id[source["source_id"]] = source
    rows = receipt.get("sources")
    if not isinstance(rows, list) or len(rows) != len(sources_by_id):
        raise IndependentVerificationError("RECEIPT_SOURCE_SET_SIZE_MISMATCH")
    seen = set()
    verified_paths = set()
    verified_count = 0
    unknown_count = 0
    future_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise IndependentVerificationError("RECEIPT_SOURCE_RECORD_INVALID")
        source_id = row.get("source_id")
        if source_id not in sources_by_id or source_id in seen:
            raise IndependentVerificationError("RECEIPT_SOURCE_ID_MISMATCH")
        seen.add(source_id)
        source = sources_by_id[source_id]
        if row.get("source_spec_sha256") != _sha256(_canonical_bytes(source)):
            raise IndependentVerificationError("SOURCE_SPEC_HASH_MISMATCH")
        for field, manifest_field in (
            ("field_group", "field_group"),
            ("source_ref", "source_ref"),
            ("source_class_claim", "source_class"),
            ("source_url", "url"),
            ("operator_local_path", "local_path"),
            ("known_at", "known_at"),
            ("known_at_basis", "known_at_basis"),
            ("published_at", "published_at"),
            ("observation_date", "observation_date"),
            ("effective_from", "effective_from"),
            ("effective_to", "effective_to"),
            ("license_status", "license_status"),
        ):
            if row.get(field) != source.get(manifest_field):
                raise IndependentVerificationError("SOURCE_METADATA_BINDING_MISMATCH")
        if row.get("admission_status") != "NOT_ADMITTED":
            raise IndependentVerificationError("SOURCE_RECORD_MUST_NOT_CLAIM_ADMISSION")
        if row.get("source_authenticity_status") != "UNVERIFIED":
            raise IndependentVerificationError("SOURCE_AUTHENTICITY_MUST_REMAIN_UNVERIFIED")
        expected_pit = _known_at_pit_status(source, str(manifest["cutoff_date"]))
        if row.get("pit_status") != expected_pit and row.get("capture_status") == "SUCCESS":
            raise IndependentVerificationError("PIT_STATUS_MISMATCH")
        if expected_pit.startswith("UNKNOWN"):
            unknown_count += 1
        if expected_pit == "BLOCKED_KNOWN_AFTER_CUTOFF":
            future_count += 1
        if row.get("capture_status") == "SUCCESS":
            path = _contained_file(root_path, row.get("raw_artifact_path"))
            actual = path.read_bytes()
            if _sha256(actual) != row.get("sha256"):
                raise IndependentVerificationError("RAW_SHA256_MISMATCH")
            if len(actual) != row.get("size_bytes"):
                raise IndependentVerificationError("RAW_SIZE_MISMATCH")
            verified_paths.add(path.relative_to(root_path / "raw").as_posix())
            verified_count += 1
        elif row.get("capture_status") == "FAILED":
            if row.get("raw_artifact_path") is not None or row.get("sha256") is not None or row.get("size_bytes") is not None:
                raise IndependentVerificationError("FAILED_CAPTURE_MUST_NOT_DECLARE_RAW_BYTES")
            if not row.get("error_code"):
                raise IndependentVerificationError("FAILED_CAPTURE_MUST_DECLARE_ERROR_CODE")
        else:
            raise IndependentVerificationError("UNKNOWN_CAPTURE_STATUS")
    actual_paths = {p.relative_to(root_path / "raw").as_posix() for p in (root_path / "raw").rglob("*") if p.is_file()}
    if actual_paths != verified_paths:
        raise IndependentVerificationError("UNREFERENCED_OR_MISSING_RAW_FILES")
    expected_status = "CAPTURED_NOT_ADMITTED" if verified_count == len(rows) else "PARTIAL_CAPTURE_NOT_ADMITTED"
    if receipt.get("status") != expected_status:
        raise IndependentVerificationError("RECEIPT_CAPTURE_STATUS_MISMATCH")
    return {
        "schema_version": "IIOS-COMPANY-EVIDENCE-INDEPENDENT-VERIFY-0.1",
        "status": "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION",
        "case_id": receipt["case_id"],
        "cutoff_date": receipt["cutoff_date"],
        "manifest_sha256": receipt["manifest_sha256"],
        "sources_declared": len(rows),
        "raw_bytes_verified": verified_count,
        "unknown_pit_sources": unknown_count,
        "future_known_sources": future_count,
        "source_origin_verified": False,
        "evidence_admission": False,
        "live_llm_required": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent byte/hash and metadata verification; does not admit evidence.")
    parser.add_argument("--root", required=True, help="Company evidence intake output directory")
    args = parser.parse_args()
    try:
        result = verify_intake(args.root)
    except (OSError, IndependentVerificationError) as exc:
        code = str(exc) if isinstance(exc, IndependentVerificationError) else "INPUT_FILE_UNAVAILABLE"
        print(json.dumps({"status": "INDEPENDENT_VERIFICATION_REJECTED", "error_code": code}, sort_keys=True))
        return 1
    output = Path(args.root) / "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json"
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
