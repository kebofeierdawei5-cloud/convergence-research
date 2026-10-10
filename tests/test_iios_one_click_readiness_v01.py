from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "iios_one_click_readiness_v01.py"
SPEC = importlib.util.spec_from_file_location("iios_one_click_readiness_v01", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_missing_bundle_and_admissions_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "manifests/company_cases").mkdir(parents=True)
    (root / "evidence/real_cases/RC-CN-A-605016-20261009").mkdir(parents=True)
    (root / "manifests/company_cases/RC-CN-A-605016-20261009.json").write_text(
        json.dumps({"case_id": "RC-CN-A-605016-20261009"}), encoding="utf-8"
    )
    (root / "evidence/real_cases/RC-CN-A-605016-20261009/FOLLOWUP_B2_RUN_20261010.json").write_text(
        json.dumps({"overall": "BLOCKED_AS_REQUIRED", "b2": {"evidence_admission": False, "pit_admission": False, "missing_required_field_groups": ["market_price"]}}), encoding="utf-8"
    )
    report = MODULE.build_report(root, None)
    ids = {b["id"] for b in report["blockers"]}
    assert report["status"] == "BLOCKED"
    assert "CANONICAL_REQUEST_BUNDLE_NOT_FOUND" in ids
    assert "CANONICAL_ADMISSION_ROOT_NOT_PROVISIONED" in ids
    assert "B2_EVIDENCE_PIT_NOT_ADMITTED" in ids
    assert report["safety_boundary"]["formal_canonical_run_executed"] is False
    assert report["safety_boundary"]["admission_records_created_or_modified"] is False


def test_examples_are_never_selected_as_canonical_bundle(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "examples").mkdir(parents=True)
    payload = {
        "raw_request": "test", "request_id": "r", "run_id": "r",
        "company": "test", "investment_case": {"case_id": "RC-CN-A-605016-20261009"},
        "evidence_manifest_path": "manifest.json", "evidence_root": "evidence",
        "artifact_type": "THESIS", "semantic_prompt": "test", "decision_relevance": "test",
    }
    (root / "examples/example.json").write_text(json.dumps(payload), encoding="utf-8")
    assert MODULE.find_bundles(root, "RC-CN-A-605016-20261009") == []


def test_admission_root_check_is_read_only(tmp_path: Path) -> None:
    missing = tmp_path / "not-created"
    report = MODULE.inspect_admissions(str(missing))
    assert report["usable"] is False
    assert not missing.exists()


def test_report_explicitly_disclaims_run_execution() -> None:
    report = {
        "status": "BLOCKED", "case_id": "RC-CN-A-605016-20261009",
        "canonical_git_head": "abc", "generated_at": "2026-10-10T00:00:00Z",
        "company_case_manifest_present": False, "request_bundle_candidates": [],
        "admission_root": {"usable": False},
        "b2": {"evidence_admission": False, "pit_admission": False, "missing_required_field_groups": ["market_price"], "current_blocker_reason": "price unresolved"},
        "blockers": [{"id": "BUNDLE_MISSING", "finding": "missing", "next": "stage it"}],
    }
    text = MODULE.render_markdown(report)
    assert "does not run the formal canonical investment decision workflow" in text
    assert "does not" in text
    assert "market_price" in text
