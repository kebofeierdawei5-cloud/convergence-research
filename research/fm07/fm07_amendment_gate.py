#!/usr/bin/env python3
import argparse, hashlib, json, subprocess
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parent

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def sha(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fm05-contract",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()

    contract=load(ROOT/"FM07_RESEARCH_EPOCH_AMENDMENT_GATE.json")
    schema=load(ROOT/"fm07_research_epoch_amendment_gate.schema.json")
    errs=sorted(Draft202012Validator(schema).iter_errors(contract),key=lambda e:list(e.path))
    assert not errs,"\n".join(str(e) for e in errs)

    fm05=load(a.fm05_contract)
    assert fm05["schema_version"]=="IIOS-FM05-SCOPE-ESTIMAND-SUFFICIENCY-0.1"
    assert fm05["contract_id"]=="FC-M12-FM05-CATL-001"
    assert fm05["research_epoch_id"]==contract["current_research_epoch_id"]
    assert fm05["status"]=="FROZEN"
    assert fm05["sufficiency_policy"]["current_adjudication"]["status"]=="INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION"

    blob=subprocess.check_output(["git","hash-object",a.fm05_contract],text=True).strip()
    assert blob==contract["evidence_basis"]["fm05_contract_git_blob_sha"]

    adj=fm05["sufficiency_policy"]["current_adjudication"]
    for key in ("outer_selection_unit_count","selected_count","outer_evaluated_count","no_selection_count","structural_conditional_group_count","empirical_conditional_group_count"):
        assert adj[key] == contract["evidence_basis"][key]

    assert contract["decision"]=="DO_NOT_AMEND_CURRENT_EPOCH"
    assert contract["new_epoch_required_for_scope_change"] is True
    assert contract["capability_boundary"]["opens_new_epoch_automatically"] is False

    receipt={
      "schema_version":"IIOS-FM07-RESEARCH-EPOCH-AMENDMENT-GATE-RECEIPT-0.1",
      "status":"PASS",
      "gate_id":contract["gate_id"],
      "current_research_epoch_id":contract["current_research_epoch_id"],
      "decision":contract["decision"],
      "contract_canonical_sha256":sha(contract),
      "fm05_contract_git_blob_sha":blob,
      "evidence_basis":contract["evidence_basis"],
      "new_epoch_required_for_scope_change":True,
      "opens_new_epoch_automatically":False
    }
    Path(a.output).write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("FM07 Research Epoch Amendment Gate: PASS")

if __name__=="__main__":
    main()
