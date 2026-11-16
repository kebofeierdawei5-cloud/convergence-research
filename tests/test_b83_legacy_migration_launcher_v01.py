from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "B83_旧运行包迁移验收.command"
PACKAGER = REPO_ROOT / "tools" / "package_b83_legacy_migration_launcher_v01.py"
LAUNCHER_NAME = "B83_旧运行包迁移验收.command"
README_NAME = "先看我_B83旧包迁移.txt"
PILOT_ID = "local-pilot-002810-20261012T141631129796Z"


def test_b83_legacy_launcher_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(LAUNCHER)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_b83_launcher_pins_one_existing_run_and_is_non_destructive() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert 'B83_BRANCH="feat/b83-durable-task-resume-20261108"' in source
    assert f'PILOT_ID="{PILOT_ID}"' in source
    assert 'IIOS_ACCEPTANCE_EXISTING_RUN_ID="$PILOT_ID"' in source
    assert 'SOURCE_ROOT="$PRIVATE_ROOT/source"' in source
    assert "git ls-remote" in source
    assert 'git clone --quiet --depth 1 --single-branch --branch "$B83_BRANCH"' in source
    assert "chmod 700" in source
    assert "git reset" not in source
    assert "git clean" not in source
    assert "git stash" not in source
    assert "rm -rf" not in source
    assert "git switch" not in source
    assert "IIOS_ACCEPTANCE_AUTO_START" not in source


def test_b83_packager_preserves_single_launcher_posix_mode_and_readme(tmp_path: Path) -> None:
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
    archives = list(tmp_path.glob("IIOS-B83-legacy-migration-*.zip"))
    assert len(archives) == 1
    with zipfile.ZipFile(archives[0], "r") as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {LAUNCHER_NAME, README_NAME}
        info = archive.getinfo(LAUNCHER_NAME)
        assert info.create_system == 3
        assert ((info.external_attr >> 16) & 0o777) == 0o755
        assert archive.read(LAUNCHER_NAME) == LAUNCHER.read_bytes()
        readme = archive.read(README_NAME).decode("utf-8")
        assert PILOT_ID in readme
        assert "/bin/bash" in readme
        assert "不要反复 chmod" in readme
        assert "不会要求重做 Round A / Round B" in readme


def test_launcher_and_runbook_do_not_recommend_changing_existing_checkout() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "~/.iios-private/source/" in source
    runbook = (
        REPO_ROOT
        / "docs"
        / "iios"
        / "MACOS_REAL_E2E_ACCEPTANCE_RUNBOOK_20261021.md"
    ).read_text(encoding="utf-8")
    assert "B83_旧运行包迁移验收.command" in runbook
    assert "IIOS_ACCEPTANCE_EXISTING_RUN_ID" in runbook
    assert "原始运行包" in runbook
    assert "历史哈希" in runbook
