from pathlib import Path
import ast

ROOT = Path(__file__).parents[1]


def test_b2e_does_not_call_decision_from_semantic_producer():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.append(node.func.id)
    assert "_assert_no_authority_fields" in calls
    assert "admit_canonical_decision" in calls


def test_b2e_requires_canonical_decision_admission():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    assert "admit_canonical_decision(" in source
    assert "build_decision_revision(" in source


def test_b2e_human_execution_boundary_is_explicit():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    assert '"semantic_producer_can_decide": False' in source
    assert '"canonical_decision_kernel_is_authoritative": True' in source
    assert '"human_approval_is_required": True' in source
    assert '"automatic_execution_is_forbidden": True' in source


def test_b2e_does_not_import_live_provider_or_order_execution():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    assert "live_provider_" not in source
    assert "order" not in source.lower()
