from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import sys
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
