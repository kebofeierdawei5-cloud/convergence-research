from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fm04_conditional_backtest import forecast_model, metric_bundle


def synthetic_records():
    records = []
    value = 1.0
    for year in (2022, 2023, 2024):
        for quarter in (1, 2, 3, 4):
            period = f"{year}Q{quarter}"
            records.append({
                "record_id": f"ORACLE-{period}",
                "security_id": "ORACLE",
                "driver_id": "REVENUE",
                "period": period,
                "value": value,
                "known_at": "2024-12-30T00:00:00+08:00",
            })
            value *= 2.0
    return records


class FM04KnownAnswerOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = synthetic_records()
        cls.by_period = {r["period"]: r for r in cls.records}
        cls.origin = "2024Q4"

        # Frozen expected answers are maintained independently of the executor.
        cls.expected = {
            "SEASONAL_NAIVE": 256.0,
            "PERSISTENCE_YOY": 4096.0,
            "TREND_LOG_LINEAR_8Q": 4096.0,
            "MEAN_REVERSION_YOY_8": 4096.0,
        }

    def visible(self):
        return dict(self.by_period)

    def test_known_answer_forecasts(self):
        for model_id, expected in self.expected.items():
            actual, _ = forecast_model(model_id, self.by_period, self.visible(), self.origin, "3M")
            self.assertTrue(math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9),
                            f"{model_id}: expected {expected}, got {actual}")

    def test_semantic_adjudication_matches_frozen_candidate_space(self):
        import json
        policy=json.loads((ROOT / "FM04_R_SEMANTIC_ADJUDICATION.json").read_text(encoding="utf-8"))
        candidate=json.loads((ROOT.parent / "fm00/CS-M12-FM00-CATL-001.json").read_text(encoding="utf-8"))
        contract=json.loads((ROOT / "FM04_CONDITIONAL_BACKTEST_CONTRACT.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["applies_to_contract_id"], contract["contract_id"])
        state_dimensions=set(contract["selection_policy"]["state_dimensions"])
        self.assertEqual(
            state_dimensions,
            set(policy["state_interpretation"]["economic_dimensions"]) | set(policy["state_interpretation"]["research_control_dimensions"]),
        )
        self.assertEqual(policy["state_interpretation"]["research_control_dimensions"], ["DATA_QUALITY"])
        admitted_families=set(candidate["models"])
        for mapping in policy["model_identity"]:
            self.assertIn(mapping["model_family"], admitted_families)
        instances={x["model_instance_id"] for x in policy["model_identity"]}
        self.assertEqual(instances, set(m["model_id"] for m in contract["models"]))

    def test_known_answer_metric_bundle(self):
        expected = {"MAE": 10.0, "RMSE": 10.0, "sMAPE": 66.66666666666667}
        actual = metric_bundle(10.0, 20.0)
        for key, value in expected.items():
            self.assertTrue(math.isclose(actual[key], value, rel_tol=0.0, abs_tol=1e-12),
                            f"{key}: expected {value}, got {actual[key]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
