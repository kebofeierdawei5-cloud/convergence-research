#!/bin/bash
# Local-only IIOS launcher. No network bootstrap, browser control, shell eval or sudo.
set -u
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd -P)" || exit 2
cd "$PROJECT_ROOT" || exit 2

if [ ! -f "$PROJECT_ROOT/iios_mvp/quick_start_v01.py" ]; then
  printf '%s\n' "未找到 IIOS 项目入口。请从完整的 convergence-research 项目目录启动此文件。"
  read -r -n 1 -s -p "按任意键退出..."
  printf '\n'
  exit 2
fi

if [ -e "$PROJECT_ROOT/.venv/bin/python" ]; then
  if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    printf '%s\n' "检测到 .venv，但其中的 Python 不可执行。为避免误用其他环境，已停止。"
    read -r -n 1 -s -p "按任意键退出..."
    printf '\n'
    exit 2
  fi
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
  RUNTIME_LABEL=".venv"
else
  if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "未找到 Python 3。请先安装 Python 3；此启动器不会自动下载或安装软件。"
    read -r -n 1 -s -p "按任意键退出..."
    printf '\n'
    exit 2
  fi
  PYTHON="$(command -v python3)"
  RUNTIME_LABEL="系统 Python 3"
fi

printf '正在检查 IIOS 本地运行环境（%s）...\n' "$RUNTIME_LABEL"
if ! PYTHONPATH="$PROJECT_ROOT" PYTHONNOUSERSITE=1 "$PYTHON" -c 'import sys; assert sys.version_info >= (3, 10), "IIOS requires Python 3.10+"; import iios_mvp.quick_start_v01'; then
  printf '%s\n' "IIOS 运行环境检查失败。未联网安装依赖、未修改系统 Python、未回退到其他环境。"
  read -r -n 1 -s -p "按任意键退出..."
  printf '\n'
  exit 2
fi

PYTHONPATH="$PROJECT_ROOT" PYTHONNOUSERSITE=1 "$PYTHON" -m iios_mvp.quick_start_v01
STATUS=$?
printf '\n%s\n' "IIOS 已退出（状态码：$STATUS）。"
read -r -n 1 -s -p "按任意键关闭窗口..."
printf '\n'
exit "$STATUS"
