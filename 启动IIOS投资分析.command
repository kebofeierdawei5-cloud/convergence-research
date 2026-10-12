#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

fail() {
  printf '\nIIOS 启动失败：%s\n' "$1"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'display dialog (item 1 of argv) buttons {"好"} default button "好" with title "IIOS 投资分析"' "$1" >/dev/null 2>&1 || true
  fi
  read -r -p '按回车关闭窗口…' _ || true
  exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
  fail '没有找到 Python 3。请先安装 Python 3.10 或更新版本。'
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
  fail '需要 Python 3.10 或更新版本。'
fi

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT"
exec python3 -m iios_mvp.local_investment_pilot_v01 --wizard
