import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]

class FM07GateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/"FM07_RESEARCH_EPOCH_AMENDMENT_GATE.json").read_text())
        cls.schema=json.loads((ROOT/"fm07_research_epoch_amendment_gate.schema.json").read_text())

    def test_schema_and_frozen_gate(self):
        errs=sorted(Draft202012Validator(self.schema).iter_errors(self.contract),key=lambda e:list(e.path))
        self.assertFalse(errs,"\n".join(str(e) for e in errs))
        self.assertEqual(self.contract["status"],"FROZEN")
        self.assertEqual(self.contract["current_epoch_status"],"CLOSED_TO_SAME_EPOCH_AMENDMENT")

    def test_decision_is_non_amendment(self):
        self.assertEqual(self.contract["decision"],"DO_NOT_AMEND_CURRENT_EPOCH")
        self.assertTrue(self.contract["new_epoch_required_for_scope_change"])

    def test_frozen_fm05_evidence(self):
        e=self.contract["evidence_basis"]
        self.assertEqual(e["sufficiency_status"],"INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION")
        self.assertEqual(e["outer_selection_unit_count"],406)
        self.assertEqual(e["selected_count"],0)
        self.assertEqual(e["outer_evaluated_count"],0)
        self.assertEqual(e["no_selection_count"],406)
        self.assertEqual(e["structural_conditional_group_count"],79)
        self.assertEqual(e["empirical_conditional_group_count"],0)

    def test_all_scope_change_classes_require_new_epoch(self):
        self.assertGreaterEqual(len(self.contract["amendment_classes"]),8)
        for item in self.contract["amendment_classes"]:
            self.assertFalse(item["same_epoch_allowed"])
            self.assertTrue(item["requires_new_epoch"])

    def test_new_epoch_has_pre_execution_controls(self):
        self.assertTrue(all(self.contract["new_epoch_entry_requirements"].values()))

    def test_gate_does_not_open_or_produce(self):
        c=self.contract["capability_boundary"]
        self.assertTrue(c["amendment_gate_only"])
        self.assertFalse(c["opens_new_epoch_automatically"])
        self.assertFalse(c["changes_current_scope"])
        self.assertFalse(c["changes_current_estimand"])
        self.assertFalse(c["changes_current_threshold"])
        self.assertFalse(c["model_selection"])
        self.assertFalse(c["production_router"])
        self.assertFalse(c["automatic_execution"])
        self.assertFalse(c["investment_decision"])

if __name__=="__main__":
    unittest.main()
