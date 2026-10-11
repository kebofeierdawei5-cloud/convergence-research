from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

KNOWN_PROVENANCE = {
    "SOURCE_VINTAGE_VERIFIED",
    "EVENT_PUBLICATION_VERIFIED",
    "VENDOR_PIT_QUERY",
    "DERIVED_FROM_ADMITTED_RAW",
    "OPERATOR_ATTESTED_MARKET_DATA",
    "UNKNOWN",
}


def parse_temporal(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO date/time string")
    raw = value.strip()
    try:
        if len(raw) == 10:
            d = date.fromisoformat(raw)
            return datetime(d.year, d.month, d.day, tzinfo=timezone(timedelta(hours=8)))
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return result


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
    if evidence.get("provenance_class") == "OPERATOR_ATTESTED_MARKET_DATA":
        attestation = evidence.get("operator_attestation")
        if not str(evidence.get("field_id", "")).startswith("market_price."):
            errors.append("OPERATOR_ATTESTATION:MARKET_PRICE_FIELD_ONLY")
        if status != "ADMITTED":
            errors.append("OPERATOR_ATTESTATION:STATUS_MUST_BE_ADMITTED")
        if not isinstance(attestation, dict):
            errors.append("OPERATOR_ATTESTATION:REQUIRED")
        else:
            if attestation.get("policy_id") != "IIOS-OPERATOR-MARKET-PRICE-ATTESTATION-0.1":
                errors.append("OPERATOR_ATTESTATION:POLICY_ID_INVALID")
            if attestation.get("operator_confirmed") is not True:
                errors.append("OPERATOR_ATTESTATION:OPERATOR_CONFIRMATION_REQUIRED")
            if attestation.get("secondary_web_audit_performed") is not False:
                errors.append("OPERATOR_ATTESTATION:SECONDARY_WEB_AUDIT_FLAG_INVALID")
            if attestation.get("original_vendor_bytes_received") is not False:
                errors.append("OPERATOR_ATTESTATION:RAW_VENDOR_BYTES_MUST_NOT_BE_CLAIMED")
            if attestation.get("case_id") != evidence.get("subject_id"):
                errors.append("OPERATOR_ATTESTATION:CASE_BINDING_MISMATCH")
            if attestation.get("source_ref") != evidence.get("source_ref"):
                errors.append("OPERATOR_ATTESTATION:SOURCE_REF_MISMATCH")
            if attestation.get("known_at") != evidence.get("known_at"):
                errors.append("OPERATOR_ATTESTATION:KNOWN_AT_MISMATCH")
            if attestation.get("observation_date") != evidence.get("observation_date"):
                errors.append("OPERATOR_ATTESTATION:OBSERVATION_DATE_MISMATCH")
            if evidence.get("currency") != attestation.get("currency"):
                errors.append("OPERATOR_ATTESTATION:CURRENCY_MISMATCH")
            if attestation.get("known_at_basis") != "OPERATOR_ATTESTS_AVAILABLE_BY_END_OF_OBSERVATION_DATE":
                errors.append("OPERATOR_ATTESTATION:KNOWN_AT_BASIS_INVALID")
            close = attestation.get("close_price")
            value = evidence.get("value")
            try:
                from decimal import Decimal, InvalidOperation
                if Decimal(str(close)) != Decimal(str(value)):
                    errors.append("OPERATOR_ATTESTATION:VALUE_MISMATCH")
                if not Decimal(str(close)).is_finite() or Decimal(str(close)) <= 0:
                    errors.append("OPERATOR_ATTESTATION:CLOSE_PRICE_INVALID")
            except (InvalidOperation, TypeError, ValueError):
                errors.append("OPERATOR_ATTESTATION:CLOSE_PRICE_INVALID")
            try:
                parse_temporal(attestation.get("attested_at"), "operator_attestation.attested_at")
            except ValueError:
                errors.append("OPERATOR_ATTESTATION:ATTESTED_AT_INVALID")
    known_raw = evidence.get("known_at")
    known_missing = known_raw is None or (
        isinstance(known_raw, str) and not known_raw.strip()
    )
    explicitly_unknown = (
        evidence.get("provenance_class") == "UNKNOWN" and status == "UNKNOWN"
    )
    try:
        # Represent an unknown time without inventing a date. This is valid as
        # an UNKNOWN record only; assert_pit() below the capture boundary will
        # still reject it for admission.
        known = None if explicitly_unknown and known_missing else parse_temporal(
            known_raw, "known_at"
        )
        retrieved = parse_temporal(evidence["retrieved_at"], "retrieved_at")
        if known is not None and retrieved < known:
            errors.append("TEMPORAL_ORDER:retrieved_at cannot precede known_at")
        published_raw = evidence.get("published_at")
        if published_raw:
            published = parse_temporal(published_raw, "published_at")
            if known is not None and published > known:
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
    if evidence.get("provenance_class") == "UNKNOWN" or evidence.get("status") == "UNKNOWN":
        raise ValueError("PIT_UNKNOWN: source availability/provenance is not established")
    if evidence.get("status") == "BLOCKED":
        raise ValueError("PIT_BLOCKED: evidence record is blocked")
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