#!/usr/bin/env python3
"""Build a one-click macOS IIOS acceptance ZIP with a single entrypoint.

The ZIP contains exactly one executable .command launcher and one short README.
The launcher is sourced from the audited canonical-main bootstrap, renamed for
the distribution, and starts the complete first-run + Replay flow automatically.
"""
from __future__ import annotations

import argparse
import os
import stat
import subprocess
import zipfile
from pathlib import Path

SOURCE_LAUNCHER = "IIOS_独立安全启动当前主线.command"
LAUNCHER_NAME = "IIOS_一键启用并验收.command"
README_NAME = "先看我_只需双击.txt"


def readme(commit_sha: str) -> str:
    return f"""IIOS 一键启用与端到端验收
对应 canonical main 提交：{commit_sha}

只需：
1. 在 Finder 中解压这个 ZIP。
2. 双击唯一的启动文件：{LAUNCHER_NAME}。

启动器会自动取得并核验公开仓库 canonical main，在 ~/.iios-private/source/ 建立隔离副本，
随后直接进入完整的“首次研究 → 运行包哈希检查 → 真正 Replay → Replay 包哈希检查”流程。
不需要手动执行 Git 命令，不需要再选菜单，不会 reset/覆盖已有项目目录。
ChatGPT 研究回答、必要的风险/估值确认仍由操作者完成人工确认；不会跳过投资判断所需的人工步骤。
不需要付费 API key 或本地模型；不自动下单，结果仍标记 PILOT_NON_CANONICAL。

如果 macOS 仍提示“没有执行权限”，不要反复 chmod，也不要关闭 Gatekeeper：
打开 Terminal，输入 /bin/bash（末尾留空格），将 {LAUNCHER_NAME} 拖进去并按回车。
若文件位于 Downloads，也可以运行：
/bin/bash "$HOME/Downloads/{LAUNCHER_NAME}"

输入、报告、回执、日志与审计 ZIP 只保存在 ~/.iios-private/，不要上传到 GitHub。
"""


def _write_zip_entry(zf: zipfile.ZipFile, name: str, data: bytes, mode: int) -> None:
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def build_package(repo_root: Path, output_dir: Path, commit_sha: str) -> Path:
    repo_root = repo_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source = repo_root / SOURCE_LAUNCHER
    if source.is_symlink() or not source.is_file():
        raise FileNotFoundError(f"Expected regular launcher is missing: {SOURCE_LAUNCHER}")
    data = source.read_bytes()
    if not data.startswith(b"#!/bin/bash"):
        raise ValueError(f"Launcher has no Bash shebang: {SOURCE_LAUNCHER}")
    if b"IIOS_ACCEPTANCE_AUTO_START=1 python3 -m iios_mvp.local_run_replay_acceptance_v01" not in data:
        raise ValueError("Source launcher does not enable the one-click full E2E acceptance path")

    out = output_dir / f"IIOS-macos-launchers-{commit_sha[:12]}.zip"
    with zipfile.ZipFile(out, "w") as zf:
        _write_zip_entry(zf, LAUNCHER_NAME, data, 0o755)
        _write_zip_entry(zf, README_NAME, readme(commit_sha).encode("utf-8"), 0o644)

    with zipfile.ZipFile(out, "r") as zf:
        expected_names = {LAUNCHER_NAME, README_NAME}
        if set(zf.namelist()) != expected_names:
            raise RuntimeError(f"Package must contain exactly one launcher and one README: {zf.namelist()!r}")
        info = zf.getinfo(LAUNCHER_NAME)
        mode = (info.external_attr >> 16) & 0o777
        if info.create_system != 3 or mode != 0o755:
            raise RuntimeError(f"Executable mode lost in ZIP: {oct(mode)}")
        if not zf.read(LAUNCHER_NAME).startswith(b"#!/bin/bash"):
            raise RuntimeError("Invalid launcher bytes")
        package_readme = zf.read(README_NAME).decode("utf-8")
        if LAUNCHER_NAME not in package_readme or "/bin/bash" not in package_readme:
            raise RuntimeError("One-click startup or no-exec-bit fallback guidance missing")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA"))
    args = parser.parse_args()
    commit_sha = (args.commit_sha or "").strip()
    if not commit_sha or any(ch not in "0123456789abcdefABCDEF" for ch in commit_sha):
        try:
            commit_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            parser.error(f"--commit-sha or a valid Git checkout is required: {exc}")
    if len(commit_sha) < 12:
        parser.error("--commit-sha must contain at least 12 hexadecimal characters")
    out = build_package(Path.cwd(), Path(args.output_dir), commit_sha)
    print(f"PACKAGE_CREATED={out}")
    print(f"ONE_CLICK_LAUNCHER={LAUNCHER_NAME}")
    print("ZIP_CONTENTS=1 executable launcher + 1 README")
    print("COMMAND_FILE_UNIX_MODE=100755")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
