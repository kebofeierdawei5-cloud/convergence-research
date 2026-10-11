#!/bin/bash
set -euo pipefail

REPO="https://github.com/kebofeierdawei5-cloud/convergence-research.git"
PRIVATE_ROOT="$HOME/Library/Application Support/IIOS/private-data"
WORKDIR="$(mktemp -d /tmp/iios-private-605016.XXXXXX)"
MODE="${1:-ingest}"

cleanup() {
  rc=$?
  trap - EXIT
  rm -rf "$WORKDIR"
  if [ -t 0 ]; then
    if [ "$rc" -eq 0 ]; then
      printf '%s\n' "运行结束。按回车关闭窗口..."
    else
      printf '%s\n' "运行被阻止或失败。请阅读上方错误。按回车关闭窗口..."
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

case "$MODE" in
  ingest|--verify-existing|--adjudicate-source-vintage) ;;
  *) fail "参数可为 --verify-existing、--adjudicate-source-vintage，或留空执行正式取证导入。" ;;
esac

command -v git >/dev/null 2>&1 || fail "未找到 git。请先安装 Xcode Command Line Tools。"
command -v python3 >/dev/null 2>&1 || fail "未找到 python3。"
if [ "$MODE" = "ingest" ]; then
  command -v gh >/dev/null 2>&1 || fail "未找到 GitHub CLI (gh)。请安装 gh，然后运行 gh auth login。"
  gh auth status --hostname github.com >/dev/null 2>&1 || fail "GitHub CLI 尚未登录。请在终端运行 gh auth login 后重新启动本程序。"
fi

python3 - <<'PY' || exit 2
import sys
if sys.version_info < (3, 12):
    raise SystemExit("[IIOS] BLOCKED: 需要 Python 3.12 或更高版本。")
PY

printf '[IIOS] 正在获取 canonical main 的工具代码……\n'
git clone --quiet --depth 1 --branch main "$REPO" "$WORKDIR/repo"

printf '[IIOS] 正在建立临时 Python 环境……\n'
python3 -m venv "$WORKDIR/venv"

if [ "$MODE" = "ingest" ]; then
  "$WORKDIR/venv/bin/python" -m pip install --quiet --disable-pip-version-check pypdf
  printf '[IIOS] 开始重新下载并核验真实 Attempt 10 原始证据；行情源将在本机重新通过 HTTPS 获取。\n'
  printf '[IIOS] 只把通过清单引用且字节哈希一致的原始文件写入本机私有目录，不向 GitHub 上传数据。\n\n'
  "$WORKDIR/venv/bin/python" "$WORKDIR/repo/tools/iios_private_605016_b2_ingest_v01.py" \
    --private-root "$PRIVATE_ROOT" \
    --repository-root "$WORKDIR/repo"
elif [ "$MODE" = "--adjudicate-source-vintage" ]; then
  printf '[IIOS] 仅基于已存在的本机私有副本进行来源时点上界裁决；不会下载 Attempt 10 或请求官方行情源。\n'
  printf '[IIOS] 依据上交所现行交易规则建立收盘价公开可获得时间的保守上界；精确首次发布时间仍不声称已知。\n'
  printf '[IIOS] 本步骤从公开 GitHub 获取代码，不需要 GitHub CLI 登录。\n\n'
  "$WORKDIR/venv/bin/python" "$WORKDIR/repo/tools/iios_private_605016_b2_ingest_v01.py" \
    --private-root "$PRIVATE_ROOT" \
    --repository-root "$WORKDIR/repo" \
    --adjudicate-source-vintage
else
  printf '[IIOS] 只验证已存在的本机私有副本；不会下载 Attempt 10 或重新请求官方行情源。\n'
  printf '[IIOS] 本步骤仍需从公开 GitHub 获取验证代码，不需要 GitHub CLI 登录。\n\n'
  "$WORKDIR/venv/bin/python" "$WORKDIR/repo/tools/iios_private_605016_b2_ingest_v01.py" \
    --private-root "$PRIVATE_ROOT" \
    --repository-root "$WORKDIR/repo" \
    --verify-existing
fi

printf '\n[IIOS] 精确首次发布时间仍未证实；该结果不等于正式签署准入、生产 Host 验收或投资决策授权。\n'
