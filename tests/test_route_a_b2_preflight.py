from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools import company_evidence_intake as intake
from tools.route_a_b2_preflight import (
    REPORT_FILENAME,
    RouteAB2PreflightError,
    _b2_cutoff_end_of_day,
    run_route_a_b2_preflight,
)
from tools.verify_company_evidence_intake import IndependentVerificationError

ROOT = Path(__file__).parents[1]
RAW = b"%PDF-1.7\x00source-bytes-retained"


def _manifest(*, sources=None):
    return {
        "schema_version": intake.MANIFEST_SCHEMA,
        "case_id": "RC-CN-A-000001-20261009",
        "market": "CN-A",
        "symbol": "000001",
        "cutoff_date": "2026-10-09",
        "sources": sources or [{
            "source_id": "SOURCE-001",
            "field_group": "financial_reality",
            "source_ref": "TEST:OFFICIAL_DOCUMENT",
            "source_class": "OFFICIAL_EXCHANGE",
            "local_path": "source.pdf",
            "known_at": "2026-10-01",
            "known_at_basis": "Declared in input only; not authenticated",
            "published_at": "2026-10-01",
            "license_status": "PUBLIC_ACCESS_REUSE_UNKNOWN",
        }],
    }


def _capture(tmp_path, *, sources=None, raw_file=True):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    if raw_file:
        (incoming / "source.pdf").write_bytes(RAW)
    manifest_path = tmp_path / "input-manifest.json"
    manifest_path.write_text(json.dumps(_manifest(sources=sources), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "run"
    receipt = intake.capture_sources(manifest_path, out_dir=output, input_root=incoming)
    return output, receipt


def test_date_only_cutoff_is_expanded_to_eod_plus_0800():
    assert _b2_cutoff_end_of_day("2026-10-09") == "2026-10-09T23:59:59+08:00"


def test_b2_preflight_reuses_exact_bytes_but_keeps_declared_known_at_unknown(tmp_path):
    root, receipt = _capture(tmp_path)
    assert receipt["sources"][0]["capture_status"] == "SUCCESS"

    report = run_route_a_b2_preflight(root, company="TESTCO")
    b2_manifest = json.loads((root / "B2_COMPANY_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "company_evidence_manifest_v0.1.schema.json").read_text(encoding="utf-8"))
    evidence_schema = json.loads((ROOT / "schemas" / "evidence_record_v0.1.schema.json").read_text(encoding="utf-8"))
    from referencing import Registry, Resource
    registry = Registry().with_resource(evidence_schema["$id"], Resource.from_contents(evidence_schema))
    Draft202012Validator(schema, registry=registry).validate(b2_manifest)

    assert report["status"] == "BLOCKED_NOT_ADMITTED"
    assert report["raw_integrity_status"] == "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION"
    assert report["raw_bytes_verified"] == 1
    assert report["captured_source_count"] == 1
    assert report["evidence_admission"] is False
    assert report["pit_admission"] is False
    assert report["llm_provider_required"] is False
    assert report["admitted_field_groups"] == []
    assert len(report["missing_required_field_groups"]) == 7
    evidence = b2_manifest["evidence"][0]
    assert evidence["known_at"] is None
    assert evidence["provenance_class"] == "UNKNOWN"
    assert evidence["status"] == "UNKNOWN"
    assert any(note == "DECLARED_KNOWN_AT_NOT_ADMITTED=2026-10-01" for note in evidence["quality_notes"])
    assert any(item.startswith("EVIDENCE[ROUTEA-SOURCE-SOURCE-001]:PIT:PIT_UNKNOWN:") for item in b2_manifest["validation_errors"])
    assert (root / REPORT_FILENAME).is_file()


def test_b2_preflight_reports_partial_capture_without_forging_failed_sources(tmp_path):
    extra = {
        "source_id": "SOURCE-MISSING",
        "field_group": "market_price",
        "source_ref": "TEST:PUBLIC_MARKET_SOURCE",
        "source_class": "PUBLIC_SECONDARY",
        "local_path": "missing.pdf",
        "known_at": "",
        "known_at_basis": "",
        "published_at": "",
        "license_status": "UNKNOWN",
    }
    root, receipt = _capture(tmp_path, sources=[_manifest()["sources"][0], extra], raw_file=True)
    report = run_route_a_b2_preflight(root)
    assert report["status"] == "BLOCKED_NOT_ADMITTED"
    assert report["captured_source_count"] == 1
    assert report["uncaptured_source_count"] == 1
    rows = {row["source_id"]: row for row in report["sources"]}
    assert rows["SOURCE-001"]["b2_evidence_status"] == "UNKNOWN"
    assert rows["SOURCE-MISSING"]["b2_evidence_status"] == "NO_RECORD_NO_RAW_BYTES"
    assert rows["SOURCE-MISSING"]["sha256"] is None
    assert "market_price" in report["missing_required_field_groups"]


def test_byte_tampering_aborts_b2_preflight(tmp_path):
    root, _ = _capture(tmp_path)
    raw = root / "raw" / "SOURCE-001.pdf"
    raw.write_bytes(RAW + b"tampered")
    with pytest.raises(IndependentVerificationError, match="RAW_SHA256_MISMATCH"):
        run_route_a_b2_preflight(root)


def test_preflight_report_matches_its_schema(tmp_path):
    root, _ = _capture(tmp_path)
    report = run_route_a_b2_preflight(root)
    schema = json.loads((ROOT / "schemas" / "route_a_b2_preflight_v0.1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
