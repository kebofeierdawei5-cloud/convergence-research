from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import stat
import sys
import zipfile
import pytest

from tools import iios_private_605016_b2_ingest_v01 as MODULE


RAW = b'{"official":"SSE","date":"2026-10-08","close":20.22}\n'
RAW_SHA = hashlib.sha256(RAW).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _patch_expected_price_hash(monkeypatch):
    monkeypatch.setattr(MODULE, "EXPECTED_PRICE_RAW_SHA256", RAW_SHA)


def _input_root(tmp_path: Path) -> Path:
    (tmp_path / "repo").mkdir(exist_ok=True)
    root = tmp_path / "attempt10"
    root.mkdir()
    _write_json(root / "intake_manifest.json", {
        "case_id": MODULE.CASE_ID,
        "symbol": "605016",
        "cutoff_date": MODULE.CUTOFF_DATE,
        "sources": [{"source_id": f"src-{n}"} for n in range(12)],
    })
    _write_json(root / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json", {
        "status": "CAPTURED_NOT_ADMITTED",
        "sources": [{"source_id": f"src-{n}"} for n in range(12)],
    })
    _write_json(root / "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json", {
        "raw_bytes_verified": 12,
        "payload_contract_mismatches": 0,
    })
    return root


def _manifest(*, raw_relative_path: str = "raw/sse-market.json") -> dict:
    evidence = [{
        "evidence_id": MODULE.PRICE_EVIDENCE_ID,
        "subject_id": MODULE.CASE_ID,
        "field_id": "market_price.close",
        "claim_type": "OBSERVED_FACT",
        "value": {
            "observation_date": "2026-10-08",
            "close_cny_per_share": 20.22,
            "quote_type": "OFFICIAL_SSE_DAILY_CLOSE",
        },
        "unit": "CNY_per_share",
        "basis": "official exchange daily close",
        "observation_date": "2026-10-08",
        "known_at": "2026-10-08T15:00:00+08:00",
        "known_at_basis": "MARKET_SESSION_CLOSE_EVENT_TIME; exact first-public timestamp not exposed",
        "retrieved_at": "2026-10-10T00:00:00+00:00",
        "source_ref": "https://yunhq.sse.com.cn:32042/v1/sh1/dayk/605016",
        "artifact_id": "fixture-source:" + RAW_SHA[:16],
        "content_sha256": RAW_SHA,
        "exact_bytes": True,
        "provenance_class": "SOURCE_VINTAGE_VERIFIED",
        "status": "ADMITTED",
        "license_status": "RESTRICTED_NO_REDISTRIBUTION",
        "source_origin_adjudication": "PASS_OFFICIAL_SSE_DOMAIN_HTTPS_TLS_AND_DATE_ROW_MATCH",
    }]
    return {
        "schema_version": "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1",
        "case_id": MODULE.CASE_ID,
        "market": "CN-A",
        "symbol": "605016",
        "company": "山东百龙创园生物科技股份有限公司",
        "cutoff_date": MODULE.CUTOFF_DATE,
        "required_field_groups": list(MODULE.REQUIRED_FIELD_GROUPS_FOR_REPORT),
        "evidence": evidence,
        "raw_artifacts": [{
            "evidence_id": MODULE.PRICE_EVIDENCE_ID,
            "relative_path": raw_relative_path,
            "expected_size_bytes": len(RAW),
            "expected_sha256": RAW_SHA,
        }],
        "audit": {"manifest_sha256": "a" * 64},
        "status": "PASS",
        "validation_errors": [],
    }


def _fake_adjudicator(input_root: Path, out_root: Path) -> dict:
    assert (input_root / "intake_manifest.json").is_file()
    raw_root = out_root / "base-b2" / "combined-evidence-root"
    (raw_root / "raw").mkdir(parents=True)
    (raw_root / "raw" / "sse-market.json").write_bytes(RAW)
    # This file is intentionally not referenced by the passing manifest, so it
    # must remain ephemeral and never be copied to the private persistent root.
    (raw_root / "raw" / "excluded-provider-response.bin").write_bytes(b"DO_NOT_PERSIST")
    manifest = _manifest()
    manifest_path = out_root / "base-b2" / "COMBINED_B2_CANDIDATE_MANIFEST.json"
    _write_json(manifest_path, manifest)
    report = {
        "overall": "PASS_EPHEMERAL_B2",
        "official_price_source": {
            "transport": "HTTPS_TLS_VERIFIED",
            "raw_sha256": MODULE.EXPECTED_PRICE_RAW_SHA256,
            "observation_date": "2026-10-08",
            "numeric_quote_value_in_report": False,
        },
        "core_b2": {
            "candidate_manifest_status": "PASS",
            "missing_required_field_groups": [],
        },
    }
    _write_json(out_root / "OFFICIAL_HTTPS_B2_ADJUDICATION_REPORT.json", report)
    return report


