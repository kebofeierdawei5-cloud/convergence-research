import copy
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from fm02_feature_builder import FM02FeatureError, build_feature_snapshot, load_json, load_ndjson


FM01 = REPO / "research" / "fm01"
FM00 = REPO / "research" / "fm00"


class FM02FeatureBuilderTests(unittest.TestCase):
    def setUp(self):
        self.records = load_ndjson(FM01 / "CATL_DRIVER_HISTORY.ndjson")
        self.manifest = load_json(FM01 / "dataset_manifest.json")
        self.admission = load_json(FM01 / "M1_1_SOURCE_ADMISSION.json")
        self.contract = load_json(ROOT / "FM02_FEATURE_CONTRACT.json")
        self.outer_lock = load_json(FM00 / "OU-M12-FM00-CATL-001.json")

    def build(self, records=None):
        return build_feature_snapshot(
            records or self.records,
            self.manifest,
            self.admission,
            self.contract,
            self.outer_lock,
        )

    def test_real_catl_snapshot_has_expected_shape_and_frozen_boundary(self):
        rows, summary = self.build()
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["row_count"], 22)
        self.assertEqual(summary["origin_count"], 11)
        self.assertEqual(summary["drivers"], ["NET_PROFIT", "REVENUE"])
        self.assertEqual(summary["security_ids"], ["300750.SZ"])
        self.assertEqual(summary["feature_ids"], [
            "YOY_GROWTH",
            "GROWTH_ACCELERATION",
            "ROLLING_GROWTH_VOL",
            "SEASONAL_DEVIATION",
            "MEAN_REVERSION_GAP",
            "SLOPE_STABILITY",
        ])
        self.assertFalse(summary["confirmatory_eligible"])
        for row in rows:
            self.assertEqual(set(row["features"]), set(summary["feature_ids"]))
            for feature in row["features"].values():
                self.assertIn(feature["status"], {"AVAILABLE", "UNKNOWN"})
                if feature["status"] == "UNKNOWN":
                    self.assertIsNone(feature["value"])
                for record_id in feature["input_record_ids"]:
                    self.assertTrue(record_id)

    def test_origin_features_are_pit_only_and_before_every_target(self):
        rows, _ = self.build()
        by_id = {record["record_id"]: record for record in self.records}
        offsets = {"3M": 1, "6M": 2, "12M": 4}
        for row in rows:
            cutoff = row["origin_cutoff"]
            for feature in row["features"].values():
                for record_id in feature["input_record_ids"]:
                    self.assertIn(record_id, by_id)
                    self.assertLessEqual(by_id[record_id]["known_at"], cutoff)
            for horizon, offset in offsets.items():
                target = _qadd(row["origin_id"], offset)
                self.assertLess(_qkey(row["feature_asof_period"]), _qkey(target))
                self.assertTrue(
                    all(
                        _qkey(by_id[rid]["period"]) < _qkey(target)
                        for feature in row["features"].values()
                        for rid in feature["input_record_ids"]
                    )
                )

    def test_future_known_revision_cannot_change_prior_origin(self):
        baseline_rows, baseline_summary = self.build()
        mutated = copy.deepcopy(self.records)
        future = copy.deepcopy(self.records[0])
        future["record_id"] = "DSR-FM02-FUTURE-REVISION"
        future["period"] = "2022Q1"
        future["known_at"] = "2030-01-01T00:00:00+08:00"
        future["published_at"] = "2030-01-01T00:00:00+08:00"
        mutated.append(future)
        rows, summary = self.build(mutated)
        self.assertEqual(summary["snapshot_sha256"], baseline_summary["snapshot_sha256"])
        self.assertEqual(rows, baseline_rows)

    def test_target_period_visible_as_of_origin_is_fail_closed(self):
        mutated = copy.deepcopy(self.records)
        target = copy.deepcopy(
            next(r for r in self.records if r["driver_id"] == "REVENUE" and r["period"] == "2023Q4")
        )
        target["record_id"] = "DSR-FM02-TARGET-EARLY"
        target["known_at"] = "2023-09-01T00:00:00+08:00"
        target["published_at"] = "2023-09-01T00:00:00+08:00"
        mutated.append(target)
        with self.assertRaisesRegex(
            FM02FeatureError, "TARGET_PERIOD_VISIBLE_AS_FEATURE_ASOF"
        ):
            self.build(mutated)

    def test_ambiguous_visible_revision_is_fail_closed(self):
        mutated = copy.deepcopy(self.records)
        conflict = copy.deepcopy(
            next(r for r in self.records if r["driver_id"] == "REVENUE" and r["period"] == "2023Q2")
        )
        conflict["record_id"] = "DSR-FM02-CONFLICT"
        conflict["value"] = conflict["value"] + 1.0
        mutated.append(conflict)
        with self.assertRaisesRegex(
            FM02FeatureError, "AMBIGUOUS_VISIBLE_REVISION"
        ):
            self.build(mutated)

    def test_insufficient_history_is_unknown_not_imputed(self):
        rows, _ = self.build()
        early = next(
            row
            for row in rows
            if row["origin_id"] == "2023Q3" and row["driver_id"] == "REVENUE"
        )
        self.assertEqual(
            early["features"]["ROLLING_GROWTH_VOL"]["status"], "UNKNOWN"
        )
        self.assertEqual(
            early["features"]["MEAN_REVERSION_GAP"]["status"], "UNKNOWN"
        )
        self.assertIsNone(early["features"]["ROLLING_GROWTH_VOL"]["value"])
        self.assertIsNone(early["features"]["MEAN_REVERSION_GAP"]["value"])

    def test_fm01_gate_cannot_be_bypassed(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["status"] = "BLOCKED_DATA_INGRESS"
        with self.assertRaisesRegex(FM02FeatureError, "FM01_NOT_DATA_READY"):
            build_feature_snapshot(
                self.records,
                manifest,
                self.admission,
                self.contract,
                self.outer_lock,
            )

    def test_repeat_build_is_byte_deterministic(self):
        rows1, summary1 = self.build()
        rows2, summary2 = self.build()
        self.assertEqual(rows1, rows2)
        self.assertEqual(summary1, summary2)


    def test_contract_cannot_authorize_downstream_capability(self):
        contract = copy.deepcopy(self.contract)
        contract["capability_boundary"]["model_selection"] = True
        with self.assertRaisesRegex(
            FM02FeatureError, "FM02 capability boundary was widened"
        ):
            build_feature_snapshot(
                self.records,
                self.manifest,
                self.admission,
                contract,
                self.outer_lock,
            )


def _qkey(period):
    return (int(period[:4]), int(period[-1]))


def _qadd(period, offset):
    year, quarter = _qkey(period)
    serial = year * 4 + quarter - 1 + offset
    return f"{serial // 4}Q{serial % 4 + 1}"


if __name__ == "__main__":
    unittest.main()
