from __future__ import annotations

"""Package the dedicated, pinned-purpose B83 legacy migration launcher."""

import argparse
import os
import stat
import subprocess
import zipfile
from pathlib import Path

LAUNCHER_NAME = "B83_旧运行包迁移验收.command"
README_NAME = "先看我_B83旧包迁移.txt"
SOURCE_LAUNCHER = LAUNCHER_NAME


def _readme(commit_sha: str) -> str:
    return f"""IIOS 历史运行包迁移与 Replay 验收
启动器构建提交：{commit_sha}

适用对象：local-pilot-002810-20261012T141631129796Z

只需：
1. 在 Finder 中解压下载的 GitHub Actions artifact ZIP。
2. 找到里面的发行 ZIP 并再解压一次。
3. 双击唯一启动文件：{LAUNCHER_NAME}。

启动器会从公开 GitHub 仓库取得 B83 历史包兼容修复分支的准确提交，
在 ~/.iios-private/source/ 建立或复用一个独立、只读用途的代码副本，
然后只处理上述固定旧运行包。不会切换、reset、stash、覆盖或清理现有项目目录。

本流程不会启动新研究向导，不会要求重做 Round A / Round B。
原始运行包、原始 Receipt 和历史失败日志保留；不会补造 2026-10-12 的历史哈希。
系统会单独生成迁移快照，再使用当前版本重建首轮运行并执行 Replay 和哈希校验。

如果 macOS 提示没有执行权限，不要反复 chmod，也不要关闭 Gatekeeper：
打开 Terminal，输入 /bin/bash（末尾留空格），将 {LAUNCHER_NAME} 拖入终端并按回车。
也可运行：/bin/bash "$HOME/Downloads/{LAUNCHER_NAME}"

输出、日志和 ZIP 只保存在本机 ~/.iios-private/。
技术验收通过不代表原始历史哈希可验证，也不构成正式投资 Decision 或交易授权。
"""


def _write_entry(archive: zipfile.ZipFile, name: str, payload: bytes, mode: int) -> None:
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, payload)


def build_package(repo_root: Path, output_dir: Path, commit_sha: str) -> Path:
    repo_root = repo_root.resolve()
    source = repo_root / SOURCE_LAUNCHER
    if source.is_symlink() or not source.is_file():
        raise FileNotFoundError(f"Expected regular launcher is missing: {SOURCE_LAUNCHER}")
    payload = source.read_bytes()
    if not payload.startswith(b"#!/bin/bash"):
        raise ValueError("Legacy migration launcher must have a Bash shebang")
    required = (
        b'B83_BRANCH="feat/b83-durable-task-resume-20261108"',
        b'PILOT_ID="local-pilot-002810-20261012T141631129796Z"',
        b'IIOS_ACCEPTANCE_EXISTING_RUN_ID="$PILOT_ID"',
        b'git ls-remote',
        b'git clone --quiet --depth 1 --single-branch --branch "$B83_BRANCH"',
    )
    missing = [item.decode("utf-8", errors="replace") for item in required if item not in payload]
    if missing:
        raise ValueError(f"Legacy migration launcher is missing pinned safety controls: {missing!r}")

    if not commit_sha or any(ch not in "0123456789abcdefABCDEF" for ch in commit_sha) or len(commit_sha) < 12:
        try:
            commit_sha = subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"A valid --commit-sha or Git checkout is required: {exc}") from exc
    if len(commit_sha) < 12:
        raise ValueError("commit SHA must contain at least 12 hexadecimal characters")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"IIOS-B83-legacy-migration-{commit_sha[:12]}.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_entry(archive, LAUNCHER_NAME, payload, 0o755)
        _write_entry(archive, README_NAME, _readme(commit_sha).encode("utf-8"), 0o644)

    with zipfile.ZipFile(archive_path, "r") as archive:
        expected = {LAUNCHER_NAME, README_NAME}
        if set(archive.namelist()) != expected:
            raise RuntimeError("B83 distribution must contain one launcher and one README")
        info = archive.getinfo(LAUNCHER_NAME)
        if info.create_system != 3 or ((info.external_attr >> 16) & 0o777) != 0o755:
            raise RuntimeError("B83 launcher executable permission metadata was not preserved")
        if not archive.read(LAUNCHER_NAME).startswith(b"#!/bin/bash"):
            raise RuntimeError("B83 launcher ZIP entry is invalid")
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA"))
    args = parser.parse_args()
    commit_sha = (args.commit_sha or "").strip()
    if not commit_sha:
        parser.error("--commit-sha or GITHUB_SHA is required")
    package = build_package(Path.cwd(), Path(args.output_dir), commit_sha)
    print(f"PACKAGE_CREATED={package}")
    print(f"LAUNCHER={LAUNCHER_NAME}")
    print("ZIP_CONTENTS=1 executable launcher + 1 README")
    print("COMMAND_FILE_UNIX_MODE=100755")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
