from __future__ import annotations

"""Low-friction local entry point for the non-canonical IIOS Pilot.

The quick start resumes the only unfinished task automatically. If several
unfinished tasks exist, it asks the operator to choose by company/symbol.
It never guesses when task state is corrupt or blocked.
"""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from .guided_task_session_v01 import GuidedTaskSession
from .guided_task_resume_v01 import run_guided_task
from .local_investment_pilot_v01 import run_guided_wizard
from .task_workspace_v01 import TaskWorkspaceError

PRIVATE_PARENT = Path.home() / ".iios-private"
PRIVATE_ROOT = PRIVATE_PARENT / "local-pilot"
INPUT_ROOT = PRIVATE_ROOT / "inputs"
TASK_ROOT = INPUT_ROOT / "tasks"
OUTPUT_ROOT = PRIVATE_ROOT / "runs"


def _discover_unfinished_tasks() -> list[tuple[GuidedTaskSession, dict[str, Any], dict[str, Any]]]:
    """Return verified active tasks; corruption and blocked tasks fail closed."""
    if PRIVATE_PARENT.is_symlink() or PRIVATE_ROOT.is_symlink() or INPUT_ROOT.is_symlink() or TASK_ROOT.is_symlink():
        raise TaskWorkspaceError("QUICK_START_PRIVATE_PATH_IS_SYMLINK")
    if not TASK_ROOT.exists():
        return []
    if not TASK_ROOT.is_dir():
        raise TaskWorkspaceError("QUICK_START_TASK_ROOT_NOT_DIRECTORY")

    found: list[tuple[GuidedTaskSession, dict[str, Any], dict[str, Any]]] = []
    for path in sorted(TASK_ROOT.iterdir(), key=lambda item: item.name):
        if not path.name.startswith("task-"):
            continue
        if path.is_symlink() or not path.is_dir():
            raise TaskWorkspaceError("QUICK_START_TASK_ENTRY_INVALID")
        session, manifest = GuidedTaskSession.open(TASK_ROOT, path.name)
        status = manifest.get("task_status")
        if status == "COMPLETED":
            continue
        if status == "BLOCKED":
            raise TaskWorkspaceError(
                "QUICK_START_BLOCKED_TASK_REQUIRES_REVIEW:"
                + str(manifest.get("current_stage") or "UNKNOWN")
            )
        if status not in {"ACTIVE", "INTERRUPTED"}:
            raise TaskWorkspaceError("QUICK_START_TASK_STATUS_UNKNOWN")

        context = session.load_json_artifact("artifacts/task_created/task_context.json")
        found.append((session, manifest, context))
    return found


def _choose_task(
    tasks: list[tuple[GuidedTaskSession, dict[str, Any], dict[str, Any]]]
) -> tuple[GuidedTaskSession, dict[str, Any], dict[str, Any]]:
    if len(tasks) == 1:
        return tasks[0]
    print("\n发现多个未完成研究，选择要继续的任务：")
    for index, (_session, manifest, context) in enumerate(tasks, start=1):
        company = str(context.get("company") or "未命名公司")
        symbol = str(context.get("symbol") or "代码未知")
        stage = str(manifest.get("current_stage") or "状态未知")
        print(f"  {index}. {company}（{symbol}）｜{stage}")
    while True:
        raw = input("输入序号继续，输入 0 退出: ").strip()
        if raw == "0":
            raise SystemExit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(tasks):
            return tasks[int(raw) - 1]
        print("序号无效，请重新输入。")


def _open_verified_report(result: dict[str, Any]) -> bool:
    """Open only the report returned after the runner's bundle verification."""
    if sys.platform != "darwin" or result.get("status") != "PILOT_CREATED":
        return False
    raw_path = result.get("report_path")
    if not isinstance(raw_path, str) or not raw_path:
        return False
    candidate = Path(raw_path).expanduser()
    if PRIVATE_PARENT.is_symlink() or PRIVATE_ROOT.is_symlink() or OUTPUT_ROOT.is_symlink() or candidate.is_symlink():
        return False
    try:
        report = candidate.resolve(strict=True)
        output_root = OUTPUT_ROOT.resolve(strict=True)
        report.relative_to(output_root)
        if not report.is_file():
            return False
        subprocess.run(["open", str(report)], check=False, timeout=5)
        return True
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def main() -> int:
    try:
        tasks = _discover_unfinished_tasks()
        if not tasks:
            print("没有未完成研究，开始新的 IIOS 研究。")
            result = run_guided_wizard()
            _open_verified_report(result)
            return 0
        session, manifest, context = _choose_task(tasks)
        print(
            "正在继续："
            + str(context.get("company") or "未命名公司")
            + "（"
            + str(context.get("symbol") or "代码未知")
            + "），当前进度："
            + str(manifest.get("current_stage") or "状态未知")
        )
        result = run_guided_task(session, output_root=OUTPUT_ROOT)
        _open_verified_report(result)
        print("\n研究任务完成：")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (TaskWorkspaceError, OSError, ValueError, KeyError, TypeError) as exc:
        # Do not print raw task artifacts or clipboard contents in error output.
        print("IIOS 已安全停止：" + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
