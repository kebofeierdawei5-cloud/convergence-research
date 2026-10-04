from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "iios_mvp"
CORE_WORKFLOW = ROOT / ".github" / "workflows" / "iios_mvp.yml"
FM00_WORKFLOW = ROOT / ".github" / "workflows" / "iios_fm00.yml"

FORBIDDEN_CORE_REFERENCE_TOKENS = (
    "OU-M12-A02-CSI800-NONFIN-PIT-001",
    "CSI800",
    "CSI Industry",
    "000906cons.xls",
    "research/a02",
    "research/b2",
)


def test_core_python_has_no_research_import_dependency() -> None:
    import_pattern = re.compile(r"^\s*(?:from|import)\s+research(?:\.|\s|$)", re.MULTILINE)
    for path in CORE_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not import_pattern.search(text), f"research import found in {path}"


def test_investment_core_workflow_has_no_research_track_dependency() -> None:
    text = CORE_WORKFLOW.read_text(encoding="utf-8")
    for token in FORBIDDEN_CORE_REFERENCE_TOKENS:
        assert token not in text, f"forbidden research-track dependency in Investment Core workflow: {token}"
    assert "research/" not in text


def test_core_scope_contract_exists_and_sets_the_boundary() -> None:
    path = ROOT / "docs" / "iios" / "CORE_00_SCOPE_RECONCILIATION_v0.1.md"
    text = path.read_text(encoding="utf-8")
    assert "A02 admission is NOT a prerequisite" in text
    assert "MIE is explanatory/conditional infrastructure" in text
    assert "Historical case" in text
    assert "known_at <= cutoff" in text


def test_research_fm00_workflow_is_not_bound_to_core_documentation() -> None:
    text = FM00_WORKFLOW.read_text(encoding="utf-8")
    assert "'docs/iios/**'" not in text
    assert "'manifests/iios/**'" not in text
    assert "research/fm00/**" in text
