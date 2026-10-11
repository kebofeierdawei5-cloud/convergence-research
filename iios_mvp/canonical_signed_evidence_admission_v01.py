from __future__ import annotations

"""Deterministic, cryptographically signed Evidence/PIT admission records.

This module has no LLM/provider dependency. It does not grant data rights: an
ADMIT decision requires a separate rights adjudication bound to the exact bytes
of an applicable permission instrument and to the exact Evidence manifest.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical_evidence_admission_v01 import validate_company_evidence_manifest

SIGNED_ADMISSION_SCHEMA = "IIOS-SIGNED-EVIDENCE-PIT-ADMISSION-0.1"
SIGNER_REGISTRY_SCHEMA = "IIOS-EVIDENCE-ADMISSION-SIGNER-REGISTRY-0.1"
RIGHTS_SCHEMA = "IIOS-SOURCE-USE-RIGHTS-ADJUDICATION-0.1"
_REQUIRED_PRIVATE_USES = {"PRIVATE_STORAGE", "LOCAL_COMPUTATION", "INTERNAL_DISPLAY"}
_HEX64 = set("0123456789abcdef")
_ALLOWED_SOURCE_CLASSES = {
    "EXCHANGE_MARKET_DATA",
    "VENDOR_MARKET_DATA",
    "PUBLIC_COMPANY_DISCLOSURE",
    "OPERATOR_ATTESTED_MARKET_DATA",
}
_ALLOWED_RIGHTS_STATUS = {"ALLOWED", "LIMITED", "UNKNOWN", "DENIED"}
_ADMIT_BASIS_BY_SOURCE_CLASS = {
    "EXCHANGE_MARKET_DATA": {"EXPLICIT_WRITTEN_PERMISSION", "LICENSED_VENDOR_CONTRACT"},
    "VENDOR_MARKET_DATA": {"LICENSED_VENDOR_CONTRACT", "EXPLICIT_WRITTEN_PERMISSION"},
    "PUBLIC_COMPANY_DISCLOSURE": {"OFFICIAL_TERMS_REVIEWED", "EXPLICIT_WRITTEN_PERMISSION"},
    # Operator attestation is not a substitute for source-vintage verification or
    # a rights instrument. It cannot make a market-price record formally admitted.
    "OPERATOR_ATTESTED_MARKET_DATA": set(),
}


class SignedAdmissionError(ValueError):
    """Raised whenever a signature, trust, source-rights or integrity gate fails."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _HEX64 for ch in value)
    )


