#!/bin/bash
set -euo pipefail

# Safely update an existing checkout to canonical origin/main.
# Never reset, delete, stash, or overwrite local operator changes.

fail() {
  printf '\n[本机代码更新已停止] %s\n' "$1" >&2
  exit 20
}

if [[ "$#" -ne 1 || -z "$1" ]]; then
  fail '调用参数错误：需要传入本地仓库根目录。'
fi

ROOT_INPUT="$1"
if [[ ! -d "$ROOT_INPUT" ]]; then
  fail "仓库目录不存在：$ROOT_INPUT"
fi
ROOT="$(cd "$ROOT_INPUT" && pwd -P)"

if ! command -v git >/dev/null 2>&1; then
  fail '没有找到 Git。请安装/启用 Git 后重新双击验收入口。'
fi

if ! TOP="$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)"; then
  fail "当前目录不是 Git 仓库：$ROOT"
fi
TOP="$(cd "$TOP" && pwd -P)"
if [[ "$TOP" != "$ROOT" ]]; then
  fail "入口必须放在仓库根目录。检测到 Git 根目录：$TOP"
fi

if ! ORIGIN_URL="$(git -C "$ROOT" remote get-url origin 2>/dev/null)" || [[ -z "$ORIGIN_URL" ]]; then
  fail '没有配置 origin 远端；为避免更新到错误代码源，已停止。'
fi

BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
STATUS="$(git -C "$ROOT" status --porcelain --untracked-files=all)"
if [[ -n "$STATUS" ]]; then
  printf '发现尚未提交的本地改动/未跟踪文件：\n%s\n' "$STATUS" >&2
  fail '为避免覆盖你的工作，未执行更新。请先自行提交或备份这些文件，再重新双击；脚本不会 stash/reset/删除。'
fi

printf '正在安全检查本机仓库：%s\n' "$ROOT"
printf '当前分支：%s\n' "$BRANCH"
printf '远端 origin：已配置\n'

if ! git -C "$ROOT" fetch --no-tags origin refs/heads/main:refs/remotes/origin/main; then
  fail '从 origin 获取 main 失败。请检查网络、远端权限和 GitHub 可访问性；未修改工作文件。'
fi

# A clean checkout on another branch may be switched to main. The old branch
# reference is preserved. Dirty working trees were rejected above.
if [[ "$BRANCH" != "main" ]]; then
  if git -C "$ROOT" show-ref --verify --quiet refs/heads/main; then
    if ! git -C "$ROOT" switch main; then
      fail '无法安全切换到本地 main。未重置或删除任何分支；请检查 Git 输出后再试。'
    fi
  else
    if ! git -C "$ROOT" switch --track -c main origin/main; then
      fail '本地没有 main，且无法从 origin/main 建立跟踪分支。未删除任何现有分支。'
    fi
  fi
fi

LOCAL_HEAD="$(git -C "$ROOT" rev-parse HEAD)"
REMOTE_HEAD="$(git -C "$ROOT" rev-parse refs/remotes/origin/main)"
if [[ "$LOCAL_HEAD" == "$REMOTE_HEAD" ]]; then
  printf '本机 main 已是最新：%s\n' "$LOCAL_HEAD"
elif git -C "$ROOT" merge-base --is-ancestor "$LOCAL_HEAD" "$REMOTE_HEAD"; then
  printf '检测到本机 main 落后于远端，将执行仅快进更新。\n'
  if ! git -C "$ROOT" merge --ff-only origin/main; then
    fail 'main 快进更新失败。未执行 reset；请保留 Git 输出以便排查。'
  fi
else
  if git -C "$ROOT" merge-base --is-ancestor "$REMOTE_HEAD" "$LOCAL_HEAD"; then
    fail '本机 main 含有远端没有的提交。为避免丢失本地提交，脚本不自动回退或重写历史。请先人工检查并备份。'
  fi
  fail '本机 main 与 origin/main 已分叉。为避免覆盖任一侧的提交，脚本没有自动合并/reset；请先备份并人工处理分叉。'
fi

FINAL_BRANCH="$(git -C "$ROOT" branch --show-current)"
FINAL_HEAD="$(git -C "$ROOT" rev-parse HEAD)"
REMOTE_HEAD="$(git -C "$ROOT" rev-parse refs/remotes/origin/main)"
FINAL_STATUS="$(git -C "$ROOT" status --porcelain --untracked-files=all)"
if [[ "$FINAL_BRANCH" != "main" || "$FINAL_HEAD" != "$REMOTE_HEAD" || -n "$FINAL_STATUS" ]]; then
  fail '更新后复核不一致（分支/提交/工作区）。验收未启动；请保留终端输出。'
fi

printf '本机代码更新并复核成功。\n'
printf '当前分支：%s\n' "$FINAL_BRANCH"
printf '当前提交：%s\n' "$FINAL_HEAD"
printf '工作区：干净\n'
