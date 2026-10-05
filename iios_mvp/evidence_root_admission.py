from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
from typing import Any, Mapping, Protocol

from .p4f_mie_snapshot import P4F_SNAPSHOT_SCHEMA, P4F_VERSION, validate_p4f_snapshot

EVIDENCE_ROOT_ADMISSION_SCHEMA = "IIOS-EVIDENCE-ROOT-ADMISSION-0.1"
ADMITTED_STATUS = "ADMITTED"
P4F_MIE_SNAPSHOT_ROOT_TYPE = "P4F_MIE_SNAPSHOT"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_REFERENCE_FIELDS = {"root_type", "root_id", "content_sha256"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _canonical_json_bytes(value: Any) -> bytes:
    return _canonical_json(value).encode("utf-8")


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON non-finite constant is not allowed: {value}")


@dataclass(frozen=True)
class EvidenceRootReference:
    root_type: str
    root_id: str
    content_sha256: str

    def validate(self) -> None:
        if self.root_type != P4F_MIE_SNAPSHOT_ROOT_TYPE:
            raise ValueError("unsupported evidence root_type")
        if not _SHA256_RE.fullmatch(self.root_id):
            raise ValueError("evidence root_id must be 64 lowercase hex characters")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError("evidence root content_sha256 must be 64 lowercase hex characters")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "root_type": self.root_type,
            "root_id": self.root_id,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvidenceRootReference":
        if not isinstance(value, Mapping):
            raise ValueError("evidence root reference must be an object")
        if set(value) != _ALLOWED_REFERENCE_FIELDS:
            extras = sorted(set(value) - _ALLOWED_REFERENCE_FIELDS)
            missing = sorted(_ALLOWED_REFERENCE_FIELDS - set(value))
            parts = []
            if extras:
                parts.append(f"unsupported fields: {extras}")
            if missing:
                parts.append(f"missing fields: {missing}")
            raise ValueError("invalid evidence root reference; " + "; ".join(parts))
        ref = cls(
            root_type=str(value["root_type"]),
            root_id=str(value["root_id"]),
            content_sha256=str(value["content_sha256"]),
        )
        ref.validate()
        return ref


class EvidenceRootResolver(Protocol):
    def resolve_p4f_snapshot(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ...


def _admission_core(
    *,
    root_id: str,
    content_sha256: str,
    artifact_name: str,
    case_id: str,
    cutoff_date: date,
    admitted_at: datetime,
) -> dict[str, Any]:
    return {
        "admission_schema": EVIDENCE_ROOT_ADMISSION_SCHEMA,
        "status": ADMITTED_STATUS,
        "root_type": P4F_MIE_SNAPSHOT_ROOT_TYPE,
        "root_id": root_id,
        "content_sha256": content_sha256,
        "artifact_name": artifact_name,
        "snapshot_schema": P4F_SNAPSHOT_SCHEMA,
        "p4f_version": P4F_VERSION,
        "case_id": case_id,
        "cutoff_date": cutoff_date.isoformat(),
        "admitted_at": admitted_at.isoformat(),
    }


def _with_admission_hash(core: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(core)
    value["admission_record_hash"] = hashlib.sha256(_canonical_json_bytes(value)).hexdigest()
    return value


def _validate_admission_record(record: Mapping[str, Any]) -> None:
    required = {
        "admission_schema", "status", "root_type", "root_id", "content_sha256",
        "artifact_name", "snapshot_schema", "p4f_version", "case_id",
        "cutoff_date", "admitted_at", "admission_record_hash",
    }
    if set(record) != required:
        raise ValueError("evidence root admission record fields are invalid")
    if record["admission_schema"] != EVIDENCE_ROOT_ADMISSION_SCHEMA:
        raise ValueError("evidence root admission schema/version mismatch")
    if record["status"] != ADMITTED_STATUS:
        raise ValueError("evidence root is not ADMITTED")
    ref = EvidenceRootReference(
        root_type=str(record["root_type"]),
        root_id=str(record["root_id"]),
        content_sha256=str(record["content_sha256"]),
    )
    ref.validate()
    if not isinstance(record["artifact_name"], str) or record["artifact_name"] != f"{ref.root_id}.mie.json":
        raise ValueError("evidence root admission artifact_name is invalid")
    if record["snapshot_schema"] != P4F_SNAPSHOT_SCHEMA or record["p4f_version"] != P4F_VERSION:
        raise ValueError("evidence root admission snapshot schema/version mismatch")
    if not str(record["case_id"]).strip():
        raise ValueError("evidence root admission case_id is required")
    _parse_date(record["cutoff_date"], "admission.cutoff_date")
    try:
        admitted_at = datetime.fromisoformat(str(record["admitted_at"]).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("admission.admitted_at must be ISO datetime") from exc
    if admitted_at.tzinfo is None:
        raise ValueError("admission.admitted_at must be timezone-aware")
    expected = _with_admission_hash({k: record[k] for k in required if k != "admission_record_hash"})
    if expected["admission_record_hash"] != record["admission_record_hash"]:
        raise ValueError("evidence root admission record hash mismatch")


class FileSystemEvidenceRootRegistry:
    """Trusted canonical store for admitted immutable evidence-root artifacts."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.artifacts_dir = self.root / "p4f_mie_snapshots"
        self.admissions_dir = self.root / "admissions"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.admissions_dir.mkdir(parents=True, exist_ok=True)

    def _artifact_path(self, root_id: str) -> Path:
        return self.artifacts_dir / f"{root_id}.mie.json"

    def _admission_path(self, root_id: str) -> Path:
        return self.admissions_dir / f"{root_id}.admission.json"

    def admit_p4f_snapshot(
        self,
        snapshot: Mapping[str, Any],
        *,
        admitted_at: datetime | None = None,
    ) -> EvidenceRootReference:
        validate_p4f_snapshot(snapshot)
        root_id = str(snapshot["snapshot_hash"])
        if not _SHA256_RE.fullmatch(root_id):
            raise ValueError("P4-F snapshot_hash must be 64 lowercase hex characters")
        cutoff = _parse_date(snapshot["cutoff_date"], "cutoff_date")
        if admitted_at is None:
            admitted_at = datetime.now(timezone.utc)
        if admitted_at.tzinfo is None:
            raise ValueError("admitted_at must be timezone-aware")

        artifact_bytes = _pretty_json_bytes(snapshot)
        content_sha256 = _sha256_bytes(artifact_bytes)
        artifact_name = f"{root_id}.mie.json"
        admission = _with_admission_hash(
            _admission_core(
                root_id=root_id,
                content_sha256=content_sha256,
                artifact_name=artifact_name,
                case_id=str(snapshot["case_id"]),
                cutoff_date=cutoff,
                admitted_at=admitted_at,
            )
        )
        artifact_path = self._artifact_path(root_id)
        admission_path = self._admission_path(root_id)

        artifact_exists = artifact_path.exists()
        admission_exists = admission_path.exists()
        if artifact_exists != admission_exists:
            raise ValueError("evidence root registry contains a partial admission; refusing to repair")
        if artifact_exists:
            existing_bytes = artifact_path.read_bytes()
            if existing_bytes != artifact_bytes:
                raise ValueError("evidence root artifact already exists with different bytes")
            try:
                existing = json.loads(
                    admission_path.read_bytes().decode("utf-8"),
                    parse_constant=_reject_json_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError("existing evidence root admission record is unreadable") from exc
            if _canonical_json(existing) != _canonical_json(admission):
                raise ValueError("existing evidence root admission record conflicts with requested admission")
            return EvidenceRootReference(P4F_MIE_SNAPSHOT_ROOT_TYPE, root_id, content_sha256)

        try:
            with artifact_path.open("xb") as handle:
                handle.write(artifact_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            with admission_path.open("xb") as handle:
                handle.write(_pretty_json_bytes(admission))
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise ValueError("evidence root admission raced with another writer; retry after re-read") from exc
        return EvidenceRootReference(P4F_MIE_SNAPSHOT_ROOT_TYPE, root_id, content_sha256)

    def resolve_p4f_snapshot(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = EvidenceRootReference.from_mapping(reference)
        if not case_id:
            raise ValueError("case_id is required when resolving evidence root")

        admission_path = self._admission_path(ref.root_id)
        artifact_path = self._artifact_path(ref.root_id)
        if not admission_path.exists() or not artifact_path.exists():
            raise ValueError("evidence root is unknown or not admitted")
        try:
            admission = json.loads(
                admission_path.read_bytes().decode("utf-8"),
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("evidence root admission record is unreadable") from exc
        if not isinstance(admission, dict):
            raise ValueError("evidence root admission record must be an object")
        _validate_admission_record(admission)
        if admission["root_id"] != ref.root_id or admission["content_sha256"] != ref.content_sha256:
            raise ValueError("evidence root reference does not match admitted root")
        if admission["case_id"] != case_id:
            raise ValueError("evidence root case_id mismatch")
        if _parse_date(admission["cutoff_date"], "admission.cutoff_date") != cutoff_date:
            raise ValueError("evidence root cutoff_date mismatch")

        artifact_bytes = artifact_path.read_bytes()
        if _sha256_bytes(artifact_bytes) != admission["content_sha256"]:
            raise ValueError("evidence root artifact content hash mismatch")
        try:
            snapshot = json.loads(
                artifact_bytes.decode("utf-8"),
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("evidence root artifact is unreadable JSON") from exc
        if not isinstance(snapshot, dict):
            raise ValueError("evidence root artifact must be a JSON object")
        validate_p4f_snapshot(snapshot)
        if snapshot["snapshot_hash"] != ref.root_id:
            raise ValueError("evidence root artifact snapshot_hash mismatch")
        if snapshot["case_id"] != case_id:
            raise ValueError("evidence root artifact case_id mismatch")
        if _parse_date(snapshot["cutoff_date"], "snapshot.cutoff_date") != cutoff_date:
            raise ValueError("evidence root artifact cutoff_date mismatch")
        return snapshot


class InMemoryEvidenceRootRegistry:
    """Deterministic test/runtime-double implementation of the resolver contract."""

    def __init__(self) -> None:
        self._artifacts: dict[str, tuple[bytes, dict[str, Any]]] = {}

    def admit_p4f_snapshot(
        self,
        snapshot: Mapping[str, Any],
        *,
        admitted_at: datetime | None = None,
    ) -> EvidenceRootReference:
        validate_p4f_snapshot(snapshot)
        root_id = str(snapshot["snapshot_hash"])
        cutoff = _parse_date(snapshot["cutoff_date"], "cutoff_date")
        if admitted_at is None:
            admitted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        if admitted_at.tzinfo is None:
            raise ValueError("admitted_at must be timezone-aware")
        artifact_bytes = _pretty_json_bytes(snapshot)
        content_sha256 = _sha256_bytes(artifact_bytes)
        admission = _with_admission_hash(
            _admission_core(
                root_id=root_id,
                content_sha256=content_sha256,
                artifact_name=f"{root_id}.mie.json",
                case_id=str(snapshot["case_id"]),
                cutoff_date=cutoff,
                admitted_at=admitted_at,
            )
        )
        existing = self._artifacts.get(root_id)
        if existing is not None:
            existing_bytes, existing_admission = existing
            if existing_bytes != artifact_bytes or _canonical_json(existing_admission) != _canonical_json(admission):
                raise ValueError("evidence root already admitted with different bytes")
        else:
            self._artifacts[root_id] = (artifact_bytes, admission)
        return EvidenceRootReference(P4F_MIE_SNAPSHOT_ROOT_TYPE, root_id, content_sha256)

    def resolve_p4f_snapshot(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = EvidenceRootReference.from_mapping(reference)
        item = self._artifacts.get(ref.root_id)
        if item is None:
            raise ValueError("evidence root is unknown or not admitted")
        artifact_bytes, admission = item
        _validate_admission_record(admission)
        if admission["root_id"] != ref.root_id or admission["content_sha256"] != ref.content_sha256:
            raise ValueError("evidence root reference does not match admitted root")
        if admission["case_id"] != case_id:
            raise ValueError("evidence root case_id mismatch")
        if _parse_date(admission["cutoff_date"], "admission.cutoff_date") != cutoff_date:
            raise ValueError("evidence root cutoff_date mismatch")
        if _sha256_bytes(artifact_bytes) != ref.content_sha256:
            raise ValueError("evidence root artifact content hash mismatch")
        snapshot = json.loads(artifact_bytes.decode("utf-8"), parse_constant=_reject_json_constant)
        if not isinstance(snapshot, dict):
            raise ValueError("evidence root artifact must be a JSON object")
        validate_p4f_snapshot(snapshot)
        if snapshot["snapshot_hash"] != ref.root_id:
            raise ValueError("evidence root artifact snapshot_hash mismatch")
        if snapshot["case_id"] != case_id:
            raise ValueError("evidence root artifact case_id mismatch")
        if _parse_date(snapshot["cutoff_date"], "snapshot.cutoff_date") != cutoff_date:
            raise ValueError("evidence root artifact cutoff_date mismatch")
        return snapshot


__all__ = [
    "ADMITTED_STATUS",
    "EVIDENCE_ROOT_ADMISSION_SCHEMA",
    "EvidenceRootReference",
    "EvidenceRootResolver",
    "FileSystemEvidenceRootRegistry",
    "InMemoryEvidenceRootRegistry",
    "P4F_MIE_SNAPSHOT_ROOT_TYPE",
]
