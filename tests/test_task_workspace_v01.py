from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path

import pytest

from iios_mvp.task_workspace_v01 import (
    TaskWorkspaceError,
    create_task,
    open_task,
    task_lock,
)




def _crash_while_holding_task_lock(root: str, task_id: str) -> None:
    workspace, _ = open_task(root, task_id)
    with task_lock(workspace):
        os._exit(17)

def test_create_task_persists_private_manifest_and_initial_journal(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks", metadata={"symbol": "603699.SH"})
    manifest = workspace.inspect()
    assert manifest["task_id"] == workspace.task_id
    assert manifest["current_stage"] == "TASK_CREATED"
    assert manifest["resume_stage"] == "ROUND_A_PROMPT_PENDING"
    assert manifest["formal_decision_created"] is False
    assert workspace.path.stat().st_mode & 0o077 == 0


def test_append_only_transitions_and_artifact_hashes(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    prompt = b"price-blind prompt"
    state = workspace.record(
        "ROUND_A_PROMPT_READY",
        artifacts={"round_a_prompt.md": prompt},
        details={"price_supplied": False},
    )
    assert state["current_stage"] == "ROUND_A_PROMPT_READY"
    assert state["artifacts"]["artifacts/round_a_prompt_ready/round_a_prompt.md"]["byte_size"] == len(prompt)
    assert workspace.inspect()["revision"] == 2
    with pytest.raises(TaskWorkspaceError, match="IMMUTABLE_FILE_ALREADY_EXISTS"):
        workspace.record(
            "ROUND_A_PROMPT_READY",
            artifacts={"round_a_prompt.md": b"overwritten"},
        )


def test_identical_orphan_artifact_is_adopted_after_interrupted_write(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    orphan = workspace.path / "artifacts" / "round_a_prompt_ready" / "prompt.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"same bytes")
    state = workspace.record("ROUND_A_PROMPT_READY", artifacts={"prompt.md": b"same bytes"})
    assert state["artifacts"]["artifacts/round_a_prompt_ready/prompt.md"]["sha256"]


def test_stale_manifest_is_rebuilt_from_durable_journal(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    workspace.record("ROUND_A_PROMPT_READY")
    manifest = json.loads(workspace.manifest_path.read_text())
    manifest["current_stage"] = "ROUND_B_PROMPT_READY"
    workspace.manifest_path.write_text(json.dumps(manifest))
    recovered = workspace.inspect()
    assert recovered["current_stage"] == "ROUND_A_PROMPT_READY"
    assert json.loads(workspace.manifest_path.read_text()) == recovered


def test_tampered_artifact_is_rejected(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    workspace.record("ROUND_A_PROMPT_READY", artifacts={"prompt.md": b"original"})
    artifact = workspace.path / "artifacts" / "round_a_prompt_ready" / "prompt.md"
    artifact.write_bytes(b"tampered")
    with pytest.raises(TaskWorkspaceError, match="ARTIFACT_HASH_MISMATCH"):
        workspace.inspect()


def test_tampered_journal_chain_is_rejected(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    workspace.record("ROUND_A_PROMPT_READY")
    lines = workspace.journal_path.read_text().splitlines()
    row = json.loads(lines[1])
    row["stage"] = "ROUND_B_PROMPT_READY"
    lines[1] = json.dumps(row)
    workspace.journal_path.write_text("\n".join(lines) + "\n")
    with pytest.raises(TaskWorkspaceError, match="JOURNAL_HASH_MISMATCH"):
        workspace.inspect()


def test_partial_journal_tail_is_rejected_not_silently_truncated(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    with workspace.journal_path.open("ab") as stream:
        stream.write(b'{"partial":')
    with pytest.raises(TaskWorkspaceError, match="TRAILING_PARTIAL_RECORD"):
        workspace.inspect()


def test_invalid_transition_and_terminal_task_are_blocked(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    with pytest.raises(TaskWorkspaceError, match="TRANSITION_INVALID"):
        workspace.record("ROUND_B_PROMPT_READY")
    workspace.record("BLOCKED", task_status="BLOCKED")
    with pytest.raises(TaskWorkspaceError, match="ALREADY_TERMINAL"):
        workspace.record("COMPLETED", task_status="COMPLETED")


def test_resume_open_validates_artifacts_and_lock_is_exclusive(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    opened, manifest = open_task(tmp_path / "tasks", workspace.task_id)
    assert manifest["current_stage"] == "TASK_CREATED"
    with task_lock(opened):
        with pytest.raises(TaskWorkspaceError, match="ALREADY_OPEN"):
            with task_lock(opened):
                pass
    with task_lock(opened):
        pass


@pytest.mark.skipif(os.name == "nt", reason="POSIX advisory-lock crash-release contract")
def test_posix_task_lock_is_released_by_kernel_after_process_crash(tmp_path: Path) -> None:
    workspace = create_task(tmp_path / "tasks")
    process = multiprocessing.Process(
        target=_crash_while_holding_task_lock,
        args=(str(tmp_path / "tasks"), workspace.task_id),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 17
    reopened, _ = open_task(tmp_path / "tasks", workspace.task_id)
    with task_lock(reopened):
        assert reopened.inspect()["current_stage"] == "TASK_CREATED"
