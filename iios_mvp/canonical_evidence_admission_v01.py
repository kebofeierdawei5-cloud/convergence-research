from __future__ import annotations

"""Core-owned, free-first company Evidence/PIT manifest admission.

This implementation intentionally lives in iios_mvp rather than importing
research.b2: Investment Core must not depend upward on the research layer.
A manifest is only admitted after exact raw bytes, manifest integrity, evidence
structure, provenance and point-in-time ordering are independently rechecked.
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

EVIDENCE_MANIFEST_SCHEMA = "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1"
REQUIRED_FIELD_GROUPS = (
    "security_identity",
    "market_price",
    "corporate_disclosures",
    "business_reality",
    "financial_reality",
    "capital_structure",
    "trust_governance_events",
)
ALLOWED_PROVENANCE = {
    "SOURCE_VINTAGE_VERIFIED", "EVENT_PUBLICATION_VERIFIED",
    "VENDOR_PIT_QUERY", "DERIVED_FROM_ADMITTED_RAW", "UNKNOWN",
}
ALLOWED_STATUS = {"ADMITTED", "CONDITIONAL", "UNKNOWN", "BLOCKED"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SHANGHAI = timezone(timedelta(hours=8))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _temporal(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO date/time string")
    raw = value.strip()
    try:
        if len(raw) == 10:
            parsed_date = date.fromisoformat(raw)
            return datetime.combine(parsed_date, time.min, tzinfo=_SHANGHAI)
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return parsed


def _evidence_errors(item: Any) -> list[str]:
    if not isinstance(item, Mapping):
        return ["EVIDENCE_TYPE:record must be an object"]
    required = {
        "evidence_id", "subject_id", "field_id", "claim_type", "known_at",
        "retrieved_at", "source_ref", "artifact_id", "content_sha256",
        "exact_bytes", "provenance_class", "status",
    }
    missing = sorted(required - set(item))
    if missing:
        return ["MISSING:" + field for field in missing]
    errors: list[str] = []
    if item.get("exact_bytes") is not True:
        errors.append("EXACT_BYTES_REQUIRED:true")
    digest = item.get("content_sha256")
    if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
        errors.append("CONTENT_SHA256:must be 64 lowercase hex characters")
    if item.get("provenance_class") not in ALLOWED_PROVENANCE:
        errors.append("PROVENANCE_CLASS:invalid")
    if item.get("status") not in ALLOWED_STATUS:
        errors.append("STATUS:invalid")
    unknown = item.get("provenance_class") == "UNKNOWN" and item.get("status") == "UNKNOWN"
    try:
        known_raw = item.get("known_at")
        if unknown and known_raw in (None, ""):
            known = None
        else:
            known = _temporal(known_raw, "known_at")
        retrieved = _temporal(item.get("retrieved_at"), "retrieved_at")
        if known is not None and retrieved < known:
            errors.append("TEMPORAL_ORDER:retrieved_at cannot precede known_at")
        published_raw = item.get("published_at")
        if published_raw:
            published = _temporal(published_raw, "published_at")
            if known is not None and published > known:
                errors.append("TEMPORAL_ORDER:published_at cannot be after known_at")
        start_raw, end_raw = item.get("effective_from"), item.get("effective_to")
        if start_raw and end_raw and _temporal(end_raw, "effective_to") <= _temporal(start_raw, "effective_from"):
            errors.append("TEMPORAL_ORDER:effective_to must be after effective_from")
    except ValueError as exc:
        errors.append(f"TEMPORAL:{exc}")
    if item.get("provenance_class") == "DERIVED_FROM_ADMITTED_RAW":
        if not isinstance(item.get("parents"), list) or not item.get("parents"):
            errors.append("DERIVED:PARENTS_REQUIRED")
        transform = item.get("transformation")
        if not isinstance(transform, Mapping) or transform.get("type") != "DERIVED":
            errors.append("DERIVED:TRANSFORMATION_REQUIRED")
    return errors


def validate_company_evidence_manifest(
    manifest: Any,
    *,
    raw_root: str | Path,
    require_raw_verification: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["COMPANY_EVIDENCE_TYPE:manifest must be an object"]
    required = {
        "schema_version", "case_id", "market", "symbol", "company",
        "cutoff_date", "required_field_groups", "evidence", "raw_artifacts", "audit",
    }
    errors.extend("MISSING:" + key for key in sorted(required - set(manifest)))
    if errors:
        return errors
    if manifest.get("schema_version") != EVIDENCE_MANIFEST_SCHEMA:
        errors.append("VERSION_INVALID")
    if manifest.get("market") not in {"CN-A", "HK"}:
        errors.append("MARKET_INVALID")
    if not all(isinstance(manifest.get(k), str) and str(manifest[k]).strip()
               for k in ("case_id", "symbol", "company")):
        errors.append("IDENTITY_REQUIRED")
    try:
        cutoff = _temporal(manifest.get("cutoff_date"), "cutoff_date")
    except ValueError as exc:
        errors.append(f"CUTOFF_INVALID:{exc}")
        cutoff = None

    groups = manifest.get("required_field_groups")
    if not isinstance(groups, list) or not groups:
        errors.append("FIELD_GROUPS_REQUIRED")
        groups = []
    if len(groups) != len(set(groups)):
        errors.append("FIELD_GROUPS_DUPLICATE")
    if any(group not in REQUIRED_FIELD_GROUPS for group in groups):
        errors.append("FIELD_GROUP_INVALID")
    absent_groups = sorted(set(REQUIRED_FIELD_GROUPS) - set(groups))
    if absent_groups:
        errors.append("REQUIRED_CANONICAL_FIELD_GROUPS_OMITTED:" + ",".join(absent_groups))

    evidence = manifest.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("EVIDENCE_REQUIRED")
        evidence = []
    evidence_ids: set[str] = set()
    covered: set[str] = set()
    for item in evidence:
        evidence_id = str(item.get("evidence_id", "?")) if isinstance(item, Mapping) else "?"
        item_errors = _evidence_errors(item)
        errors.extend(f"EVIDENCE[{evidence_id}]:{err}" for err in item_errors)
        if not isinstance(item, Mapping):
            continue
        if str(item.get("subject_id", "")).strip() != str(manifest.get("case_id", "")).strip():
            errors.append(f"EVIDENCE[{evidence_id}]:SUBJECT_CASE_MISMATCH")
        if evidence_id in evidence_ids:
            errors.append(f"DUPLICATE_EVIDENCE_ID:{evidence_id}")
        evidence_ids.add(evidence_id)
        pit_passed = False
        if cutoff is not None and not item_errors and item.get("status") == "ADMITTED" and item.get("provenance_class") != "UNKNOWN":
            try:
                pit_passed = _temporal(item.get("known_at"), "known_at") <= cutoff
                if not pit_passed:
                    errors.append(f"EVIDENCE[{evidence_id}]:PIT:PIT_FAIL:known_at exceeds cutoff")
            except ValueError as exc:
                errors.append(f"EVIDENCE[{evidence_id}]:PIT:{exc}")
        field_id = str(item.get("field_id", ""))
        if (
            "." in field_id and not item_errors and evidence_id
            and str(item.get("subject_id", "")).strip() == str(manifest.get("case_id", "")).strip()
            and item.get("status") == "ADMITTED"
            and item.get("provenance_class") != "UNKNOWN" and pit_passed
        ):
            covered.add(field_id.split(".", 1)[0])
    uncovered = sorted(set(groups) - covered)
    if uncovered:
        errors.append("REQUIRED_FIELD_GROUPS_UNCOVERED:" + ",".join(uncovered))

    raw_artifacts = manifest.get("raw_artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        errors.append("RAW_ARTIFACTS_REQUIRED")
        raw_artifacts = []
    declared: set[str] = set()
    base = Path(raw_root).resolve()
    for declaration in raw_artifacts:
        if not isinstance(declaration, Mapping):
            errors.append("RAW_ARTIFACT_ENTRY_INVALID")
            continue
        evidence_id = str(declaration.get("evidence_id", "")).strip()
        if not evidence_id:
            errors.append("RAW_ARTIFACT_EVIDENCE_ID_REQUIRED")
            continue
        if evidence_id in declared:
            errors.append("DUPLICATE_RAW_ARTIFACT_EVIDENCE_ID:" + evidence_id)
        declared.add(evidence_id)
        matching = next((x for x in evidence if isinstance(x, Mapping) and str(x.get("evidence_id", "")).strip() == evidence_id), None)
        if matching is None:
            errors.append("RAW_ARTIFACT_WITHOUT_EVIDENCE:" + evidence_id)
        relative = declaration.get("relative_path")
        digest = declaration.get("expected_sha256")
        size = declaration.get("expected_size_bytes")
        if not isinstance(relative, str) or not relative.strip() or not isinstance(size, int) or size < 0 or not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            errors.append(f"RAW_ARTIFACT[{evidence_id}]:DECLARATION_INVALID")
            continue
        if matching is not None and str(matching.get("content_sha256", "")) != digest:
            errors.append(f"RAW_ARTIFACT[{evidence_id}]:EVIDENCE_HASH_MISMATCH")
        if require_raw_verification:
            path = (base / relative).resolve()
            try:
                path.relative_to(base)
            except ValueError:
                errors.append(f"RAW_ARTIFACT[{evidence_id}]:RAW_ARTIFACT_PATH_ESCAPE")
                continue
            if not path.is_file():
                errors.append(f"RAW_ARTIFACT[{evidence_id}]:RAW_ARTIFACT_MISSING")
                continue
            raw = path.read_bytes()
            actual_hash = hashlib.sha256(raw).hexdigest()
            if len(raw) != size or actual_hash != digest:
                errors.append(f"RAW_ARTIFACT[{evidence_id}]:EXACT_BYTES_MISMATCH")
    missing_raw = sorted(evidence_ids - declared)
    if require_raw_verification and missing_raw:
        errors.append("EVIDENCE_WITHOUT_RAW_ARTIFACT:" + ",".join(missing_raw))

    audit = manifest.get("audit")
    if not isinstance(audit, Mapping):
        errors.append("AUDIT_REQUIRED")
    else:
        body = {k: v for k, v in manifest.items() if k not in {"audit", "status", "validation_errors"}}
        if audit.get("manifest_sha256") != _sha(body):
            errors.append("MANIFEST_HASH_MISMATCH")
    if manifest.get("status") != "PASS":
        errors.append("MANIFEST_STATUS_NOT_PASS")
    declared_errors = manifest.get("validation_errors")
    if declared_errors not in (None, []):
        errors.extend("MANIFEST_VALIDATION_ERROR:" + str(x) for x in declared_errors)
    return errors


__all__ = ["EVIDENCE_MANIFEST_SCHEMA", "REQUIRED_FIELD_GROUPS", "validate_company_evidence_manifest"]
