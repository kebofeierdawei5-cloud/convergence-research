#!/bin/bash
set -euo pipefail

PINNED_COMMIT="4ccb8cf89084d7299dfa8d0774cce97009eb5b54"
PRIVATE_BASE="$HOME/.iios-private"
TOOL_ROOT="$PRIVATE_BASE/tools/path-a-scenario-$PINNED_COMMIT"
MODULE_DIR="$TOOL_ROOT/iios_mvp"
OUTPUT_ROOT="$PRIVATE_BASE/scenario-analysis"
SCENARIO_FILE="$MODULE_DIR/private_scenario_analysis_v01.py"
PRICE_FILE="$MODULE_DIR/operator_attested_price_input_v01.py"
SCENARIO_BLOB_SHA="0bcc38ad953dc0a8ff60fcef6abd008a5507595c"
PRICE_BLOB_SHA="b3aa8afaa6e6b753dc9192f736f9ddec58e52672"
REPO="kebofeierdawei5-cloud/convergence-research"

show_dialog() {
  /usr/bin/osascript -e 'on run argv' -e 'display dialog (item 1 of argv) buttons {"好"} default button "好" with title "IIOS 私有情景分析"' -e 'end run' "$1" >/dev/null 2>&1 || true
}

fail() {
  show_dialog "$1"
  printf '\nIIOS 私有情景分析：%s\n' "$1"
  read -r -p '按回车关闭窗口…' _ || true
  exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
  show_dialog '未找到 python3。即将打开 Python 官方 macOS 下载页。'
  open 'https://www.python.org/downloads/macos/' >/dev/null 2>&1 || true
  fail '需要 Python 3.10 或更新版本；本工具不使用 python 命令、LLM 或模型 API。'
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
  show_dialog '当前 python3 版本低于 3.10。即将打开 Python 官方下载页。'
  open 'https://www.python.org/downloads/macos/' >/dev/null 2>&1 || true
  fail '需要 Python 3.10 或更新版本。'
fi

INPUT_PATH="$(/usr/bin/osascript <<'APPLESCRIPT'
try
  set homePath to POSIX path of (path to home folder)
  set defaultFolder to POSIX file (homePath & ".iios-private/analysis-inputs/")
  set pickedFile to choose file with prompt "选择已经保存的 Path A 标准化私有行情记录 JSON（不是原始输入文件，也不是 receipt）" default location defaultFolder
  POSIX path of pickedFile
on error
  return ""
end try
APPLESCRIPT
)"
[[ -n "$INPUT_PATH" && -f "$INPUT_PATH" && ! -L "$INPUT_PATH" ]] || fail '未选择有效的私有行情记录；没有执行分析。'

# Do not follow an operator-created symlink for any protected private path.
for protected_path in "$PRIVATE_BASE" "$PRIVATE_BASE/tools" "$TOOL_ROOT" "$MODULE_DIR" "$OUTPUT_ROOT"; do
  [[ ! -L "$protected_path" ]] || fail "检测到受保护目录是符号链接：$protected_path。为避免写入到非预期位置，已停止。"
done

mkdir -p "$MODULE_DIR"
chmod 700 "$PRIVATE_BASE" "$PRIVATE_BASE/tools" "$TOOL_ROOT" "$MODULE_DIR"

# The Python module intentionally refuses to chmod an existing output root.
# This launcher may repair the root directory only after an explicit operator choice.
if [[ ! -e "$OUTPUT_ROOT" ]]; then
  mkdir -m 700 -p "$OUTPUT_ROOT" || fail '无法建立私有输出目录；未执行分析。'
else
  [[ -d "$OUTPUT_ROOT" && ! -L "$OUTPUT_ROOT" ]] || fail '情景分析输出路径存在但不是普通目录；未执行分析。'
  if python3 - "$OUTPUT_ROOT" <<'PY'
import os, stat, sys
try:
    info = os.stat(sys.argv[1], follow_symlinks=False)
except OSError:
    raise SystemExit(2)
if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
    raise SystemExit(2)
if stat.S_IMODE(info.st_mode) & 0o077:
    raise SystemExit(1)
raise SystemExit(0)
PY
  then
    : # Existing output root is already private and owned by this user.
  else
    permission_check=$?
    if [[ "$permission_check" -ne 1 ]]; then
      fail '现有输出目录的所有权或类型不符合安全要求；未更改该目录，也未执行分析。'
    fi
    permission_choice="$(/usr/bin/osascript <<'APPLESCRIPT' || true
