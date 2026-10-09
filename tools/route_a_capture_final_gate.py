from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class CaptureFinalGateError(ValueError):
    """The run did not create a trustworthy raw-evidence artifact."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptureFinalGateError("REQUIRED_RUN_ARTIFACT_MISSING_OR_INVALID_JSON") from exc
    if not isinstance(data, dict):
        raise CaptureFinalGateError("REQUIRED_RUN_ARTIFACT_MUST_BE_OBJECT")
    return data


def validate_capture_final_gate(
    root: str | Path,
    *,
    capture_outcome: str,
    verify_outcome: str,
    b2_preflight_outcome: str,
    upload_outcome: str,
) -> dict[str, Any]:
    """Accept a byte-verified complete or partial capture, never evidence admission."""
    root_path = Path(root).resolve()
    if verify_outcome != "success":
        raise CaptureFinalGateError("INDEPENDENT_INTEGRITY_VERIFIER_STEP_NOT_SUCCESS")
    if b2_preflight_outcome != "success":
        raise CaptureFinalGateError("B2_PREFLIGHT_EXECUTION_NOT_SUCCESS")
    if upload_outcome != "success":
        raise CaptureFinalGateError("EVIDENCE_ARTIFACT_UPLOAD_NOT_SUCCESS")

    receipt = _read_json(root_path / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json")
    verification = _read_json(root_path / "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json")
    preflight = _read_json(root_path / "ROUTE_A_B2_PREFLIGHT.json")

    if receipt.get("admission_status") != "NOT_ADMITTED":
        raise CaptureFinalGateError("CAPTURE_RECEIPT_MUST_REMAIN_NOT_ADMITTED")
    if verification.get("status") != "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION":
        raise CaptureFinalGateError("INDEPENDENT_INTEGRITY_STATUS_INVALID")
    if preflight.get("raw_integrity_status") != verification.get("status"):
        raise CaptureFinalGateError("B2_PREFLIGHT_RAW_INTEGRITY_BINDING_MISMATCH")
    if preflight.get("evidence_admission") is not False or preflight.get("pit_admission") is not False:
        raise CaptureFinalGateError("B2_PREFLIGHT_MUST_NOT_CLAIM_ADMISSION")
    if preflight.get("source_origin_verified") is not False:
        raise CaptureFinalGateError("B2_PREFLIGHT_MUST_NOT_CLAIM_SOURCE_ORIGIN_VERIFIED")

    rows = receipt.get("sources")
    if not isinstance(rows, list) or not rows:
        raise CaptureFinalGateError("CAPTURE_RECEIPT_SOURCE_ROWS_INVALID")
    succeeded = sum(1 for row in rows if isinstance(row, dict) and row.get("capture_status") == "SUCCESS")
    failed = sum(1 for row in rows if isinstance(row, dict) and row.get("capture_status") == "FAILED")
    if succeeded + failed != len(rows):
        raise CaptureFinalGateError("CAPTURE_RECEIPT_SOURCE_STATUS_INVALID")

    raw_verified = verification.get("raw_bytes_verified")
    if isinstance(raw_verified, bool) or not isinstance(raw_verified, int):
        raise CaptureFinalGateError("RAW_BYTES_VERIFIED_COUNT_INVALID")
    if raw_verified != succeeded:
        raise CaptureFinalGateError("CAPTURE_SUCCESS_COUNT_MISMATCHES_VERIFIED_RAW_BYTES")
    if raw_verified <= 0:
        raise CaptureFinalGateError("NO_VERIFIED_RAW_BYTES")

    status = receipt.get("status")
    if status == "CAPTURED_NOT_ADMITTED":
        if failed != 0 or succeeded != len(rows) or capture_outcome != "success":
            raise CaptureFinalGateError("COMPLETE_CAPTURE_STATUS_MISMATCH")
        expected_b2 = "BLOCKED_NOT_ADMITTED"
        gate_status = "CAPTURE_COMPLETE_NOT_ADMITTED"
    elif status == "PARTIAL_CAPTURE_NOT_ADMITTED":
        if succeeded <= 0 or failed <= 0 or capture_outcome != "failure":
            raise CaptureFinalGateError("PARTIAL_CAPTURE_STATUS_MISMATCH")
        expected_b2 = "BLOCKED_NOT_ADMITTED"
        gate_status = "PARTIAL_CAPTURE_VERIFIED_NOT_ADMITTED"
    else:
        raise CaptureFinalGateError("CAPTURE_RECEIPT_STATUS_INVALID")
    if preflight.get("status") != expected_b2:
        raise CaptureFinalGateError("B2_PREFLIGHT_STATUS_INVALID_FOR_CAPTURED_BYTES")
    if preflight.get("raw_bytes_verified") != raw_verified:
        raise CaptureFinalGateError("B2_PREFLIGHT_RAW_BYTE_COUNT_MISMATCH")
    if preflight.get("case_id") != receipt.get("case_id"):
        raise CaptureFinalGateError("B2_PREFLIGHT_CASE_ID_MISMATCH")
    if preflight.get("intake_receipt_status") != status:
        raise CaptureFinalGateError("B2_PREFLIGHT_RECEIPT_STATUS_MISMATCH")

    return {
        "status": gate_status,
        "case_id": receipt.get("case_id"),
        "capture_receipt_status": status,
        "sources_declared": len(rows),
        "sources_captured": succeeded,
        "sources_failed": failed,
        "raw_bytes_verified": raw_verified,
        "raw_integrity": "PASS",
        "b2_preflight": expected_b2,
        "evidence_admission": False,
        "pit_admission": False,
        "llm_provider_required": False,
        "meaning": (
            "Partial capture retained; failed source rows remain explicit in the receipt."
            if failed
            else "All declared sources captured and byte-verified."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate complete or partial Route A capture artifacts without promoting them to B2 evidence."
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--capture-outcome", required=True, choices=("success", "failure", "cancelled", "skipped"))
    parser.add_argument("--verify-outcome", required=True, choices=("success", "failure", "cancelled", "skipped"))
    parser.add_argument("--b2-preflight-outcome", required=True, choices=("success", "failure", "cancelled", "skipped"))
    parser.add_argument("--upload-outcome", required=True, choices=("success", "failure", "cancelled", "skipped"))
    args = parser.parse_args()
    try:
        report = validate_capture_final_gate(
            args.root,
            capture_outcome=args.capture_outcome,
            verify_outcome=args.verify_outcome,
            b2_preflight_outcome=args.b2_preflight_outcome,
            upload_outcome=args.upload_outcome,
        )
    except (OSError, CaptureFinalGateError) as exc:
        code = str(exc) if isinstance(exc, CaptureFinalGateError) else "RUN_ARTIFACT_NOT_AVAILABLE"
        print(json.dumps({
            "status": "CAPTURE_FINAL_GATE_REJECTED",
            "error_code": code,
            "evidence_admission": False,
            "pit_admission": False,
        }, sort_keys=True))
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
