#!/bin/bash
# Local-only IIOS quick start. No network bootstrap, browser control or sudo.
set -u

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PROJECT_ROOT" || exit 2

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  printf '%s\n' "未找到 Python 3。请先安装 Python 3；此启动器不会自动下载或安装软件。"
  read -r -n 1 -s -p "按任意键退出..."
  exit 2
fi

if ! "$PYTHON" -c 'import iios_mvp.quick_start_v01' >/dev/null 2>&1; then
  printf '%s\n' "IIOS 运行环境未就绪，或依赖缺失。未自动联网安装，也未修改系统环境。"
  printf '%s\n' "请先完成一次本地环境初始化，再重新启动。"
  read -r -n 1 -s -p "按任意键退出..."
  exit 2
fi

"$PYTHON" -m iios_mvp.quick_start_v01
STATUS=$?
printf '\n%s\n' "IIOS 已退出（状态码：$STATUS）。"
read -r -n 1 -s -p "按任意键关闭窗口..."
printf '\n'
exit "$STATUS"
