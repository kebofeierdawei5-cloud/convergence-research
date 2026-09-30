from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any
from fm00_common import load_json, sha256_json
from jsonschema import Draft202012Validator

REQUIRED_FILES = {
    "epoch": "RE-EXPLORATORY-CATL-20260930.json",
    "plan": "RP-M12-FM00-EXP-001.json",
    "candidate_space": "CS-M12-FM00-CATL-001.json",
    "outer_lock": "OU-M12-FM00-CATL-001.json",
    "purity_boundary": "EPB-M12-FM00-EXP-001.json",
}
SCHEMA_FILES = {
    "epoch": "research_epoch.schema.json",
    "plan": "research_plan.schema.json",
    "candidate_space": "candidate_space.schema.json",
    "outer_lock": "outer_universe_lock.schema.json",
    "purity_boundary": "evaluation_purity_boundary.schema.json",
}


def err(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def validate_package(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    objs: dict[str, Any] = {}
    for key, name in REQUIRED_FILES.items():
        p = root / name
        if not p.exists():
            findings.append(err("FM00-FILE-001", f"Missing required artifact: {name}"))
            continue
        try:
            objs[key] = load_json(p)
        except Exception as exc:
            findings.append(err("FM00-FILE-002", f"Invalid JSON in {name}: {exc}"))

    if findings:
        return {"status":"FAIL","findings":findings}

    # Structural validation is independently recomputed from JSON Schema.
    for key, schema_name in SCHEMA_FILES.items():
        try:
            schema = load_json(root / schema_name)
            validator = Draft202012Validator(schema)
            for issue in sorted(validator.iter_errors(objs[key]), key=lambda e: list(e.path)):
                path = ".".join(str(x) for x in issue.path) or "$"
                findings.append(err("FM00-SCHEMA-001", f"{key} schema violation at {path}: {issue.message}"))
        except Exception as exc:
            findings.append(err("FM00-SCHEMA-002", f"Unable to validate {key} against {schema_name}: {exc}"))

    if findings:
        return {"status":"FAIL","findings":findings}

    epoch = objs["epoch"]
    plan = objs["plan"]
    cs = objs["candidate_space"]
    ou = objs["outer_lock"]
    epb = objs["purity_boundary"]

    # Cross-object identity bindings.
    if epoch["epoch_id"] != plan["epoch_id"]:
        findings.append(err("FM00-BIND-001", "Research Plan epoch_id does not match Research Epoch."))
    expected_refs = {
        "research_plan_id": plan["plan_id"],
        "candidate_space_id": cs["candidate_space_id"],
        "outer_universe_lock_id": ou["lock_id"],
        "purity_boundary_id": epb["boundary_id"],
    }
    for field, expected in expected_refs.items():
        if epoch["scope_refs"][field] != expected:
            findings.append(err("FM00-BIND-002", f"Epoch scope_refs.{field} does not resolve to the exact current artifact."))

    # Frozen research-cleanliness semantics.
    if epoch["epoch_type"] == "EXPLORATORY":
        if epoch["research_cleanliness"]["confirmatory_eligible"]:
            findings.append(err("FM00-PURITY-001", "EXPLORATORY epoch cannot be confirmatory_eligible."))
        if epoch["result_exposure"]["allowed_use"] not in {"DEVELOPMENT_ONLY", "DESCRIPTIVE_ONLY"}:
            findings.append(err("FM00-PURITY-002", "EXPLORATORY result exposure must remain development/descriptive only."))
    if epoch["contamination"]["status"] in {"EXPOSED_PRIOR_RESULTS","EXPOSED_CURRENT_RESULTS"}:
        if epoch["research_cleanliness"]["status"] != "CONTAMINATED":
            findings.append(err("FM00-PURITY-003", "Exposed epoch must be marked CONTAMINATED."))
        if epoch["research_cleanliness"]["confirmatory_eligible"]:
            findings.append(err("FM00-PURITY-004", "Contaminated epoch cannot be confirmatory eligible."))
    if epoch["result_exposure"]["can_read_current_oos_results"]:
        findings.append(err("FM00-PURITY-005", "Current OOS results must not be visible inside the same epoch."))

    # Frozen object rules.
    if epoch["status"] == "FROZEN" and cs["status"] != "FROZEN":
        findings.append(err("FM00-FREEZE-001", "Frozen epoch requires frozen Candidate Space."))
    if epoch["status"] == "FROZEN" and plan["status"] != "FROZEN":
        findings.append(err("FM00-FREEZE-002", "Frozen epoch requires frozen Research Plan."))
    if epoch["status"] == "FROZEN" and ou["status"] != "FROZEN":
        findings.append(err("FM00-FREEZE-003", "Frozen epoch requires frozen Outer Universe Lock."))
    if epoch["status"] == "FROZEN" and epb["status"] != "FROZEN":
        findings.append(err("FM00-FREEZE-004", "Frozen epoch requires frozen Purity Boundary."))

    # PIT and anti-leakage contract.
    if not plan["data_policy"]["pit_required"]:
        findings.append(err("FM00-PIT-001", "PIT is mandatory."))
    if plan["data_policy"]["future_actuals_allowed_in_feature_engineering"]:
        findings.append(err("FM00-PIT-002", "Future actuals cannot be used in feature engineering."))
    if plan["data_policy"]["current_price_allowed_in_forecast_inputs"]:
        findings.append(err("FM00-LEAK-001", "Current price cannot be a forecast input in the FM-00 contract."))
    if plan["selection_policy"]["result_driven_tuning_same_epoch"]:
        findings.append(err("FM00-PURITY-006", "Result-driven tuning in the same epoch is forbidden."))

    # Pairwise / statistics semantics.
    if plan["evaluation"]["pairwise_comparison_rule"] != "SAME_ORIGIN_UNIVERSE_SAME_TARGET_SAME_HORIZON_SAME_ACTUAL":
        findings.append(err("FM00-STATS-001", "Pairwise comparison universe is not locked."))
    if plan["evaluation"]["independence_statement"] != "ROLLING_ORIGINS_ARE_NOT_ASSUMED_IID":
        findings.append(err("FM00-STATS-002", "Rolling-origin iid assumption must remain explicitly false."))
    if plan["evaluation"]["insufficiency_outcome"] != "NO_SELECTION":
        findings.append(err("FM00-STATS-003", "Statistical insufficiency must permit NO_SELECTION."))

    # Outer universe immutability / no silent origin removal.
    seen = set()
    for origin in ou["origins"]:
        oid = origin["origin_id"]
        if oid in seen:
            findings.append(err("FM00-ORIGIN-001", f"Duplicate origin_id: {oid}"))
        seen.add(oid)
    if ou["eligibility_policy"] != "PRE_SCHEDULED_AND_IMMUTABLE_AFTER_FREEZE":
        findings.append(err("FM00-ORIGIN-002", "Origin eligibility must be pre-scheduled and immutable after freeze."))
    horizon_counts = {h: sum(h in o["scheduled_horizons"] for o in ou["origins"]) for h in ("3M","6M","12M")}
    expected_origin_counts = {"3M": 11, "6M": 10, "12M": 8}
    for h, expected in expected_origin_counts.items():
        if horizon_counts[h] != expected:
            findings.append(err("FM00-ORIGIN-004", f"Locked exploratory schedule has {horizon_counts[h]} eligible origins for {h}; expected {expected} from M1.1 baseline."))
    if ou["exclusion_record_policy"] != "RETAIN_ORIGIN_WITH_EXPLICIT_REASON_AND_NO_SILENT_DROP":
        findings.append(err("FM00-ORIGIN-003", "Excluded origins must remain visible with explicit reasons."))

    # Feature PIT contract.
    for feature in cs["features"]:
        if feature["pit_rule"] != "ONLY_INFORMATION_AVAILABLE_AT_ORIGIN":
            findings.append(err("FM00-FEATURE-001", f"Feature {feature['feature_id']} violates PIT rule."))
        if feature["transform_class"] == "LEARNED_PIT_FIT" and "PIT" not in feature["formula"] and "historical" not in feature["formula"].lower() and "rolling" not in feature["formula"].lower():
            findings.append(err("FM00-FEATURE-002", f"Learned feature {feature['feature_id']} lacks an auditable PIT-fit marker in formula."))

    # No production router from exploratory epoch.
    if plan["selection_policy"]["production_router_allowed"]:
        findings.append(err("FM00-ROUTER-001", "FM-00 exploratory epoch cannot authorize a production router."))

    hashes = {k: sha256_json(v) for k, v in objs.items()}
    schema_hashes = {k: sha256_json(load_json(root / name)) for k, name in SCHEMA_FILES.items()}
    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "artifact_hashes": hashes,
        "schema_hashes": schema_hashes,
        "semantic_summary": {
            "epoch_type": epoch["epoch_type"],
            "contamination": epoch["contamination"]["status"],
            "confirmatory_eligible": epoch["research_cleanliness"]["confirmatory_eligible"],
            "candidate_space_status": cs["status"],
            "outer_origin_count": len(ou["origins"]),
            "horizon_origin_counts": {h: sum(h in o["scheduled_horizons"] for o in ou["origins"]) for h in ("3M","6M","12M")},
            "production_router_allowed": plan["selection_policy"]["production_router_allowed"],
        }
    }


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    result = validate_package(root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