def _fake_core_validator(manifest, *, raw_root, require_raw_verification):
    errors = []
    if require_raw_verification is not True:
        errors.append("RAW_VERIFICATION_MUST_BE_REQUIRED")
    if manifest.get("status") != "PASS":
        errors.append("MANIFEST_STATUS_NOT_PASS")
    if manifest.get("validation_errors") != []:
        errors.append("MANIFEST_ERRORS_PRESENT")
    evidence_by_id = {item["evidence_id"]: item for item in manifest.get("evidence", [])}
    for declaration in manifest.get("raw_artifacts", []):
        evidence = evidence_by_id.get(declaration["evidence_id"])
        if evidence is None or evidence.get("content_sha256") != declaration["expected_sha256"]:
            errors.append("EVIDENCE_HASH_BINDING_MISMATCH")
        path = raw_root / declaration["relative_path"]
        if not path.is_file():
            errors.append("RAW_ARTIFACT_MISSING")
            continue
        raw = path.read_bytes()
        if len(raw) != declaration["expected_size_bytes"]:
            errors.append("RAW_ARTIFACT_SIZE_MISMATCH")
        if hashlib.sha256(raw).hexdigest() != declaration["expected_sha256"]:
            errors.append("RAW_ARTIFACT_HASH_MISMATCH")
    return errors


def test_persists_only_manifest_referenced_bytes_and_keeps_production_gates_open(tmp_path: Path) -> None:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"

    result = MODULE.ingest_private_b2_candidate(
        private_root=private_root,
        repository_root=tmp_path / "repo",
        attempt10_root=input_root,
        adjudicator=_fake_adjudicator,
        core_validator=_fake_core_validator,
    )

    assert result["status"] == "PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED"
    assert result["core_validator_status"] == "PASS"
    assert result["source_vintage_review_required"] is True
    assert result["exact_first_public_timestamp_verified"] is False
    assert result["formal_signed_admission_created"] is False
    assert result["production_host_accepted"] is False
    assert result["bundle_created"] is False
    assert result["decision_created"] is False
    assert result["auto_execution"] is False
    assert private_root.stat().st_mode & 0o077 == 0

    output = Path(result["evidence_root"])
    assert (output / "raw" / "sse-market.json").read_bytes() == RAW
    assert not (output / "raw" / "excluded-provider-response.bin").exists()
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["evidence"][0]["content_sha256"] == RAW_SHA

    receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["receipt_is_cryptographically_signed"] is False
    assert receipt["source_vintage_review_required"] is True
    assert "20.22" not in json.dumps(receipt)
    assert receipt["receipt_sha256"]


