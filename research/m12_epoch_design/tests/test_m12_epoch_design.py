import json, unittest
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]

class ProposalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((ROOT/"M12_NEW_RESEARCH_EPOCH_DESIGN_PROPOSAL.json").read_text())
        cls.s=json.loads((ROOT/"m12_new_research_epoch_design_proposal.schema.json").read_text())
    def test_schema(self):
        errs=sorted(Draft202012Validator(self.s).iter_errors(self.p),key=lambda e:list(e.path))
        self.assertFalse(errs,"\n".join(str(e) for e in errs))
    def test_current_epoch_is_preserved(self):
        self.assertEqual(self.p["current_epoch_action"],"CLOSE_AND_PRESERVE")
        self.assertFalse(self.p["activation_authorized"])
    def test_recommended_path_preserves_n3(self):
        r=self.p["recommended_design"]
        self.assertEqual(r["strategy"],"CROSS_SECTIONAL_UNIVERSE_EXPANSION_WITH_THRESHOLD_PRESERVATION")
        self.assertEqual(r["min_common_inner_observations"],3)
        self.assertFalse(r["same_epoch_result_reuse_for_tuning"])
    def test_threshold_relaxation_not_default(self):
        x=next(a for a in self.p["candidate_amendments"] if a["id"]=="THRESHOLD_RELAXATION")
        self.assertEqual(x["status"],"REJECTED_FOR_NEXT_EPOCH_DEFAULT")
        self.assertFalse(x["preserves_selection_threshold"])
    def test_a02_is_hard_entry_gate(self):
        self.assertEqual(self.p["current_blocker"]["id"],"A02_DATA_ADMISSION")
        self.assertEqual(self.p["current_blocker"]["status"],"BLOCKED")
    def test_no_capability_leak(self):
        c=self.p["capability_boundary"]
        for k in ("activates_new_epoch","changes_current_epoch","changes_current_estimand","changes_current_threshold","model_selection","production_router","automatic_execution","investment_decision"):
            self.assertFalse(c[k])

if __name__=="__main__":
    unittest.main()
