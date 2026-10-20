#!/usr/bin/env python3
"""Build a macOS IIOS launcher ZIP with explicit Unix executable modes.

Raw browser downloads of .command files do not reliably preserve execute bits.
This package writes 100755 to each command's ZIP central-directory external
attributes, then reads the archive back and verifies those bits before publish.
"""
from __future__ import annotations

import argparse
import os
import stat
import subprocess
import zipfile
from pathlib import Path

COMMAND_FILES = (
    "IIOS_独立安全启动当前主线.command",
    "启动IIOS投资分析.command",
    "验收IIOS全流程与Replay.command",
)
README_NAME = "先看我_IIOS命令文件权限与启动说明.txt"


def readme(commit_sha: str) -> str:
    return f"""IIOS macOS 启动器发行包
对应 canonical main 提交：{commit_sha}

推荐方式：
1. 从 GitHub Actions 的 IIOS macOS launcher distribution 工作流下载本 ZIP。
2. 在 Finder 中解压 ZIP。
3. 双击 IIOS_独立安全启动当前主线.command，启动最新 canonical main 的本地全流程与 Replay。

如果 macOS 仍提示“没有执行权限”，无需 chmod，也无需关闭系统安全保护：
1. 打开 Terminal。
2. 输入：/bin/bash （末尾保留一个空格）。
3. 将解压后的 IIOS_独立安全启动当前主线.command 拖入 Terminal。
4. 按回车运行。

若文件直接位于 Downloads，也可运行：
/bin/bash "$HOME/Downloads/IIOS_独立安全启动当前主线.command"

这个方式由 Bash 读取文本脚本，不依赖脚本文件自身具有执行位。
请只使用 canonical 仓库产生的发行包。研究输入、报告、回执、日志与审计 ZIP 应保留在 ~/.iios-private/，不要提交到 Git。
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
    files: list[tuple[str, bytes]] = []
    for filename in COMMAND_FILES:
        path = repo_root / filename
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"Expected regular launcher is missing: {filename}")
        data = path.read_bytes()
        if not data.startswith(b"#!/bin/bash"):
            raise ValueError(f"Launcher has no Bash shebang: {filename}")
        files.append((filename, data))

    out = output_dir / f"IIOS-macos-launchers-{commit_sha[:12]}.zip"
    with zipfile.ZipFile(out, "w") as zf:
        for filename, data in files:
            _write_zip_entry(zf, filename, data, 0o755)
        _write_zip_entry(zf, README_NAME, readme(commit_sha).encode("utf-8"), 0o644)

    with zipfile.ZipFile(out, "r") as zf:
        for filename in COMMAND_FILES:
            info = zf.getinfo(filename)
            mode = (info.external_attr >> 16) & 0o777
            if info.create_system != 3 or mode != 0o755:
                raise RuntimeError(f"Executable mode lost in ZIP for {filename}: {oct(mode)}")
        if README_NAME not in zf.namelist():
            raise RuntimeError("Permission/startup README missing from ZIP")
        for info in zf.infolist():
            if info.filename.endswith(".command") and not zf.read(info.filename).startswith(b"#!/bin/bash"):
                raise RuntimeError(f"Invalid launcher bytes: {info.filename}")
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
    print(f"COMMAND_FILE_UNIX_MODE=100755 ({', '.join(COMMAND_FILES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
