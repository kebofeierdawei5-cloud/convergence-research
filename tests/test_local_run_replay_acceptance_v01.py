from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from iios_mvp import local_run_replay_acceptance_v01 as acceptance


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "验收IIOS全流程与Replay.command"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def _bundle(tmp_path: Path, *, replay_of: str | None = None) -> Path:
    run_dir = tmp_path / "local-pilot-TEST-20261015T123456Z"
    run_dir.mkdir(mode=0o700)
    if os.name != "nt":
        run_dir.chmod(0o700)

    analysis = {
        "schema_version": acceptance.ANALYSIS_SCHEMA,
        "pilot_id": run_dir.name,
        "status": acceptance.PILOT_STATUS,
        **{key: {} for key in acceptance.REQUIRED_ANALYSIS_FIELDS},
        "decision": {"provisional_action": "REVIEW_REQUIRED"},
        "valuation_transmission": {"status": "NOT_LINKED"},
        "price_zone_sensitivity": {"status": "UNKNOWN"},
        "governance": {
            "formal_decision_created": False,
            "canonical_run_receipt_created": False,
            "execution_authorized": False,
            "auto_execution": False,
        },
    }
    receipt = {
        "receipt_schema": acceptance.RECEIPT_SCHEMA,
        "status": acceptance.PILOT_STATUS,
        "pilot_id": run_dir.name,
        "replay_of": replay_of,
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }
    (run_dir / "input.json").write_text('{"schema_version":"test"}', encoding="utf-8")
    (run_dir / "report.md").write_text("# IIOS test report\n", encoding="utf-8")
    _write_json(run_dir / "analysis.json", analysis)
    _write_json(run_dir / "pilot_receipt.json", receipt)
    if os.name != "nt":
        (run_dir / "input.json").chmod(0o600)
        (run_dir / "report.md").chmod(0o600)
    return run_dir


def test_acceptance_launcher_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(LAUNCHER)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_acceptance_launcher_calls_the_acceptance_module_and_has_no_destructive_cleanup() -> None:
    content = LAUNCHER.read_text(encoding="utf-8")
    assert "python3 -m iios_mvp.local_run_replay_acceptance_v01" in content
    assert '[[ ! -f "$REPO_ROOT/iios_mvp/local_investment_pilot_v01.py" ]]' in content
    assert "set -euo pipefail" in content
    assert "rm -rf" not in content
    assert "git reset --hard" not in content
    assert "按回车关闭窗口" in content


def test_extract_cli_result_accepts_check_run_schema_without_run_dir(tmp_path: Path) -> None:
    log = tmp_path / "cli.log"
    log.write_text(
        "checking bundle...\n"
        + json.dumps({
            "status": "PILOT_BUNDLE_HASH_CHECK_PASS",
            "pilot_id": "local-pilot-TEST-20261015T123456Z",
            "hash_algorithm": "SHA-256",
            "verified_files": [],
        }, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    result = acceptance._extract_cli_result(log, {"PILOT_BUNDLE_HASH_CHECK_PASS"})
    assert result["status"] == "PILOT_BUNDLE_HASH_CHECK_PASS"
    assert "run_dir" not in result


def test_extract_cli_result_chooses_the_last_complete_run_result(tmp_path: Path) -> None:
    log = tmp_path / "wizard.log"
    first = {
        "status": "PILOT_CREATED",
        "pilot_id": "local-pilot-OLD",
        "run_dir": "/private/old",
    }
    last = {
        "status": "PILOT_CREATED",
        "pilot_id": "local-pilot-NEW",
        "run_dir": "/private/new",
    }
    log.write_text(
        "wizard text\n"
        + json.dumps(first, ensure_ascii=False)
        + "\nmore output\n"
        + json.dumps(last, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    result = acceptance._extract_cli_result(log, {"PILOT_CREATED"})
    assert result["pilot_id"] == "local-pilot-NEW"
    assert result["run_dir"] == "/private/new"


def test_prompt_completion_issues_detect_skipped_portfolio_and_unknown_b5() -> None:
    issues = acceptance._prompt_completion_issues({
        "portfolio_package": {"status": "NOT_PROVIDED"},
        "operator_valuation_context": {
            "selected_model_family": "UNKNOWN",
            "baseline_includes_project": None,
        },
    })
    assert any("组合风险预算" in issue for issue in issues)
    assert any("主估值模型" in issue for issue in issues)


def test_prompt_completion_issues_require_eps_project_scope_confirmation() -> None:
    issues = acceptance._prompt_completion_issues({
        "portfolio_package": {"status": "CONDITIONAL_PACKAGE_READY_NOT_AUTHORIZED"},
        "operator_valuation_context": {
            "selected_model_family": "EPS_MULTIPLE",
            "baseline_includes_project": None,
        },
    })
    assert len(issues) == 1
    assert "未确认原估值是否已包含项目" in issues[0]


def test_non_eps_model_does_not_require_eps_project_scope_flag() -> None:
    issues = acceptance._prompt_completion_issues({
        "portfolio_package": {"status": "CONDITIONAL_PACKAGE_READY_NOT_AUTHORIZED"},
        "operator_valuation_context": {
            "selected_model_family": "FCF_DCF",
            "baseline_includes_project": None,
        },
    })
    assert issues == []


def test_inspect_bundle_checks_required_current_b5_b6_fields_and_no_trade_flags(tmp_path: Path) -> None:
    run_dir = _bundle(tmp_path)
    analysis, receipt = acceptance._inspect_bundle(run_dir, expected_replay_of=None)
    assert analysis["valuation_transmission"]
    assert analysis["price_zone_sensitivity"]
    assert receipt["status"] == acceptance.PILOT_STATUS


def test_inspect_bundle_rejects_wrong_replay_parent(tmp_path: Path) -> None:
    run_dir = _bundle(tmp_path, replay_of="some-other-run")
    with pytest.raises(acceptance.AcceptanceError, match="RUN_RECEIPT_REPLAY_PARENT_MISMATCH"):
        acceptance._inspect_bundle(run_dir, expected_replay_of=None)


def test_inspect_bundle_fails_closed_when_trade_boundary_is_not_false(tmp_path: Path) -> None:
    run_dir = _bundle(tmp_path)
    analysis = json.loads((run_dir / "analysis.json").read_text(encoding="utf-8"))
    analysis["governance"]["execution_authorized"] = True
    _write_json(run_dir / "analysis.json", analysis)
    with pytest.raises(acceptance.AcceptanceError, match="NO_TRADE_BOUNDARY_NOT_FALSE"):
        acceptance._inspect_bundle(run_dir, expected_replay_of=None)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission contract")
def test_inspect_bundle_rejects_world_readable_output(tmp_path: Path) -> None:
    run_dir = _bundle(tmp_path)
    (run_dir / "report.md").chmod(0o644)
    with pytest.raises(acceptance.AcceptanceError, match="FILE_PERMISSIONS_TOO_OPEN"):
        acceptance._inspect_bundle(run_dir, expected_replay_of=None)
