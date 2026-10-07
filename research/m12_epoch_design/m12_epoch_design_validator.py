#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parent

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fm05-contract",required=True)
    ap.add_argument("--a02-evidence",required=True)
    args=ap.parse_args()

    proposal=load(ROOT/"M12_NEW_RESEARCH_EPOCH_DESIGN_PROPOSAL.json")
    schema=load(ROOT/"m12_new_research_epoch_design_proposal.schema.json")
    errs=sorted(Draft202012Validator(schema).iter_errors(proposal),key=lambda e:list(e.path))
    assert not errs,"\n".join(str(e) for e in errs)

    fm05=load(args.fm05_contract)
    assert fm05["contract_id"]=="FC-M12-FM05-CATL-001"
    assert fm05["research_epoch_id"]==proposal["current_epoch_id"]
    adj=fm05["sufficiency_policy"]["current_adjudication"]
    for k in ("outer_selection_units","selected","outer_evaluated","no_selection","structural_groups","empirical_groups"):
        mapping={"outer_selection_units":"outer_selection_unit_count","selected":"selected_count","outer_evaluated":"outer_evaluated_count","no_selection":"no_selection_count","structural_groups":"structural_conditional_group_count","empirical_groups":"empirical_conditional_group_count"}
        assert adj[mapping[k]]==proposal["observed_boundary"][k]

    blob=subprocess.check_output(["git","hash-object",args.a02_evidence],text=True).strip()
    assert blob==proposal["current_blocker"]["evidence_doc_git_blob_sha"]

    assert proposal["activation_authorized"] is False
    assert proposal["current_epoch_action"]=="CLOSE_AND_PRESERVE"
    assert proposal["recommended_design"]["min_common_inner_observations"]==3
    assert proposal["capability_boundary"]["changes_current_epoch"] is False

    print("M1.2 New Research Epoch Design Proposal: PASS")
if __name__=="__main__":
    main()
