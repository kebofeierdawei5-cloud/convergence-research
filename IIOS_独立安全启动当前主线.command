#!/bin/bash
set -euo pipefail

# Standalone bootstrap: use a clean, versioned clone of canonical main without
# mutating the operator's existing checkout. Intended to be downloaded and
# double-clicked even when a local repository has diverged or contains edits.

fail() {
  printf '\nIIOS 当前主线安全启动失败：%s\n' "$1" >&2
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'on run argv' -e 'display dialog (item 1 of argv) buttons {"好"} default button "好" with title "IIOS 当前主线安全启动"' -e 'end run' "$1" >/dev/null 2>&1 || true
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
if ! command -v git >/dev/null 2>&1; then
  fail '没有找到 Git。请安装/启用 Git 后重新启动。'
fi

umask 077
PRIVATE_ROOT="$HOME/.iios-private"
SOURCE_ROOT="$PRIVATE_ROOT/source"
CANONICAL_URL="https://github.com/kebofeierdawei5-cloud/convergence-research.git"

ensure_private_directory() {
  local path="$1"
  if [[ -L "$path" ]]; then
    fail "私有缓存路径不能是符号链接：$path"
  fi
  mkdir -p "$path" || fail "无法创建私有缓存目录：$path"
  chmod 700 "$path" || fail "无法设置私有缓存目录权限：$path"
  if [[ ! -d "$path" || -L "$path" ]]; then
    fail "缓存路径不是普通目录：$path"
  fi
}
ensure_private_directory "$PRIVATE_ROOT"
ensure_private_directory "$SOURCE_ROOT"

printf '正在解析 canonical main 的当前提交……\n'
if ! REMOTE_SHA="$(git ls-remote "$CANONICAL_URL" refs/heads/main 2>/dev/null | awk 'NR == 1 {print $1}')"; then
  fail '无法连接 canonical GitHub main。请检查网络后重新双击；本地现有仓库未被修改。'
fi
if [[ ! "$REMOTE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  fail '无法解析 canonical main 的提交 SHA；为避免启动未知版本，已停止。'
fi

SELECTED_ROOT=""
CACHE="$SOURCE_ROOT/convergence-research-main-$REMOTE_SHA"
if [[ -d "$CACHE" && ! -L "$CACHE" ]]; then
  CACHE_ROOT="$(git -C "$CACHE" rev-parse --show-toplevel 2>/dev/null || true)"
  CACHE_HEAD="$(git -C "$CACHE" rev-parse HEAD 2>/dev/null || true)"
  CACHE_BRANCH="$(git -C "$CACHE" branch --show-current 2>/dev/null || true)"
  CACHE_ORIGIN="$(git -C "$CACHE" remote get-url origin 2>/dev/null || true)"
  CACHE_STATUS="$(git -C "$CACHE" status --porcelain --untracked-files=all 2>/dev/null || true)"
  if [[ "$CACHE_ROOT" == "$CACHE" &&
        "$CACHE_HEAD" == "$REMOTE_SHA" &&
        "$CACHE_BRANCH" == "main" &&
        "$CACHE_ORIGIN" == "$CANONICAL_URL" &&
        -z "$CACHE_STATUS" ]]; then
    SELECTED_ROOT="$CACHE"
    printf '复用已校验的当前主线私有副本：%s\n' "$SELECTED_ROOT"
  else
    printf '发现同 SHA 缓存但未通过完整性复核；原目录保留，不覆盖。\n' >&2
  fi
elif [[ -e "$CACHE" || -L "$CACHE" ]]; then
  printf '发现同 SHA 缓存路径不是安全的普通目录；原路径保留，不覆盖。\n' >&2
fi

if [[ -z "$SELECTED_ROOT" ]]; then
  printf '本次使用独立私有副本。不会 reset、stash、清理或覆盖你的既有项目目录。\n'
  TEMP_ROOT="$(mktemp -d "$SOURCE_ROOT/.iios-main-bootstrap.XXXXXX")" || fail '无法建立临时下载目录。'
  printf '正在克隆公开仓库 canonical main……\n'
  if ! git clone --branch main --single-branch "$CANONICAL_URL" "$TEMP_ROOT/repo"; then
    fail "克隆失败。临时诊断目录保留于：$TEMP_ROOT；现有项目目录未被修改。"
  fi
  if ! git -C "$TEMP_ROOT/repo" fetch --no-tags origin refs/heads/main:refs/remotes/origin/main; then
    fail "更新临时副本的 main 失败。临时诊断目录保留于：$TEMP_ROOT；现有项目目录未被修改。"
  fi
  CLONED_HEAD="$(git -C "$TEMP_ROOT/repo" rev-parse HEAD)"
  FETCHED_HEAD="$(git -C "$TEMP_ROOT/repo" rev-parse refs/remotes/origin/main)"
  if [[ "$CLONED_HEAD" != "$FETCHED_HEAD" ]]; then
    if ! git -C "$TEMP_ROOT/repo" merge --ff-only refs/remotes/origin/main; then
      fail "临时副本无法快进到远端 main。临时诊断目录保留于：$TEMP_ROOT。"
    fi
  fi
  SELECTED_SHA="$(git -C "$TEMP_ROOT/repo" rev-parse HEAD)"
  SELECTED_BRANCH="$(git -C "$TEMP_ROOT/repo" branch --show-current)"
  SELECTED_ORIGIN="$(git -C "$TEMP_ROOT/repo" remote get-url origin)"
  SELECTED_STATUS="$(git -C "$TEMP_ROOT/repo" status --porcelain --untracked-files=all)"
  if [[ ! "$SELECTED_SHA" =~ ^[0-9a-f]{40}$ ||
        "$SELECTED_BRANCH" != "main" ||
        "$SELECTED_ORIGIN" != "$CANONICAL_URL" ||
        -n "$SELECTED_STATUS" ||
        "$(git -C "$TEMP_ROOT/repo" rev-parse refs/remotes/origin/main)" != "$SELECTED_SHA" ]]; then
    fail "独立副本最终复核失败。临时诊断目录保留于：$TEMP_ROOT。"
  fi

  SELECTED_ROOT="$SOURCE_ROOT/convergence-research-main-$SELECTED_SHA"
  if [[ -e "$SELECTED_ROOT" || -L "$SELECTED_ROOT" ]]; then
    SELECTED_ROOT="$SOURCE_ROOT/convergence-research-main-$SELECTED_SHA-$(date +%Y%m%dT%H%M%S)-$$"
  fi
  if ! mv "$TEMP_ROOT/repo" "$SELECTED_ROOT"; then
    fail "无法保存已验证的独立副本。临时目录保留于：$TEMP_ROOT。"
  fi
  if ! rmdir "$TEMP_ROOT"; then
    printf '提示：临时父目录仍有内容并保留用于诊断：%s\n' "$TEMP_ROOT" >&2
  fi
  chmod 700 "$SELECTED_ROOT"
  printf '独立副本已验证：%s\n' "$SELECTED_ROOT"
fi

if [[ ! -f "$SELECTED_ROOT/iios_mvp/local_run_replay_acceptance_v01.py" ||
      ! -f "$SELECTED_ROOT/iios_mvp/local_investment_pilot_v01.py" ]]; then
  fail "当前主线副本缺少 IIOS 本地模块：$SELECTED_ROOT"
fi

printf '使用代码提交：%s\n' "$(git -C "$SELECTED_ROOT" rev-parse HEAD)"
printf '研究输入、报告、回执、验收日志及审计 ZIP 都保留在 ~/.iios-private/，不会写入 Git 仓库。\n'
cd "$SELECTED_ROOT"
export PYTHONPATH="$SELECTED_ROOT"
export PYTHONUNBUFFERED=1
if IIOS_ACCEPTANCE_AUTO_START=1 python3 -m iios_mvp.local_run_replay_acceptance_v01; then
  status=0
else
  status=$?
fi
printf '\nIIOS 当前主线全流程与 Replay 结束，退出码：%s\n' "$status"
read -r -p '按回车关闭窗口…' _ || true
exit "$status"
