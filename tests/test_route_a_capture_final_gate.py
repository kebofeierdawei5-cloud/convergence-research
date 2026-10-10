from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.route_a_capture_final_gate import CaptureFinalGateError, validate_capture_final_gate


def _write_run(root: Path, *, status="CAPTURED_NOT_ADMITTED", succeeded=2, failed=0, payload_mismatches=0):
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(succeeded):
        mismatch = index < payload_mismatches
        rows.append({
            "source_id": f"OK-{index}", "capture_status": "SUCCESS",
            "expected_payload_type": "PDF" if mismatch else "ANY",
            "payload_contract_status": "MISMATCH" if mismatch else "NOT_CHECKED",
            "payload_contract_error": "EXPECTED_PDF_RECEIVED_HTML_OR_ACCESS_CHALLENGE" if mismatch else None,
        })
    for index in range(failed):
        rows.append({"source_id": f"FAIL-{index}", "capture_status": "FAILED"})
    receipt = {
        "schema_version": "IIOS-COMPANY-EVIDENCE-INTAKE-RECEIPT-0.1",
        "case_id": "RC-CN-A-000001-20261009",
        "status": status,
        "admission_status": "NOT_ADMITTED",
        "sources": rows,
    }
    verification = {
        "status": "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION",
        "raw_bytes_verified": succeeded,
        "payload_contract_checked": payload_mismatches,
        "payload_contract_passes": 0,
        "payload_contract_mismatches": payload_mismatches,
    }
    preflight = {
        "schema_version": "IIOS-ROUTE-A-B2-PREFLIGHT-0.1",
        "status": "BLOCKED_NOT_ADMITTED" if succeeded else "BLOCKED_NO_RAW_BYTES",
        "case_id": receipt["case_id"],
        "intake_receipt_status": status,
        "raw_integrity_status": verification["status"],
        "raw_bytes_verified": succeeded,
        "payload_contract_failure_count": payload_mismatches,
        "source_origin_verified": False,
        "evidence_admission": False,
        "pit_admission": False,
    }
    for name, value in (
        ("COMPANY_EVIDENCE_INTAKE_RECEIPT.json", receipt),
        ("COMPANY_EVIDENCE_INTAKE_VERIFICATION.json", verification),
        ("ROUTE_A_B2_PREFLIGHT.json", preflight),
    ):
        (root / name).write_text(json.dumps(value), encoding="utf-8")


def _validate(root, **overrides):
    arguments = {
        "capture_outcome": "success",
        "verify_outcome": "success",
        "b2_preflight_outcome": "success",
        "upload_outcome": "success",
    }
    arguments.update(overrides)
    return validate_capture_final_gate(root, **arguments)


def test_complete_capture_artifact_is_accepted_but_not_admitted(tmp_path):
    _write_run(tmp_path / "complete")
    result = _validate(tmp_path / "complete")
    assert result["status"] == "CAPTURE_COMPLETE_NOT_ADMITTED"
    assert result["sources_captured"] == 2
    assert result["sources_failed"] == 0
    assert result["evidence_admission"] is False
    assert result["pit_admission"] is False
    assert result["llm_provider_required"] is False


def test_partial_capture_with_verified_bytes_is_preserved_not_misreported_complete(tmp_path):
    root = tmp_path / "partial"
    _write_run(root, status="PARTIAL_CAPTURE_NOT_ADMITTED", succeeded=2, failed=1)
    result = _validate(root, capture_outcome="failure")
    assert result["status"] == "PARTIAL_CAPTURE_VERIFIED_NOT_ADMITTED"
    assert result["sources_captured"] == 2
    assert result["sources_failed"] == 1
    assert "failed source rows remain explicit" in result["meaning"]


def test_complete_raw_capture_with_html_challenge_bytes_is_not_reported_as_complete_documents(tmp_path):
    root = tmp_path / "payload-mismatch"
    _write_run(root, succeeded=2, failed=0, payload_mismatches=1)
    result = _validate(root)
    assert result["status"] == "RAW_CAPTURE_COMPLETE_WITH_PAYLOAD_MISMATCHES_NOT_ADMITTED"
    assert result["sources_captured"] == 2
    assert result["payload_contract_mismatches"] == 1
    assert "not emitted as B2 Evidence Records" in result["meaning"]
    assert result["evidence_admission"] is False
    assert result["pit_admission"] is False


def test_partial_capture_with_zero_verified_bytes_is_rejected(tmp_path):
    root = tmp_path / "empty"
    _write_run(root, status="PARTIAL_CAPTURE_NOT_ADMITTED", succeeded=0, failed=2)
    with pytest.raises(CaptureFinalGateError, match="NO_VERIFIED_RAW_BYTES"):
        _validate(root, capture_outcome="failure")


def test_partial_capture_cannot_claim_successful_capture_step(tmp_path):
    root = tmp_path / "mismatch"
    _write_run(root, status="PARTIAL_CAPTURE_NOT_ADMITTED", succeeded=1, failed=1)
    with pytest.raises(CaptureFinalGateError, match="PARTIAL_CAPTURE_STATUS_MISMATCH"):
        _validate(root, capture_outcome="success")


def test_complete_capture_cannot_hide_capture_step_failure(tmp_path):
    root = tmp_path / "mismatch-complete"
    _write_run(root)
    with pytest.raises(CaptureFinalGateError, match="COMPLETE_CAPTURE_STATUS_MISMATCH"):
        _validate(root, capture_outcome="failure")


@pytest.mark.parametrize(
    ("field", "kwargs", "message"),
    [
        ("verify", {"verify_outcome": "failure"}, "INDEPENDENT_INTEGRITY_VERIFIER_STEP_NOT_SUCCESS"),
        ("preflight", {"b2_preflight_outcome": "failure"}, "B2_PREFLIGHT_EXECUTION_NOT_SUCCESS"),
        ("upload", {"upload_outcome": "failure"}, "EVIDENCE_ARTIFACT_UPLOAD_NOT_SUCCESS"),
    ],
)
def test_failed_verifier_preflight_or_upload_still_fails_closed(tmp_path, field, kwargs, message):
    root = tmp_path / field
    _write_run(root)
    with pytest.raises(CaptureFinalGateError, match=message):
        _validate(root, **kwargs)


def test_forged_b2_admission_claim_is_rejected(tmp_path):
    root = tmp_path / "forged"
    _write_run(root)
    path = root / "ROUTE_A_B2_PREFLIGHT.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence_admission"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CaptureFinalGateError, match="B2_PREFLIGHT_MUST_NOT_CLAIM_ADMISSION"):
        _validate(root)
