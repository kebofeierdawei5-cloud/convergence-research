import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "research" / "fm02"))

from fm02_feature_builder import (
    build_feature_snapshot as build_fm02,
    load_json,
    load_ndjson,
)
from fm03_state_engine import (
    FM03StateError,
    build_state_snapshot,
    canonical_sha,
    validate_capability_context,
)

FM00 = REPO / "research" / "fm00"
FM01 = REPO / "research" / "fm01"
FM02 = REPO / "research" / "fm02"


class FM03StateEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_json(ROOT / "FM03_STATE_CONTRACT.json")
        cls.lock = load_json(FM00 / "OU-M12-FM00-CATL-001.json")
        records = load_ndjson(FM01 / "CATL_DRIVER_HISTORY.ndjson")
        manifest = load_json(FM01 / "dataset_manifest.json")
        admission = load_json(FM01 / "M1_1_SOURCE_ADMISSION.json")
        fm02_contract = load_json(FM02 / "FM02_FEATURE_CONTRACT.json")
        cls.feature_rows, _ = build_fm02(records, manifest, admission, fm02_contract, cls.lock)
        cls.capability = {"schema_version":"IIOS-CAPABILITY-CONTEXT-0.1","principal":"iios_research","grants":["m1.2.fm03.state_engine"]}

    def build(self, rows=None, capability=None, lock=None):
        return build_state_snapshot(
            copy.deepcopy(rows if rows is not None else self.feature_rows),
            copy.deepcopy(self.contract),
            copy.deepcopy(lock if lock is not None else self.lock),
            copy.deepcopy(capability if capability is not None else self.capability),
        )

    def test_real_catl_state_snapshot_shape_and_determinism(self):
        rows, receipt = self.build()
        rows2, receipt2 = self.build()
        self.assertEqual(len(rows), 22)
        self.assertEqual(rows, rows2)
        self.assertEqual(receipt["snapshot_sha256"], receipt2["snapshot_sha256"])
        self.assertEqual(receipt["origin_count"], 11)
        self.assertEqual(receipt["row_count"], 22)
        self.assertFalse(receipt["confirmatory_eligible"])
        self.assertEqual(receipt["capability_principal"], "iios_research")
        self.assertEqual(receipt["capability_grant"], "m1.2.fm03.state_engine")

    def test_first_origin_has_no_prior_for_comparison_states(self):
        rows, _ = self.build()
        first = next(row for row in rows if row["origin_id"] == "2023Q3" and row["driver_id"] == "REVENUE")
        self.assertEqual(first["states"]["VOLATILITY"]["state"], "UNKNOWN")
        self.assertEqual(first["states"]["VOLATILITY"]["unknown_reason"], "NO_PRIOR_FROZEN_ORIGIN")
        self.assertEqual(first["states"]["STRUCTURAL_STABILITY"]["state"], "UNKNOWN")
        self.assertEqual(first["states"]["STRUCTURAL_STABILITY"]["unknown_reason"], "NO_PRIOR_FROZEN_ORIGIN")

    def test_signed_state_semantics(self):
        row = next(r for r in self.feature_rows if r["origin_id"] == "2025Q4" and r["driver_id"] == "REVENUE")
        states, _ = self.build()
        output = next(r for r in states if r["origin_id"] == row["origin_id"] and r["driver_id"] == row["driver_id"])
        self.assertEqual(output["states"]["DIRECTION"]["state"], "UP" if row["features"]["YOY_GROWTH"]["value"] > 0 else "DOWN")
        self.assertEqual(output["states"]["MOMENTUM"]["state"], "ACCELERATING" if row["features"]["GROWTH_ACCELERATION"]["value"] > 0 else "DECELERATING")
        self.assertEqual(output["states"]["SEASONALITY"]["state"], "POSITIVE" if row["features"]["SEASONAL_DEVIATION"]["value"] > 0 else "NEGATIVE")
        self.assertEqual(output["states"]["MEAN_REVERSION_PRESSURE"]["state"], "DOWNWARD" if row["features"]["MEAN_REVERSION_GAP"]["value"] > 0 else "UPWARD")

    def test_comparison_state_provenance_binds_current_and_prior_rows(self):
        rows, _ = self.build()
        current = next(r for r in rows if r["origin_id"] == "2023Q4" and r["driver_id"] == "REVENUE")
        self.assertEqual(len(current["states"]["VOLATILITY"]["input_feature_ids"]), 1)
        self.assertGreaterEqual(len(current["states"]["VOLATILITY"]["input_feature_row_ids"]), 2)
        self.assertIn(current["feature_row_id"], current["states"]["VOLATILITY"]["input_feature_row_ids"])
        self.assertEqual(current["states"]["VOLATILITY"]["status"], "UNKNOWN" if current["states"]["VOLATILITY"]["unknown_reason"] else "AVAILABLE")

    def test_unknown_feature_propagates_without_imputation(self):
        rows = copy.deepcopy(self.feature_rows)
        target = next(r for r in rows if r["origin_id"] == "2025Q4" and r["driver_id"] == "REVENUE")
        target["features"]["YOY_GROWTH"] = {"value":None,"status":"UNKNOWN","unknown_reason":"TEST_UNKNOWN","input_record_ids":[]}
        target["input_record_ids"] = sorted({
            record_id
            for feature in target["features"].values()
            for record_id in feature["input_record_ids"]
        })
        out, _ = self.build(rows)
        result = next(r for r in out if r["origin_id"] == "2025Q4" and r["driver_id"] == "REVENUE")
        self.assertEqual(result["states"]["DIRECTION"]["state"], "UNKNOWN")
        self.assertEqual(result["states"]["DIRECTION"]["status"], "UNKNOWN")
        self.assertEqual(result["states"]["DIRECTION"]["input_record_ids"], [])
        self.assertEqual(result["states"]["DATA_QUALITY"]["state"], "PARTIAL")

    def test_future_feature_asof_fails_closed(self):
        rows = copy.deepcopy(self.feature_rows)
        target = next(r for r in rows if r["origin_id"] == "2025Q2" and r["driver_id"] == "REVENUE")
        target["feature_asof_period"] = "2025Q3"
        with self.assertRaisesRegex(FM03StateError, "PIT_BOUNDARY_FAILURE"):
            self.build(rows)

    def test_origin_schedule_mutation_fails_closed(self):
        rows = copy.deepcopy(self.feature_rows)
        rows[0]["origin_id"] = "2022Q4"
        with self.assertRaisesRegex(FM03StateError, "ORIGIN_OUTSIDE_FROZEN_SCHEDULE|FROZEN_ORIGIN_OR_DRIVER_SET_MISMATCH"):
            self.build(rows)

    def test_duplicate_feature_row_fails_closed(self):
        rows = copy.deepcopy(self.feature_rows)
        rows.append(copy.deepcopy(rows[-1]))
        with self.assertRaisesRegex(FM03StateError, "FM03_FEATURE_ROW_COUNT_MISMATCH"):
            self.build(rows)

    def test_incomplete_lineage_fails_closed(self):
        rows = copy.deepcopy(self.feature_rows)
        target = next(r for r in rows if r["origin_id"] == "2025Q4" and r["driver_id"] == "REVENUE")
        target["input_record_ids"] = []
        with self.assertRaisesRegex(FM03StateError, "INCOMPLETE_LINEAGE"):
            self.build(rows)

    def test_outer_lock_hash_fails_closed(self):
        lock = copy.deepcopy(self.lock)
        lock["origins"][0]["scheduled_horizons"] = ["3M"]
        with self.assertRaisesRegex(FM03StateError, "FM03_OUTER_LOCK_HASH_MISMATCH"):
            self.build(lock=lock)

    def test_downstream_capability_fails_closed(self):
        capability = copy.deepcopy(self.capability)
        capability["grants"].append("m1.2.model_selection")
        with self.assertRaisesRegex(FM03StateError, "DOWNSTREAM_CAPABILITY_PRESENT"):
            validate_capability_context(capability, self.contract)

    def test_wrong_principal_fails_closed(self):
        capability = copy.deepcopy(self.capability)
        capability["principal"] = "iios_scoring"
        with self.assertRaisesRegex(FM03StateError, "CAPABILITY_PRINCIPAL_MISMATCH"):
            validate_capability_context(capability, self.contract)

    def test_contract_is_non_confirmatory_and_research_only(self):
        self.assertEqual(self.contract["status"], "FROZEN")
        self.assertFalse(self.contract["confirmatory_eligible"])
        self.assertTrue(self.contract["capability_boundary"]["state_engine_only"])
        self.assertFalse(self.contract["capability_boundary"]["conditional_backtest"])
        self.assertFalse(self.contract["capability_boundary"]["model_selection"])
        self.assertFalse(self.contract["capability_boundary"]["production_router"])
        self.assertFalse(self.contract["capability_boundary"]["automatic_execution"])

    def test_state_snapshot_hash_is_canonical(self):
        rows, receipt = self.build()
        self.assertEqual(receipt["snapshot_sha256"], canonical_sha(rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
