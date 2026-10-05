from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.b2.company_evidence import validate_company_evidence_manifest


def _fixture_manifest(digest: str, size: int) -> dict:
    manifest = {
        "schema_version": "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1",
        "case_id": "CASE-PRIVATE-001",
        "market": "CN-A",
        "symbol": "300750",
        "company": "CATL",
        "cutoff_date": "2026-10-05T09:30:00+08:00",
        "required_field_groups": ["market_price"],
        "evidence": [{
            "evidence_id": "E-PRIVATE",
            "subject_id": "CASE-PRIVATE-001",
            "field_id": "market_price.close.2026-09-30",
            "claim_type": "OBSERVED_FACT",
            "value": 291.11,
            "unit": "CNY/share",
            "currency": "CNY",
            "observation_date": "2026-09-30",
            "known_at": "2026-09-30",
            "retrieved_at": "2026-10-05T02:29:16+00:00",
            "source_ref": "SZSE:MARKET_DATA",
            "source_locator": "https://www.szse.cn/api/report/ShowReport",
            "artifact_id": "private.xlsx",
            "content_sha256": digest,
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
            "license_status": "UNKNOWN",
        }],
        "raw_artifacts": [{
            "evidence_id": "E-PRIVATE",
            "relative_path": "private.xlsx",
            "expected_size_bytes": size,
            "expected_sha256": digest,
        }],
    }
    body = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest["audit"] = {
        "manifest_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()
    }
    return manifest


class PrivateRawVaultTests(unittest.TestCase):
    def test_private_raw_manifest_passes_with_exact_bytes(self):
        payload = b"private-raw"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = _fixture_manifest(digest, len(payload))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "private.xlsx").write_bytes(payload)
            errors = validate_company_evidence_manifest(
                manifest,
                raw_root=root,
                require_raw_verification=True,
            )
        self.assertEqual(errors, [])

    def test_private_raw_manifest_without_vault_fails_closed(self):
        payload = b"private-raw"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = _fixture_manifest(digest, len(payload))
        errors = validate_company_evidence_manifest(
            manifest,
            raw_root=None,
            require_raw_verification=True,
        )
        self.assertIn("RAW_VERIFICATION_ROOT_REQUIRED", errors)


if __name__ == "__main__":
    unittest.main()
