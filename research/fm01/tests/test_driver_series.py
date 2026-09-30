import copy
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from driver_series import DriverSeriesError, derive_h1_minus_q1, derive_annual_minus_q1_q2_q3, resolve_at_cutoff, resolve_series, validate_record, validate_records


def base(**overrides):
    row = {
        "schema_version": "IIOS-DRIVER-SERIES-0.1",
        "record_id": "DSR-TEST-001",
        "security_id": "300750.SZ",
        "driver_id": "REVENUE",
        "period": "2023Q1",
        "value": 100.0,
        "unit": "CNY",
        "source_type": "COMPANY_DISCLOSURE",
        "source_ref": "SYNTHETIC-TEST-CONTROL",
        "source_date": "2023-04-28",
        "known_at": "2023-04-28T12:00:00+00:00",
        "published_at": "2023-04-28T09:00:00+00:00",
        "transformation_type": "NONE",
        "provenance": "DIRECT_PERIODIC_FILING",
        "revision": {"revision_id": "2023Q1-R1", "sequence": 1},
        "supersedes_record_id": None,
        "input_record_ids": [],
        "formula": None,
        "status": "VALID",
        "quality_status": "VERIFIED",
    }
    row.update(overrides)
    return row


class DriverSeriesTests(unittest.TestCase):
    def test_positive_direct(self):
        self.assertEqual(validate_record(base()), [])

    def test_future_known_value_is_excluded(self):
        rows = [base(value=100.0), base(record_id="DSR-TEST-002", value=110.0, known_at="2024-05-01T00:00:00+00:00", published_at="2024-05-01T00:00:00+00:00", revision={"revision_id":"2023Q1-R2","sequence":2})]
        got = resolve_at_cutoff(rows, security_id="300750.SZ", driver_id="REVENUE", period="2023Q1", cutoff="2023-12-31T23:59:59+00:00")
        self.assertEqual(got["value"], 100.0)

    def test_new_known_revision_wins(self):
        rows = [base(value=100.0), base(record_id="DSR-TEST-002", value=120.0, known_at="2023-07-30T00:00:00+00:00", published_at="2023-07-30T00:00:00+00:00", revision={"revision_id":"2023Q1-R2","sequence":2})]
        got = resolve_at_cutoff(rows, security_id="300750.SZ", driver_id="REVENUE", period="2023Q1", cutoff="2024-01-01T00:00:00+00:00")
        self.assertEqual(got["value"], 120.0)

    def test_same_snapshot_conflict_is_fail_closed(self):
        rows = [base(value=100.0), base(record_id="DSR-TEST-002", value=120.0)]
        with self.assertRaises(DriverSeriesError):
            resolve_at_cutoff(rows, security_id="300750.SZ", driver_id="REVENUE", period="2023Q1", cutoff="2024-01-01T00:00:00+00:00")

    def test_missing_period_is_unknown_not_imputed(self):
        result = resolve_series([], security_id="300750.SZ", driver_id="REVENUE", periods=["2023Q1"], cutoff="2023-12-31T23:59:59+00:00")
        self.assertEqual(result["status_by_period"]["2023Q1"], "UNKNOWN")
        self.assertNotIn("2023Q1", result["records"])

    def test_known_at_before_published_at_is_rejected(self):
        row = base(known_at="2023-04-27T08:00:00+00:00", published_at="2023-04-28T09:00:00+00:00")
        self.assertTrue(any(x.startswith("PIT-001") for x in validate_record(row)))

    def test_derived_requires_lineage_and_formula(self):
        row = base(provenance="DERIVED_H1_MINUS_Q1", transformation_type="H1_MINUS_Q1", quality_status="DERIVED_VERIFIED")
        findings = validate_record(row)
        self.assertIn("PROV-006", {x.split(":",1)[0] for x in findings})
        self.assertIn("PROV-007", {x.split(":",1)[0] for x in findings})

    def test_direct_cannot_smuggle_lineage(self):
        row = base(input_record_ids=["DSR-PARENT"], formula="parent")
        codes = {x.split(":",1)[0] for x in validate_record(row)}
        self.assertIn("PROV-002", codes)
        self.assertIn("PROV-003", codes)

    def test_unknown_must_not_carry_numeric_value(self):
        row = base(status="UNKNOWN", quality_status="UNKNOWN")
        codes = {x.split(":",1)[0] for x in validate_record(row)}
        self.assertIn("DATA-002", codes)

    def test_h1_minus_q1_derivation_preserves_lineage(self):
        h1 = base(record_id="DSR-H1", period="2024Q2", value=250.0, revision={"revision_id":"2024H1-R1","sequence":1})
        q1 = base(record_id="DSR-Q1", period="2024Q1", value=100.0, revision={"revision_id":"2024Q1-R1","sequence":1})
        out = derive_h1_minus_q1(h1=h1, q1=q1, target_period="2024Q2", record_id="DSR-Q2-DERIVED", source_ref="SYNTHETIC", known_at="2024-08-30T00:00:00+00:00", published_at="2024-08-30T00:00:00+00:00")
        self.assertEqual(out["value"], 150.0)
        self.assertEqual(out["provenance"], "DERIVED_H1_MINUS_Q1")
        self.assertEqual(out["input_record_ids"], ["DSR-H1", "DSR-Q1"])
        self.assertEqual(validate_record(out), [])

    def test_annual_minus_q1_q2_q3_derivation_is_explicit(self):
        annual = base(record_id="DSR-ANNUAL", period="2024Q4", value=1000.0)
        q1 = base(record_id="DSR-Q1", period="2024Q1", value=200.0)
        q2 = base(record_id="DSR-Q2", period="2024Q2", value=250.0)
        q3 = base(record_id="DSR-Q3", period="2024Q3", value=300.0)
        out = derive_annual_minus_q1_q2_q3(annual=annual, q1=q1, q2=q2, q3=q3, target_period="2024Q4", record_id="DSR-Q4-DERIVED", source_ref="SYNTHETIC", known_at="2025-04-30T00:00:00+00:00", published_at="2025-04-30T00:00:00+00:00")
        self.assertEqual(out["value"], 250.0)
        self.assertEqual(out["provenance"], "DERIVED_ANNUAL_MINUS_Q1_Q2_Q3")
        self.assertEqual(validate_record(out), [])

    def test_derivation_never_allows_missing_parent(self):
        h1 = base(record_id="DSR-H1", value=250.0)
        with self.assertRaises(DriverSeriesError):
            # q1 is intentionally absent/None rather than silently assumed
            derive_h1_minus_q1(h1=h1, q1={}, target_period="2024Q2", record_id="DSR-Q2-DERIVED", source_ref="SYNTHETIC", known_at="2024-08-30T00:00:00+00:00", published_at="2024-08-30T00:00:00+00:00")

    def test_2021_to_2026_coverage_shape_without_values(self):
        manifest = json.loads((ROOT / "dataset_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["coverage_target"]["expected_quarters"], 22)
        self.assertFalse(manifest["data_status"]["exact_source_snapshot_present"])


if __name__ == "__main__":
    unittest.main()
