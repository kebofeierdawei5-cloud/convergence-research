#!/bin/bash
set -euo pipefail

REPO="https://github.com/kebofeierdawei5-cloud/convergence-research.git"
PRIVATE_ROOT="$HOME/Library/Application Support/IIOS/private-data"
WORKDIR="$(mktemp -d /tmp/iios-private-605016.XXXXXX)"

cleanup() {
  rc=$?
  trap - EXIT
  rm -rf "$WORKDIR"
  if [ -t 0 ]; then
    if [ "$rc" -eq 0 ]; then
      printf '%s\n' "运行结束。按回车关闭窗口..."
    else
      printf '%s\\n' "运行被阻止或失败。请阅读上方错误。按回车关闭窗口..."
    fi
    # Portable in Bash and Zsh; prompt output is separate from reading stdin.
    IFS= read -r _ || true
  fi
  exit "$rc"
}
trap cleanup EXIT

fail() {
  printf '\n[IIOS] BLOCKED: %s\n' "$1" >&2
  exit 2
}

command -v git >/dev/null 2>&1 || fail "未找到 git。请先安装 Xcode Command Line Tools。"
command -v python3 >/dev/null 2>&1 || fail "未找到 python3。"
command -v gh >/dev/null 2>&1 || fail "未找到 GitHub CLI (gh)。请安装 gh，然后运行 gh auth login。"
gh auth status --hostname github.com >/dev/null 2>&1 || fail "GitHub CLI 尚未登录。请在终端运行 gh auth login 后重新启动本程序。"

python3 - <<'PY' || exit 2
import sys
if sys.version_info < (3, 12):
    raise SystemExit("[IIOS] BLOCKED: 需要 Python 3.12 或更高版本。")
PY

printf '[IIOS] 正在获取 canonical main 的工具代码……\n'
git clone --quiet --depth 1 --branch main "$REPO" "$WORKDIR/repo"

printf '[IIOS] 正在建立临时 Python 环境……\n'
python3 -m venv "$WORKDIR/venv"
"$WORKDIR/venv/bin/python" -m pip install --quiet --disable-pip-version-check pypdf

printf '[IIOS] 开始重新下载并核验真实 Attempt 10 原始证据；行情源将在本机重新通过 HTTPS 获取。\n'
printf '[IIOS] 只把通过清单引用且字节哈希一致的原始文件写入本机私有目录，不向 GitHub 上传数据。\n\n'
"$WORKDIR/venv/bin/python" "$WORKDIR/repo/tools/iios_private_605016_b2_ingest_v01.py" \
  --private-root "$PRIVATE_ROOT" \
  --repository-root "$WORKDIR/repo"

printf '\n[IIOS] 请注意：私有持久化候选通过不等于生产 Host 验收；来源首次发布时间精度审查仍保留为待处理项。\n'
