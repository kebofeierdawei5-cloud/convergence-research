from __future__ import annotations

import ast
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]
B2E_PATH = ROOT / "iios_mvp" / "b2e_nl_semantic_decision_e2e_v01.py"
LIFECYCLE_PATH = ROOT / "iios_mvp" / "decision_lifecycle_production.py"
LIFECYCLE_SCHEMA_PATH = ROOT / "schemas" / "decision_lifecycle_v0.2.schema.json"
B2D3_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "iios_b2d3_real_provider.yml"
LIFECYCLE_TESTS_PATH = ROOT / "tests" / "test_decision_lifecycle_production.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path))


def _function(path: Path, name: str) -> ast.FunctionDef:
    for node in _tree(path).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function not found: {name}")


def _called_names(node: ast.AST) -> list[str]:
    names = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            names.append(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            names.append(child.func.attr)
    return names


def _contains_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def test_rt_fr1_semantic_projection_is_the_actual_decision_input():
    source = _source(B2E_PATH)
    fn = _function(B2E_PATH, "run_b2e_conformance")
    assert "project_thesis_semantic_to_core(" in source
    assignments = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "projected_case" for t in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "project_thesis_semantic_to_core"
    ]
    assert assignments, "semantic output must be transformed into the canonical economic case"
    decision_calls = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "decide_v03"
    ]
    assert decision_calls, "canonical Decision Kernel call missing"
    assert any(_contains_name(call, "projected_case") for call in decision_calls)
    assert "_build_snapshot(case=projected_case" in source
    assert "case=projected_case" in source[source.index("admit_canonical_decision("):]


def test_rt_fr2_forecast_valuation_admission_is_validator_backed():
    source = _source(B2E_PATH)
    fn = _function(B2E_PATH, "_transition_pre_decision")
    names = _called_names(fn)
    assert "validate_forecast_valuation_return_lineage" in names
    assert source.index("validate_forecast_valuation_return_lineage(") < source.index("Stage.FORECAST_ADMITTED")
    assert 'forecast_ref["admission_record_hash"]' in source
    assert 'valuation_ref["admission_record_hash"]' in source
    assert "Stage.DECISION_PENDING" in source
    assert "input_hashes=(" in source


def test_rt_fr3_semantic_authority_guard_recurses_through_objects_and_lists():
    source = _source(B2E_PATH)
    fn = _function(B2E_PATH, "_assert_no_authority_fields")
    assert "FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS" in source
    assert "walk(output, \"output\")" in source
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "walk"
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "child"
        for node in ast.walk(fn)
    ), "authority guard must recursively inspect mapping/list children"
    assert "isinstance(node, (list, tuple))" in source
    assert "authority fields at " in source


def test_rt_fr4_decision_series_identity_is_derived_and_admission_bound():
    source = _source(LIFECYCLE_PATH)
    fn = _function(LIFECYCLE_PATH, "build_decision_revision")
    assert "def _derive_series_identity(" in source
    assert "canonical_series_id, series_identity, series_identity_hash = _derive_series_identity(snapshot_core)" in source
    assert "if bound_series_id != canonical_series_id" in source
    assert "'decision_series_identity': series_identity" in source
    assert "'decision_series_identity_hash': series_identity_hash" in source
    assert "decision series identity does not match canonical Decision Admission" in source
    validator = _function(LIFECYCLE_PATH, "validate_decision_revision")
    assert "decision series identity mismatch: series_id" in ast.unparse(validator)
    assert "decision series identity hash mismatch" in ast.unparse(validator)
    schema = json.loads(_source(LIFECYCLE_SCHEMA_PATH))
    required = set(schema["required"])
    assert {"decision_series_identity", "decision_series_identity_hash"} <= required
    identity = schema["properties"]["decision_series_identity"]
    assert set(identity["required"]) == {"case_id", "market", "symbol", "company"}
    lifecycle_tests = _source(LIFECYCLE_TESTS_PATH)
    assert "test_revision_rejects_noncanonical_series_id" in lifecycle_tests
    assert "test_revision_rejects_tampered_series_identity_even_with_rehashed_revision" in lifecycle_tests


def test_rt_fr5_only_dispatch_is_authorized_to_touch_provider_runtime():
    source = _source(B2D3_WORKFLOW_PATH)
    workflow = yaml.load(source, Loader=yaml.BaseLoader)
    assert workflow["name"] == "IIOS B2-D3 Real Provider Live Evidence"
    assert list(workflow["on"].keys()) == ["workflow_dispatch"]
    assert set(workflow["jobs"]) == {"preflight", "live_and_verify"}
    trigger_block = source.split("permissions:", 1)[0]
    events = re.findall(r"(?m)^  ([A-Za-z_][A-Za-z0-9_-]*):\s*$", trigger_block)
    assert events == ["workflow_dispatch"], f"unexpected workflow triggers: {events}"

    jobs_block = source.split("jobs:", 1)[1]
    job_matches = list(re.finditer(r"(?m)^  ([A-Za-z_][A-Za-z0-9_-]*):\s*$", jobs_block))
    guarded_secret_jobs = []
    for index, match in enumerate(job_matches):
        block_start = match.end()
        block_end = job_matches[index + 1].start() if index + 1 < len(job_matches) else len(jobs_block)
        block = jobs_block[block_start:block_end]
        header = block.split("steps:", 1)[0]
        if "secrets." in block:
            guarded_secret_jobs.append(match.group(1))
            assert "if: github.event_name == 'workflow_dispatch'" in header, (
                f"provider-secret-bearing job lacks fail-closed trigger guard: {match.group(1)}"
            )
    assert set(guarded_secret_jobs) == {"preflight", "live_and_verify"}
    assert "needs: preflight" in jobs_block
    assert "python -m iios_mvp.live_provider_evidence_v01" in source
    assert "python -m iios_mvp.live_provider_independent_verify_v01" in source
    assert "LIVE_RESPONSE_CAPTURED_AND_INDEPENDENTLY_VERIFIED" in source


def test_rt_fr5_no_provider_credentials_or_live_capture_were_admitted_by_repair():
    state = _source(ROOT / "docs" / "PROJECT_STATE_INDEX.md")
    assert "B2-D Live Provider Invocation / Evidence                BLOCKED" in state
    assert "B2-E fixture-backed conformance is not admitted as live-provider evidence." in state
