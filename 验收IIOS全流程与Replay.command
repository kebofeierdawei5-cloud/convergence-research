#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

fail() {
  printf '\nIIOS 全流程与 Replay 验收启动失败：%s\n' "$1"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'on run argv' -e 'display dialog (item 1 of argv) buttons {"好"} default button "好" with title "IIOS 全流程与 Replay 验收"' -e 'end run' "$1" >/dev/null 2>&1 || true
  fi
  read -r -p '按回车关闭窗口…' _ || true
  exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
  fail '没有找到 Python 3。请安装 Python 3.10 或更新版本。'
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
  fail '需要 Python 3.10 或更新版本。'
fi
if [[ ! -f "$REPO_ROOT/iios_mvp/local_investment_pilot_v01.py" ]]; then
  fail '未找到 IIOS 本地分析模块。请确认这是最新 canonical main 仓库根目录，并已更新到最新版本。'
fi
if [[ ! -f "$REPO_ROOT/iios_mvp/local_run_replay_acceptance_v01.py" ]]; then
  fail '未找到全流程与 Replay 验收模块。请先更新仓库到包含此脚本的最新 canonical main。'
fi

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT"
export PYTHONUNBUFFERED=1

# Do not use exec: keep a double-clicked Finder Terminal window open so the
# result/exit code can be read and copied after the acceptance run finishes.
if python3 -m iios_mvp.local_run_replay_acceptance_v01; then
  status=0
else
  status=$?
fi
printf '\nIIOS 全流程与 Replay 验收结束，退出码：%s\n' "$status"
read -r -p '按回车关闭窗口…' _ || true
exit "$status"
