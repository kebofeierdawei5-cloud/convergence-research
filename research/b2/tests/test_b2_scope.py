from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
B2_DIR = ROOT / "research" / "b2"
B2_WORKFLOW = ROOT / ".github" / "workflows" / "iios_b2.yml"

FORBIDDEN_TOKENS = (
    "A02",
    "CSI800",
    "CSI Industry",
    "OU-M12-A02",
    "000906cons.xls",
    "a02_exact_admission",
)


def test_b2_namespace_contains_no_a02_or_csi_research_track_code() -> None:
    for path in B2_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".json", ".md", ".yml", ".yaml"}:
            continue
        if path == Path(__file__):
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"forbidden research-track token {token!r} found in {path}"


def test_b2_workflow_contains_no_a02_or_csi_research_track_execution() -> None:
    text = B2_WORKFLOW.read_text(encoding="utf-8")
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden research-track token {token!r} found in B2 workflow"


def test_a02_validator_is_outside_b2_namespace() -> None:
    assert not (B2_DIR / "a02_exact_admission.py").exists()
    assert not (B2_DIR / "A02_EXACT_ADMISSION_ATTEMPT_2026-10-04.json").exists()
    assert (ROOT / "research" / "a02" / "a02_exact_admission.py").exists()
