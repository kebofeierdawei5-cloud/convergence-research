from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from iios_mvp.canonical_signed_evidence_admission_v01 import (
    RIGHTS_SCHEMA,
    SIGNED_ADMISSION_SCHEMA,
    SIGNER_REGISTRY_SCHEMA,
    SignedAdmissionError,
    add_signature,
    generate_keypair,
    prepare_signer_enrollment_request,
    build_admission_payload,
    verify_signed_admission,
)
from iios_mvp.canonical_evidence_admission_v01 import REQUIRED_FIELD_GROUPS


CASE_ID = "RC-CN-A-TEST-20261009"
SIGNED_AT = "2026-10-11T18:00:00+08:00"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _make_manifest(tmp_path: Path) -> tuple[Path, Path, str]:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    raw = b"test evidence bytes; no actual exchange data\n"
    (raw_root / "source.bin").write_bytes(raw)
    raw_sha = _sha(raw)

    evidence = []
    raw_artifacts = []
    for idx, group in enumerate(REQUIRED_FIELD_GROUPS, start=1):
        evidence_id = f"TEST-E-{idx:02d}"
        evidence.append({
            "evidence_id": evidence_id,
            "subject_id": CASE_ID,
            "field_id": group + ".test_fact",
            "claim_type": "TEST",
            "known_at": "2026-10-08T14:00:00+08:00",
            "retrieved_at": "2026-10-10T00:00:00+08:00",
            "source_ref": "https://example.invalid/test-source",
            "artifact_id": "TEST-ARTIFACT",
            "content_sha256": raw_sha,
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
        })
        raw_artifacts.append({
            "evidence_id": evidence_id,
            "relative_path": "source.bin",
            "expected_sha256": raw_sha,
            "expected_size_bytes": len(raw),
        })

    body = {
        "schema_version": "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1",
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "000001",
        "company": "Test Issuer",
        "cutoff_date": "2026-10-09",
        "required_field_groups": list(REQUIRED_FIELD_GROUPS),
        "evidence": evidence,
        "raw_artifacts": raw_artifacts,
    }
    manifest = {
        **body,
        "audit": {"manifest_sha256": _sha(_canonical(body))},
        "status": "PASS",
        "validation_errors": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest_path, raw_root, raw_sha


def _write_rights(tmp_path: Path, *, source_class="EXCHANGE_MARKET_DATA", status="ALLOWED",
                  basis_kind="EXPLICIT_WRITTEN_PERMISSION", required_roles=None):
    permission_path = tmp_path / "permission-instrument.bin"
    permission_path.write_bytes(b"fixture permission instrument bytes; not a real license\n")
    rights = {
        "schema_version": RIGHTS_SCHEMA,
        "case_id": CASE_ID,
        "source_class": source_class,
        "status": status,
        "basis_kind": basis_kind,
        "permission_instrument_id": "TEST-LICENSE-001",
        "permission_evidence_sha256": _sha(permission_path.read_bytes()),
        "allowed_uses": ["PRIVATE_STORAGE", "LOCAL_COMPUTATION", "INTERNAL_DISPLAY"],
        "required_signer_roles": required_roles or ["EVIDENCE_ADMISSION_SIGNER"],
        "expires_at": "2027-10-11T00:00:00+00:00",
    }
    rights_path = tmp_path / "rights.json"
    rights_path.write_text(json.dumps(rights, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return rights_path, permission_path


def _make_registry(tmp_path: Path, roles_by_key=None):
    roles_by_key = roles_by_key or {
        "owner-test": ["EVIDENCE_ADMISSION_SIGNER"],
        "reviewer-test": ["INDEPENDENT_REVIEWER"],
    }
    private_raws = {"owner-test": bytes(range(32)), "reviewer-test": bytes(range(1, 33))}
    entries = []
    key_paths = {}
    for key_id, roles in roles_by_key.items():
        private = Ed25519PrivateKey.from_private_bytes(private_raws[key_id])
        public_raw = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        key_path = tmp_path / f"{key_id}.key"
        key_path.write_text(base64.b64encode(private_raws[key_id]).decode("ascii") + "\n", encoding="ascii")
        key_path.chmod(0o600)
        key_paths[key_id] = key_path
        entries.append({
            "signer_key_id": key_id,
            "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
            "roles": roles,
            "status": "ACTIVE",
            "case_scopes": [CASE_ID],
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_until": None,
            "revoked_at": None,
        })
    registry_path = tmp_path / "signer-registry.json"
    registry_path.write_text(json.dumps({
        "schema_version": SIGNER_REGISTRY_SCHEMA,
        "registry_status": "TEST_ONLY",
        "signers": entries,
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return registry_path, key_paths


def _create_envelope(tmp_path: Path, *, source_class="EXCHANGE_MARKET_DATA", status="ALLOWED",
                     basis_kind="EXPLICIT_WRITTEN_PERMISSION", required_roles=None):
    manifest_path, raw_root, _ = _make_manifest(tmp_path)
    rights_path, permission_path = _write_rights(
        tmp_path, source_class=source_class, status=status,
        basis_kind=basis_kind, required_roles=required_roles,
    )
    payload = build_admission_payload(
        manifest_path=manifest_path,
        raw_root=raw_root,
        rights_record_path=rights_path,
        permission_evidence_path=permission_path,
        decision="ADMIT",
        signed_at=SIGNED_AT,
    )
    return payload, manifest_path, raw_root, rights_path, permission_path


def test_enrollment_request_is_private_proposal_and_never_registers_a_signer(tmp_path):
    private_path = tmp_path / "private" / "admission.key"
    public_path = tmp_path / "public" / "admission.public.json"
    out_path = tmp_path / "private" / "enrollment-request.json"
    generated = generate_keypair(private_path, public_path)
    result = prepare_signer_enrollment_request(
        public_path,
        signer_key_id="OWNER-C1-20261012",
        display_label="owner-admission-signer",
        role="EVIDENCE_ADMISSION_SIGNER",
        case_scopes=["RC-CN-A-605016-20261009"],
        valid_from="2026-10-13T00:00:00+08:00",
        authorization_note="Owner identity and scope require explicit human approval; test fixture only.",
        out_path=out_path,
        requested_at="2026-10-12T12:00:00+08:00",
    )
    request = json.loads(out_path.read_text(encoding="utf-8"))
    assert result["status"] == "ENROLLMENT_REQUEST_CREATED_NOT_TRUSTED"
    assert request["request_status"] == "PROPOSED_NOT_TRUSTED"
    assert request["trusted_signer_created"] is False
    assert request["registry_mutation_performed"] is False
    assert request["private_key_included"] is False
    assert "private_key" not in json.dumps(request).lower()
    assert request["signer"]["public_key_sha256"] == generated["public_key_sha256"]
    assert request["signer"]["roles"] == ["EVIDENCE_ADMISSION_SIGNER"]
    assert request["signer"]["case_scopes"] == ["RC-CN-A-605016-20261009"]
    assert private_path.read_text(encoding="ascii").strip() not in out_path.read_text(encoding="utf-8")
    if os.name != "nt":
        assert (out_path.stat().st_mode & 0o777) == 0o600


def test_enrollment_request_rejects_wildcard_and_combined_roles(tmp_path):
    private_path = tmp_path / "private" / "admission.key"
    public_path = tmp_path / "public" / "admission.public.json"
    generate_keypair(private_path, public_path)
    common = dict(
        signer_key_id="OWNER-C1-20261012",
        display_label="reviewer-proposal",
        valid_from="2026-10-13T00:00:00+08:00",
        authorization_note="Test only; no trusted enrollment.",
        requested_at="2026-10-12T12:00:00+08:00",
    )
    with pytest.raises(SignedAdmissionError, match="WILDCARD_SIGNER_SCOPE_NOT_ALLOWED"):
        prepare_signer_enrollment_request(
            public_path, **common, role="EVIDENCE_ADMISSION_SIGNER",
            case_scopes=["*"], out_path=tmp_path / "private" / "wildcard.json"
        )
    with pytest.raises(SignedAdmissionError, match="SIGNER_ROLE_INVALID"):
        prepare_signer_enrollment_request(
            public_path, **common, role="EVIDENCE_ADMISSION_SIGNER,INDEPENDENT_REVIEWER",
            case_scopes=[CASE_ID], out_path=tmp_path / "private" / "bad-role.json"
        )


def test_enrollment_request_rejects_public_key_fingerprint_mismatch(tmp_path):
    private_path = tmp_path / "private" / "admission.key"
    public_path = tmp_path / "public" / "admission.public.json"
    generate_keypair(private_path, public_path)
    doc = json.loads(public_path.read_text(encoding="utf-8"))
    doc["public_key_sha256"] = "0" * 64
    public_path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(SignedAdmissionError, match="SIGNER_PUBLIC_KEY_FINGERPRINT_MISMATCH"):
        prepare_signer_enrollment_request(
            public_path,
            signer_key_id="OWNER-C1-20261012",
            display_label="owner-admission-signer",
            role="EVIDENCE_ADMISSION_SIGNER",
            case_scopes=[CASE_ID],
            valid_from="2026-10-13T00:00:00+08:00",
            authorization_note="Test only.",
            out_path=tmp_path / "private" / "enrollment-request.json",
            requested_at="2026-10-12T12:00:00+08:00",
        )


def test_signed_admission_requires_trusted_signature_and_exact_core_pit_bytes(tmp_path):
    payload, manifest, raw_root, rights, permission = _create_envelope(tmp_path)
    registry, keys = _make_registry(tmp_path)
    envelope = {"schema_version": SIGNED_ADMISSION_SCHEMA, "payload": payload, "signatures": []}
    envelope = add_signature(
        envelope, signer_registry_path=registry, signer_key_id="owner-test",
        private_key_path=keys["owner-test"], signed_at=SIGNED_AT,
    )
    result = verify_signed_admission(
        envelope, manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
        permission_evidence_path=permission, signer_registry_path=registry,
    )
    assert result["status"] == "FORMALLY_ADMITTED"
    assert result["core_pit_validation"] == "PASS"
    assert result["missing_signer_roles"] == []


def test_admission_refuses_unknown_rights_even_when_core_pit_passes(tmp_path):
    manifest, raw_root, _ = _make_manifest(tmp_path)
    rights, permission = _write_rights(tmp_path, status="UNKNOWN", basis_kind="OFFICIAL_TERMS_REVIEWED")
    with pytest.raises(SignedAdmissionError, match="ADMISSION_BLOCKED_RIGHTS_NOT_ALLOWED"):
        build_admission_payload(
            manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
            permission_evidence_path=permission, decision="ADMIT", signed_at=SIGNED_AT,
        )


def test_exchange_public_terms_alone_do_not_count_as_explicit_market_data_permission(tmp_path):
    manifest, raw_root, _ = _make_manifest(tmp_path)
    rights, permission = _write_rights(
        tmp_path, source_class="EXCHANGE_MARKET_DATA",
        status="ALLOWED", basis_kind="OFFICIAL_TERMS_REVIEWED",
    )
    with pytest.raises(SignedAdmissionError, match="RIGHTS_BASIS_INSUFFICIENT_FOR_SOURCE_CLASS"):
        build_admission_payload(
            manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
            permission_evidence_path=permission, decision="ADMIT", signed_at=SIGNED_AT,
        )


def test_operator_attested_market_price_cannot_be_promoted_to_formal_source_admission(tmp_path):
    manifest, raw_root, _ = _make_manifest(tmp_path)
    rights, permission = _write_rights(
        tmp_path, source_class="OPERATOR_ATTESTED_MARKET_DATA",
        status="ALLOWED", basis_kind="EXPLICIT_WRITTEN_PERMISSION",
    )
    with pytest.raises(SignedAdmissionError, match="OPERATOR_ATTESTED_PRICE_CANNOT_BE_SOURCE_ADMITTED"):
        build_admission_payload(
            manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
            permission_evidence_path=permission, decision="ADMIT", signed_at=SIGNED_AT,
        )


def test_manifest_byte_change_invalidates_signature(tmp_path):
    payload, manifest, raw_root, rights, permission = _create_envelope(tmp_path)
    registry, keys = _make_registry(tmp_path)
    envelope = {"schema_version": SIGNED_ADMISSION_SCHEMA, "payload": payload, "signatures": []}
    envelope = add_signature(
        envelope, signer_registry_path=registry, signer_key_id="owner-test",
        private_key_path=keys["owner-test"], signed_at=SIGNED_AT,
    )
    manifest.write_text(manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(SignedAdmissionError, match="MANIFEST_BYTES_CHANGED_AFTER_SIGNING"):
        verify_signed_admission(
            envelope, manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
            permission_evidence_path=permission, signer_registry_path=registry,
        )


def test_independent_reviewer_role_requires_second_distinct_key(tmp_path):
    payload, manifest, raw_root, rights, permission = _create_envelope(
        tmp_path, required_roles=["EVIDENCE_ADMISSION_SIGNER", "INDEPENDENT_REVIEWER"]
    )
    registry, keys = _make_registry(tmp_path)
    envelope = {"schema_version": SIGNED_ADMISSION_SCHEMA, "payload": payload, "signatures": []}
    envelope = add_signature(
        envelope, signer_registry_path=registry, signer_key_id="owner-test",
        private_key_path=keys["owner-test"], signed_at=SIGNED_AT,
    )
    pending = verify_signed_admission(
        envelope, manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
        permission_evidence_path=permission, signer_registry_path=registry,
    )
    assert pending["status"] == "SIGNATURES_PENDING"
    envelope = add_signature(
        envelope, signer_registry_path=registry, signer_key_id="reviewer-test",
        private_key_path=keys["reviewer-test"], signed_at="2026-10-11T18:05:00+08:00",
    )
    completed = verify_signed_admission(
        envelope, manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
        permission_evidence_path=permission, signer_registry_path=registry,
    )
    assert completed["status"] == "FORMALLY_ADMITTED"
    assert {x["signer_key_id"] for x in completed["verified_signatures"]} == {"owner-test", "reviewer-test"}


def test_one_key_cannot_self_certify_as_both_admission_signer_and_independent_reviewer(tmp_path):
    payload, manifest, raw_root, rights, permission = _create_envelope(
        tmp_path, required_roles=["EVIDENCE_ADMISSION_SIGNER", "INDEPENDENT_REVIEWER"]
    )
    registry, keys = _make_registry(tmp_path, roles_by_key={
        "owner-test": ["EVIDENCE_ADMISSION_SIGNER", "INDEPENDENT_REVIEWER"],
    })
    envelope = {"schema_version": SIGNED_ADMISSION_SCHEMA, "payload": payload, "signatures": []}
    envelope = add_signature(
        envelope, signer_registry_path=registry, signer_key_id="owner-test",
        private_key_path=keys["owner-test"], signed_at=SIGNED_AT,
    )
    result = verify_signed_admission(
        envelope, manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
        permission_evidence_path=permission, signer_registry_path=registry,
    )
    assert result["status"] == "SIGNATURES_PENDING"
    assert "INDEPENDENT_REVIEWER_DISTINCT_SIGNER" in result["missing_signer_roles"]


def test_public_company_disclosure_admission_requires_independent_reviewer(tmp_path):
    manifest, raw_root, _ = _make_manifest(tmp_path)
    rights, permission = _write_rights(
        tmp_path, source_class="PUBLIC_COMPANY_DISCLOSURE",
        status="ALLOWED", basis_kind="OFFICIAL_TERMS_REVIEWED",
        required_roles=["EVIDENCE_ADMISSION_SIGNER"],
    )
    with pytest.raises(SignedAdmissionError, match="PUBLIC_COMPANY_DISCLOSURE_REQUIRES_INDEPENDENT_REVIEWER"):
        build_admission_payload(
            manifest_path=manifest, raw_root=raw_root, rights_record_path=rights,
            permission_evidence_path=permission, decision="ADMIT", signed_at=SIGNED_AT,
        )
