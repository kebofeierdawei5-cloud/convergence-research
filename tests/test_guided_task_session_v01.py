from __future__ import annotations

import json
from pathlib import Path

import pytest

from iios_mvp.guided_task_session_v01 import GuidedTaskSession
from iios_mvp.task_workspace_v01 import TaskWorkspaceError


def test_round_a_interruption_resumes_at_response_without_regenerating_prompt(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={"symbol": "603699.SH"})
    session.checkpoint_prompt("ROUND_A", "exact prompt bytes", response_filename="round-a.json")
    resumed, contract = GuidedTaskSession.open(tmp_path / "tasks", session.task_id)
    assert contract["resume_stage"] == "ROUND_A_RESPONSE_PENDING"
    instruction = resumed.resume_contract()
    assert instruction["resume_action"] == "ROUND_A_RESPONSE_PENDING"
    assert resumed.load_artifact("artifacts/round_a_prompt_ready/prompt.md") == b"exact prompt bytes"


def test_invalid_response_attempt_is_preserved_and_new_attempt_is_append_only(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "prompt", response_filename="round-a.json")
    session.capture_response("ROUND_A", b'{"invalid":')
    session.capture_response("ROUND_A", b'{"corrected": true}')
    manifest = session.inspect()
    attempts = sorted(
        name for name in manifest["artifacts"]
        if name.startswith("artifacts/round_a_response_captured/")
    )
    assert len(attempts) == 2
    assert session.load_artifact(attempts[0]) == b'{"invalid":'
    assert session.load_artifact(attempts[1]) == b'{"corrected": true}'


def test_round_a_validated_resumes_directly_at_round_b(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "A prompt", response_filename="a.json")
    session.capture_response("ROUND_A", b'{"patch":"A"}')
    session.accept_validated_payload("ROUND_A", {"frozen": {"earnings": 100}})
    resumed, _ = GuidedTaskSession.open(tmp_path / "tasks", session.task_id)
    contract = resumed.resume_contract()
    assert contract["resume_action"] == "ROUND_B_PROMPT_PENDING"
    frozen = json.loads(resumed.load_artifact(
        "artifacts/round_a_validated/round_a_validated_payload.json"
    ))
    assert frozen == {"frozen": {"earnings": 100}}


def test_round_b_validation_and_operator_context_are_distinct_boundaries(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "A", response_filename="a.json")
    session.capture_response("ROUND_A", b'{"a":1}')
    session.accept_validated_payload("ROUND_A", {"frozen": True})
    session.checkpoint_prompt("ROUND_B", "B", response_filename="b.json")
    session.capture_response("ROUND_B", b'{"b":1}')
    assert session.resume_contract()["resume_action"] == "ROUND_B_VALIDATION_PENDING"
    session.accept_validated_payload("ROUND_B", {"accepted": True})
    assert session.resume_contract()["resume_action"] == "OPERATOR_CONTEXT_PENDING"
    session.checkpoint_operator_context({"max_loss_pct": 25})
    assert session.resume_contract()["resume_action"] == "RUN_CREATION_PENDING"


def test_run_receipt_requires_matching_id_and_completion_requires_hash_verification(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "A", response_filename="a.json")
    session.capture_response("ROUND_A", b'{"a":1}')
    session.accept_validated_payload("ROUND_A", {"frozen": True})
    session.checkpoint_prompt("ROUND_B", "B", response_filename="b.json")
    session.capture_response("ROUND_B", b'{"b":1}')
    session.accept_validated_payload("ROUND_B", {"accepted": True})
    session.checkpoint_operator_context({"max_loss_pct": 25})
    with pytest.raises(TaskWorkspaceError, match="RECEIPT_ID_MISMATCH"):
        session.checkpoint_run(run_id="run-1", receipt={"pilot_id": "run-2"})
    session.checkpoint_run(run_id="run-1", receipt={"pilot_id": "run-1"})
    with pytest.raises(TaskWorkspaceError, match="NOT_PASSED"):
        session.complete(verification={"status": "UNKNOWN"})
    result = session.complete(verification={"status": "PILOT_BUNDLE_HASH_CHECK_PASS"})
    assert result["current_stage"] == "COMPLETED"
    assert result["resume_stage"] == "NO_AUTOMATIC_RESUME"


def test_corrupted_task_fails_closed_on_reopen(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "A", response_filename="a.json")
    artifact = session.workspace.path / "artifacts" / "round_a_prompt_ready" / "prompt.md"
    artifact.write_bytes(b"tampered")
    with pytest.raises(TaskWorkspaceError, match="ARTIFACT_HASH_MISMATCH"):
        GuidedTaskSession.open(tmp_path / "tasks", session.task_id)
