#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parent
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--a02-status-doc',required=True); a=ap.parse_args()
    m=load(ROOT/'B01_FREE_FIRST_SOURCE_MATRIX.json'); s=load(ROOT/'b01_free_first_source_matrix.schema.json')
    errs=sorted(Draft202012Validator(s).iter_errors(m),key=lambda e:list(e.path)); assert not errs,'\n'.join(str(e) for e in errs)
    doc_blob=subprocess.check_output(['git','hash-object',a.a02_status_doc],text=True).strip(); assert doc_blob=='2b2297a62d2a9dbdd14abdf815f9e8d796282580'
    assert m['admission_state']['status']=='BLOCKED'
    assert m['free_first_rules']['paid_source_required'] is False and m['free_first_rules']['tushare_credential_required'] is False
    covered=set(); [covered.update(x['domains']) for x in m['sources']]; assert set(m['required_domains']).issubset(covered)
    print('A02 B-01 free-first source matrix: PASS / ADMISSION REMAINS BLOCKED')
if __name__=='__main__': main()
