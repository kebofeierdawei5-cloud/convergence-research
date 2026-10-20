from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGER = REPO_ROOT / "tools" / "package_macos_launchers_v01.py"
COMMANDS = (
    "IIOS_独立安全启动当前主线.command",
    "启动IIOS投资分析.command",
    "验收IIOS全流程与Replay.command",
)


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
        assert set(COMMANDS).issubset(names)
        readmes = [name for name in names if name.endswith(".txt")]
        assert readmes
        readme = zf.read(readmes[0]).decode("utf-8")
        assert "/bin/bash" in readme
        assert "chmod" in readme
        for filename in COMMANDS:
            info = zf.getinfo(filename)
            assert info.create_system == 3
            assert ((info.external_attr >> 16) & 0o777) == 0o755
            assert zf.read(filename).startswith(b"#!/bin/bash")


def test_no_chmod_fallback_is_documented_in_project_incident_record() -> None:
    content = (REPO_ROOT / "docs" / "MACOS_COMMAND_PERMISSION_INCIDENT_20261020.md").read_text(encoding="utf-8")
    assert "/bin/bash" in content
    assert "第四次" in content or "第 4 次" in content
    assert "不要" in content and "chmod" in content
