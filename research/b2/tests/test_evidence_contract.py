from __future__ import annotations

import unittest
from datetime import datetime, timezone

from research.b2.evidence_contract import (
    assert_pit,
    derived_known_at,
    effective_qualified,
    pit_qualified,
    validate_evidence_record,
)


def evidence(**overrides):
    base = {
        "evidence_id": "EV-1",
        "subject_id": "000001.SZ",
        "field_id": "listing_status",
        "claim_type": "DIRECT_OBSERVATION",
        "value": "LISTED",
        "known_at": "2025-01-01T10:00:00+08:00",
        "retrieved_at": "2026-01-01T10:00:00+08:00",
        "source_ref": "TEST:SOURCE",
        "artifact_id": "ART-1",
        "content_sha256": "a" * 64,
        "exact_bytes": True,
        "provenance_class": "SOURCE_VINTAGE_VERIFIED",
        "status": "ADMITTED",
    }
    base.update(overrides)
    return base


class EvidenceContractTests(unittest.TestCase):
    def test_future_known_at_is_not_pit(self):
        self.assertFalse(pit_qualified(evidence(known_at="2025-04-01T00:00:00+08:00"), "2025-03-31T23:59:59+08:00"))

    def test_retrieval_after_cutoff_is_allowed_when_known_before(self):
        item = evidence(retrieved_at="2026-01-01T00:00:00+08:00")
        self.assertTrue(pit_qualified(item, "2025-12-31T23:59:59+08:00"))
        assert_pit(item, "2025-12-31T23:59:59+08:00")

    def test_effective_interval_is_independent(self):
        item = evidence(effective_from="2025-01-02T00:00:00+08:00", effective_to="2025-06-30T00:00:00+08:00")
        self.assertTrue(effective_qualified(item, "2025-03-31T23:59:59+08:00"))
        self.assertFalse(effective_qualified(item, "2025-12-31T23:59:59+08:00"))

    def test_missing_known_at_blocks_record(self):
        errors = validate_evidence_record(evidence(known_at=""))
        self.assertTrue(any(item.startswith("TEMPORAL:") for item in errors))

    def test_derived_known_at_is_latest_parent(self):
        result = derived_known_at([
            "2025-01-01T00:00:00+08:00",
            "2025-02-01T00:00:00+08:00",
        ])
        self.assertEqual(result, datetime(2025, 2, 1, tzinfo=timezone.utc))

    def test_derived_requires_parents_and_transformation(self):
        item = evidence(
            provenance_class="DERIVED_FROM_ADMITTED_RAW",
            parents=[],
            transformation={"type":"DIRECT"},
        )
        errors = validate_evidence_record(item)
        self.assertIn("DERIVED:PARENTS_REQUIRED", errors)
        self.assertIn("DERIVED:TRANSFORMATION_REQUIRED", errors)

    def test_sha_must_be_lowercase_hex(self):
        errors = validate_evidence_record(evidence(content_sha256="A" * 64))
        self.assertIn("CONTENT_SHA256:must be 64 lowercase hex characters", errors)


if __name__ == "__main__":
    unittest.main()