from __future__ import annotations

"""Bind canonical forecasts and valuations to a signed, PIT-verified evidence manifest."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_FIELDS = {
    "envelope_sha256",
    "manifest_sha256",
    "rights_record_sha256",
    "permission_evidence_sha256",
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_regular_file(path: str | Path, field: str) -> bytes:
    target = Path(path).expanduser()
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"{field}_MUST_BE_REGULAR_FILE")
    return target.read_bytes()


@dataclass(frozen=True)
class CanonicalSignedEvidenceAdmissionReference:
    envelope_sha256: str
    manifest_sha256: str
    rights_record_sha256: str
    permission_evidence_sha256: str

    def validate(self) -> None:
        for field in _REFERENCE_FIELDS:
            value = getattr(self, field)
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise ValueError(f"{field} must be 64 lowercase hex characters")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {field: getattr(self, field) for field in sorted(_REFERENCE_FIELDS)}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CanonicalSignedEvidenceAdmissionReference":
        if not isinstance(value, Mapping) or set(value) != _REFERENCE_FIELDS:
            extras = sorted(set(value) - _REFERENCE_FIELDS) if isinstance(value, Mapping) else []
            missing = sorted(_REFERENCE_FIELDS - set(value)) if isinstance(value, Mapping) else sorted(_REFERENCE_FIELDS)
            raise ValueError(f"invalid signed Evidence/PIT reference; extras={extras}; missing={missing}")
        result = cls(**{field: str(value[field]) for field in _REFERENCE_FIELDS})
        result.validate()
        return result


def build_canonical_signed_evidence_admission_reference(
    *,
    envelope_path: str | Path,
    manifest_path: str | Path,
    rights_record_path: str | Path,
    permission_evidence_path: str | Path,
) -> dict[str, str]:
    """Return a content pointer only; it does not assert that the bundle is admitted."""
    envelope = _read_regular_file(envelope_path, "SIGNED_ADMISSION_ENVELOPE")
    manifest = _read_regular_file(manifest_path, "EVIDENCE_MANIFEST")
    rights = _read_regular_file(rights_record_path, "RIGHTS_RECORD")
    permission = _read_regular_file(permission_evidence_path, "PERMISSION_EVIDENCE")
    return CanonicalSignedEvidenceAdmissionReference(
        envelope_sha256=_sha256(envelope),
        manifest_sha256=_sha256(manifest),
        rights_record_sha256=_sha256(rights),
        permission_evidence_sha256=_sha256(permission),
    ).to_dict()


class CanonicalSignedEvidenceAdmissionResolver(Protocol):
    def resolve_signed_evidence_admission(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
        required_evidence_ids: list[str],
    ) -> dict[str, Any]:
        ...


class FileSystemCanonicalSignedEvidenceAdmissionResolver:
    """Re-verify signatures, rights, exact bytes and PIT from operator-configured paths."""

    def __init__(
        self,
        *,
        envelope_path: str | Path,
        manifest_path: str | Path,
        raw_root: str | Path,
        rights_record_path: str | Path,
        permission_evidence_path: str | Path,
        signer_registry_path: str | Path,
    ) -> None:
        self.envelope_path = Path(envelope_path).expanduser()
        self.manifest_path = Path(manifest_path).expanduser()
        self.raw_root = Path(raw_root).expanduser()
        self.rights_record_path = Path(rights_record_path).expanduser()
        self.permission_evidence_path = Path(permission_evidence_path).expanduser()
        self.signer_registry_path = Path(signer_registry_path).expanduser()

    def resolve_signed_evidence_admission(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
        required_evidence_ids: list[str],
    ) -> dict[str, Any]:
        ref = CanonicalSignedEvidenceAdmissionReference.from_mapping(reference)
        requested = [str(item).strip() for item in required_evidence_ids]
        if not requested or any(not item for item in requested) or len(set(requested)) != len(requested):
            raise ValueError("required_evidence_ids must be non-empty, unique and explicit")

        envelope_bytes = _read_regular_file(self.envelope_path, "SIGNED_ADMISSION_ENVELOPE")
        manifest_bytes = _read_regular_file(self.manifest_path, "EVIDENCE_MANIFEST")
        rights_bytes = _read_regular_file(self.rights_record_path, "RIGHTS_RECORD")
        permission_bytes = _read_regular_file(self.permission_evidence_path, "PERMISSION_EVIDENCE")
        exact_hashes = {
            "envelope": (_sha256(envelope_bytes), ref.envelope_sha256),
            "manifest": (_sha256(manifest_bytes), ref.manifest_sha256),
            "rights_record": (_sha256(rights_bytes), ref.rights_record_sha256),
            "permission_evidence": (_sha256(permission_bytes), ref.permission_evidence_sha256),
        }
        for label, (actual, expected) in exact_hashes.items():
            if actual != expected:
                raise ValueError(f"signed Evidence/PIT {label} bytes differ from reference")

        try:
            envelope = json.loads(envelope_bytes.decode("utf-8"))
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("signed Evidence/PIT bundle contains invalid JSON") from exc
        if not isinstance(envelope, Mapping) or not isinstance(manifest, Mapping):
            raise ValueError("signed Evidence/PIT envelope and manifest must be JSON objects")

        from .canonical_signed_evidence_admission_v01 import verify_signed_admission

        verified = verify_signed_admission(
            envelope,
            manifest_path=self.manifest_path,
            raw_root=self.raw_root,
            rights_record_path=self.rights_record_path,
            permission_evidence_path=self.permission_evidence_path,
            signer_registry_path=self.signer_registry_path,
        )
        if (
            verified.get("status") != "FORMALLY_ADMITTED"
            or verified.get("decision") != "ADMIT"
            or verified.get("core_pit_validation") != "PASS"
        ):
            raise ValueError("signed Evidence/PIT admission is not FORMALLY_ADMITTED")

        expected_identity = {
            "case_id": case_id,
            "market": market,
            "symbol": symbol,
        }
        payload = envelope.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("signed Evidence/PIT payload is invalid")
        for field, expected in expected_identity.items():
            if payload.get(field) != expected or manifest.get(field) != expected:
                raise ValueError(f"signed Evidence/PIT {field} does not match forecast lineage")

        # Preserve the signed cutoff representation exactly, but compare its
        # Shanghai-local calendar day to the canonical forecast cutoff date.
        manifest_cutoff_raw = manifest.get("cutoff_date")
        payload_cutoff_raw = payload.get("cutoff_date")
        if not isinstance(manifest_cutoff_raw, str) or not isinstance(payload_cutoff_raw, str):
            raise ValueError("signed Evidence/PIT cutoff_date must be a date or ISO-8601 timestamp")
        if payload_cutoff_raw != manifest_cutoff_raw:
            raise ValueError("signed Evidence/PIT payload cutoff_date differs from exact manifest cutoff_date")
        try:
            shanghai_tz = timezone(timedelta(hours=8))
            if len(manifest_cutoff_raw) == 10:
                manifest_cutoff_date = date.fromisoformat(manifest_cutoff_raw)
                cutoff_local = datetime.combine(
                    manifest_cutoff_date, datetime.min.time(), tzinfo=shanghai_tz
                )
            else:
                parsed_cutoff = datetime.fromisoformat(
                    manifest_cutoff_raw.replace("Z", "+00:00")
                )
                if parsed_cutoff.tzinfo is None:
                    raise ValueError("timezone is required")
                cutoff_local = parsed_cutoff.astimezone(shanghai_tz)
                manifest_cutoff_date = cutoff_local.date()
        except ValueError as exc:
            raise ValueError("signed Evidence/PIT cutoff_date is invalid") from exc
        if manifest_cutoff_date != cutoff_date:
            raise ValueError("signed Evidence/PIT cutoff_date does not match forecast lineage")
        expected_identity["cutoff_date"] = cutoff_date.isoformat()

        evidence_rows = manifest.get("evidence")
        if not isinstance(evidence_rows, list):
            raise ValueError("admitted Evidence/PIT manifest evidence list is invalid")
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in evidence_rows:
            if not isinstance(row, Mapping):
                continue
            evidence_id = str(row.get("evidence_id") or "").strip()
            if not evidence_id or evidence_id in by_id:
                raise ValueError("admitted Evidence/PIT manifest contains missing or duplicate evidence IDs")
            by_id[evidence_id] = row

        for evidence_id in requested:
            row = by_id.get(evidence_id)
            if row is None:
                raise ValueError(f"forecast or valuation evidence ID is absent from signed manifest: {evidence_id}")
            if row.get("status") != "ADMITTED" or row.get("provenance_class") == "UNKNOWN":
                raise ValueError(f"forecast or valuation evidence ID is not admitted: {evidence_id}")
            if row.get("exact_bytes") is not True:
                raise ValueError(f"forecast or valuation evidence ID lacks exact bytes: {evidence_id}")
            known_at_raw = str(row.get("known_at") or "").strip()
            try:
                if len(known_at_raw) == 10:
                    # Match Core Evidence/PIT semantics: date-only known_at
                    # means 00:00 at the China/HK local timezone.
                    known_date = date.fromisoformat(known_at_raw)
                    known_at = datetime.combine(
                        known_date,
                        datetime.min.time(),
                        tzinfo=cutoff_local.tzinfo,
                    )
                else:
                    known_at = datetime.fromisoformat(known_at_raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"forecast or valuation evidence known_at is invalid: {evidence_id}") from exc
            if known_at.tzinfo is None or known_at.astimezone(cutoff_local.tzinfo) > cutoff_local:
                raise ValueError(f"forecast or valuation evidence is after PIT cutoff: {evidence_id}")

        return {
            "status": "FORMALLY_ADMITTED",
            "decision": "ADMIT",
            "core_pit_validation": "PASS",
            **expected_identity,
            "manifest_sha256": ref.manifest_sha256,
            "evidence_manifest_audit_sha256": str((manifest.get("audit") or {}).get("manifest_sha256") or ""),
            "rights_record_sha256": ref.rights_record_sha256,
            "permission_evidence_sha256": ref.permission_evidence_sha256,
            "envelope_sha256": ref.envelope_sha256,
            "source_class": verified.get("source_class"),
            "rights_status": verified.get("rights_status"),
            "verified_signatures": verified.get("verified_signatures", []),
            "evidence_ids_verified": sorted(requested),
            "formal_evidence_pit_admission_created": True,
            "decision_authority": False,
        }


__all__ = [
    "CanonicalSignedEvidenceAdmissionReference",
    "CanonicalSignedEvidenceAdmissionResolver",
    "FileSystemCanonicalSignedEvidenceAdmissionResolver",
    "build_canonical_signed_evidence_admission_reference",
]
