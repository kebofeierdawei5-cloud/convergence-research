from __future__ import annotations

from pathlib import Path

import pytest

import iios_mvp.quick_start_v01 as quick_start
from iios_mvp.task_workspace_v01 import TaskWorkspaceError


def test_quick_start_starts_new_wizard_when_no_unfinished_tasks(monkeypatch):
    calls = []
    monkeypatch.setattr(quick_start, "_discover_unfinished_tasks", lambda: [])
    monkeypatch.setattr(quick_start, "_pilot_main", lambda args: calls.append(args) or 0)

    assert quick_start.main() == 0
    assert calls == [["--wizard"]]


def test_quick_start_resumes_the_only_unfinished_task_without_task_id(monkeypatch):
    session = object()
    manifest = {"current_stage": "ROUND_A_PROMPT_READY"}
    context = {"company": "示例公司", "symbol": "600000.SH"}
    calls = []
    monkeypatch.setattr(
        quick_start, "_discover_unfinished_tasks",
        lambda: [(session, manifest, context)],
    )
    monkeypatch.setattr(
        quick_start, "run_guided_task",
        lambda actual_session, output_root=None: calls.append((actual_session, output_root)) or {"status": "COMPLETED"},
    )

    assert quick_start.main() == 0
    assert calls == [(session, quick_start.OUTPUT_ROOT)]


def test_quick_start_asks_only_when_multiple_tasks_exist(monkeypatch):
    tasks = [
        (object(), {"current_stage": "ROUND_A_PROMPT_READY"}, {"company": "甲", "symbol": "000001.SZ"}),
        (object(), {"current_stage": "ROUND_B_PROMPT_READY"}, {"company": "乙", "symbol": "00700.HK"}),
    ]
    monkeypatch.setattr(quick_start, "_discover_unfinished_tasks", lambda: tasks)
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    selected = quick_start._choose_task(tasks)
    assert selected is tasks[1]


def test_discovery_fails_closed_on_symlinked_task_root(monkeypatch, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "tasks"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(quick_start, "TASK_ROOT", link)

    with pytest.raises(TaskWorkspaceError, match="QUICK_START_TASK_ROOT_IS_SYMLINK"):
        quick_start._discover_unfinished_tasks()