def test_raw_copy_preflights_all_hashes_before_creating_destination(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    (source_root / "raw").mkdir(parents=True)
    good = b'{"valid":true}'
    bad = b'{"valid":false}'
    (source_root / "raw" / "good.json").write_bytes(good)
    (source_root / "raw" / "bad.json").write_bytes(bad)
    destination_root = tmp_path / "private-stage"

    declarations = [
        {
            "evidence_id": "fact-good",
            "relative_path": "raw/good.json",
            "expected_size_bytes": len(good),
            "expected_sha256": hashlib.sha256(good).hexdigest(),
        },
        {
            "evidence_id": "fact-bad",
            "relative_path": "raw/bad.json",
            "expected_size_bytes": len(bad),
            "expected_sha256": "0" * 64,
        },
    ]
    with pytest.raises(MODULE.PrivateIngestError, match="RAW_ARTIFACT_EXACT_BYTES_MISMATCH"):
        MODULE._copy_exact_artifacts(
            source_root=source_root,
            destination_root=destination_root,
            declarations=declarations,
        )
    # A good earlier declaration must not be copied before a later hash fails.
    assert not destination_root.exists()


def test_raw_copy_rejects_symlinked_source_before_creating_destination(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    raw_dir = source_root / "raw"
    raw_dir.mkdir(parents=True)
    target = raw_dir / "original.json"
    target.write_bytes(RAW)
    link = raw_dir / "alias.json"
    try:
        link.symlink_to(target.name)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this test environment")
    destination_root = tmp_path / "private-stage"

    declarations = [{
        "evidence_id": "fact-through-link",
        "relative_path": "raw/alias.json",
        "expected_size_bytes": len(RAW),
        "expected_sha256": RAW_SHA,
    }]
    with pytest.raises(MODULE.PrivateIngestError, match="RAW_ARTIFACT_SOURCE_SYMLINK_FORBIDDEN"):
        MODULE._copy_exact_artifacts(
            source_root=source_root,
            destination_root=destination_root,
            declarations=declarations,
        )
    assert not destination_root.exists()


def test_private_persistence_allows_multiple_evidence_records_to_share_exact_raw_source(
    tmp_path: Path,
) -> None:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"

    def shared_source_adjudicator(input_root: Path, out_root: Path) -> dict:
        report = _fake_adjudicator(input_root, out_root)
        manifest_path = out_root / "base-b2" / "COMBINED_B2_CANDIDATE_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        original = manifest["evidence"][0]
        shared = dict(original)
        shared["evidence_id"] = "605016-IDENTITY-SHARED-SOURCE-FIXTURE"
        shared["field_id"] = "security_identity.issuer_code"
        shared["value"] = {"issuer_code": "605016"}
        manifest["evidence"].append(shared)
        manifest["raw_artifacts"].append({
            "evidence_id": shared["evidence_id"],
            "relative_path": manifest["raw_artifacts"][0]["relative_path"],
            "expected_size_bytes": len(RAW),
            "expected_sha256": RAW_SHA,
        })
        _write_json(manifest_path, manifest)
        return report

    result = MODULE.ingest_private_b2_candidate(
        private_root=private_root,
        repository_root=tmp_path / "repo",
        attempt10_root=input_root,
        adjudicator=shared_source_adjudicator,
        core_validator=_fake_core_validator,
    )

    assert result["status"] == "PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED"
    assert result["raw_artifact_count"] == 2  # legacy alias: manifest declarations
    assert result["raw_artifact_declaration_count"] == 2
    assert result["unique_raw_file_count"] == 1
    assert result["raw_artifact_count_semantics"] == "MANIFEST_DECLARATIONS_NOT_UNIQUE_FILES"
    persisted_raw = Path(result["evidence_root"]) / "raw" / "sse-market.json"
    assert persisted_raw.read_bytes() == RAW
    assert len([path for path in (Path(result["evidence_root"]) / "raw").iterdir() if path.is_file()]) == 1

    # The durable verifier must accept the same evidence-centric manifest while
    # requiring exactly the one unique persisted byte path.
    verified = MODULE.verify_existing_private_b2_candidate(
        private_root=private_root,
        repository_root=tmp_path / "repo",
        core_validator=_fake_core_validator,
    )
    assert verified["status"] == "VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED"
    assert verified["candidates"][0]["raw_artifact_count"] == 2
    assert verified["candidates"][0]["raw_artifact_declaration_count"] == 2
    assert verified["candidates"][0]["unique_raw_file_count"] == 1
    assert verified["candidates"][0]["raw_artifact_count_semantics"] == "MANIFEST_DECLARATIONS_NOT_UNIQUE_FILES"


def test_shared_raw_path_with_conflicting_byte_contract_fails_before_any_write(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    raw_path = source_root / "raw" / "shared.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(RAW)
    destination_root = tmp_path / "private-stage"

    declarations = [
        {
            "evidence_id": "fact-a",
            "relative_path": "raw/shared.json",
            "expected_size_bytes": len(RAW),
            "expected_sha256": RAW_SHA,
        },
        {
            "evidence_id": "fact-b",
            "relative_path": "raw/shared.json",
            "expected_size_bytes": len(RAW),
            "expected_sha256": "0" * 64,
        },
    ]
    with pytest.raises(MODULE.PrivateIngestError, match="RAW_ARTIFACT_PATH_CONTRACT_CONFLICT"):
        MODULE._copy_exact_artifacts(
            source_root=source_root,
            destination_root=destination_root,
            declarations=declarations,
        )
    assert not destination_root.exists()


def test_same_candidate_is_immutable_and_idempotent(tmp_path: Path) -> None:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"
    first = MODULE.ingest_private_b2_candidate(
        private_root=private_root, repository_root=tmp_path / "repo",
        attempt10_root=input_root, adjudicator=_fake_adjudicator,
        core_validator=_fake_core_validator,
    )
    second = MODULE.ingest_private_b2_candidate(
        private_root=private_root, repository_root=tmp_path / "repo",
        attempt10_root=input_root, adjudicator=_fake_adjudicator,
        core_validator=_fake_core_validator,
    )
    assert first["candidate_fingerprint"] == second["candidate_fingerprint"]
    assert second["status"] == "ALREADY_PERSISTED_CORE_VALIDATED_NOT_PRODUCTION_ACCEPTED"
    assert Path(first["manifest_path"]).read_bytes() == Path(second["manifest_path"]).read_bytes()


def test_core_validator_blocked_creates_no_private_store(tmp_path: Path) -> None:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"
    with pytest.raises(MODULE.PrivateIngestError, match="CORE_OWNED_B2_PIT_VALIDATOR_BLOCKED"):
        MODULE.ingest_private_b2_candidate(
            private_root=private_root, repository_root=tmp_path / "repo",
            attempt10_root=input_root, adjudicator=_fake_adjudicator,
            core_validator=lambda *_args, **_kwargs: ["PIT_BLOCKED"],
        )
    assert not private_root.exists()


def test_rejects_private_root_inside_public_repository_before_ingest(tmp_path: Path) -> None:
    input_root = _input_root(tmp_path)
    repo = tmp_path / "repo"
    called = False

    def should_not_run(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("adjudicator must not run for an unsafe destination")

    with pytest.raises(MODULE.PrivateIngestError, match="PRIVATE_ROOT_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY"):
        MODULE.ingest_private_b2_candidate(
            private_root=repo / "evidence",
            repository_root=repo,
            attempt10_root=input_root,
            adjudicator=should_not_run,
            core_validator=_fake_core_validator,
        )
    assert called is False
    assert not (repo / "evidence").exists()


def test_rejects_path_traversal_in_manifest_and_cleans_new_root(tmp_path: Path) -> None:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"

    def traversal_adjudicator(input_root: Path, out_root: Path) -> dict:
        report = _fake_adjudicator(input_root, out_root)
        manifest_path = out_root / "base-b2" / "COMBINED_B2_CANDIDATE_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["raw_artifacts"][0]["relative_path"] = "../sse-market.json"
        _write_json(manifest_path, manifest)
        return report

    with pytest.raises(MODULE.PrivateIngestError, match="RAW_ARTIFACT_RELATIVE_PATH_UNSAFE"):
        MODULE.ingest_private_b2_candidate(
            private_root=private_root, repository_root=tmp_path / "repo",
            attempt10_root=input_root, adjudicator=traversal_adjudicator,
            core_validator=lambda *_args, **_kwargs: [],
        )
    assert not private_root.exists()


def test_rejects_wrong_official_price_hash_before_persistence(tmp_path: Path) -> None:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"

    def wrong_hash_adjudicator(input_root: Path, out_root: Path) -> dict:
        report = _fake_adjudicator(input_root, out_root)
        report["official_price_source"]["raw_sha256"] = "0" * 64
        return report

    with pytest.raises(MODULE.PrivateIngestError, match="OFFICIAL_PRICE_RAW_HASH_MISMATCH"):
        MODULE.ingest_private_b2_candidate(
            private_root=private_root, repository_root=tmp_path / "repo",
            attempt10_root=input_root, adjudicator=wrong_hash_adjudicator,
            core_validator=_fake_core_validator,
        )
    assert not private_root.exists()



def _make_real_core_validator_fixture(tmp_path: Path) -> tuple[dict, Path]:
    from research.b2.company_evidence import (
        REQUIRED_COMPANY_FIELD_GROUPS,
        build_company_evidence_manifest,
    )

    raw_root = tmp_path / "real-core-raw"
    evidence = []
    raw_artifacts = []
    for index, field_group in enumerate(REQUIRED_COMPANY_FIELD_GROUPS):
        if index in {0, 1}:
            # Two facts sourced from the same official publication should have
            # separate evidence declarations that reference one byte object.
            relative_path = "raw/shared-official-publication.json"
            raw = b'{"source":"one official publication","exact_bytes":true}'
        else:
            relative_path = f"raw/{field_group}.json"
            raw = json.dumps(
                {"field_group": field_group, "fact_number": index},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        raw_path = raw_root / relative_path
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        evidence_id = f"CORE-CONTRACT-{field_group.upper()}"
        evidence.append({
            "evidence_id": evidence_id,
            "subject_id": MODULE.CASE_ID,
            "field_id": field_group + ".contract_fact",
            "claim_type": "OBSERVED_FACT",
            "value": {"fixture_fact": field_group},
            "unit": "test_unit",
            "basis": "isolated validator contract fixture",
            "observation_date": "2026-10-08",
            "known_at": "2026-10-08T15:00:00+08:00",
            "retrieved_at": "2026-10-10T12:00:00+00:00",
            "source_ref": f"https://official.example.test/{field_group}",
            "artifact_id": "core-contract:" + digest[:16],
            "content_sha256": digest,
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
            "license_status": "TEST_FIXTURE_ONLY",
            "source_locator": "isolated contract test; not real-world evidence",
            "parents": [],
            "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
        })
        raw_artifacts.append({
            "evidence_id": evidence_id,
            "relative_path": relative_path,
            "expected_size_bytes": len(raw),
            "expected_sha256": digest,
        })

    manifest = build_company_evidence_manifest(
        case_id=MODULE.CASE_ID,
        market="CN-A",
        symbol="605016",
        company="山东百龙创园生物科技股份有限公司",
        cutoff_date=MODULE.CUTOFF_DATE,
        evidence=evidence,
        raw_artifacts=raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=raw_root,
    )
    assert manifest["status"] == "PASS", manifest["validation_errors"]
    return manifest, raw_root


def test_real_investment_core_validator_replays_exact_manifest_bytes(tmp_path: Path) -> None:
    manifest, raw_root = _make_real_core_validator_fixture(tmp_path)

    assert MODULE._validate_core(manifest, raw_root, validator=None) == []

    declaration = manifest["raw_artifacts"][0]
    tampered = raw_root / declaration["relative_path"]
    tampered.write_bytes(tampered.read_bytes() + b"tampered")
    errors = MODULE._validate_core(manifest, raw_root, validator=None)

    assert any("EXACT_BYTES_MISMATCH" in error for error in errors)





def _make_test_artifact_zip(path: Path, extra_entries: list[tuple[str, bytes, int | None]] | None = None) -> tuple[str, int]:
    payloads = [
        ("capture/intake_manifest.json", json.dumps({
            "case_id": MODULE.CASE_ID,
            "symbol": "605016",
            "cutoff_date": MODULE.CUTOFF_DATE,
            "sources": [{"source_id": f"source-{i}"} for i in range(12)],
        }).encode("utf-8"), None),
        ("capture/COMPANY_EVIDENCE_INTAKE_RECEIPT.json", json.dumps({
            "status": "CAPTURED_NOT_ADMITTED",
            "sources": [{"source_id": f"source-{i}"} for i in range(12)],
        }).encode("utf-8"), None),
        ("capture/COMPANY_EVIDENCE_INTAKE_VERIFICATION.json", json.dumps({
            "raw_bytes_verified": 12,
            "payload_contract_mismatches": 0,
        }).encode("utf-8"), None),
    ]
    payloads.extend(extra_entries or [])
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content, unix_mode in payloads:
            info = zipfile.ZipInfo(name)
            if unix_mode is not None:
                info.create_system = 3
                info.external_attr = unix_mode << 16
            archive.writestr(info, content)
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size


def test_attempt10_archive_is_hash_checked_before_safe_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "attempt10.zip"
    digest, size = _make_test_artifact_zip(archive)
    destination = tmp_path / "unpacked"
    result = MODULE._extract_verified_attempt10_archive(
        archive, destination, expected_sha256=digest, expected_size_bytes=size,
    )
    assert result.name == "capture"
    assert (result / "intake_manifest.json").is_file()
    assert result.stat().st_mode & 0o077 == 0
    assert (result / "intake_manifest.json").stat().st_mode & 0o077 == 0


def test_attempt10_archive_digest_mismatch_blocks_before_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "attempt10.zip"
    _digest, size = _make_test_artifact_zip(archive)
    destination = tmp_path / "unpacked"
    with pytest.raises(MODULE.PrivateIngestError, match="ATTEMPT10_ARTIFACT_ARCHIVE_SHA256_MISMATCH"):
        MODULE._extract_verified_attempt10_archive(
            archive, destination, expected_sha256="0" * 64, expected_size_bytes=size,
        )
    assert not destination.exists()


def test_attempt10_archive_zip_slip_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "attempt10.zip"
    digest, size = _make_test_artifact_zip(archive, [("../escaped.txt", b"not allowed", None)])
    destination = tmp_path / "unpacked"
    with pytest.raises(MODULE.PrivateIngestError, match="ATTEMPT10_ARCHIVE_PATH_UNSAFE"):
        MODULE._extract_verified_attempt10_archive(
            archive, destination, expected_sha256=digest, expected_size_bytes=size,
        )
    assert not (tmp_path / "escaped.txt").exists()


def test_attempt10_archive_symlink_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "attempt10.zip"
    digest, size = _make_test_artifact_zip(
        archive, [("capture/link", b"target", stat.S_IFLNK | 0o777)]
    )
    destination = tmp_path / "unpacked"
    with pytest.raises(MODULE.PrivateIngestError, match="ATTEMPT10_ARCHIVE_SPECIAL_FILE_FORBIDDEN"):
        MODULE._extract_verified_attempt10_archive(
            archive, destination, expected_sha256=digest, expected_size_bytes=size,
        )

def _persist_mock_candidate(tmp_path: Path) -> tuple[Path, dict]:
    input_root = _input_root(tmp_path)
    private_root = tmp_path / "private-data"
    result = MODULE.ingest_private_b2_candidate(
        private_root=private_root,
        repository_root=tmp_path / "repo",
        attempt10_root=input_root,
        adjudicator=_fake_adjudicator,
        core_validator=_fake_core_validator,
    )
    return private_root, result


def test_offline_verifier_replays_existing_candidate_without_source_download(tmp_path: Path, monkeypatch) -> None:
    private_root, persisted = _persist_mock_candidate(tmp_path)

    def forbidden_download(*_args, **_kwargs):
        raise AssertionError("offline verifier must not redownload source artifacts")

    monkeypatch.setattr(MODULE, "_download_attempt10", forbidden_download)
    result = MODULE.verify_existing_private_b2_candidate(
        private_root=private_root,
        repository_root=tmp_path / "repo",
        core_validator=_fake_core_validator,
    )

    assert result["status"] == "VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED"
    assert result["official_source_refetched"] is False
    assert result["candidate_count"] == 1
    assert result["candidates"][0]["candidate_fingerprint"] == persisted["candidate_fingerprint"]
    assert result["candidates"][0]["manifest_sha256"] == persisted["manifest_sha256"]
    assert result["formal_signed_admission_created"] is False
    assert result["production_host_accepted"] is False
    assert result["decision_created"] is False
    assert result["auto_execution"] is False


def test_offline_verifier_blocks_tampered_persisted_raw_bytes(tmp_path: Path) -> None:
    private_root, persisted = _persist_mock_candidate(tmp_path)
    raw_file = Path(persisted["evidence_root"]) / "raw" / "sse-market.json"
    raw_file.write_bytes(raw_file.read_bytes() + b"tampered")

    with pytest.raises(MODULE.PrivateIngestError, match="EXISTING_PRIVATE_CANDIDATE_FAILED_CORE_REPLAY"):
        MODULE.verify_existing_private_b2_candidate(
            private_root=private_root,
            repository_root=tmp_path / "repo",
            core_validator=_fake_core_validator,
        )


def test_offline_verifier_blocks_receipt_semantics_tamper_even_with_rehashed_receipt(tmp_path: Path) -> None:
    private_root, persisted = _persist_mock_candidate(tmp_path)
    receipt_path = Path(persisted["receipt_path"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["production_host_accepted"] = True
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = MODULE._sha256(MODULE._canonical_bytes(core))
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(MODULE.PrivateIngestError, match="EXISTING_PRIVATE_RECEIPT_SEMANTICS_MISMATCH:production_host_accepted"):
        MODULE.verify_existing_private_b2_candidate(
            private_root=private_root,
            repository_root=tmp_path / "repo",
            core_validator=_fake_core_validator,
        )


def test_offline_verifier_blocks_unlisted_raw_file(tmp_path: Path) -> None:
    private_root, persisted = _persist_mock_candidate(tmp_path)
    extra = Path(persisted["evidence_root"]) / "raw" / "unlisted.bin"
    extra.write_bytes(b"must-not-be-present")
    os.chmod(extra, 0o600)

    with pytest.raises(MODULE.PrivateIngestError, match="EXISTING_PRIVATE_RAW_FILE_SET_MISMATCH"):
        MODULE.verify_existing_private_b2_candidate(
            private_root=private_root,
            repository_root=tmp_path / "repo",
            core_validator=_fake_core_validator,
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission-mode contract")
def test_offline_verifier_blocks_loose_private_file_permissions(tmp_path: Path) -> None:
    private_root, persisted = _persist_mock_candidate(tmp_path)
    raw_file = Path(persisted["evidence_root"]) / "raw" / "sse-market.json"
    os.chmod(raw_file, 0o644)

    with pytest.raises(MODULE.PrivateIngestError, match="PRIVATE_CANDIDATE_FILE_PERMISSIONS_TOO_OPEN"):
        MODULE.verify_existing_private_b2_candidate(
            private_root=private_root,
            repository_root=tmp_path / "repo",
            core_validator=_fake_core_validator,
        )


def test_cli_verify_existing_flag_does_not_call_ingester(tmp_path: Path, monkeypatch, capsys) -> None:
    private_root = tmp_path / "private-data"
    (tmp_path / "repo").mkdir()
    expected = {
        "status": "VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
        "official_source_refetched": False,
        "formal_signed_admission_created": False,
        "production_host_accepted": False,
        "decision_created": False,
        "auto_execution": False,
    }
    monkeypatch.setattr(sys, "argv", [
        "iios_private_605016_b2_ingest_v01.py",
        "--private-root", str(private_root),
        "--repository-root", str(tmp_path / "repo"),
        "--verify-existing",
    ])
    monkeypatch.setattr(MODULE, "verify_existing_private_b2_candidate", lambda **_kwargs: expected)
    monkeypatch.setattr(MODULE, "ingest_private_b2_candidate", lambda **_kwargs: pytest.fail("ingester must not run"))

    code = MODULE.main()
    output = capsys.readouterr().out
    assert code == 0
    assert '"official_source_refetched": false' in output


def test_main_renders_validation_error_as_blocked_json_not_traceback(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["iios_private_605016_b2_ingest_v01.py"])
    monkeypatch.setattr(
        MODULE,
        "ingest_private_b2_candidate",
        lambda **_kwargs: (_ for _ in ()).throw(
            ValueError("OFFICIAL_DIVIDEND_PDF_DIRECT_HTTPS_FETCH_BLOCKED")
        ),
    )

    code = MODULE.main()
    output = capsys.readouterr().out

    assert code == 2
    assert '"status": "BLOCKED"' in output
    assert '"reason": "OFFICIAL_DIVIDEND_PDF_DIRECT_HTTPS_FETCH_BLOCKED"' in output
    assert "Traceback" not in output



def test_artifact_api_transport_falls_back_to_curl_without_token_in_process_args(monkeypatch) -> None:
    token = "test-token-not-for-process-arguments"

    class FailingOpener:
        def open(self, *_args, **_kwargs):
            raise MODULE.URLError(MODULE.ssl.SSLCertVerificationError("certificate verify failed"))

    monkeypatch.setattr(MODULE, "build_opener", lambda *_args, **_kwargs: FailingOpener())
    monkeypatch.setattr(MODULE.shutil, "which", lambda name: "/usr/bin/curl" if name == "curl" else None)
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["input"] = kwargs["input"]
        return MODULE.subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout="HTTP/2 302\r\nlocation: https://artifact-storage.example/signed-object\r\n\r\n",
            stderr="",
        )

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    location = MODULE._request_attempt10_archive_url(token)

    assert location == "https://artifact-storage.example/signed-object"
    assert token not in " ".join(captured["args"])
    assert "Authorization: Bearer " + token in captured["input"]
    assert "--config" in captured["args"]
    assert "-L" not in captured["args"]


def test_artifact_api_double_transport_failure_reports_bounded_diagnostics(monkeypatch) -> None:
    class FailingOpener:
        def open(self, *_args, **_kwargs):
            raise MODULE.URLError(MODULE.socket.gaierror("temporary failure in name resolution"))

    monkeypatch.setattr(MODULE, "build_opener", lambda *_args, **_kwargs: FailingOpener())
    monkeypatch.setattr(MODULE.shutil, "which", lambda name: "/usr/bin/curl" if name == "curl" else None)

    def fake_run(args, **kwargs):
        return MODULE.subprocess.CompletedProcess(
            args=args, returncode=6, stdout="", stderr="Could not resolve host: api.github.com"
        )

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    with pytest.raises(
        MODULE.PrivateIngestError,
        match="ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED_PYTHON_DNS_LOOKUP_FAILED_CURL_DNS_LOOKUP_FAILED",
    ):
        MODULE._request_attempt10_archive_url("dummy-token")


def test_artifact_api_response_maps_access_and_retention_failures() -> None:
    with pytest.raises(
        MODULE.PrivateIngestError,
        match="GITHUB_ACTIONS_ARTIFACT_ACCESS_DENIED_CHECK_TOKEN_ACTIONS_READ",
    ):
        MODULE._parse_artifact_api_response(403)
    with pytest.raises(
        MODULE.PrivateIngestError,
        match="ATTEMPT10_ARTIFACT_MISSING_OR_EXPIRED_CHECK_CANONICAL_ARTIFACT",
    ):
        MODULE._parse_artifact_api_response(410)


def test_curl_header_parser_uses_final_response_block() -> None:
    headers = (
        "HTTP/1.1 200 Connection established\r\n\r\n"
        "HTTP/2 302\r\n"
        "location: https://artifact-storage.example/signed-object\r\n"
        "content-length: 0\r\n\r\n"
    )
    status, location = MODULE._parse_curl_dumped_headers(headers)
    assert status == 302
    assert location == "https://artifact-storage.example/signed-object"



def test_download_attempt10_uses_curl_when_python_cannot_open_signed_url(tmp_path: Path, monkeypatch) -> None:
    token = "gh-test-token"
    archive_bytes = b"verified-archive-placeholder"
    captured = {}

    monkeypatch.setattr(
        MODULE.shutil, "which",
        lambda name: "/fake/gh" if name == "gh" else ("/fake/curl" if name == "curl" else None),
    )
    monkeypatch.setattr(
        MODULE.subprocess, "run",
        lambda args, **kwargs: MODULE.subprocess.CompletedProcess(
            args=args, returncode=0, stdout=token, stderr=""
        ),
    )

    class FailingOpener:
        def open(self, *_args, **_kwargs):
            raise MODULE.URLError(MODULE.socket.gaierror("temporary failure in name resolution"))

    monkeypatch.setattr(MODULE, "build_opener", lambda *_args, **_kwargs: FailingOpener())
    monkeypatch.setattr(
        MODULE, "_request_attempt10_archive_url",
        lambda actual_token: (
            "https://signed-storage.example/archive?signature=temporary"
            if actual_token == token else (_ for _ in ()).throw(AssertionError("wrong token"))
        ),
    )

    def fake_curl_download(location, archive_path, *, python_reason):
        captured["location"] = location
        captured["python_reason"] = python_reason
        archive_path.write_bytes(archive_bytes)

    monkeypatch.setattr(MODULE, "_download_attempt10_archive_with_curl", fake_curl_download)
    monkeypatch.setattr(MODULE, "ATTEMPT10_ARTIFACT_SIZE_BYTES", len(archive_bytes))
    monkeypatch.setattr(MODULE, "ATTEMPT10_ARTIFACT_SHA256", hashlib.sha256(archive_bytes).hexdigest())
    candidate = tmp_path / "candidate"
    monkeypatch.setattr(MODULE, "_extract_verified_attempt10_archive", lambda _archive, _dest: candidate)

    result = MODULE._download_attempt10(tmp_path / "unpacked")

    assert result == candidate
    assert captured["location"] == "https://signed-storage.example/archive?signature=temporary"
    assert captured["python_reason"] == "DNS_LOOKUP_FAILED"
    assert not (tmp_path / "attempt10-artifact.zip").exists()


def test_signed_url_curl_fallback_is_https_only_bounded_and_has_no_api_auth(
    tmp_path: Path, monkeypatch
) -> None:
    location = "https://signed-storage.example/archive?signature=temporary"
    archive_path = tmp_path / "attempt10-artifact.zip"
    captured = {}

    monkeypatch.setattr(MODULE.shutil, "which", lambda name: "/fake/curl" if name == "curl" else None)

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["config"] = kwargs["input"]
        archive_path.write_bytes(b"placeholder-zip")
        return MODULE.subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    MODULE._download_attempt10_archive_with_curl(
        location, archive_path, python_reason="DNS_LOOKUP_FAILED"
    )

    config = captured["config"]
    assert captured["args"] == ["/fake/curl", "--config", "-"]
    assert location in config
    assert "Authorization" not in config
    assert "Bearer " not in config
    assert 'proto = "=https"' in config
    assert 'proto-redir = "=https"' in config
    assert "max-redirs = 5" in config
    assert f"max-filesize = {MODULE.ATTEMPT10_ARTIFACT_SIZE_BYTES}" in config
    assert str(archive_path) in config
    assert archive_path.stat().st_mode & 0o077 == 0


def test_signed_url_curl_fallback_reports_sanitized_transport_category_and_cleans_partial_file(
    tmp_path: Path, monkeypatch
) -> None:
    archive_path = tmp_path / "attempt10-artifact.zip"
    monkeypatch.setattr(MODULE.shutil, "which", lambda name: "/fake/curl" if name == "curl" else None)

    def failed_run(args, **kwargs):
        archive_path.write_bytes(b"partial")
        return MODULE.subprocess.CompletedProcess(
            args=args, returncode=6, stdout="", stderr="Could not resolve host: signed-storage.example"
        )

    monkeypatch.setattr(MODULE.subprocess, "run", failed_run)
    with pytest.raises(
        MODULE.PrivateIngestError,
        match="ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED_PYTHON_TLS_CERTIFICATE_VERIFY_FAILED_CURL_DNS_LOOKUP_FAILED",
    ):
        MODULE._download_attempt10_archive_with_curl(
            "https://signed-storage.example/archive?signature=secret",
            archive_path,
            python_reason="TLS_CERTIFICATE_VERIFY_FAILED",
        )

    assert not archive_path.exists()
