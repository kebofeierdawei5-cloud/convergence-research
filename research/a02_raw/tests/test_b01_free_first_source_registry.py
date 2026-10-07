import json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
class B01Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=json.loads((ROOT/'B01_FREE_FIRST_SOURCE_MATRIX.json').read_text()); cls.s=json.loads((ROOT/'b01_free_first_source_matrix.schema.json').read_text())
    def test_schema(self):
        errs=sorted(Draft202012Validator(self.s).iter_errors(self.m),key=lambda e:list(e.path)); self.assertFalse(errs,'\n'.join(str(e) for e in errs))
    def test_free_first(self):
        r=self.m['free_first_rules']; self.assertFalse(r['paid_source_required']); self.assertFalse(r['tushare_credential_required']); self.assertTrue(r['field_level_known_at_required']); self.assertTrue(r['raw_bytes_and_metadata_required'])
    def test_current_sources_are_not_pit_claims(self):
        for s in self.m['sources']:
            if s['temporal_capability']=='CURRENT_SNAPSHOT': self.assertFalse(s['pit_known_at_capability'])
    def test_blocked_admission(self):
        self.assertEqual(self.m['admission_state']['status'],'BLOCKED'); self.assertIn('industry_history',self.m['admission_state']['blocking_domains'])
if __name__=='__main__': unittest.main()
