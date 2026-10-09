from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import company_evidence_intake as intake
from tools.verify_company_evidence_intake import IndependentVerificationError, verify_intake

BODY = b"%PDF-1.7\x00exact-official-source-bytes\x01"


def manifest():
    return {
        "schema_version": intake.MANIFEST_SCHEMA,
        "case_id": "RC-CN-A-300750-20261009",
        "market": "CN-A",
        "symbol": "300750",
        "cutoff_date": "2026-10-09",
        "sources": [{
            "source_id": "SZSE-ANNOUNCEMENT-001",
            "field_group": "corporate_disclosures",
            "source_ref": "SZSE:COMPANY_ANNOUNCEMENT",
            "source_class": "OFFICIAL_EXCHANGE",
            "local_path": "raw_input/announcement.pdf",
            "known_at": "2026-07-25",
            "known_at_basis": "Official publication date shown on originating exchange announcement.",
            "published_at": "2026-07-25",
            "observation_date": "2026-06-30",
            "license_status": "PUBLIC_ACCESS_REUSE_UNKNOWN",
        }],
    }


def build_run(tmp_path):
    input_root = tmp_path / "incoming" / "raw_input"
    input_root.mkdir(parents=True)
    (input_root / "announcement.pdf").write_bytes(BODY)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest(), ensure_ascii=False), encoding="utf-8")
    root = tmp_path / "run-output"
    intake.capture_sources(manifest_path, out_dir=root, input_root=input_root.parent)
    return root


def read_receipt(root):
    path = root / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_redteam_raw_byte_mutation_is_detected(tmp_path):
    root = build_run(tmp_path)
    path = root / "raw" / "SZSE-ANNOUNCEMENT-001.pdf"
    path.write_bytes(BODY + b"tampered")
    with pytest.raises(IndependentVerificationError, match="RAW_SHA256_MISMATCH"):
        verify_intake(root)


def test_redteam_forged_admission_status_is_rejected(tmp_path):
    root = build_run(tmp_path)
    path, receipt = read_receipt(root)
    receipt["admission_status"] = "ADMITTED"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(IndependentVerificationError, match="INTAKE_RECEIPT_MUST_NOT_CLAIM_ADMISSION"):
        verify_intake(root)


def test_redteam_path_escape_is_rejected(tmp_path):
    root = build_run(tmp_path)
    path, receipt = read_receipt(root)
    receipt["sources"][0]["raw_artifact_path"] = "raw/../../intake_manifest.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(IndependentVerificationError, match="RAW_PATH_ESCAPES_ROOT_OR_FILE_MISSING|RAW_PATH_INVALID"):
        verify_intake(root)


def test_redteam_manifest_source_swap_is_rejected(tmp_path):
    root = build_run(tmp_path)
    path = root / "intake_manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["sources"][0]["source_ref"] = "ISSUER:INVESTOR_RELATIONS_PUBLIC"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(IndependentVerificationError, match="MANIFEST_SHA256_MISMATCH"):
        verify_intake(root)


def test_redteam_unknown_pit_cannot_be_promoted_by_receipt_edit(tmp_path):
    input_root = tmp_path / "incoming" / "raw_input"
    input_root.mkdir(parents=True)
    (input_root / "announcement.pdf").write_bytes(BODY)
    value = manifest()
    value["sources"][0]["known_at"] = ""
    value["sources"][0]["known_at_basis"] = ""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    root = tmp_path / "run-output"
    intake.capture_sources(manifest_path, out_dir=root, input_root=input_root.parent)
    path, receipt = read_receipt(root)
    receipt["sources"][0]["pit_status"] = "PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(IndependentVerificationError, match="PIT_STATUS_MISMATCH"):
        verify_intake(root)


def test_independent_verifier_does_not_import_collector():
    source = (Path(__file__).parents[1] / "tools" / "verify_company_evidence_intake.py").read_text(encoding="utf-8")
    assert "company_evidence_intake import" not in source
    assert "from tools.company_evidence_intake" not in source
