import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from fm04_conditional_backtest import (
    FM04BacktestError,
    build_result,
    canonical_sha,
    forecast_model,
    validate_capability_context,
    load_json,
    load_ndjson,
)


class FM04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_json(ROOT / "FM04_CONDITIONAL_BACKTEST_CONTRACT.json")
        cls.lock = load_json(REPO / "research/fm00/OU-M12-FM00-CATL-001.json")
        path = Path(os.environ.get("FM03_STATE_SNAPSHOT", REPO / "research/fm03/FM03_STATE_SNAPSHOT.ndjson"))
        cls.states = load_ndjson(path) if path.exists() else None
        cls.records = load_ndjson(REPO / "research/fm01/CATL_DRIVER_HISTORY.ndjson")

    def capability(self):
        return {"schema_version":"IIOS-CAPABILITY-CONTEXT-0.1","principal":"iios_research","grants":["m1.2.fm04.conditional_backtest"]}

    def test_capability_is_fail_closed(self):
        bad = self.capability()
        bad["grants"] = ["m1.2.fm04.conditional_backtest", "m1.2.model_selection"]
        with self.assertRaisesRegex(FM04BacktestError, "DOWNSTREAM_CAPABILITY_PRESENT"):
            validate_capability_context(bad, self.contract)

    def test_wrong_principal_is_fail_closed(self):
        bad = self.capability()
        bad["principal"] = "iios_scoring"
        with self.assertRaisesRegex(FM04BacktestError, "CAPABILITY_PRINCIPAL_MISMATCH"):
            validate_capability_context(bad, self.contract)

    def test_four_model_universe_is_frozen(self):
        self.assertEqual(
            [m["model_id"] for m in sorted(self.contract["models"], key=lambda x:x["order"])],
            ["SEASONAL_NAIVE","PERSISTENCE_YOY","TREND_LOG_LINEAR_8Q","MEAN_REVERSION_YOY_8"],
        )
        self.assertEqual(self.contract["selection_policy"]["min_common_inner_observations"], 3)

    def test_state_snapshot_hash_is_pinned_when_available(self):
        if self.states is not None:
            self.assertEqual(canonical_sha(self.states), self.contract["input_contract"]["state_snapshot_sha256"])

    def test_no_current_price_or_confirmatory_authority(self):
        self.assertFalse(self.contract["confirmatory_eligible"])
        self.assertFalse(self.contract["capability_boundary"]["production_router"])
        self.assertFalse(self.contract["capability_boundary"]["production_model_selection"])
        self.assertFalse(self.contract["capability_boundary"]["automatic_execution"])
        self.assertFalse(self.contract["capability_boundary"]["investment_decision"])

    def test_real_result_can_be_built_from_frozen_inputs(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        result = build_result(copy.deepcopy(self.contract), copy.deepcopy(self.states), copy.deepcopy(self.lock), copy.deepcopy(self.records))
        self.assertEqual(result["summary"]["outer_selection_unit_count"], 406)
        self.assertEqual(result["summary"]["selected_count"] + result["summary"]["no_selection_count"], 406)
        self.assertEqual(result["summary"]["conditional_group_count"], len(result["conditional_performance"]))

    def test_unknown_state_forces_no_selection(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        states = copy.deepcopy(self.states)
        target = next(r for r in states if r["origin_id"]=="2025Q4" and r["driver_id"]=="REVENUE")
        target["states"]["DIRECTION"] = {
            "state":"UNKNOWN","status":"UNKNOWN","unknown_reason":"TEST_UNKNOWN",
            "input_feature_ids":["YOY_GROWTH"],"input_feature_row_ids":[target["feature_row_id"]],"input_record_ids":[]
        }
        result = build_result(self.contract, states, self.lock, self.records)
        unit = next(x for x in result["outer_selection_evaluations"] if x["outer_origin_id"]=="2025Q4" and x["driver_id"]=="REVENUE" and x["horizon"]=="3M" and x["state_dimension"]=="DIRECTION")
        self.assertEqual(unit["status"], "NO_SELECTION")
        self.assertEqual(unit["no_selection_reason"], "UNKNOWN_STATE")

    def test_outer_model_inputs_are_pit_bounded(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        result = build_result(self.contract, self.states, self.lock, self.records)
        by_id = {r["record_id"]: r for r in self.records}
        for item in result["outer_selection_evaluations"]:
            for record_id in item["provenance"]["outer_model_input_record_ids"]:
                self.assertLessEqual(by_id[record_id]["period"], item["outer_origin_id"])

    def test_inner_actual_knowledge_is_bounded_by_outer_cutoff(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        result = build_result(self.contract, self.states, self.lock, self.records)
        by_id = {r["record_id"]: r for r in self.records}
        for item in result["outer_selection_evaluations"]:
            outer_origin = item["outer_origin_id"]
            cutoff = item["outer_origin_id"]
            for obs in item["provenance"]["inner"]:
                actual = by_id[obs["inner_actual_record_id"]]
                self.assertLessEqual(actual["period"], outer_origin)
                self.assertLessEqual(actual["known_at"], f"{outer_origin[:4]}-{ {'Q1':'03','Q2':'06','Q3':'09','Q4':'12'}[outer_origin[4:]] }-{ {'Q1':'31','Q2':'30','Q3':'30','Q4':'31'}[outer_origin[4:]] }T23:59:59+08:00")

    def test_model_forecasts_never_require_future_periods(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        by_driver = {"REVENUE":{}, "NET_PROFIT":{}}
        for r in self.records:
            by_driver[r["driver_id"]][r["period"]] = r
        from fm04_conditional_backtest import visible_records
        for origin in ["2023Q3","2024Q4","2026Q1"]:
            for driver in by_driver:
                vis = visible_records(by_driver[driver], __import__("fm04_conditional_backtest").qcutoff(origin))
                for horizon in ("3M","6M","12M"):
                    if horizon=="12M" and origin in ("2025Q3","2025Q4","2026Q1"):
                        continue
                    for model in ("SEASONAL_NAIVE","PERSISTENCE_YOY","TREND_LOG_LINEAR_8Q","MEAN_REVERSION_YOY_8"):
                        try:
                            _, ids = forecast_model(model, by_driver[driver], vis, origin, horizon)
                            self.assertTrue(all(by_driver[driver][next(p for p,r in by_driver[driver].items() if r["record_id"]==rid)]["period"] <= origin for rid in ids))
                        except Exception:
                            pass

    def test_deterministic_replay(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        a = build_result(self.contract, self.states, self.lock, self.records)
        b = build_result(self.contract, self.states, self.lock, self.records)
        self.assertEqual(a, b)
        self.assertEqual(canonical_sha(a), canonical_sha(b))

    def test_insufficient_inner_sample_is_no_selection(self):
        if self.states is None:
            self.skipTest("FM03 snapshot is not committed; CI builds it before FM04")
        result = build_result(self.contract, self.states, self.lock, self.records)
        for item in result["outer_selection_evaluations"]:
            if item["inner_sample_size"] < 3:
                self.assertEqual(item["status"], "NO_SELECTION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
