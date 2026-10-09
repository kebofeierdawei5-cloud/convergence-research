from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import company_evidence_intake as intake
from tools.route_a_b2_preflight import run_route_a_b2_preflight
from tools.verify_company_evidence_intake import IndependentVerificationError

RAW = b"%PDF-1.7\x00adversarial-source-bytes"


def make_run(tmp_path, declared_known_at="2026-10-01"):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "source.pdf").write_bytes(RAW)
    manifest = {
        "schema_version": intake.MANIFEST_SCHEMA,
        "case_id": "RC-CN-A-000001-20261009",
        "market": "CN-A",
        "symbol": "000001",
        "cutoff_date": "2026-10-09",
        "sources": [{
            "source_id": "SOURCE-RT-001",
            "field_group": "security_identity",
            "source_ref": "TEST:UNVERIFIED_PRIMARY",
            "source_class": "ISSUER_PRIMARY",
            "local_path": "source.pdf",
            "known_at": declared_known_at,
            "known_at_basis": "Attacker-declared date; not authenticated",
            "published_at": declared_known_at,
            "license_status": "PUBLIC_ACCESS_REUSE_UNKNOWN",
        }],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    root = tmp_path / "run"
    intake.capture_sources(manifest_path, out_dir=root, input_root=incoming)
    return root


def test_redteam_pre_cutoff_claim_does_not_become_admitted_known_at(tmp_path):
    root = make_run(tmp_path)
    report = run_route_a_b2_preflight(root)
    b2_manifest = json.loads((root / "B2_COMPANY_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED_NOT_ADMITTED"
    assert b2_manifest["evidence"][0]["known_at"] is None
    assert b2_manifest["evidence"][0]["status"] == "UNKNOWN"
    assert b2_manifest["evidence"][0]["provenance_class"] == "UNKNOWN"
    assert not report["evidence_admission"] and not report["pit_admission"]


def test_redteam_missing_known_at_does_not_inherit_retrieved_at(tmp_path):
    root = make_run(tmp_path, declared_known_at="")
    report = run_route_a_b2_preflight(root)
    b2_manifest = json.loads((root / "B2_COMPANY_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
    evidence = b2_manifest["evidence"][0]
    assert evidence["known_at"] is None
    assert evidence["known_at"] != evidence["retrieved_at"]
    assert report["status"] == "BLOCKED_NOT_ADMITTED"


def test_redteam_tampered_raw_bytes_are_rejected_before_b2(tmp_path):
    root = make_run(tmp_path)
    path = root / "raw" / "SOURCE-RT-001.pdf"
    path.write_bytes(RAW[:-1] + b"!")
    with pytest.raises(IndependentVerificationError, match="RAW_SHA256_MISMATCH"):
        run_route_a_b2_preflight(root)
