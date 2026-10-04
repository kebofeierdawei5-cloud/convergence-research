from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

KNOWN_PROVENANCE = {
    "SOURCE_VINTAGE_VERIFIED",
    "EVENT_PUBLICATION_VERIFIED",
    "VENDOR_PIT_QUERY",
    "DERIVED_FROM_ADMITTED_RAW",
    "UNKNOWN",
}


def parse_temporal(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO date/time string")
    raw = value.strip()
    try:
        if len(raw) == 10:
            d = date.fromisoformat(raw)
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return result


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def pit_qualified(evidence: dict[str, Any], cutoff: Any) -> bool:
    known = parse_temporal(evidence.get("known_at"), "known_at")
    cutoff_dt = parse_temporal(cutoff, "cutoff") if isinstance(cutoff, str) else cutoff
    if not isinstance(cutoff_dt, datetime) or cutoff_dt.tzinfo is None:
        raise ValueError("cutoff must be an offset-aware datetime or ISO string")
    return known <= cutoff_dt


def effective_qualified(evidence: dict[str, Any], cutoff: Any) -> bool:
    start_raw = evidence.get("effective_from")
    if start_raw in (None, ""):
        return False
    start = parse_temporal(start_raw, "effective_from")
    cutoff_dt = parse_temporal(cutoff, "cutoff") if isinstance(cutoff, str) else cutoff
    if not isinstance(cutoff_dt, datetime) or cutoff_dt.tzinfo is None:
        raise ValueError("cutoff must be an offset-aware datetime or ISO string")
    end_raw = evidence.get("effective_to")
    if end_raw in (None, ""):
        return start <= cutoff_dt
    end = parse_temporal(end_raw, "effective_to")
    return start <= cutoff_dt < end


def derived_known_at(parent_known_ats: Iterable[Any]) -> datetime:
    parsed = [parse_temporal(v, "parent_known_at") if isinstance(v, str) else v for v in parent_known_ats]
    if not parsed:
        raise ValueError("derived evidence requires at least one parent known_at")
    if any(not isinstance(v, datetime) or v.tzinfo is None for v in parsed):
        raise ValueError("parent known_at values must be offset-aware datetimes")
    return max(parsed)


def validate_evidence_record(evidence: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(evidence, dict):
        return ["EVIDENCE_TYPE:record must be an object"]
    required = (
        "evidence_id", "subject_id", "field_id", "claim_type", "known_at",
        "retrieved_at", "source_ref", "artifact_id", "content_sha256",
        "exact_bytes", "provenance_class", "status"
    )
    for field in required:
        if field not in evidence:
            errors.append(f"MISSING:{field}")
    if errors:
        return errors
    if evidence.get("exact_bytes") is not True:
        errors.append("EXACT_BYTES_REQUIRED:true")
    sha = evidence.get("content_sha256")
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        errors.append("CONTENT_SHA256:must be 64 lowercase hex characters")
    if evidence.get("provenance_class") not in KNOWN_PROVENANCE:
        errors.append("PROVENANCE_CLASS:invalid")
    status = evidence.get("status")
    if status not in {"ADMITTED", "CONDITIONAL", "UNKNOWN", "BLOCKED"}:
        errors.append("STATUS:invalid")
    try:
        known = parse_temporal(evidence["known_at"], "known_at")
        retrieved = parse_temporal(evidence["retrieved_at"], "retrieved_at")
        if retrieved < known:
            errors.append("TEMPORAL_ORDER:retrieved_at cannot precede known_at")
        published_raw = evidence.get("published_at")
        if published_raw:
            published = parse_temporal(published_raw, "published_at")
            if published > known:
                errors.append("TEMPORAL_ORDER:published_at cannot be after known_at")
        start_raw = evidence.get("effective_from")
        end_raw = evidence.get("effective_to")
        if start_raw and end_raw and parse_temporal(end_raw, "effective_to") <= parse_temporal(start_raw, "effective_from"):
            errors.append("TEMPORAL_ORDER:effective_to must be after effective_from")
    except ValueError as exc:
        errors.append(f"TEMPORAL:{exc}")
    if evidence.get("provenance_class") == "DERIVED_FROM_ADMITTED_RAW":
        parents = evidence.get("parents")
        transform = evidence.get("transformation")
        if not isinstance(parents, list) or not parents:
            errors.append("DERIVED:PARENTS_REQUIRED")
        if not isinstance(transform, dict) or transform.get("type") != "DERIVED":
            errors.append("DERIVED:TRANSFORMATION_REQUIRED")
    return errors


def assert_pit(evidence: dict[str, Any], cutoff: Any) -> None:
    errors = validate_evidence_record(evidence)
    if errors:
        raise ValueError("; ".join(errors))
    if not pit_qualified(evidence, cutoff):
        raise ValueError("PIT_FAIL: known_at exceeds cutoff")


__all__ = [
    "KNOWN_PROVENANCE",
    "parse_temporal",
    "pit_qualified",
    "effective_qualified",
    "derived_known_at",
    "validate_evidence_record",
    "assert_pit",
]