try
  set answerButton to button returned of (display dialog "现有情景分析输出目录允许同一台 Mac 上的其他本地账户访问。是否仅将这个目录的权限收紧为 700（仅当前用户可访问）？不会删除或覆盖目录内文件。" buttons {"取消并停止", "收紧权限"} default button "取消并停止" cancel button "取消并停止" with title "IIOS 私有目录权限修复")
  return answerButton
on error
  return "取消并停止"
end try
APPLESCRIPT
)"
    [[ "$permission_choice" == "收紧权限" ]] || fail '未获准调整现有输出目录权限；已安全停止，没有运行分析。'
    chmod 700 "$OUTPUT_ROOT" || fail '无法将输出目录权限收紧为 700；没有运行分析。'
  fi
fi

blob_sha1() {
  { printf 'blob %s\0' "$(wc -c < "$1" | tr -d '[:space:]')"; cat "$1"; } | shasum -a 1 | awk '{print $1}'
}

download_pinned() {
  local path="$1" expected="$2" destination="$3"
  local url="https://raw.githubusercontent.com/$REPO/$PINNED_COMMIT/$path"
  local api="https://api.github.com/repos/$REPO/contents/$path?ref=$PINNED_COMMIT"
  local temp="$destination.tmp.$$" api_temp="$TOOL_ROOT/api-$$.json" downloaded=0 actual
  if [[ -f "$destination" && ! -L "$destination" ]]; then
    actual="$(blob_sha1 "$destination")"
    [[ "$actual" == "$expected" ]] || fail '发现已有工具文件哈希不匹配，已停止且没有覆盖文件。'
    return 0
  fi
  if curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$url" -o "$temp"; then
    downloaded=1
  else
    rm -f "$temp"
    if curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
      -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2022-11-28' "$api" -o "$api_temp"; then
      if python3 - "$api_temp" "$temp" "$expected" <<'PY'
import base64, json, sys
src, dst, expected = sys.argv[1:]
with open(src, 'r', encoding='utf-8') as f:
    obj = json.load(f)
if obj.get('sha') != expected or not obj.get('content'):
    raise SystemExit(1)
raw = base64.b64decode(obj['content'], validate=False)
with open(dst, 'wb') as f:
    f.write(raw)
PY
      then downloaded=1; fi
    fi
  fi
  rm -f "$api_temp"
  [[ "$downloaded" == "1" && -f "$temp" ]] || { rm -f "$temp"; fail '无法从 canonical GitHub 获取固定版本的分析工具；未运行分析。'; }
  actual="$(blob_sha1 "$temp")"
  if [[ "$actual" != "$expected" ]]; then
    rm -f "$temp"
    fail '下载工具的 Git blob SHA-1 与 canonical 固定值不一致；已停止。'
  fi
  chmod 600 "$temp"
  mv "$temp" "$destination"
}

download_pinned "iios_mvp/operator_attested_price_input_v01.py" "$PRICE_BLOB_SHA" "$PRICE_FILE"
download_pinned "iios_mvp/private_scenario_analysis_v01.py" "$SCENARIO_BLOB_SHA" "$SCENARIO_FILE"

cd "$TOOL_ROOT"
# Initialize and quote the exit code explicitly to avoid nounset expansion failures.
OUTPUT=""
code=0
if OUTPUT="$(PYTHONPATH="$TOOL_ROOT" python3 -m iios_mvp.private_scenario_analysis_v01 --prices "$INPUT_PATH" --output-root "$OUTPUT_ROOT" 2>&1)"; then
  printf '\n%s\n' "$OUTPUT"
  show_dialog '情景分析已完成或通过哈希校验复用了相同结果。报告和私有行情只保存在本机；正在打开输出目录。'
  open "$OUTPUT_ROOT" >/dev/null 2>&1 || true
  printf '\n输出目录：%s\n' "$OUTPUT_ROOT"
  printf '提醒：此为 NON-CANONICAL 情景分析；不创建正式行情准入、Forecast、Decision、Publication 或交易授权。\n'
  read -r -p '按回车关闭窗口…' _ || true
else
  code=$?
  printf '\n%s\n' "${OUTPUT:-分析命令未返回详情}"
  fail "分析已阻断（退出码 ${code}）。请检查上方原因；没有产生正式投资决策。"
fi
