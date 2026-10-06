"""Deterministic C0 state-authority and continuity checks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_INDEX = REPO_ROOT / "docs" / "PROJECT_STATE_INDEX.md"
STATUS = REPO_ROOT / "STATUS.md"
REPO_README = REPO_ROOT / "README.md"
A0_POLICY = REPO_ROOT / "docs" / "iios" / "A0_STATE_AUTHORITY_POLICY_v0.1.md"
LEGACY_INDEX = REPO_ROOT / "docs" / "iios" / "IIOS_CURRENT_STATE_INDEX.md"
LEGACY_ROADMAP = REPO_ROOT / "docs" / "iios" / "IIOS_CONSOLIDATED_POST_REDTEAM_DEVELOPMENT_PLAN_2026-10-04.md"
STAGE_C_PLAN = REPO_ROOT / "docs" / "iios" / "IIOS_STAGE_C_PRODUCTIZATION_PLAN_v0.1.md"

def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing required file: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")

def _contains(text: str, needle: str, path: Path) -> None:
    if needle not in text:
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} missing required text: {needle!r}")

def _not_contains(text: str, needle: str, path: Path) -> None:
    if needle in text:
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} contains forbidden stale text: {needle!r}")

def _historical_banner(path: Path) -> None:
    header = '\n'.join(_read(path).splitlines()[:12])
    if "HISTORICAL" not in header and "SUPERSEDED" not in header:
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} lacks an explicit historical/superseded banner")
    _contains(header, "docs/PROJECT_STATE_INDEX.md", path)

def validate() -> None:
    canonical = _read(CANONICAL_INDEX)
    status = _read(STATUS)
    readme = _read(REPO_README)
    a0 = _read(A0_POLICY)
    stage_c = _read(STAGE_C_PLAN)

    _contains(canonical, "State classification: **CANONICAL**", CANONICAL_INDEX)
    _contains(canonical, "Authority: this file is the **only canonical Current State Index**.", CANONICAL_INDEX)
    _contains(canonical, "TR-03 Validation / Replay = PASS / MERGED / CANONICAL", CANONICAL_INDEX)
    _contains(canonical, "Stage C", CANONICAL_INDEX)
    _contains(canonical, "C0 Governance Hygiene / Stage Baseline", CANONICAL_INDEX)

    _contains(status, "State classification: **CANONICAL SUMMARY**", STATUS)
    _contains(status, "docs/PROJECT_STATE_INDEX.md", STATUS)
    _contains(status, "TR-03 Validation / Replay is now PASS / MERGED / CANONICAL.", STATUS)
    _contains(status, "Stage C", STATUS)

    _contains(readme, "Expected Annualized Return_H", REPO_README)
    _contains(readme, "Entry Return Cushion", REPO_README)
    _contains(readme, "Required Return", REPO_README)
    _contains(readme, "Stage C", REPO_README)
    _contains(readme, "scheduler", REPO_README)
    _contains(readme, "auto-ordering", REPO_README)
    _not_contains(readme, "No fixed 1–3 year holding period and no annualized-return core gate.", REPO_README)
    _not_contains(readme, "Batch 2 v0.1 = OPEN / RED-TEAM BLOCKED", REPO_README)
    _not_contains(readme, "Next: Investment Core Contract v0.2", REPO_README)

    _contains(a0, "docs/PROJECT_STATE_INDEX.md — the only canonical Current State Index", A0_POLICY)
    _contains(a0, "New development starts only from canonical `main`", A0_POLICY)

    _historical_banner(LEGACY_INDEX)
    _historical_banner(LEGACY_ROADMAP)

    _contains(stage_c, "# IIOS Stage C", STAGE_C_PLAN)
    _contains(stage_c, "### C0", STAGE_C_PLAN)
    _contains(stage_c, "### C8", STAGE_C_PLAN)

    candidates = list((REPO_ROOT / 'docs').rglob('*CURRENT_STATE_INDEX*.md'))
    for path in candidates:
        if path.resolve() == CANONICAL_INDEX.resolve():
            continue
        _historical_banner(path)

if __name__ == "__main__":
    validate()
    print("C0 state-authority validation: PASS")