def _read_json(path: str | Path, label: str) -> tuple[dict[str, Any], bytes]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise SignedAdmissionError(f"{label}_MUST_BE_REGULAR_FILE")
    raw = source.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SignedAdmissionError(f"{label}_INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise SignedAdmissionError(f"{label}_MUST_BE_OBJECT")
    return value, raw


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SignedAdmissionError(f"{label}_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SignedAdmissionError(f"{label}_INVALID_ISO8601") from exc
    if parsed.tzinfo is None:
        raise SignedAdmissionError(f"{label}_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _load_registry(path: str | Path) -> dict[str, Any]:
    registry, _ = _read_json(path, "SIGNER_REGISTRY")
    if registry.get("schema_version") != SIGNER_REGISTRY_SCHEMA:
        raise SignedAdmissionError("SIGNER_REGISTRY_SCHEMA_INVALID")
    if not isinstance(registry.get("signers"), list):
        raise SignedAdmissionError("SIGNER_REGISTRY_SIGNERS_REQUIRED")
    return registry


def _find_trusted_signer(
    registry: Mapping[str, Any],
    signer_key_id: str,
    signed_at: str,
    case_id: str,
) -> tuple[dict[str, Any], bytes]:
    at = _timestamp(signed_at, "SIGNED_AT")
    matches = [
        item for item in registry.get("signers", [])
        if isinstance(item, Mapping) and item.get("signer_key_id") == signer_key_id
    ]
    if len(matches) != 1:
        raise SignedAdmissionError("SIGNER_KEY_ID_NOT_UNIQUELY_REGISTERED")
    entry = dict(matches[0])
    if entry.get("status") != "ACTIVE":
        raise SignedAdmissionError("SIGNER_NOT_ACTIVE")
    roles = entry.get("roles")
    if not isinstance(roles, list) or not roles:
        raise SignedAdmissionError("SIGNER_ROLES_REQUIRED")
    scopes = entry.get("case_scopes")
    if not isinstance(scopes, list) or not (case_id in scopes or "*" in scopes):
        raise SignedAdmissionError("SIGNER_CASE_SCOPE_DENIED")
    valid_from = _timestamp(entry.get("valid_from"), "SIGNER_VALID_FROM")
    if at < valid_from:
        raise SignedAdmissionError("SIGNER_NOT_YET_VALID")
    valid_until_raw = entry.get("valid_until")
    if valid_until_raw:
        if at > _timestamp(valid_until_raw, "SIGNER_VALID_UNTIL"):
            raise SignedAdmissionError("SIGNER_EXPIRED")
    revoked_at_raw = entry.get("revoked_at")
    if revoked_at_raw and at >= _timestamp(revoked_at_raw, "SIGNER_REVOKED_AT"):
        raise SignedAdmissionError("SIGNATURE_AFTER_SIGNER_REVOCATION")
    public_key_b64 = entry.get("public_key_b64")
    try:
        public_key = base64.b64decode(public_key_b64, validate=True)
    except (TypeError, ValueError) as exc:
        raise SignedAdmissionError("SIGNER_PUBLIC_KEY_INVALID_BASE64") from exc
    if len(public_key) != 32:
        raise SignedAdmissionError("SIGNER_PUBLIC_KEY_LENGTH_INVALID")
    return entry, public_key


def _validate_rights_record(
    rights: Mapping[str, Any],
    *,
    case_id: str,
    decision: str,
    signed_at: str,
    permission_evidence_sha256: str | None,
) -> tuple[str, str, list[str], list[str]]:
    if rights.get("schema_version") != RIGHTS_SCHEMA:
        raise SignedAdmissionError("RIGHTS_RECORD_SCHEMA_INVALID")
    if rights.get("case_id") != case_id:
        raise SignedAdmissionError("RIGHTS_RECORD_CASE_MISMATCH")
    source_class = rights.get("source_class")
    if source_class not in _ALLOWED_SOURCE_CLASSES:
        raise SignedAdmissionError("RIGHTS_SOURCE_CLASS_INVALID")
    status = rights.get("status")
    if status not in _ALLOWED_RIGHTS_STATUS:
        raise SignedAdmissionError("RIGHTS_STATUS_INVALID")
    basis_kind = rights.get("basis_kind")
    allowed_uses = rights.get("allowed_uses", [])
    if not isinstance(allowed_uses, list) or any(not isinstance(x, str) for x in allowed_uses):
        raise SignedAdmissionError("RIGHTS_ALLOWED_USES_INVALID")
    required_roles = rights.get("required_signer_roles")
    if (
        not isinstance(required_roles, list) or not required_roles
        or any(not isinstance(role, str) or not role.strip() for role in required_roles)
        or len(set(required_roles)) != len(required_roles)
    ):
        raise SignedAdmissionError("REQUIRED_SIGNER_ROLES_INVALID")
    if "EVIDENCE_ADMISSION_SIGNER" not in required_roles:
        raise SignedAdmissionError("EVIDENCE_ADMISSION_SIGNER_ROLE_REQUIRED")

    if decision == "ADMIT":
        if status != "ALLOWED":
            raise SignedAdmissionError("ADMISSION_BLOCKED_RIGHTS_NOT_ALLOWED")
        if source_class == "OPERATOR_ATTESTED_MARKET_DATA":
            raise SignedAdmissionError("OPERATOR_ATTESTED_PRICE_CANNOT_BE_SOURCE_ADMITTED")
        permitted_bases = _ADMIT_BASIS_BY_SOURCE_CLASS[source_class]
        if basis_kind not in permitted_bases:
            raise SignedAdmissionError("RIGHTS_BASIS_INSUFFICIENT_FOR_SOURCE_CLASS")
        if not _REQUIRED_PRIVATE_USES.issubset(set(allowed_uses)):
            raise SignedAdmissionError("REQUIRED_PRIVATE_RESEARCH_USES_NOT_GRANTED")
        if not _is_sha256(permission_evidence_sha256):
            raise SignedAdmissionError("PERMISSION_EVIDENCE_HASH_REQUIRED")
        if rights.get("permission_evidence_sha256") != permission_evidence_sha256:
            raise SignedAdmissionError("PERMISSION_EVIDENCE_HASH_MISMATCH")
        expires_at = rights.get("expires_at")
        if expires_at and _timestamp(signed_at, "SIGNED_AT") > _timestamp(expires_at, "RIGHTS_EXPIRES_AT"):
            raise SignedAdmissionError("RIGHTS_PERMISSION_EXPIRED")
        instrument_id = rights.get("permission_instrument_id")
        if not isinstance(instrument_id, str) or not instrument_id.strip():
            raise SignedAdmissionError("PERMISSION_INSTRUMENT_ID_REQUIRED")
    return str(source_class), str(status), list(allowed_uses), list(required_roles)


def _signature_message(payload: Mapping[str, Any], signer_key_id: str, signed_at: str) -> bytes:
    return _canonical_bytes({
        "payload": dict(payload),
        "signer_key_id": signer_key_id,
        "signed_at": signed_at,
    })


def _validate_candidate_manifest(
    manifest: Mapping[str, Any],
    raw_root: str | Path,
    decision: str,
) -> None:
    if decision != "ADMIT":
        return
    errors = validate_company_evidence_manifest(manifest, raw_root=raw_root, require_raw_verification=True)
    if errors:
        raise SignedAdmissionError("CORE_PIT_VALIDATION_FAILED:" + "|".join(errors))


def build_admission_payload(
    *,
    manifest_path: str | Path,
    raw_root: str | Path,
    rights_record_path: str | Path,
    permission_evidence_path: str | Path | None,
    decision: str,
    signed_at: str,
) -> dict[str, Any]:
    """Build the signed payload; ADMIT is impossible without Core/PIT and rights PASS."""
    if decision not in {"ADMIT", "BLOCK"}:
        raise SignedAdmissionError("DECISION_MUST_BE_ADMIT_OR_BLOCK")
    _timestamp(signed_at, "SIGNED_AT")
    manifest, manifest_bytes = _read_json(manifest_path, "EVIDENCE_MANIFEST")
    rights, rights_bytes = _read_json(rights_record_path, "RIGHTS_RECORD")
    case_id = manifest.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise SignedAdmissionError("MANIFEST_CASE_ID_REQUIRED")
    _validate_candidate_manifest(manifest, raw_root, decision)

    permission_sha: str | None = None
    if permission_evidence_path is not None:
        permission_path = Path(permission_evidence_path)
        if permission_path.is_symlink() or not permission_path.is_file():
            raise SignedAdmissionError("PERMISSION_EVIDENCE_MUST_BE_REGULAR_FILE")
        permission_sha = _sha256(permission_path.read_bytes())
    elif decision == "ADMIT":
        raise SignedAdmissionError("PERMISSION_EVIDENCE_FILE_REQUIRED")

    source_class, rights_status, allowed_uses, required_roles = _validate_rights_record(
        rights,
        case_id=case_id,
        decision=decision,
        signed_at=signed_at,
        permission_evidence_sha256=permission_sha,
    )
    return {
        "schema_version": SIGNED_ADMISSION_SCHEMA,
        "case_id": case_id,
        "market": manifest.get("market"),
        "symbol": manifest.get("symbol"),
        "cutoff_date": manifest.get("cutoff_date"),
        "decision": decision,
        "manifest_sha256": _sha256(manifest_bytes),
        "rights_record_sha256": _sha256(rights_bytes),
        "permission_evidence_sha256": permission_sha,
        "source_class": source_class,
        "rights_status": rights_status,
        "rights_basis_kind": rights.get("basis_kind"),
        "allowed_uses": allowed_uses,
        "required_signer_roles": required_roles,
        "signed_payload_created_at": signed_at,
    }


def generate_keypair(private_key_path: str | Path, public_key_path: str | Path) -> dict[str, str]:
    """Create a dedicated keypair. The private key is never returned or printed."""
    private_path = Path(private_key_path).expanduser()
    public_path = Path(public_key_path).expanduser()
    repository_root = Path(__file__).resolve().parents[1]
    for candidate, label in ((private_path, "PRIVATE"), (public_path, "PUBLIC")):
        if candidate.is_symlink():
            raise SignedAdmissionError(f"{label}_KEY_PATH_MUST_NOT_BE_SYMLINK")
        resolved = candidate.resolve(strict=False)
        if label == "PRIVATE" and (resolved == repository_root or repository_root in resolved.parents):
            raise SignedAdmissionError("PRIVATE_KEY_MUST_BE_OUTSIDE_REPOSITORY")
        if candidate.exists():
            raise SignedAdmissionError(f"{label}_KEY_PATH_ALREADY_EXISTS")
    if private_path.resolve() == public_path.resolve():
        raise SignedAdmissionError("KEY_PATHS_MUST_DIFFER")
    private_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    public_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    private_fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(private_fd, "w", encoding="ascii") as handle:
            handle.write(base64.b64encode(private_raw).decode("ascii") + "\n")
    except Exception:
        try:
            private_path.unlink(missing_ok=True)
        finally:
            raise
    public_doc = {
        "algorithm": "Ed25519",
        "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
        "public_key_sha256": _sha256(public_raw),
    }
    public_fd = os.open(public_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(public_fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(public_doc, ensure_ascii=False, indent=2) + "\n")
    os.chmod(private_path, 0o600)
    return {"public_key_sha256": public_doc["public_key_sha256"], "algorithm": "Ed25519"}


def add_signature(
    envelope: Mapping[str, Any],
    *,
    signer_registry_path: str | Path,
    signer_key_id: str,
    private_key_path: str | Path,
    signed_at: str,
) -> dict[str, Any]:
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("schema_version") != SIGNED_ADMISSION_SCHEMA:
        raise SignedAdmissionError("SIGNED_ADMISSION_PAYLOAD_INVALID")
    _timestamp(signed_at, "SIGNED_AT")
    registry = _load_registry(signer_registry_path)
    signer, registered_public_raw = _find_trusted_signer(
        registry, signer_key_id, signed_at, str(payload.get("case_id", ""))
    )
    if Path(private_key_path).is_symlink():
        raise SignedAdmissionError("PRIVATE_KEY_PATH_MUST_NOT_BE_SYMLINK")
    private_path = Path(private_key_path).expanduser().resolve(strict=True)
    repository_root = Path(__file__).resolve().parents[1]
    if private_path == repository_root or repository_root in private_path.parents:
        raise SignedAdmissionError("PRIVATE_KEY_MUST_BE_OUTSIDE_REPOSITORY")
    mode = stat.S_IMODE(private_path.stat().st_mode)
    if os.name != "nt" and mode & 0o077:
        raise SignedAdmissionError("PRIVATE_KEY_PERMISSIONS_TOO_OPEN")
    try:
        private_raw = base64.b64decode(private_path.read_text(encoding="ascii").strip(), validate=True)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SignedAdmissionError("PRIVATE_KEY_INVALID_BASE64") from exc
    if len(private_raw) != 32:
        raise SignedAdmissionError("PRIVATE_KEY_LENGTH_INVALID")
    private_key = Ed25519PrivateKey.from_private_bytes(private_raw)
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if public_raw != registered_public_raw:
        raise SignedAdmissionError("PRIVATE_KEY_DOES_NOT_MATCH_REGISTERED_SIGNER")
    signatures = envelope.get("signatures", [])
    if not isinstance(signatures, list):
        raise SignedAdmissionError("SIGNATURES_MUST_BE_LIST")
    if any(isinstance(sig, Mapping) and sig.get("signer_key_id") == signer_key_id for sig in signatures):
        raise SignedAdmissionError("SIGNER_ALREADY_SIGNED")
    message = _signature_message(payload, signer_key_id, signed_at)
    signed = {
        "signer_key_id": signer_key_id,
        "signed_at": signed_at,
        "signature_b64": base64.b64encode(private_key.sign(message)).decode("ascii"),
    }
    result = dict(envelope)
    result["schema_version"] = SIGNED_ADMISSION_SCHEMA
    result["signatures"] = list(signatures) + [signed]
    return result


def verify_signed_admission(
    envelope: Mapping[str, Any],
    *,
    manifest_path: str | Path,
    raw_root: str | Path,
    rights_record_path: str | Path,
    permission_evidence_path: str | Path | None,
    signer_registry_path: str | Path,
) -> dict[str, Any]:
    if envelope.get("schema_version") != SIGNED_ADMISSION_SCHEMA:
        raise SignedAdmissionError("SIGNED_ADMISSION_SCHEMA_INVALID")
    payload = envelope.get("payload")
    signatures = envelope.get("signatures")
    if not isinstance(payload, Mapping) or not isinstance(signatures, list):
        raise SignedAdmissionError("SIGNED_ADMISSION_SHAPE_INVALID")
    decision = payload.get("decision")
    if decision not in {"ADMIT", "BLOCK"}:
        raise SignedAdmissionError("DECISION_INVALID")
    manifest, manifest_bytes = _read_json(manifest_path, "EVIDENCE_MANIFEST")
    rights, rights_bytes = _read_json(rights_record_path, "RIGHTS_RECORD")
    if _sha256(manifest_bytes) != payload.get("manifest_sha256"):
        raise SignedAdmissionError("MANIFEST_BYTES_CHANGED_AFTER_SIGNING")
    if _sha256(rights_bytes) != payload.get("rights_record_sha256"):
        raise SignedAdmissionError("RIGHTS_RECORD_BYTES_CHANGED_AFTER_SIGNING")
    if manifest.get("case_id") != payload.get("case_id") or rights.get("case_id") != payload.get("case_id"):
        raise SignedAdmissionError("CASE_ID_MISMATCH")
    _validate_candidate_manifest(manifest, raw_root, str(decision))
    permission_sha: str | None = None
    if permission_evidence_path is not None:
        permission_path = Path(permission_evidence_path)
        if permission_path.is_symlink() or not permission_path.is_file():
            raise SignedAdmissionError("PERMISSION_EVIDENCE_MUST_BE_REGULAR_FILE")
        permission_sha = _sha256(permission_path.read_bytes())
    elif decision == "ADMIT":
        raise SignedAdmissionError("PERMISSION_EVIDENCE_FILE_REQUIRED")
    if permission_sha != payload.get("permission_evidence_sha256"):
        raise SignedAdmissionError("PERMISSION_EVIDENCE_BYTES_CHANGED_AFTER_SIGNING")
    source_class, rights_status, allowed_uses, required_roles = _validate_rights_record(
        rights,
        case_id=str(payload.get("case_id")),
        decision=str(decision),
        signed_at=str(payload.get("signed_payload_created_at")),
        permission_evidence_sha256=permission_sha,
    )
    expected_fields = {
        "source_class": source_class,
        "rights_status": rights_status,
        "rights_basis_kind": rights.get("basis_kind"),
        "allowed_uses": allowed_uses,
        "required_signer_roles": required_roles,
        "market": manifest.get("market"),
        "symbol": manifest.get("symbol"),
        "cutoff_date": manifest.get("cutoff_date"),
    }
    for key, expected in expected_fields.items():
        if payload.get(key) != expected:
            raise SignedAdmissionError("SIGNED_PAYLOAD_FIELD_MISMATCH:" + key)

    registry = _load_registry(signer_registry_path)
    seen_keys: set[str] = set()
    covered_roles: set[str] = set()
    roles_by_signer: dict[str, set[str]] = {}
    signature_results = []
    for signature in signatures:
        if not isinstance(signature, Mapping):
            raise SignedAdmissionError("SIGNATURE_ENTRY_INVALID")
        key_id = signature.get("signer_key_id")
        signed_at = signature.get("signed_at")
        if not isinstance(key_id, str) or key_id in seen_keys:
            raise SignedAdmissionError("SIGNER_DUPLICATE_OR_INVALID")
        seen_keys.add(key_id)
        signer, public_raw = _find_trusted_signer(registry, key_id, str(signed_at), str(payload.get("case_id")))
        if decision == "ADMIT" and rights.get("expires_at"):
            if _timestamp(str(signed_at), "SIGNED_AT") > _timestamp(rights.get("expires_at"), "RIGHTS_EXPIRES_AT"):
                raise SignedAdmissionError("RIGHTS_PERMISSION_EXPIRED_AT_SIGNATURE")
        try:
            signature_raw = base64.b64decode(signature.get("signature_b64"), validate=True)
        except (TypeError, ValueError) as exc:
            raise SignedAdmissionError("SIGNATURE_INVALID_BASE64") from exc
        try:
            Ed25519PublicKey.from_public_bytes(public_raw).verify(
                signature_raw, _signature_message(payload, key_id, str(signed_at))
            )
        except Exception as exc:
            raise SignedAdmissionError("SIGNATURE_VERIFICATION_FAILED:" + key_id) from exc
        signer_roles = {str(role) for role in signer.get("roles", [])}
        roles_by_signer[key_id] = signer_roles
        covered_roles.update(signer_roles)
        signature_results.append({"signer_key_id": key_id, "verified": True})
    missing_roles = sorted(set(required_roles) - covered_roles)
    if "INDEPENDENT_REVIEWER" in required_roles:
        admission_signers = {key for key, roles in roles_by_signer.items() if "EVIDENCE_ADMISSION_SIGNER" in roles}
        independent_reviewers = {key for key, roles in roles_by_signer.items() if "INDEPENDENT_REVIEWER" in roles}
        if not admission_signers or not independent_reviewers or admission_signers.intersection(independent_reviewers):
            missing_roles = sorted(set(missing_roles) | {"INDEPENDENT_REVIEWER_DISTINCT_SIGNER"})
    if decision == "ADMIT" and missing_roles:
        status = "SIGNATURES_PENDING"
    elif decision == "ADMIT":
        status = "FORMALLY_ADMITTED"
    elif missing_roles:
        status = "SIGNED_BLOCK_DECISION_SIGNATURES_PENDING"
    else:
        status = "FORMALLY_BLOCKED"
    return {
        "status": status,
        "case_id": payload.get("case_id"),
        "decision": decision,
        "manifest_sha256": payload.get("manifest_sha256"),
        "rights_record_sha256": payload.get("rights_record_sha256"),
        "verified_signatures": signature_results,
        "required_signer_roles": required_roles,
        "missing_signer_roles": missing_roles,
        "core_pit_validation": "PASS" if decision == "ADMIT" else "NOT_REQUIRED_FOR_BLOCK",
        "rights_status": rights_status,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IIOS signed Evidence/PIT admission; no LLM dependency.")
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("generate-keypair")
    gen.add_argument("--private-key-out", required=True)
    gen.add_argument("--public-key-out", required=True)
    sign = commands.add_parser("sign")
    sign.add_argument("--manifest", required=True)
    sign.add_argument("--raw-root", required=True)
    sign.add_argument("--rights-record", required=True)
    sign.add_argument("--permission-evidence")
    sign.add_argument("--registry", required=True)
    sign.add_argument("--signer-key-id", required=True)
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--signed-at", required=True)
    sign.add_argument("--decision", required=True, choices=("ADMIT", "BLOCK"))
    sign.add_argument("--out", required=True)
    sign.add_argument("--existing-envelope")
    verify = commands.add_parser("verify")
    verify.add_argument("--envelope", required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--raw-root", required=True)
    verify.add_argument("--rights-record", required=True)
    verify.add_argument("--permission-evidence")
    verify.add_argument("--registry", required=True)
    verify.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate-keypair":
            result = generate_keypair(args.private_key_out, args.public_key_out)
        elif args.command == "sign":
            if args.existing_envelope:
                envelope, _ = _read_json(args.existing_envelope, "EXISTING_ENVELOPE")
                existing_payload = envelope.get("payload")
                if not isinstance(existing_payload, Mapping):
                    raise SignedAdmissionError("EXISTING_ENVELOPE_PAYLOAD_INVALID")
                payload_created_at = existing_payload.get("signed_payload_created_at")
                if not isinstance(payload_created_at, str):
                    raise SignedAdmissionError("EXISTING_ENVELOPE_CREATED_AT_MISSING")
            else:
                envelope = {"schema_version": SIGNED_ADMISSION_SCHEMA, "payload": {}, "signatures": []}
                payload_created_at = args.signed_at
            payload = build_admission_payload(
                manifest_path=args.manifest,
                raw_root=args.raw_root,
                rights_record_path=args.rights_record,
                permission_evidence_path=args.permission_evidence,
                decision=args.decision,
                signed_at=payload_created_at,
            )
            if args.existing_envelope:
                if existing_payload != payload:
                    raise SignedAdmissionError("EXISTING_ENVELOPE_PAYLOAD_MISMATCH")
            else:
                envelope["payload"] = payload
            result = add_signature(
                envelope, signer_registry_path=args.registry, signer_key_id=args.signer_key_id,
                private_key_path=args.private_key, signed_at=args.signed_at,
            )
            out_path = Path(args.out)
            if out_path.is_symlink():
                raise SignedAdmissionError("OUTPUT_PATH_MUST_NOT_BE_SYMLINK")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
            result = {"status": "SIGNATURE_APPENDED", "out": str(out_path), "signer_key_id": args.signer_key_id}
        else:
            envelope, _ = _read_json(args.envelope, "SIGNED_ENVELOPE")
            result = verify_signed_admission(
                envelope, manifest_path=args.manifest, raw_root=args.raw_root,
                rights_record_path=args.rights_record, permission_evidence_path=args.permission_evidence,
                signer_registry_path=args.registry,
            )
            if args.out:
                out_path = Path(args.out)
                if out_path.is_symlink():
                    raise SignedAdmissionError("OUTPUT_PATH_MUST_NOT_BE_SYMLINK")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with out_path.open("x", encoding="utf-8") as handle:
                    json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2)
                    handle.write("\n")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (SignedAdmissionError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
