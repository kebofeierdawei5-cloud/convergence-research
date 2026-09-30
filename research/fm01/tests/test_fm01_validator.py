import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fm01_validator import validate_dataset


def record(record_id="DSR-X1", period="2023Q1", driver_id="REVENUE", value=100.0):
    return {
        "schema_version": "IIOS-DRIVER-SERIES-0.1",
        "record_id": record_id,
        "security_id": "300750.SZ",
        "driver_id": driver_id,
        "period": period,
        "value": value,
        "unit": "CNY",
        "source_type": "COMPANY_DISCLOSURE",
        "source_ref": "SYNTHETIC",
        "source_date": "2023-04-28",
        "known_at": "2023-04-28T12:00:00+00:00",
        "published_at": "2023-04-28T09:00:00+00:00",
        "transformation_type": "NONE",
        "provenance": "DIRECT_PERIODIC_FILING",
        "revision": {"revision_id": period + "-R1", "sequence": 1},
        "supersedes_record_id": None,
        "input_record_ids": [],
        "formula": None,
        "status": "VALID",
        "quality_status": "VERIFIED",
    }


class FM01ValidatorTests(unittest.TestCase):
    def write_ndjson(self, root, rows):
        path = root / "dataset.ndjson"
        path.write_text("\n".join(json.dumps(x) for x in rows) + ("\n" if rows else ""), encoding="utf-8")
        return path

    def test_empty_current_catl_dataset_blocks_only_data_gate(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_ndjson(Path(td), [])
            result = validate_dataset(path)
        self.assertEqual(result["status"], "BLOCKED_DATA_INGRESS")
        self.assertEqual(result["validation_findings"], [])
        self.assertEqual(result["record_count"], 0)

    def test_valid_synthetic_rows_do_not_clear_missing_source_gate(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_ndjson(Path(td), [record()])
            result = validate_dataset(path)
        self.assertEqual(result["status"], "BLOCKED_DATA_INGRESS")
        self.assertEqual(result["validation_findings"], [])

    def test_duplicate_record_id_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_ndjson(Path(td), [record(), record()])
            result = validate_dataset(path)
        self.assertTrue(any(x["code"] == "DATASET-001" for x in result["validation_findings"]))
        self.assertEqual(result["status"], "BLOCKED_DATA_INGRESS")

    def test_scope_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_ndjson(Path(td), [record(driver_id="EBITDA")])
            result = validate_dataset(path)
        self.assertTrue(any(x["code"] == "DATASET-002" for x in result["validation_findings"]))

    def test_status_file_is_consistent(self):
        status = json.loads((ROOT / "CATL_DRIVER_HISTORY_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "BLOCKED_DATA_INGRESS")
        self.assertFalse(status["source_snapshot"]["present"])
        self.assertEqual(status["records_ingested"], 0)


if __name__ == "__main__":
    unittest.main()
