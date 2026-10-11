from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research.b2.evidence_contract import assert_pit, validate_evidence_record
from tools.iios_operator_market_price_attestation_v01 import (
    OperatorMarketPriceAttestationError,
    build_operator_market_price_bundle,
)

CASE_ID = "RC-CN-A-000001-20261009"


def _bundle(tmp_path: Path, **overrides):
    args = {
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "002001",
        "company": "TESTCO",
        "cutoff_date": "2026-10-09",
        "observation_date": "2026-10-08",
        "close_price": "123.45",
        "currency": "CNY",
        "source_ref": "OPERATOR-PROVIDED:historical close assertion",
        "out_dir": tmp_path / "private-bundle",
        "operator_confirmed": True,
        "known_by_cutoff_confirmed": True,
        "known_at": None,
        "attested_at": "2026-10-11T12:00:00+08:00",
    }
    args.update(overrides)
    return build_operator_market_price_bundle(**args)


def test_creates_private_hash_bound_attestation_without_source_fetch(tmp_path):
    result = _bundle(tmp_path)
    root = tmp_path / "private-bundle"
    raw = root / "raw" / "operator_market_price_attestation.json"
    payload = json.loads(raw.read_text(encoding="utf-8"))
    evidence = json.loads((root / "evidence_record.json").read_text(encoding="utf-8"))
    declaration = json.loads((root / "raw_artifact_declaration.json").read_text(encoding="utf-8"))
    assert result["status"] == "OPERATOR_ATTESTATION_CREATED_NOT_SOURCE_VERIFIED"
    assert result["secondary_web_audit_performed"] is False
    assert result["original_vendor_bytes_received"] is False
    assert result["close_price_in_summary"] is False
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    assert digest == evidence["content_sha256"] == declaration["expected_sha256"]
    assert declaration["expected_size_bytes"] == raw.stat().st_size
    assert payload["close_price"] == "123.45"
    assert evidence["provenance_class"] == "OPERATOR_ATTESTED_MARKET_DATA"
    assert evidence["status"] == "ADMITTED"
    assert validate_evidence_record(evidence) == []
    assert_pit(evidence, "2026-10-09T00:00:00+08:00")


def test_operator_attestation_fails_closed_if_known_at_exceeds_cutoff(tmp_path):
    with pytest.raises(OperatorMarketPriceAttestationError, match="KNOWN_AT_AFTER_CUTOFF"):
        _bundle(
            tmp_path,
            known_at="2026-10-09T00:00:01+08:00",
        )


def test_operator_attestation_requires_explicit_operator_confirmation(tmp_path):
    with pytest.raises(OperatorMarketPriceAttestationError, match="OPERATOR_CONFIRMATION_REQUIRED"):
        _bundle(tmp_path, operator_confirmed=False)


def test_operator_attestation_requires_explicit_cutoff_confirmation(tmp_path):
    with pytest.raises(OperatorMarketPriceAttestationError, match="KNOWN_BY_CUTOFF_ATTESTATION_REQUIRED"):
        _bundle(tmp_path, known_by_cutoff_confirmed=False)


def test_operator_attestation_is_market_price_only(tmp_path):
    result = _bundle(tmp_path)
    evidence = json.loads((tmp_path / "private-bundle" / "evidence_record.json").read_text(encoding="utf-8"))
    evidence["field_id"] = "financial_reality.revenue"
    errors = validate_evidence_record(evidence)
    assert "OPERATOR_ATTESTATION:MARKET_PRICE_FIELD_ONLY" in errors


def test_operator_attestation_rejects_case_source_and_value_mismatches(tmp_path):
    result = _bundle(tmp_path)
    evidence_path = tmp_path / "private-bundle" / "evidence_record.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["operator_attestation"]["source_ref"] = "OTHER-SOURCE"
    assert "OPERATOR_ATTESTATION:SOURCE_REF_MISMATCH" in validate_evidence_record(evidence)
    evidence["operator_attestation"]["source_ref"] = evidence["source_ref"]
    evidence["value"] = 999.0
    assert "OPERATOR_ATTESTATION:VALUE_MISMATCH" in validate_evidence_record(evidence)


def test_cli_can_import_core_contract_when_started_outside_repository_root(tmp_path):
    import os
    import subprocess
    import sys

    script = Path(__file__).parents[1] / "tools" / "iios_operator_market_price_attestation_v01.py"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "operator-attested market-price evidence bundle" in result.stdout
