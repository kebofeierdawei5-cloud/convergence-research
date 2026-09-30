import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fm00_validator import validate_package
from fm00_common import load_json, write_json


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "epoch": "RE-EXPLORATORY-CATL-20260930.json",
    "plan": "RP-M12-FM00-EXP-001.json",
    "candidate_space": "CS-M12-FM00-CATL-001.json",
    "outer_lock": "OU-M12-FM00-CATL-001.json",
    "purity_boundary": "EPB-M12-FM00-EXP-001.json",
    "epoch_schema": "research_epoch.schema.json",
    "plan_schema": "research_plan.schema.json",
    "candidate_space_schema": "candidate_space.schema.json",
    "outer_lock_schema": "outer_universe_lock.schema.json",
    "purity_boundary_schema": "evaluation_purity_boundary.schema.json",
}


class FM00Tests(unittest.TestCase):
    def copy_case(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for name in FILES.values():
            (root / name).write_text((ROOT / name).read_text(encoding="utf-8"), encoding="utf-8")
        return td, root

    def test_positive_control(self):
        result = validate_package(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["semantic_summary"]["confirmatory_eligible"])

    def test_current_oos_visibility_is_killed(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        epoch_path = root / FILES["epoch"]
        epoch = load_json(epoch_path)
        epoch["result_exposure"]["can_read_current_oos_results"] = True
        write_json(epoch_path, epoch)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(f["code"] == "FM00-PURITY-005" for f in result["findings"]))

    def test_result_driven_same_epoch_tuning_is_killed(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        plan_path = root / FILES["plan"]
        plan = load_json(plan_path)
        plan["selection_policy"]["result_driven_tuning_same_epoch"] = True
        write_json(plan_path, plan)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["findings"])
        self.assertTrue(any(f["code"] in {"FM00-PURITY-006", "FM00-SCHEMA-001"} for f in result["findings"]))

    def test_silent_origin_drop_policy_is_killed(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        ou_path = root / FILES["outer_lock"]
        ou = load_json(ou_path)
        ou["exclusion_record_policy"] = "DROP_AFTER_OUTCOME_CHECK"
        write_json(ou_path, ou)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["findings"])
        self.assertTrue(any(f["code"] in {"FM00-ORIGIN-003", "FM00-SCHEMA-001"} for f in result["findings"]))

    def test_contamination_cannot_be_renamed_clean(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        epoch_path = root / FILES["epoch"]
        epoch = load_json(epoch_path)
        epoch["research_cleanliness"]["status"] = "CLEAN_ATTESTED"
        epoch["research_cleanliness"]["confirmatory_eligible"] = True
        write_json(epoch_path, epoch)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("FM00-PURITY-003", codes)
        self.assertIn("FM00-PURITY-004", codes)

    def test_feature_future_lookahead_is_killed(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        path = root / FILES["candidate_space"]
        cs = load_json(path)
        cs["features"][0]["pit_rule"] = "USES_FUTURE_OUTCOME"
        write_json(path, cs)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["findings"])
        self.assertTrue(any(f["code"] in {"FM00-FEATURE-001", "FM00-SCHEMA-001"} for f in result["findings"]))

    def test_required_field_schema_violation_is_killed(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        path = root / FILES["plan"]
        plan = load_json(path)
        del plan["objective"]
        write_json(path, plan)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(f["code"] == "FM00-SCHEMA-001" for f in result["findings"]))

    def test_extra_field_schema_violation_is_killed(self):
        td, root = self.copy_case()
        self.addCleanup(td.cleanup)
        path = root / FILES["epoch"]
        epoch = load_json(path)
        epoch["attacker_override"] = True
        write_json(path, epoch)
        result = validate_package(root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(f["code"] == "FM00-SCHEMA-001" for f in result["findings"]))

if __name__ == "__main__":
    unittest.main()
