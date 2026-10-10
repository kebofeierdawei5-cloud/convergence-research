from __future__ import annotations

"""Read-only one-click readiness diagnostic. Never creates admissions or runs a decision."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any

CASE_ID = "RC-CN-A-605016-20261009"
REQUIRED = (
    "raw_request", "request_id", "run_id", "company", "investment_case",
    "evidence_manifest_path", "evidence_root", "artifact_type",
    "semantic_prompt", "decision_relevance",
)
STORE_DIRS = (
    "investment_admissions", "valuation_outputs",
    "current_price_admissions", "independent_forecast_admissions",
)
EXCLUDED = (
    "examples/", "tests/", "schemas/", "evidence/", "manifests/company_cases/",
    "research/", "docs/", "artifacts/", ".github/",
)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def has_case(value: Any, case_id: str) -> bool:
    if isinstance(value, dict):
        return value.get("case_id") == case_id or any(has_case(v, case_id) for v in value.values())
    if isinstance(value, list):
        return any(has_case(v, case_id) for v in value)
    return False


def under_checkout(value: str, root: Path, *, directory: bool) -> Path | None:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        if directory and not resolved.is_dir():
            return None
        if not directory and not resolved.is_file():
            return None
        return resolved
    except (OSError, ValueError):
        return None


def find_bundles(root: Path, case_id: str) -> list[dict[str, Any]]:
    """Only count tracked, full-shape bundles outside examples and fixtures."""
    try:
        raw = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.json"], cwd=root,
            check=True, capture_output=True, timeout=10,
        ).stdout.decode("utf-8")
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError):
        return []
    found = []
    for rel in sorted(set(p for p in raw.split("\0") if p.endswith(".json"))):
        if rel.startswith(EXCLUDED):
            continue
        data = read_json(root / rel)
        if not data or any(k not in data or data[k] in (None, "") for k in REQUIRED):
            continue
        if not has_case(data.get("investment_case"), case_id):
            continue
        manifest_path = under_checkout(str(data["evidence_manifest_path"]), root, directory=False)
        evidence_path = under_checkout(str(data["evidence_root"]), root, directory=True)
        manifest = read_json(manifest_path) if manifest_path else None
        rows = manifest.get("evidence") if manifest else None
        rows_valid = isinstance(rows, list) and bool(rows) and all(
            isinstance(row, dict) and row.get("evidence_id") and row.get("content_sha256")
            for row in rows
        )
        found.append({
            "path": rel,
            "manifest_exists_in_checkout": manifest_path is not None,
            "evidence_root_exists_in_checkout": evidence_path is not None,
            "manifest_has_hashed_evidence_rows": rows_valid,
            "structurally_usable_here": bool(manifest_path and evidence_path and rows_valid),
        })
    return found


def inspect_admissions(value: str | None) -> dict[str, Any]:
    if not value:
        return {"configured": False, "usable": False, "stores": {}, "path": None}
    root = Path(value).expanduser()
    try:
        root = root.resolve(strict=True)
        exists = root.is_dir()
    except OSError:
        exists = False
    stores = {name: bool(exists and (root / name).is_dir()) for name in STORE_DIRS}
    return {"configured": True, "usable": bool(exists and all(stores.values())), "stores": stores, "path": str(root)}


def build_report(root: Path, admission_root: str | None) -> dict[str, Any]:
    case_path = root / "manifests/company_cases" / f"{CASE_ID}.json"
    case_manifest = read_json(case_path)
    ledger_path = root / "evidence/real_cases" / CASE_ID / "FOLLOWUP_B2_RUN_20261010.json"
    ledger = read_json(ledger_path)
    bundle_candidates = find_bundles(root, CASE_ID)
    admissions = inspect_admissions(admission_root)
    blockers: list[dict[str, str]] = []

    if not case_manifest:
        blockers.append({"id": "CASE_MANIFEST_MISSING", "finding": "Canonical company case manifest not found.", "next": "Refresh the checkout from canonical main; do not reconstruct this file manually."})
    if not bundle_candidates:
        blockers.append({"id": "CANONICAL_REQUEST_BUNDLE_NOT_FOUND", "finding": "No tracked, full-shape canonical request bundle for this case exists outside examples/templates/tests.", "next": "A governed staging step must bind a reviewed request to the real case and admitted evidence; do not rename an example JSON."})
    elif not any(item["structurally_usable_here"] for item in bundle_candidates):
        blockers.append({"id": "REQUEST_BUNDLE_EVIDENCE_PATHS_NOT_USABLE", "finding": "Bundle-shaped file(s) exist, but the referenced evidence manifest/root cannot be verified inside this canonical checkout.", "next": "Restore exact admitted manifest and raw bytes through governed intake; do not create placeholder evidence."})
    if not admissions["usable"]:
        blockers.append({"id": "CANONICAL_ADMISSION_ROOT_NOT_PROVISIONED", "finding": "No usable formal admission store is available to this hosted diagnostic run.", "next": "Provision/mount the existing formal store in the actual execution host. This GitHub runner cannot see folders on your Mac; do not upload private admissions or manufacture records."})

    b2 = ledger.get("b2", {}) if ledger else {}
    if not ledger:
        blockers.append({"id": "B2_LEDGER_MISSING", "finding": "Latest B2 follow-up ledger not found.", "next": "Refresh canonical source-adjudication records from main."})
    elif b2.get("evidence_admission") is not True or b2.get("pit_admission") is not True:
        blockers.append({"id": "B2_EVIDENCE_PIT_NOT_ADMITTED", "finding": "Canonical B2 ledger remains blocked; market_price is still UNKNOWN/unadmitted.", "next": str(b2.get("current_blocker_reason") or "Resolve the unchanged B2/PIT finding using a cutoff-correct, permitted source; do not relax the gate.")})

    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        head = "UNKNOWN_NOT_A_GIT_CHECKOUT"

    return {
        "schema_version": "IIOS-ONE-CLICK-READINESS-0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": CASE_ID,
        "canonical_git_head": head,
        "status": "BLOCKED" if blockers else "PRECHECK_CANDIDATE_READY_NOT_EXECUTED",
        "mode": "READ_ONLY_PREFLIGHT_ONLY",
        "company_case_manifest_present": case_manifest is not None,
        "request_bundle_candidates": bundle_candidates,
        "admission_root": admissions,
        "b2": {
            "overall": ledger.get("overall", "UNKNOWN") if ledger else "UNKNOWN",
            "missing_required_field_groups": b2.get("missing_required_field_groups", []),
            "evidence_admission": b2.get("evidence_admission", False),
            "pit_admission": b2.get("pit_admission", False),
            "formal_valuation_decision_publication_report_receipt_authorized": b2.get("formal_valuation_decision_publication_report_run_receipt_authorized", False),
            "current_blocker_reason": b2.get("current_blocker_reason"),
        },
        "blockers": blockers,
        "safety_boundary": {
            "formal_canonical_run_executed": False,
            "chatgpt_called": False,
            "admission_records_created_or_modified": False,
            "decision_created": False,
            "formal_report_or_run_receipt_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    b2 = report["b2"]
    lines = [
        "# IIOS — 605016 readiness report", "",
        f"- **Result:** {report['status']}",
        f"- **Case:** {report['case_id']}",
        f"- **Canonical commit:** {report['canonical_git_head']}",
        f"- **Generated:** {report['generated_at']}",
        "- **Mode:** read-only preflight. This is not an investment decision or production acceptance.", "",
        "## At a glance",
        f"- Company case manifest: {'present' if report['company_case_manifest_present'] else 'missing'}",
        f"- Canonical request-bundle candidates: {len(report['request_bundle_candidates'])}",
        f"- Formal admission store usable in this run: {'yes' if report['admission_root']['usable'] else 'no'}",
        f"- Evidence/PIT admission: {'PASS' if b2['evidence_admission'] is True and b2['pit_admission'] is True else 'NOT ADMITTED'}",
        f"- Missing required evidence groups: {', '.join(b2['missing_required_field_groups']) or 'none recorded'}", "",
        "## What needs to happen next",
    ]
    if not report["blockers"]:
        lines.append("No blocker was found by this limited preflight. A formal canonical run has still NOT been executed.")
    else:
        for i, blocker in enumerate(report["blockers"], 1):
            lines.extend([f"### {i}. {blocker['id']}", f"**Finding:** {blocker['finding']}", f"**Next action:** {blocker['next']}", ""])
    if b2.get("current_blocker_reason"):
        lines.extend(["## Current market-price blocker", b2["current_blocker_reason"], ""])
    lines.extend([
        "## What this click does not do",
        "- It does not access files on your Mac, create admissions, call ChatGPT, or submit a trade.",
        "- It does not run the formal canonical investment decision workflow or create a formal Decision/report/Run Receipt.",
        "- A green GitHub Actions status means only that this diagnostic report was generated; the report's internal readiness result is authoritative.",
        "- Free ChatGPT web responses still require a manual handoff. Their origin remains unverified by a cryptographic provider signature.", "",
        "## Open related pages",
        "- [Canonical company case](https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/manifests/company_cases/RC-CN-A-605016-20261009.json)",
        "- [Latest B2 ledger](https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/evidence/real_cases/RC-CN-A-605016-20261009/FOLLOWUP_B2_RUN_20261010.json)",
        "- [Open ChatGPT Free](https://chatgpt.com/)", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--report-dir", default="artifacts/operator-readiness")
    parser.add_argument("--admission-root", default=os.environ.get("IIOS_CANONICAL_ADMISSION_ROOT"))
    args = parser.parse_args()
    root = Path(args.repo_root).resolve(strict=True)
    output = Path(args.report_dir)
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(root, args.admission_root)
    md = output / f"{CASE_ID}-readiness.md"
    machine = output / f"{CASE_ID}-readiness.json"
    md.write_text(render_markdown(report), encoding="utf-8")
    machine.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "diagnostic_generation": "SUCCESS",
        "case_status": report["status"],
        "blocker_count": len(report["blockers"]),
        "markdown_report": str(md),
        "machine_report": str(machine),
        "formal_run_executed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
