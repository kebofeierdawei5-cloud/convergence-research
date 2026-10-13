from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from iios_mvp.c2_independent_fact_review_v01 import (
    EXPECTED_CASE_ID,
    EXPECTED_CUTOFF,
    EXPECTED_FACT_COUNT,
    ReviewPacketError,
    _ensure_private_output_path,
    build_review_packet,
    prepare_review_packet,
)
from iios_mvp.canonical_signed_evidence_admission_v01 import _sha256


def _report() -> dict:
    source_ids = [
        "SZSE-2026-H1-SUMMARY",
        "SZSE-2026-H1-FULL",
        "SZSE-2026-BUYBACK-PLAN",
    ]
    facts = []
    for index in range(EXPECTED_FACT_COUNT):
        source_id = source_ids[index % len(source_ids)]
        facts.append({
            "fact_id": f"XHC-FACT-TEST-{index + 1:03d}",
            "label": f"Public filing fact label {index + 1}",
            "source_id": source_id,
            "physical_pdf_page": index + 1,
            "source_pdf_sha256": f"{index + 1:064x}",
            "source_pdf_size_bytes": 1000 + index,
            "conservative_known_at": "2026-08-20T23:59:59+08:00",
            "known_at_before_cutoff": True,
            "official_https_szse_url": True,
            "url_date_matches_intake_publication_date": True,
            "locator_status": "PASS",
            "license_status": "PUBLIC_ACCESS_REUSE_UNKNOWN",
            "retention_permission_declared": False,
        })
    return {
        "archive_record_schema": "IIOS-C2-P3-CI-RESULT-ARCHIVE-0.1",
        "ci_provenance": {
            "workflow_name": "IIOS Route A C2-P3 Separate-Method Fact Review",
            "workflow_run_id": 12345,
            "workflow_run_url": "https://github.com/example/repo/actions/runs/12345",
            "workflow_head_sha": "a" * 40,
            "downloaded_artifact_zip_sha256": "b" * 64,
            "original_report_json_sha256": "c" * 64,
        },
        "result": {
            "case_id": EXPECTED_CASE_ID,
            "cutoff": EXPECTED_CUTOFF,
            "fact_count": EXPECTED_FACT_COUNT,
            "fact_locator_pass_count": EXPECTED_FACT_COUNT,
            "all_conservative_known_at_before_cutoff": True,
            "all_fact_locators_pass": True,
            "all_source_urls_https_official_szse": True,
            "all_url_date_matches_intake_publication_date": True,
            "same_day_buyback_progress_excluded": True,
            "market_price_value_in_report": False,
            "formal_signed_admission_created": False,
            "facts": facts,
        },
    }


def test_review_packet_contains_thirteen_pending_facts_and_never_claims_admission():
    packet = build_review_packet(_report(), source_report_ref="test-review-report.json")

    assert packet["schema_version"] == "IIOS-C2-INDEPENDENT-FACT-USE-REVIEW-PACKET-0.1"
    assert packet["record_class"] == "HUMAN_REVIEW_TEMPLATE_NOT_SIGNED_NOT_ADMITTED"
    assert packet["status"] == "TEMPLATE_PENDING_NOT_REVIEWED"
    assert packet["case"]["case_id"] == EXPECTED_CASE_ID
    assert packet["case"]["cutoff"] == EXPECTED_CUTOFF
    assert len(packet["facts"]) == 13
    assert packet["independent_review"]["review_status"] == "PENDING"
    assert packet["independent_review"]["completed_fact_count"] == 0
    assert packet["independent_review"]["allowed_uses"]["private_storage"] == "PENDING"
    assert all(row["independent_review"]["disposition"] == "PENDING" for row in packet["facts"])
    assert all(row["machine_reuse_status"] == "PUBLIC_ACCESS_REUSE_UNKNOWN" for row in packet["facts"])
    assert packet["non_claims"]
    assert "formal_admission_created" not in packet


def test_prepare_review_packet_writes_mode_0600_outside_repo(tmp_path):
    report_path = tmp_path / "ci-report.json"
    report_path.write_text(json.dumps(_report(), ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "private" / "review-packet.json"

    result = prepare_review_packet(report_path=report_path, output_path=output_path)
    packet = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["status"] == "REVIEW_PACKET_CREATED_NOT_REVIEWED"
    assert result["fact_count"] == 13
    assert result["formal_admission_created"] is False
    assert packet["status"] == "TEMPLATE_PENDING_NOT_REVIEWED"
    if os.name != "nt":
        assert (output_path.stat().st_mode & 0o777) == 0o600
        assert (output_path.parent.stat().st_mode & 0o777) == 0o700


def test_review_packet_rejects_wrong_case_cutoff_or_incomplete_locator_report():
    report = _report()
    report["result"]["case_id"] = "RC-CN-A-605016-20261009"
    with pytest.raises(ReviewPacketError, match="SOURCE_REVIEW_CASE_OR_CUTOFF_MISMATCH"):
        build_review_packet(report, source_report_ref="test")

    report = _report()
    report["result"]["fact_locator_pass_count"] = 12
    with pytest.raises(ReviewPacketError, match="SOURCE_REVIEW_LOCATOR_COUNT_NOT_PASS"):
        build_review_packet(report, source_report_ref="test")


def test_review_packet_refuses_price_values_or_reuse_status_upgrade():
    report = _report()
    report["result"]["market_price_value_in_report"] = True
    with pytest.raises(ReviewPacketError, match="SOURCE_REVIEW_MUST_NOT_INCLUDE_MARKET_PRICE"):
        build_review_packet(report, source_report_ref="test")

    report = _report()
    report["result"]["facts"][0]["license_status"] = "ALLOWED"
    with pytest.raises(ReviewPacketError, match="SOURCE_REVIEW_REUSE_STATUS_CHANGED"):
        build_review_packet(report, source_report_ref="test")


def test_review_packet_rejects_duplicate_fact_ids_and_unmapped_source_ids():
    report = _report()
    report["result"]["facts"][1]["fact_id"] = report["result"]["facts"][0]["fact_id"]
    with pytest.raises(ReviewPacketError, match="SOURCE_REVIEW_FACT_ID_OR_LABEL_INVALID"):
        build_review_packet(report, source_report_ref="test")

    report = _report()
    report["result"]["facts"][0]["source_id"] = "UNKNOWN-SOURCE"
    with pytest.raises(ReviewPacketError, match="SOURCE_REVIEW_SOURCE_ID_UNMAPPED"):
        build_review_packet(report, source_report_ref="test")


def test_review_packet_never_allows_output_inside_repository():
    from iios_mvp.c2_independent_fact_review_v01 import __file__ as module_path

    root = Path(module_path).resolve().parents[1]
    candidate = root / "must-not-create-c2-review-packet.json"
    with pytest.raises(ReviewPacketError, match="REVIEW_PACKET_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY"):
        _ensure_private_output_path(candidate)
    assert not candidate.exists()
