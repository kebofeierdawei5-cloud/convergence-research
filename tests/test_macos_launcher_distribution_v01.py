from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGER = REPO_ROOT / "tools" / "package_macos_launchers_v01.py"
ONE_CLICK_COMMAND = "IIOS_一键启用并验收.command"


def test_packager_creates_zip_with_executable_posix_mode_and_readme(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PACKAGER),
            "--output-dir",
            str(tmp_path),
            "--commit-sha",
            "0123456789abcdef0123456789abcdef01234567",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    archives = list(tmp_path.glob("IIOS-macos-launchers-*.zip"))
    assert len(archives) == 1

    with zipfile.ZipFile(archives[0]) as zf:
        names = set(zf.namelist())
        assert names == {ONE_CLICK_COMMAND, "先看我_只需双击.txt"}
        readmes = [name for name in names if name.endswith(".txt")]
        assert readmes == ["先看我_只需双击.txt"]
        readme = zf.read(readmes[0]).decode("utf-8")
        assert "/bin/bash" in readme
        assert "双击唯一的启动文件" in readme
        assert "chmod" in readme
        info = zf.getinfo(ONE_CLICK_COMMAND)
        assert info.create_system == 3
        assert ((info.external_attr >> 16) & 0o777) == 0o755
        launcher_bytes = zf.read(ONE_CLICK_COMMAND)
        assert launcher_bytes.startswith(b"#!/bin/bash")
        assert b"IIOS_ACCEPTANCE_AUTO_START=1 python3 -m iios_mvp.local_run_replay_acceptance_v01" in launcher_bytes


def test_current_e2e_runbook_covers_permission_json_recovery_b27_and_private_outputs() -> None:
    runbook = (
        REPO_ROOT
        / "docs"
        / "iios"
        / "MACOS_REAL_E2E_ACCEPTANCE_RUNBOOK_20261021.md"
    ).read_text(encoding="utf-8")

    required_controls = (
        "IIOS_一键启用并验收.command",
        "/bin/bash",
        "CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT",
        "CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT",
        "CHATGPT_JSON_INVALID_CODE_FENCE_NOT_CLOSED",
        "_local_operator_controlled_field_recovery",
        "eps_earnings_bridge",
        "acceptance-bundles",
        "不要把 JSON 粘贴到 Terminal",
        "不要关闭 Gatekeeper",
        "自动进入完整分析",
    )
    missing = [item for item in required_controls if item not in runbook]
    assert not missing, f"current Mac E2E runbook is missing controls: {missing}"


def test_historical_mac_acceptance_guide_points_to_current_runbook() -> None:
    guide = (
        REPO_ROOT
        / "docs"
        / "iios"
        / "MACOS_FULL_RUN_AND_REPLAY_ACCEPTANCE_20261015.md"
    ).read_text(encoding="utf-8")
    assert "MACOS_REAL_E2E_ACCEPTANCE_RUNBOOK_20261021.md" in guide
    assert "follow the 2026-10-21 runbook" in guide or "使用本文" in guide


def test_no_chmod_fallback_is_documented_in_project_incident_record() -> None:
    content = (REPO_ROOT / "docs" / "MACOS_COMMAND_PERMISSION_INCIDENT_20261020.md").read_text(encoding="utf-8")
    assert "/bin/bash" in content
    assert "第四次" in content or "第 4 次" in content
    assert "不要" in content and "chmod" in content
