from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "b_raw_preflight.py"
ORIGINS = [
    "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4",
    "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1",
]
DOMAINS = [
    "identity", "listing_delisting", "common_equity",
    "st_history", "industry_history", "source_vintages",
]


def execute(root: Path) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def base_manifest() -> dict:
    return {
        "schema_version": "IIOS-A02-DATA-01-DELIVERY-MANIFEST-0.1",
        "universe_id": "OU-M12-A02-CSI800-NONFIN-PIT-001",
        "required_origins": ORIGINS,
        "required_b_domains": DOMAINS,
        "b_domain_records": [],
    }


def test_manifest_only_blocks(tmp_path: Path) -> None:
    (tmp_path / "DELIVERY_MANIFEST.json").write_text(
        json.dumps(base_manifest()), encoding="utf-8"
    )
    rc, result = execute(tmp_path)
    assert rc == 4
    assert result["status"] == "BLOCKED"


def test_retrieved_at_as_known_at_blocks(tmp_path: Path) -> None:
    raw = tmp_path / "raw.bin"
    raw.write_bytes(b"raw")
    digest = hashlib.sha256(b"raw").hexdigest()
    relative = "raw.bin"

    manifest = base_manifest()
    manifest["b_domain_records"] = [
        {
            "domain": domain,
            "raw_paths": [relative],
            "origin_periods": ORIGINS,
            "source_ref": "SRC",
            "license_redistribution_status": "LOCAL_PRIVATE",
            "known_at_basis": "retrieved_at",
            "retrieved_at": "2026-10-07T00:00:00Z",
            "knowledge_evidence_class": "EVENT_PUBLICATION_VERIFIED",
            "exact_bytes": True,
            "raw_sha256_by_path": {relative: digest},
        }
        for domain in DOMAINS
    ]
    (tmp_path / "DELIVERY_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    rc, result = execute(tmp_path)
    assert rc == 4
    assert any(
        item["reason"] == "retrieved_at_used_as_known_at"
        for item in result["b_domains"]["invalid"]
    )


def test_checksum_without_bytes_blocks(tmp_path: Path) -> None:
    manifest = base_manifest()
    manifest["b_domain_records"] = [
        {
            "domain": domain,
            "raw_paths": ["missing.bin"],
            "origin_periods": ORIGINS,
            "source_ref": "SRC",
            "license_redistribution_status": "LOCAL_PRIVATE",
            "known_at_basis": {"type": "source_publication"},
            "knowledge_evidence_class": "EVENT_PUBLICATION_VERIFIED",
            "exact_bytes": True,
            "raw_sha256_by_path": {"missing.bin": "0" * 64},
        }
        for domain in DOMAINS
    ]
    (tmp_path / "DELIVERY_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    rc, result = execute(tmp_path)
    assert rc == 4
    assert any(
        item["reason"] == "raw_file_missing"
        for item in result["b_domains"]["invalid"]
    )


def test_current_only_knowledge_blocks(tmp_path: Path) -> None:
    raw = tmp_path / "raw.bin"
    raw.write_bytes(b"current")
    digest = hashlib.sha256(b"current").hexdigest()

    manifest = base_manifest()
    manifest["b_domain_records"] = [
        {
            "domain": domain,
            "raw_paths": ["raw.bin"],
            "origin_periods": ORIGINS,
            "source_ref": "SRC",
            "license_redistribution_status": "LOCAL_PRIVATE",
            "known_at_basis": {"type": "current_snapshot"},
            "knowledge_evidence_class": "UNKNOWN",
            "exact_bytes": True,
            "raw_sha256_by_path": {"raw.bin": digest},
        }
        for domain in DOMAINS
    ]
    (tmp_path / "DELIVERY_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    rc, result = execute(tmp_path)
    assert rc == 4
    assert any(
        item["reason"] == "knowledge_evidence_not_historical_capable"
        for item in result["b_domains"]["invalid"]
    )
