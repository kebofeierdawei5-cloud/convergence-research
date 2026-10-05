from __future__ import annotations

import json
from pathlib import Path

from research.b2.company_evidence import validate_company_evidence_manifest


ROOT = Path(__file__).resolve().parents[3]
SUPPLEMENT = (
    ROOT
    / "evidence"
    / "real_cases"
    / "RC-CN-A-300750-20261004"
    / "E002_primary_supplement_manifest_v0.1.json"
)


def test_e002_primary_supplement_metadata_is_admissible_without_public_raw_bytes():
    manifest = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))
    errors = validate_company_evidence_manifest(
        manifest,
        raw_root=None,
        require_raw_verification=False,
    )
    assert errors == [], errors

    evidence = manifest["evidence"][0]
    artifact = manifest["raw_artifacts"][0]
    assert evidence["evidence_id"] == "E011"
    assert evidence["source_ref"] == "SZSE:MARKET_DATA"
    assert evidence["field_id"] == "market_price.close.2026-09-30"
    assert evidence["value"] == 291.11
    assert evidence["known_at"] == "2026-09-30"
    assert evidence["exact_bytes"] is True
    assert evidence["content_sha256"] == artifact["expected_sha256"]
    assert artifact["expected_size_bytes"] == 231394
    assert artifact["expected_sha256"] == "349b422f6f9c95d5ea8787aa664e8cd913f9aac3b056914e68f3826567cd6ea2"


def test_e002_public_ci_without_private_vault_remains_fail_closed():
    manifest = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))
    errors = validate_company_evidence_manifest(
        manifest,
        raw_root=None,
        require_raw_verification=True,
    )
    assert "RAW_VERIFICATION_ROOT_REQUIRED" in errors
