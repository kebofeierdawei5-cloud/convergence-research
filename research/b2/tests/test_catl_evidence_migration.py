from __future__ import annotations

import json
from pathlib import Path

from research.b2.company_evidence import validate_company_evidence_manifest


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "evidence" / "real_cases" / "RC-CN-A-300750-20261004" / "b2_company_evidence_manifest_v0.1.json"


def test_catl_existing_capture_manifest_is_pit_and_exact_byte_valid():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    errors = validate_company_evidence_manifest(
        manifest,
        raw_root=ROOT,
        require_raw_verification=True,
    )
    assert errors == [], errors
    assert manifest["case_id"] == "RC-CN-A-300750-20261004"
    assert len(manifest["evidence"]) == 10
    assert len(manifest["raw_artifacts"]) == 10
    assert all(item["exact_bytes"] is True for item in manifest["evidence"])


def test_catl_migration_does_not_introduce_research_universe_dependencies():
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    forbidden = ("A02", "CSI800", "CSI Industry", "OU-M12-A02")
    for token in forbidden:
        assert token not in text
