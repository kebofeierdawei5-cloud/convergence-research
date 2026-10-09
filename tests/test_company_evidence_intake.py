from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools import company_evidence_intake as intake
from tools.verify_company_evidence_intake import IndependentVerificationError, verify_intake

ROOT = Path(__file__).parents[1]
BODY = b"%PDF-1.7\x00exact-official-source-bytes\x01"


def manifest(*, source_overrides=None, sources=None):
    source = {
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
    }
    source.update(source_overrides or {})
    return {
        "schema_version": intake.MANIFEST_SCHEMA,
        "case_id": "RC-CN-A-300750-20261009",
        "market": "CN-A",
        "symbol": "300750",
        "cutoff_date": "2026-10-09",
        "sources": [source] if sources is None else sources,
    }


def write_manifest(tmp_path, value):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def prepare_input(tmp_path):
    input_root = tmp_path / "incoming"
    raw_input = input_root / "raw_input"
    raw_input.mkdir(parents=True)
    (raw_input / "announcement.pdf").write_bytes(BODY)
    return input_root


def run_capture(tmp_path, value=None, *, source_overrides=None):
    input_root = prepare_input(tmp_path)
    if value is None:
        value = manifest(source_overrides=source_overrides)
    path = write_manifest(tmp_path, value)
    out = tmp_path / "run-output"
    receipt = intake.capture_sources(path, out_dir=out, input_root=input_root)
    return input_root, out, receipt


def test_manual_original_bytes_are_retained_and_hash_bound(tmp_path):
    _, out, receipt = run_capture(tmp_path)
    raw = out / "raw" / "SZSE-ANNOUNCEMENT-001.pdf"
    assert raw.read_bytes() == BODY
    assert receipt["sources"][0]["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert receipt["sources"][0]["capture_status"] == "SUCCESS"
    assert receipt["status"] == "CAPTURED_NOT_ADMITTED"
    assert receipt["admission_status"] == "NOT_ADMITTED"
    assert receipt["sources"][0]["source_authenticity_status"] == "UNVERIFIED"
    report = verify_intake(out)
    assert report["status"] == "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION"
    assert report["raw_bytes_verified"] == 1
    assert report["evidence_admission"] is False


def test_https_download_retains_exact_response_bytes(monkeypatch, tmp_path):
    value = manifest(source_overrides={
        "url": "https://www.szse.cn/disclosure/announcement.pdf",
    })
    value["sources"][0].pop("local_path")
    input_root = tmp_path / "unused"
    input_root.mkdir()
    path = write_manifest(tmp_path, value)

    class Response:
        status = 200
        headers = {"Content-Type": "application/pdf"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __init__(self):
            self.payload = BODY

        def read(self, amount=-1):
            if amount < 0:
                data, self.payload = self.payload, b""
                return data
            data, self.payload = self.payload[:amount], self.payload[amount:]
            return data

    class Opener:
        def open(self, request, timeout):
            assert request.full_url.startswith("https://")
            assert timeout == 30
            return Response()

    monkeypatch.setattr(intake, "build_opener", lambda handler: Opener())
    out = tmp_path / "download-output"
    receipt = intake.capture_sources(path, out_dir=out, input_root=input_root)
    assert receipt["sources"][0]["http_status"] == 200
    assert (out / "raw" / "SZSE-ANNOUNCEMENT-001.pdf").read_bytes() == BODY
    assert receipt["sources"][0]["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert verify_intake(out)["raw_bytes_verified"] == 1


def test_missing_known_at_remains_unknown_and_cannot_admit(tmp_path):
    _, out, receipt = run_capture(tmp_path, source_overrides={"known_at": None, "known_at_basis": ""})
    row = receipt["sources"][0]
    assert row["pit_status"] == "UNKNOWN_NO_KNOWN_AT"
    assert row["admission_status"] == "NOT_ADMITTED"
    assert verify_intake(out)["unknown_pit_sources"] == 1


def test_known_after_cutoff_is_captured_but_pit_blocked(tmp_path):
    _, out, receipt = run_capture(
        tmp_path,
        source_overrides={
            "known_at": "2026-10-10",
            "known_at_basis": "Declared publication date after case cutoff.",
            "published_at": "2026-10-10",
        },
    )
    assert receipt["sources"][0]["pit_status"] == "BLOCKED_KNOWN_AFTER_CUTOFF"
    assert receipt["admission_status"] == "NOT_ADMITTED"
    assert verify_intake(out)["future_known_sources"] == 1


def test_known_before_cutoff_is_only_a_candidate_not_admission(tmp_path):
    _, out, receipt = run_capture(tmp_path)
    assert receipt["sources"][0]["pit_status"] == "PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW"
    assert receipt["admission_status"] == "NOT_ADMITTED"
    assert verify_intake(out)["evidence_admission"] is False


def test_remote_sources_require_https_and_reject_credential_urls():
    with pytest.raises(intake.IntakeError, match="SOURCE_URL_MUST_USE_HTTPS"):
        intake._validate_source_url("http://www.szse.cn/report.pdf")
    with pytest.raises(intake.IntakeError, match="SOURCE_URL_USERINFO_FORBIDDEN"):
        intake._validate_source_url("https://user:pass@www.szse.cn/report.pdf")
    with pytest.raises(intake.IntakeError, match="POSSIBLE_CREDENTIAL_IN_SOURCE_URL"):
        intake._validate_source_url("https://example.org/download?api_key=secret")


def test_local_path_traversal_and_duplicate_ids_are_rejected():
    with pytest.raises(intake.IntakeError, match="LOCAL_PATH_MUST_BE_SAFE_RELATIVE_PATH"):
        intake.validate_manifest(manifest(source_overrides={"local_path": "../outside.pdf"}))
    duplicated = manifest(sources=[
        manifest()["sources"][0],
        manifest()["sources"][0],
    ])
    with pytest.raises(intake.IntakeError, match="DUPLICATE_SOURCE_ID"):
        intake.validate_manifest(duplicated)


def test_new_run_output_must_be_empty_and_append_only(tmp_path):
    input_root = prepare_input(tmp_path)
    path = write_manifest(tmp_path, manifest())
    out = tmp_path / "already-used"
    out.mkdir()
    (out / "older-run.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(intake.IntakeError, match="OUTPUT_DIRECTORY_MUST_BE_EMPTY_APPEND_ONLY_RUN"):
        intake.capture_sources(path, out_dir=out, input_root=input_root)
    assert (out / "older-run.txt").read_text(encoding="utf-8") == "do not overwrite"


def test_invalid_identity_and_empty_source_set_fail_closed():
    bad = manifest()
    bad["case_id"] = "RC-CN-A-OTHER-20261009"
    with pytest.raises(intake.IntakeError, match="CASE_ID_MARKET_SYMBOL_CUTOFF_MISMATCH"):
        intake.validate_manifest(bad)
    empty = manifest(sources=[])
    with pytest.raises(intake.IntakeError, match="SOURCES_MUST_CONTAIN_1_TO_100_ITEMS"):
        intake.validate_manifest(empty)


def test_verifier_does_not_depend_on_collector_module():
    source = (ROOT / "tools" / "verify_company_evidence_intake.py").read_text(encoding="utf-8")
    assert "company_evidence_intake import" not in source
    assert "from tools.company_evidence_intake" not in source
