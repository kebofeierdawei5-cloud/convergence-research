#!/bin/bash
set -euo pipefail
umask 077

REPO_URL="https://github.com/kebofeierdawei5-cloud/convergence-research.git"
B83_BRANCH="feat/b83-durable-task-resume-20261108"
PILOT_ID="local-pilot-002810-20261012T141631129796Z"
PRIVATE_ROOT="$HOME/.iios-private"
SOURCE_ROOT="$PRIVATE_ROOT/source"

fail() {
  printf '\nIIOS 历史运行包迁移验收已停止：%s\n' "$1" >&2
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'on run argv' -e 'display dialog (item 1 of argv) buttons {"好"} default button "好" with title "IIOS 历史运行包迁移验收"' -e 'end run' "$1" >/dev/null 2>&1 || true
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

RUN_DIR="$PRIVATE_ROOT/local-pilot/runs/$PILOT_ID"
if [[ -L "$RUN_DIR" || ! -d "$RUN_DIR" ]]; then
  fail "没有找到预期的旧运行目录：$RUN_DIR。未创建新任务，也没有修改任何文件。"
fi
if [[ -L "$RUN_DIR/pilot_receipt.json" || ! -f "$RUN_DIR/pilot_receipt.json" ]]; then
  fail '旧运行包缺少正常的 pilot_receipt.json，或该文件是符号链接。已停止。'
fi

for path in "$PRIVATE_ROOT" "$SOURCE_ROOT"; do
  if [[ -L "$path" ]]; then
    fail "私有代码目录不能是符号链接：$path"
  fi
  mkdir -p "$path" || fail "无法创建私有目录：$path"
  chmod 700 "$path" || fail "无法将私有目录权限限制为 0700：$path"
done

printf '正在取得 B83 历史包迁移修复版本……\n'
REMOTE_LIST=""
if ! REMOTE_LIST="$(git ls-remote "$REPO_URL" "refs/heads/$B83_BRANCH")"; then
  fail '无法连接 GitHub 查询 B83 分支。请检查网络后重试。'
fi
REMOTE_SHA="$(printf '%s\n' "$REMOTE_LIST" | awk 'NR == 1 {print $1}')"
if [[ ! "$REMOTE_SHA" =~ ^[0-9a-fA-F]{40}$ ]]; then
  fail 'GitHub 未返回有效的 B83 分支提交 SHA。'
fi
REMOTE_SHA="$(printf '%s' "$REMOTE_SHA" | tr 'A-F' 'a-f')"
TARGET="$SOURCE_ROOT/convergence-research-b83-$REMOTE_SHA"
TARGET_REPO="$TARGET/repo"

if [[ -L "$TARGET" ]]; then
  fail "检测到同名代码目录是符号链接，为避免跟随路径写入已停止：$TARGET"
fi

if [[ -e "$TARGET" ]]; then
  if [[ -L "$TARGET_REPO" || ! -d "$TARGET_REPO" ]]; then
    fail "同名隔离代码目录结构不符合预期，未覆盖：$TARGET"
  fi
  LOCAL_SHA="$(git -C "$TARGET_REPO" rev-parse HEAD 2>/dev/null || true)"
  LOCAL_ORIGIN="$(git -C "$TARGET_REPO" remote get-url origin 2>/dev/null || true)"
  LOCAL_STATUS="$(git -C "$TARGET_REPO" status --porcelain --untracked-files=all 2>/dev/null || true)"
  if [[ "$LOCAL_SHA" != "$REMOTE_SHA" || "$LOCAL_ORIGIN" != "$REPO_URL" || -n "$LOCAL_STATUS" ]]; then
    fail "已有隔离代码副本与预期提交不一致或含本地改动；未覆盖：$TARGET_REPO"
  fi
  printf '复用已校验的隔离代码副本：%s\n' "$TARGET_REPO"
else
  STAGING="$SOURCE_ROOT/.b83-legacy-bootstrap-$"
  if [[ -e "$STAGING" || -L "$STAGING" ]]; then
    fail "临时克隆路径已存在，未覆盖：$STAGING"
  fi
  if ! git clone --quiet --depth 1 --single-branch --branch "$B83_BRANCH" "$REPO_URL" "$STAGING"; then
    fail '无法克隆 B83 分支。已保留原始运行包和现有项目目录。'
  fi
  CLONED_SHA="$(git -C "$STAGING" rev-parse HEAD 2>/dev/null || true)"
  CLONED_ORIGIN="$(git -C "$STAGING" remote get-url origin 2>/dev/null || true)"
  CLONED_STATUS="$(git -C "$STAGING" status --porcelain --untracked-files=all 2>/dev/null || true)"
  if [[ "$CLONED_SHA" != "$REMOTE_SHA" || "$CLONED_ORIGIN" != "$REPO_URL" || -n "$CLONED_STATUS" ]]; then
    fail "克隆期间 B83 分支发生变化或副本校验失败。临时副本保留在：$STAGING；请勿手工修改旧运行包。"
  fi
  if [[ -e "$TARGET" || -L "$TARGET" ]]; then
    fail "创建期间目标代码目录已出现，未覆盖：$TARGET"
  fi
  mkdir "$TARGET" || fail "无法为隔离代码副本保留唯一目标目录：$TARGET"
  chmod 700 "$TARGET" || fail "无法限制隔离代码目录权限：$TARGET"
  mv "$STAGING" "$TARGET_REPO" || fail "无法将已校验的代码副本放入隔离目录；原始运行包未修改。"
  chmod 700 "$TARGET_REPO" || fail "无法限制隔离代码副本权限：$TARGET_REPO"
  printf '已建立隔离代码副本：%s\n' "$TARGET_REPO"
fi

if [[ ! -f "$TARGET_REPO/iios_mvp/local_run_replay_acceptance_v01.py" || ! -f "$TARGET_REPO/iios_mvp/legacy_pilot_bundle_migration_v01.py" ]]; then
  fail '隔离副本缺少历史包迁移/验收模块。'
fi

VERIFIED_SHA="$(git -C "$TARGET_REPO" rev-parse HEAD)"
if [[ "$VERIFIED_SHA" != "$REMOTE_SHA" ]]; then
  fail '隔离副本的最终提交 SHA 与远端分支不一致。'
fi

printf '\n代码版本：%s\n' "$VERIFIED_SHA"
printf '固定旧运行：%s\n' "$PILOT_ID"
printf '原始运行包和失败日志将保留；历史哈希不会补造。\n'
printf '即将执行：迁移快照 → 当前版本重建 → 首轮哈希 → Replay → Replay 哈希 → 私有审计 ZIP。\n\n'

cd "$TARGET_REPO"
export PYTHONPATH="$TARGET_REPO"
export PYTHONUNBUFFERED=1
export IIOS_ACCEPTANCE_EXISTING_RUN_ID="$PILOT_ID"

if python3 -m iios_mvp.local_run_replay_acceptance_v01; then
  status=0
else
  status=$?
fi

printf '\nIIOS 历史运行包迁移验收结束，退出码：%s\n' "$status"
read -r -p '按回车关闭窗口…' _ || true
exit "$status"
