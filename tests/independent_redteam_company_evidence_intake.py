from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_company_evidence_intake import BODY, manifest, prepare_input, write_manifest
from tools import company_evidence_intake as intake
from tools.verify_company_evidence_intake import IndependentVerificationError, verify_intake


def build_run(tmp_path):
    input_root = prepare_input(tmp_path)
    manifest_path = write_manifest(tmp_path, manifest())
    out = tmp_path / "run-output"
    intake.capture_sources(manifest_path, out_dir=out, input_root=input_root)
    return out


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
    manifest_value = json.loads(path.read_text(encoding="utf-8"))
    manifest_value["sources"][0]["source_ref"] = "ISSUER:INVESTOR_RELATIONS_PUBLIC"
    path.write_text(json.dumps(manifest_value), encoding="utf-8")
    with pytest.raises(IndependentVerificationError, match="MANIFEST_SHA256_MISMATCH"):
        verify_intake(root)


def test_redteam_receipt_cannot_upgrade_unknown_pit(tmp_path):
    value = manifest()
    value["sources"][0]["known_at"] = None
    value["sources"][0]["known_at_basis"] = ""
    input_root = prepare_input(tmp_path)
    manifest_path = write_manifest(tmp_path, value)
    root = tmp_path / "run-output"
    intake.capture_sources(manifest_path, out_dir=root, input_root=input_root)
    path, receipt = read_receipt(root)
    receipt["sources"][0]["pit_status"] = "PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(IndependentVerificationError, match="PIT_STATUS_MISMATCH"):
        verify_intake(root)
