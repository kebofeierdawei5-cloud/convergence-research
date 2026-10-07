#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def canonical_sha(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fm04-result", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    contract = load(ROOT / "FM05_SCOPE_ESTIMAND_SUFFICIENCY_CONTRACT.json")
    schema = load(ROOT / "fm05_scope_estimand_sufficiency.schema.json")
    errors = sorted(Draft202012Validator(schema).iter_errors(contract), key=lambda e: list(e.path))
    assert not errors, "\n".join(str(e) for e in errors)

    fm04 = load(args.fm04_result)
    assert fm04["schema_version"] == contract["provenance_policy"]["required_fm04_result_schema_version"]
    assert fm04["contract_id"] == contract["provenance_policy"]["fm04_contract_id"]
    assert fm04["research_epoch_id"] == contract["research_epoch_id"]
    assert fm04["confirmatory_eligible"] is False

    ib = fm04["input_bindings"]
    assert ib["state_snapshot_sha256"] == contract["provenance_policy"]["state_snapshot_sha256"]
    for key, expected in contract["provenance_policy"]["upstream_git_blob_sha"].items():
        assert ib[key + "_git_blob_sha"] == expected

    summary = fm04["summary"]
    adjudication = contract["sufficiency_policy"]["current_adjudication"]
    for result_key, freeze_key in [
        ("outer_selection_unit_count", "outer_selection_unit_count"),
        ("selected_count", "selected_count"),
        ("outer_evaluated_count", "outer_evaluated_count"),
        ("no_selection_count", "no_selection_count"),
        ("conditional_group_count", "structural_conditional_group_count"),
        ("empirical_conditional_group_count", "empirical_conditional_group_count"),
    ]:
        assert summary[result_key] == adjudication[freeze_key]

    assert summary["current_price_used"] is False
    assert summary["automatic_execution"] is False
    assert len(fm04["conditional_group_definitions"]) == adjudication["structural_conditional_group_count"]
    assert len(fm04["conditional_empirical_performance"]) == adjudication["empirical_conditional_group_count"]
    assert all(e["status"] == "NO_SELECTION" for e in fm04["outer_selection_evaluations"])

    paths = {
        "state_contract": "research/fm03/FM03_STATE_CONTRACT.json",
        "driver_history": "research/fm01/CATL_DRIVER_HISTORY.ndjson",
        "outer_universe_lock": "research/fm00/OU-M12-FM00-CATL-001.json",
        "research_plan": "research/fm00/RP-M12-FM00-EXP-001.json",
        "candidate_space": "research/fm00/CS-M12-FM00-CATL-001.json",
        "purity_boundary": "research/fm00/EPB-M12-FM00-EXP-001.json",
    }
    for key, path in paths.items():
        got = subprocess.check_output(["git", "hash-object", path], text=True).strip()
        assert got == contract["provenance_policy"]["upstream_git_blob_sha"][key]

    receipt = {
        "schema_version": "IIOS-FM05-SCOPE-FREEZE-RECEIPT-0.1",
        "status": "PASS",
        "contract_id": contract["contract_id"],
        "research_epoch_id": contract["research_epoch_id"],
        "confirmatory_eligible": False,
        "contract_canonical_sha256": canonical_sha(contract),
        "fm04_result_sha256": hashlib.sha256(Path(args.fm04_result).read_bytes()).hexdigest(),
        "adjudication": adjudication,
        "capability_boundary": contract["capability_boundary"],
        "same_epoch_result_driven_changes_forbidden": True,
        "current_epoch_unchanged": True,
    }
    Path(args.output).write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("FM05 Scope / Estimand / Sufficiency Freeze: PASS")

if __name__ == "__main__":
    main()
