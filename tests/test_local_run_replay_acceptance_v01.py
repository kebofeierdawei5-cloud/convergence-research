from __future__ import annotations

import hashlib
import json
import os
import select
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from iios_mvp import local_run_replay_acceptance_v01 as acceptance


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "验收IIOS全流程与Replay.command"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def _bundle(
    tmp_path: Path,
    *,
    replay_of: str | None = None,
    run_dir_name: str | None = None,
) -> Path:
    run_dir = tmp_path / (run_dir_name or "local-pilot-TEST-20261015T123456Z")
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
    receipt["file_manifest"] = {}
    for filename in ("input.json", "analysis.json", "report.md"):
        payload = (run_dir / filename).read_bytes()
        receipt["file_manifest"][filename] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byte_size": len(payload),
        }
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


UPDATE_HELPER = REPO_ROOT / "tools" / "iios_update_local_main_v01.sh"


def test_acceptance_launcher_updates_local_main_before_importing_current_modules() -> None:
    content = LAUNCHER.read_text(encoding="utf-8")
    update_call = 'bash "$REPO_ROOT/tools/iios_update_local_main_v01.sh" "$REPO_ROOT"'
    module_check = '[[ ! -f "$REPO_ROOT/iios_mvp/local_run_replay_acceptance_v01.py" ]]'
    assert update_call in content
    assert module_check in content
    assert content.index(update_call) < content.index(module_check)
    assert "未能安全更新到最新 origin/main" in content


def test_local_main_updater_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(UPDATE_HELPER)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stdout}\n{result.stderr}")
    return result


def _git_remote_and_checkout(tmp_path: Path) -> tuple[Path, Path, Path]:
    import shutil

    remote = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    checkout = tmp_path / "checkout"
    remote_result = subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(remote)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert remote_result.returncode == 0, remote_result.stderr
    seed.mkdir()
    _git(tmp_path, "init", "--initial-branch=main", str(seed))
    _git(seed, "config", "user.email", "iios-test@example.invalid")
    _git(seed, "config", "user.name", "IIOS acceptance test")
    (seed / "tools").mkdir()
    shutil.copy2(UPDATE_HELPER, seed / "tools" / UPDATE_HELPER.name)
    (seed / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "baseline")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", "main")
    _git(tmp_path, "clone", str(remote), str(checkout))
    _git(checkout, "config", "user.email", "iios-test@example.invalid")
    _git(checkout, "config", "user.name", "IIOS acceptance test")
    return remote, seed, checkout


