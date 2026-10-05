from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from research.b2.company_evidence import (
    REQUIRED_COMPANY_FIELD_GROUPS,
    build_company_evidence_manifest,
    validate_company_evidence_manifest,
)


def _evidence(evidence_id: str, field_id: str, digest: str, known_at: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "subject_id": "CASE-001",
        "field_id": field_id,
        "claim_type": "DIRECT_OBSERVATION",
        "value": "fixture",
        "known_at": known_at,
        "retrieved_at": "2026-10-05T09:00:00+08:00",
        "source_ref": "TEST:PRIMARY",
        "artifact_id": f"ART-{evidence_id}",
        "content_sha256": digest,
        "exact_bytes": True,
        "provenance_class": "SOURCE_VINTAGE_VERIFIED",
        "status": "ADMITTED",
    }


class CompanyEvidenceTests(unittest.TestCase):
    def test_single_company_manifest_passes_with_exact_raw_bytes(self):
        payload = b"exact-test-source"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "security.txt").write_bytes(payload)
            manifest = build_company_evidence_manifest(
                case_id="CASE-001",
                market="CN-A",
                symbol="000001",
                company="TESTCO",
                cutoff_date="2026-10-05T09:30:00+08:00",
                evidence=[_evidence("EV-1", "security_identity.primary", digest, "2026-10-04T09:00:00+08:00")],
                raw_artifacts=[{
                    "evidence_id": "EV-1",
                    "relative_path": "security.txt",
                    "expected_size_bytes": len(payload),
                    "expected_sha256": digest,
                }],
                required_field_groups=["security_identity"],
                raw_root=root,
            )
        self.assertEqual(manifest["status"], "PASS")
        self.assertEqual(manifest["validation_errors"], [])

    def test_future_known_at_blocks_manifest(self):
        payload = b"future"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(payload)
            manifest = build_company_evidence_manifest(
                case_id="CASE-002",
                market="CN-A",
                symbol="300750",
                company="CATL",
                cutoff_date="2026-10-05T09:30:00+08:00",
                evidence=[_evidence("EV-2", "financial_reality.revenue", digest, "2026-10-06T00:00:00+08:00")],
                raw_artifacts=[{
                    "evidence_id": "EV-2",
                    "relative_path": "source.txt",
                    "expected_size_bytes": len(payload),
                    "expected_sha256": digest,
                }],
                required_field_groups=["financial_reality"],
                raw_root=root,
            )
        self.assertEqual(manifest["status"], "BLOCKED")
        self.assertTrue(any(":PIT:" in item for item in manifest["validation_errors"]))

    def test_hash_mismatch_blocks(self):
        payload = b"same-size"
        good_digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(payload)
            manifest = build_company_evidence_manifest(
                case_id="CASE-003",
                market="CN-A",
                symbol="000002",
                company="TESTCO",
                cutoff_date="2026-10-05T09:30:00+08:00",
                evidence=[_evidence("EV-3", "market_price.close", good_digest, "2026-10-05T08:00:00+08:00")],
                raw_artifacts=[{
                    "evidence_id": "EV-3",
                    "relative_path": "source.txt",
                    "expected_size_bytes": len(payload),
                    "expected_sha256": "0" * 64,
                }],
                required_field_groups=["market_price"],
                raw_root=root,
            )
        self.assertEqual(manifest["status"], "BLOCKED")
        self.assertTrue(any("EXACT_BYTES_MISMATCH" in item for item in manifest["validation_errors"]))

    def test_missing_required_group_blocks(self):
        payload = b"identity-only"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(payload)
            manifest = build_company_evidence_manifest(
                case_id="CASE-004",
                market="CN-A",
                symbol="000003",
                company="TESTCO",
                cutoff_date="2026-10-05T09:30:00+08:00",
                evidence=[_evidence("EV-4", "security_identity.primary", digest, "2026-10-05T08:00:00+08:00")],
                raw_artifacts=[{
                    "evidence_id": "EV-4",
                    "relative_path": "source.txt",
                    "expected_size_bytes": len(payload),
                    "expected_sha256": digest,
                }],
                required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
                raw_root=root,
            )
        self.assertEqual(manifest["status"], "BLOCKED")
        self.assertTrue(any("REQUIRED_FIELD_GROUPS_UNCOVERED" in item for item in manifest["validation_errors"]))

    def test_no_raw_root_exact_admission_is_blocked(self):
        payload = b"metadata-only"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = build_company_evidence_manifest(
            case_id="CASE-005",
            market="CN-A",
            symbol="000004",
            company="TESTCO",
            cutoff_date="2026-10-05T09:30:00+08:00",
            evidence=[_evidence("EV-5", "security_identity.primary", digest, "2026-10-05T08:00:00+08:00")],
            raw_artifacts=[{
                "evidence_id": "EV-5",
                "relative_path": "source.txt",
                "expected_size_bytes": len(payload),
                "expected_sha256": digest,
            }],
            required_field_groups=["security_identity"],
            raw_root=None,
        )
        errors = validate_company_evidence_manifest(
            manifest,
            raw_root=None,
            require_raw_verification=True,
        )
        self.assertIn("RAW_VERIFICATION_ROOT_REQUIRED", errors)


def test_evidence_subject_must_match_case_id():
    payload = b"subject"
    digest = hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "source.txt").write_bytes(payload)
        manifest = build_company_evidence_manifest(
            case_id="CASE-A",
            market="CN-A",
            symbol="000005",
            company="TESTCO",
            cutoff_date="2026-10-05T09:30:00+08:00",
            evidence=[{
                **_evidence("EV-6", "security_identity.primary", digest, "2026-10-05T08:00:00+08:00"),
                "subject_id": "OTHER-CASE",
            }],
            raw_artifacts=[{
                "evidence_id": "EV-6",
                "relative_path": "source.txt",
                "expected_size_bytes": len(payload),
                "expected_sha256": digest,
            }],
            required_field_groups=["security_identity"],
            raw_root=root,
        )
    assert manifest["status"] == "BLOCKED"
    assert any("SUBJECT_CASE_MISMATCH" in item for item in manifest["validation_errors"])


def test_raw_artifact_hash_must_match_evidence_hash():
    payload = b"hash-binding"
    good_digest = hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "source.txt").write_bytes(payload)
        manifest = build_company_evidence_manifest(
            case_id="CASE-007",
            market="CN-A",
            symbol="000006",
            company="TESTCO",
            cutoff_date="2026-10-05T09:30:00+08:00",
            evidence=[_evidence("EV-7", "market_price.close", good_digest, "2026-10-05T08:00:00+08:00")],
            raw_artifacts=[{
                "evidence_id": "EV-7",
                "relative_path": "source.txt",
                "expected_size_bytes": len(payload),
                "expected_sha256": "1" * 64,
            }],
            required_field_groups=["market_price"],
            raw_root=root,
        )
    assert manifest["status"] == "BLOCKED"
    assert any("EVIDENCE_HASH_MISMATCH" in item for item in manifest["validation_errors"])


if __name__ == "__main__":
    unittest.main()
