from __future__ import annotations

from pathlib import Path

import pytest

import iios_mvp.quick_start_v01 as quick_start
import iios_mvp.guided_task_resume_v01 as guided_resume
from iios_mvp.task_workspace_v01 import TaskWorkspaceError


def test_quick_start_starts_new_wizard_when_no_unfinished_tasks(monkeypatch):
    calls = []
    monkeypatch.setattr(quick_start, "_discover_unfinished_tasks", lambda: [])
    monkeypatch.setattr(
        quick_start, "run_guided_wizard",
        lambda: calls.append("wizard") or {"status": "CANCELLED"},
    )

    assert quick_start.main() == 0
    assert calls == ["wizard"]


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

    with pytest.raises(TaskWorkspaceError, match="QUICK_START_PRIVATE_PATH_IS_SYMLINK"):
        quick_start._discover_unfinished_tasks()



def test_quick_start_opens_only_verified_report_inside_private_output_root(monkeypatch, tmp_path):
    report = tmp_path / "run-1" / "report.md"
    report.parent.mkdir()
    report.write_text("# verified", encoding="utf-8")
    calls = []
    monkeypatch.setattr(quick_start.sys, "platform", "darwin")
    monkeypatch.setattr(quick_start, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(
        quick_start.subprocess, "run",
        lambda command, **kwargs: calls.append(command),
    )

    assert quick_start._open_verified_report({
        "status": "PILOT_CREATED",
        "report_path": str(report),
    }) is True
    assert calls == [["open", str(report.resolve())]]


def test_prompt_handoff_does_not_open_textedit(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(guided_resume.sys, "platform", "darwin")
    monkeypatch.setattr(
        guided_resume.subprocess, "run",
        lambda command, **kwargs: calls.append(command),
    )

    guided_resume._show_prompt("safe prompt", tmp_path / "response.json", phase="Round A")

    assert calls[0] == ["pbcopy"]
    assert calls[1] == ["open", "https://chatgpt.com/"]
    assert all("TextEdit" not in part for command in calls for part in command)



def test_double_click_launcher_is_local_and_checks_python_environment():
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "IIOS.command").read_text(encoding="utf-8")

    assert "umask 077" in launcher
    assert "PYTHONNOUSERSITE=1" in launcher
    assert "sys.version_info >= (3, 10)" in launcher
    assert "iios_mvp.quick_start_v01" in launcher
    assert "pip install" not in launcher
    assert "curl " not in launcher
    assert "eval " not in launcher
