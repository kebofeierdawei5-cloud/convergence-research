from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
B2E = ROOT / "iios_mvp" / "b2e_nl_semantic_decision_e2e_v01.py"
DECISION_LIFECYCLE = ROOT / "iios_mvp" / "decision_lifecycle_production.py"
B2E_SCHEMA = ROOT / "schemas" / "b2e_nl_semantic_decision_e2e_v0.1.schema.json"

FORBIDDEN = {
    "action",
    "decision_status",
    "new_capital_allowed",
    "human_approval_required",
    "auto_execution",
    "capital_effect",
    "decision_admission",
    "decision_precedence_rule_id",
    "decision_pre_admission_action",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_tree(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(_source(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function not found: {name}")


def _names(node: ast.AST) -> set[str]:
    return {
        n.id
        for n in ast.walk(node)
        if isinstance(n, ast.Name)
    }


def _attribute_calls(node: ast.AST) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    ]


def test_rt_b2f_001_request_identity_is_preserved_into_b2e():
    s = _source(B2E)
    assert "case_identity" in s
    assert "admitted_identity" in s
    assert "expanded Investment Core case identity does not match admitted Research Case" in s


def test_rt_b2f_002_semantic_authority_fields_are_denied_at_top_level():
    s = _source(B2E)
    assert "FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS" in s
    assert "FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS.intersection(output.keys())" in s


def test_rt_b2f_003_decision_kernel_is_reexecuted():
    s = _source(B2E)
    assert "canonical_decision = decide_v03(" in s
    assert "decision_admission = admit_canonical_decision(" in s


def test_rt_b2f_004_human_execution_boundary_remains_closed():
    schema = json.loads(_source(B2E_SCHEMA))
    assert schema["properties"]["human_approval_required"]["const"] is True
    assert schema["properties"]["auto_execution"]["const"] is False
    boundary = schema["properties"]["authority_boundary"]["properties"]
    assert boundary["semantic_producer_can_decide"]["const"] is False
    assert boundary["canonical_decision_kernel_is_authoritative"]["const"] is True


def test_rt_b2f_005_finding_semantic_output_has_no_economic_causal_edge():
    s = _source(B2E)
    tree = ast.parse(s)
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "decide_v03":
            calls.append(node)
    assert calls, "B2-E must call the canonical Decision Kernel"
    call = calls[0]
    assert any(
        isinstance(arg, ast.Name) and arg.id == "case"
        for arg in call.args
    ), "current B2-E Decision Kernel call no longer uses the explicit expanded case"
    assert "semantic" in _names(tree)
    raise AssertionError(
        "F-001 P0 reproduced: semantic artifact is admitted and hashed, but the canonical "
        "Decision Kernel is called with the independently supplied expanded Investment Core "
        "case; no semantic-output-to-economic-input transformation is present in B2-E."
    )


def test_rt_b2f_006_finding_forecast_and_valuation_stage_admission_is_not_validator_backed():
    source = _source(B2E)
    fn = _function_tree(B2E, "_transition_pre_decision")
    calls = _attribute_calls(fn)
    called_names = {
        c.func.attr
        for c in calls
        if isinstance(c.func, ast.Attribute)
    }
    assert "transition" in called_names
    validator_tokens = (
        "validate_forecast",
        "admit_forecast",
        "validate_valuation",
        "admit_valuation",
    )
    assert not any(token in source for token in validator_tokens)
    raise AssertionError(
        "F-002 P1 reproduced: B2-E can mark FORECAST_ADMITTED and VALUATION_ADMITTED "
        "from case mappings plus local hashes without invoking dedicated canonical "
        "Forecast/Valuation admission validators in the orchestrator path."
    )


def test_rt_b2f_007_finding_nested_decision_field_can_evade_semantic_guard():
    fn = _function_tree(B2E, "_assert_no_authority_fields")
    source = _source(B2E)
    assert "output.keys()" in source
    assert "recursive" not in source.lower()
    raise AssertionError(
        "F-003 P1 reproduced: semantic authority screening checks only top-level output keys; "
        "a nested object such as output.decision.action is outside the guard."
    )


def test_rt_b2f_008_finding_decision_series_identity_is_caller_supplied():
    fn = _function_tree(DECISION_LIFECYCLE, "build_decision_revision")
    args = {
        node.arg
        for node in ast.walk(fn)
        if isinstance(node, ast.arg)
    }
    for field in ("case_id", "market", "symbol", "company"):
        assert field in args or field == "case_id"
    source = _source(DECISION_LIFECYCLE)
    assert "decision_series_id: str" in source
    assert "'decision_series_id': _text(decision_series_id" in source
    assert "'market'" not in {
        key
        for key in [
            "decision_series_id_market",
            "decision_series_market",
        ]
    }
    raise AssertionError(
        "F-004 P1 reproduced: Decision Revision accepts an externally supplied decision_series_id "
        "and does not structurally carry market/symbol/company into the series identity record; "
        "series binding therefore depends on caller discipline rather than the lifecycle contract."
    )


def test_rt_b2f_009_b2e_does_not_import_order_or_live_provider():
    s = _source(B2E)
    assert "live_provider_" not in s
    assert "order" not in s.lower()


def test_rt_b2f_010_b2e_schema_is_closed():
    schema = json.loads(_source(B2E_SCHEMA))
    assert schema["additionalProperties"] is False


def test_rt_b2f_011_b2e_does_not_emit_human_approval():
    s = _source(B2E)
    assert "build_human_approval(" not in s


def test_rt_b2f_012_findings_are_independent_of_fixture_values():
    s = _source(B2E)
    assert "semantic_artifact_hash" in s
    assert "case_hash" in s
    assert "decide_v03(dict(case)" in s