def _push_remote_update(seed: Path) -> str:
    (seed / "README.md").write_text("updated from origin/main\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "remote update")
    _git(seed, "push", "origin", "main")
    return _git(seed, "rev-parse", "HEAD").stdout.strip()


def _run_update(checkout: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(UPDATE_HELPER), str(checkout)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_updater_fast_forwards_clean_local_main_to_origin_main(tmp_path: Path) -> None:
    _remote, seed, checkout = _git_remote_and_checkout(tmp_path)
    expected_head = _push_remote_update(seed)
    result = _run_update(checkout)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(checkout, "branch", "--show-current").stdout.strip() == "main"
    assert _git(checkout, "rev-parse", "HEAD").stdout.strip() == expected_head
    assert (checkout / "README.md").read_text(encoding="utf-8") == "updated from origin/main\n"
    assert _git(checkout, "status", "--porcelain", "--untracked-files=all").stdout == ""
    assert "本机代码更新并复核成功" in result.stdout


def test_updater_refuses_dirty_worktree_without_overwriting_local_file(tmp_path: Path) -> None:
    _remote, seed, checkout = _git_remote_and_checkout(tmp_path)
    _push_remote_update(seed)
    local_note = checkout / "operator-notes.txt"
    local_note.write_text("keep this private work\n", encoding="utf-8")
    before_head = _git(checkout, "rev-parse", "HEAD").stdout.strip()
    result = _run_update(checkout)
    assert result.returncode == 20
    assert local_note.read_text(encoding="utf-8") == "keep this private work\n"
    assert _git(checkout, "rev-parse", "HEAD").stdout.strip() == before_head
    assert "未执行更新" in result.stdout + result.stderr


def test_updater_switches_clean_feature_checkout_to_main_and_preserves_feature_ref(tmp_path: Path) -> None:
    _remote, seed, checkout = _git_remote_and_checkout(tmp_path)
    _git(checkout, "switch", "-c", "operator-work")
    _push_remote_update(seed)
    expected_head = _git(seed, "rev-parse", "HEAD").stdout.strip()
    result = _run_update(checkout)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(checkout, "branch", "--show-current").stdout.strip() == "main"
    assert _git(checkout, "rev-parse", "HEAD").stdout.strip() == expected_head
    assert _git(checkout, "show-ref", "--verify", "refs/heads/operator-work").returncode == 0


def test_updater_refuses_diverged_main_without_rewriting_local_or_remote_commit(tmp_path: Path) -> None:
    _remote, seed, checkout = _git_remote_and_checkout(tmp_path)
    (checkout / "local-only.txt").write_text("local commit stays\n", encoding="utf-8")
    _git(checkout, "add", "local-only.txt")
    _git(checkout, "commit", "-m", "local-only")
    local_head = _git(checkout, "rev-parse", "HEAD").stdout.strip()
    remote_head = _push_remote_update(seed)
    result = _run_update(checkout)
    assert result.returncode == 20
    assert _git(checkout, "rev-parse", "HEAD").stdout.strip() == local_head
    assert _git(checkout, "rev-parse", "refs/remotes/origin/main").stdout.strip() == remote_head
    assert (checkout / "local-only.txt").read_text(encoding="utf-8") == "local commit stays\n"
    assert "已分叉" in result.stdout + result.stderr


@pytest.mark.skipif(os.name == "nt", reason="POSIX private-log permission contract")
def test_stream_command_creates_private_log_and_streams_output(tmp_path: Path) -> None:
    log_path = tmp_path / "stream.log"
    return_code = acceptance._stream_command(
        [sys.executable, "-c", "print('IIOS_STREAM_OK')"],
        log_path,
    )
    assert return_code == 0
    assert log_path.read_text(encoding="utf-8") == "IIOS_STREAM_OK\n"
    assert log_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX interactive-prompt streaming test")
def test_stream_command_shows_prompt_before_child_receives_input(tmp_path: Path) -> None:
    """Regression: a prompt without a newline must be visible before stdin is sent."""
    log_path = tmp_path / "interactive-prompt.log"
    child_code = (
        "import sys; "
        "print('公司名称:', end='', flush=True); "
        "value = input(); "
        "print('\\n收到=' + value)"
    )
    driver_code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from iios_mvp import local_run_replay_acceptance_v01 as acceptance\n"
        "raise SystemExit(acceptance._stream_command("
        "[sys.executable, '-c', " + repr(child_code) + "], Path(sys.argv[1])))\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", driver_code, str(log_path)],
        cwd=str(REPO_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    prompt = "公司名称:".encode("utf-8")
    seen = bytearray()
    deadline = time.monotonic() + 5
    try:
        while not seen.endswith(prompt):
            remaining = deadline - time.monotonic()
            assert remaining > 0, (
                "Prompt was not displayed before input was sent; "
                f"captured output={seen!r}"
            )
            ready, _, _ = select.select([process.stdout], [], [], remaining)
            assert ready, (
                "Prompt was not displayed before input was sent; "
                f"captured output={seen!r}"
            )
            chunk = os.read(process.stdout.fileno(), 1)
            assert chunk, f"Driver exited before showing prompt; output={seen!r}"
            seen.extend(chunk)

        process.stdin.write("纽威股份\n".encode("utf-8"))
        process.stdin.flush()
        tail = process.stdout.read().decode("utf-8", errors="replace")
        assert process.wait(timeout=5) == 0, tail
        assert "收到=纽威股份" in tail
        full_log = log_path.read_text(encoding="utf-8")
        assert "公司名称:" in full_log
        assert "收到=纽威股份" in full_log
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()


def test_acceptance_bundle_includes_first_run_replay_logs_and_verified_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root = tmp_path / "runs"
    run_root.mkdir(mode=0o700)
    original = _bundle(
        run_root,
        run_dir_name="local-pilot-ORIGINAL-20261019T120000Z",
    )
    replay = _bundle(
        run_root,
        replay_of=original.name,
        run_dir_name="local-pilot-REPLAY-20261019T120100Z",
    )
    monkeypatch.setattr(acceptance, "RUN_ROOT", run_root)

    log_root = tmp_path / "acceptance-logs"
    log_root.mkdir(mode=0o700)
    log_path = log_root / "current-run.log"
    log_path.write_text("original + replay acceptance log\n", encoding="utf-8")
    if os.name != "nt":
        log_path.chmod(0o600)
    monkeypatch.setattr(acceptance, "LOG_ROOT", log_root)

    bundle_root = tmp_path / "private" / "acceptance-bundles"
    monkeypatch.setattr(acceptance, "ACCEPTANCE_BUNDLE_ROOT", bundle_root)
    comparison = {
        "mode": "DECISION_MATERIAL_FIELDS_V1",
        "status": "MATCH",
        "hash_verification": "PASS",
        "prior_pilot_id": original.name,
        "compared_fields": ["decision", "valuation_timing"],
        "mismatched_fields": [],
    }
    archive_path = acceptance._create_acceptance_bundle(
        original_dir=original,
        replay_dir=replay,
        log_paths=[log_path],
        comparison=comparison,
        prompt_issues=[],
    )

    assert archive_path.is_file()
    if os.name != "nt":
        assert archive_path.stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(archive_path, "r") as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        first_analysis = f"first_run/{original.name}/analysis.json"
        replay_analysis = f"replay_run/{replay.name}/analysis.json"
        assert first_analysis in names
        assert replay_analysis in names
        assert f"first_run/{original.name}/pilot_receipt.json" in names
        assert f"replay_run/{replay.name}/pilot_receipt.json" in names
        assert "acceptance_logs/current-run.log" in names
        assert "acceptance_summary.json" in names
        assert "bundle_manifest.json" in names

        summary = json.loads(archive.read("acceptance_summary.json"))
        assert summary["overall_status"] == "PASS"
        assert summary["technical_status"] == "PASS"
        assert summary["first_run"]["pilot_id"] == original.name
        assert summary["replay_run"]["pilot_id"] == replay.name
        assert summary["replay_comparison"] == comparison
        assert summary["formal_decision_created"] is False
        assert summary["execution_authorized"] is False
        assert summary["auto_execution"] is False

        manifest = json.loads(archive.read("bundle_manifest.json"))
        assert manifest["hash_algorithm"] == "SHA-256"
        assert manifest["manifest_excludes_self"] is True
        for record in manifest["files"]:
            payload = archive.read(record["path"])
            assert len(payload) == record["byte_size"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]


def test_acceptance_bundle_rejects_run_artifact_drift_from_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root = tmp_path / "runs"
    run_root.mkdir(mode=0o700)
    original = _bundle(
        run_root,
        run_dir_name="local-pilot-ORIGINAL-20261019T130000Z",
    )
    replay = _bundle(
        run_root,
        replay_of=original.name,
        run_dir_name="local-pilot-REPLAY-20261019T130100Z",
    )
    monkeypatch.setattr(acceptance, "RUN_ROOT", run_root)
    (original / "analysis.json").write_text('{"changed":true}\n', encoding="utf-8")

    with pytest.raises(
        acceptance.AcceptanceError,
        match="ACCEPTANCE_BUNDLE_SOURCE_HASH_MISMATCH:first_run:analysis.json",
    ):
        acceptance._create_acceptance_bundle(
            original_dir=original,
            replay_dir=replay,
            log_paths=[],
            comparison={"status": "MATCH", "hash_verification": "PASS", "mismatched_fields": []},
            prompt_issues=[],
        )
    assert not (tmp_path / "acceptance-bundles").exists()
