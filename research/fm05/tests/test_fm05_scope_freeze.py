import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

class FM05ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "FM05_SCOPE_ESTIMAND_SUFFICIENCY_CONTRACT.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "fm05_scope_estimand_sufficiency.schema.json").read_text(encoding="utf-8"))

    def test_schema_and_frozen_status(self):
        errors = sorted(Draft202012Validator(self.schema).iter_errors(self.contract), key=lambda e: list(e.path))
        self.assertFalse(errors, "\n".join(str(e) for e in errors))
        self.assertEqual(self.contract["status"], "FROZEN")
        self.assertFalse(self.contract["confirmatory_eligible"])

    def test_scope_and_estimand_are_frozen(self):
        scope = self.contract["scope"]
        self.assertEqual(scope["securities"], ["300750.SZ"])
        self.assertEqual(scope["drivers"], ["REVENUE", "NET_PROFIT"])
        self.assertEqual(scope["horizons"], ["3M", "6M", "12M"])
        self.assertEqual(scope["origin_schedule"]["origin_count"], 11)
        self.assertEqual(scope["model_instances"], [
            "SEASONAL_NAIVE", "PERSISTENCE_YOY", "TREND_LOG_LINEAR_8Q", "MEAN_REVERSION_YOY_8"
        ])
        estimand = self.contract["estimand"]
        self.assertEqual(estimand["selection_unit"], "security × driver × horizon × state_dimension × state_value × outer_origin")
        self.assertEqual(estimand["primary_metric"], "MAE")
        self.assertFalse(estimand["inferential_claims_allowed"])
        self.assertTrue(estimand["descriptive_only"])

    def test_sufficiency_boundary_is_explicit(self):
        s = self.contract["sufficiency_policy"]["current_adjudication"]
        self.assertEqual(s["status"], "INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION")
        self.assertEqual(s["outer_selection_unit_count"], 406)
        self.assertEqual(s["selected_count"], 0)
        self.assertEqual(s["outer_evaluated_count"], 0)
        self.assertEqual(s["no_selection_count"], 406)
        self.assertEqual(s["structural_conditional_group_count"], 79)
        self.assertEqual(s["empirical_conditional_group_count"], 0)

    def test_same_epoch_relaxation_is_forbidden(self):
        a = self.contract["amendment_policy"]
        forbidden = set(a["same_epoch_forbidden_changes"])
        for item in (
            "LOWER_SELECTION_MIN_COMMON_INNER_OBSERVATIONS",
            "MERGE_STATE_VALUES",
            "DELETE_OR_SKIP_ORIGINS",
            "EXPAND_MODEL_FAMILY_UNIVERSE",
            "CHANGE_PRIMARY_METRIC",
            "REDEFINE_ESTIMAND_FROM_FM04_OUTCOME",
        ):
            self.assertIn(item, forbidden)
        self.assertTrue(a["result_driven_change_requires_new_epoch"])
        self.assertTrue(a["new_epoch_requires_new_scope_and_estimand_freeze"])

    def test_capability_is_research_governance_only(self):
        c = self.contract["capability_boundary"]
        self.assertTrue(c["scope_freeze_only"])
        for key in ("model_selection", "production_router", "production_forecast", "automatic_execution", "investment_decision"):
            self.assertFalse(c[key])

if __name__ == "__main__":
    unittest.main()
