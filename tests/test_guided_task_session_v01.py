from __future__ import annotations

import json
from pathlib import Path

import pytest

from iios_mvp.guided_task_session_v01 import GuidedTaskSession
from iios_mvp.task_workspace_v01 import TaskWorkspaceError


def test_round_a_interruption_resumes_at_response_without_regenerating_prompt(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={"symbol": "603699.SH"})
    session.checkpoint_prompt("ROUND_A", "exact prompt bytes", response_filename="round-a.json", prompt_context={"prompt_input_payload": {}})
    resumed, contract = GuidedTaskSession.open(tmp_path / "tasks", session.task_id)
    assert contract["resume_stage"] == "ROUND_A_RESPONSE_PENDING"
    instruction = resumed.resume_contract()
    assert instruction["resume_action"] == "ROUND_A_RESPONSE_PENDING"
    assert resumed.load_artifact("artifacts/round_a_prompt_ready/prompt.md") == b"exact prompt bytes"


def test_invalid_response_attempt_is_preserved_and_new_attempt_is_append_only(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "prompt", response_filename="round-a.json", prompt_context={"prompt_input_payload": {}})
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
    session.checkpoint_prompt("ROUND_A", "A prompt", response_filename="a.json", prompt_context={"prompt_input_payload": {}})
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
    session.checkpoint_prompt("ROUND_A", "A", response_filename="a.json", prompt_context={"prompt_input_payload": {}})
    session.capture_response("ROUND_A", b'{"a":1}')
    session.accept_validated_payload("ROUND_A", {"frozen": True})
    session.checkpoint_prompt("ROUND_B", "B", response_filename="b.json", prompt_context={"prompt_input_payload": {}, "frozen_artifact_sha256": "test-hash"})
    session.capture_response("ROUND_B", b'{"b":1}')
    assert session.resume_contract()["resume_action"] == "ROUND_B_VALIDATION_PENDING"
    session.accept_validated_payload("ROUND_B", {"accepted": True})
    assert session.resume_contract()["resume_action"] == "OPERATOR_CONTEXT_PENDING"
    session.checkpoint_operator_context({"max_loss_pct": 25})
    assert session.resume_contract()["resume_action"] == "RUN_CREATION_PENDING"


def test_run_receipt_requires_matching_id_and_completion_requires_hash_verification(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "A", response_filename="a.json", prompt_context={"prompt_input_payload": {}})
    session.capture_response("ROUND_A", b'{"a":1}')
    session.accept_validated_payload("ROUND_A", {"frozen": True})
    session.checkpoint_prompt("ROUND_B", "B", response_filename="b.json", prompt_context={"prompt_input_payload": {}, "frozen_artifact_sha256": "test-hash"})
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
    session.checkpoint_prompt("ROUND_A", "A", response_filename="a.json", prompt_context={"prompt_input_payload": {}})
    artifact = session.workspace.path / "artifacts" / "round_a_prompt_ready" / "prompt.md"
    artifact.write_bytes(b"tampered")
    with pytest.raises(TaskWorkspaceError, match="ARTIFACT_HASH_MISMATCH"):
        GuidedTaskSession.open(tmp_path / "tasks", session.task_id)


def test_empty_response_cannot_advance_the_durable_stage(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "prompt", response_filename="round-a.json", prompt_context={"prompt_input_payload": {}})
    with pytest.raises(TaskWorkspaceError, match="RAW_RESPONSE_EMPTY"):
        session.capture_response("ROUND_A", b"")
    assert session.inspect()["current_stage"] == "ROUND_A_PROMPT_READY"


def test_response_validation_resume_requires_a_captured_attempt(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt("ROUND_A", "prompt", response_filename="round-a.json", prompt_context={"prompt_input_payload": {}})
    # A prompt-ready task is waiting for an operator response, not validation.
    assert session.resume_contract()["resume_action"] == "ROUND_A_RESPONSE_PENDING"


def test_operator_confirmed_context_is_immutable_and_survives_reopen(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={"symbol": "002810.SZ"})
    context = {
        "symbol": "002810.SZ",
        "template_payload": {"case": {"symbol": "002810.SZ"}, "price_input": {"price": "19.74"}},
        "analysis_prompt_text": "immutable base prompt",
    }
    session.checkpoint_context(context)
    reopened, manifest = GuidedTaskSession.open(tmp_path / "tasks", session.task_id)
    assert manifest["resume_stage"] == "ROUND_A_PROMPT_PENDING"
    assert reopened.load_json_artifact("artifacts/task_created/task_context.json") == context
    with pytest.raises(TaskWorkspaceError, match="CONTEXT_ALREADY_FROZEN"):
        reopened.checkpoint_context(context)


def test_offline_response_correction_becomes_a_new_attempt_before_validation(tmp_path: Path) -> None:
    import iios_mvp.local_investment_pilot_v01 as pilot
    from iios_mvp.guided_task_resume_v01 import _capture_or_reuse_response

    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt(
        "ROUND_A",
        "prompt",
        response_filename="round-a.json",
        prompt_context={"prompt_input_payload": {}},
    )
    response_path = tmp_path / "round-a.json"
    first = b'{"attempt": 1}'
    corrected = b'{"attempt": 2}'
    response_path.write_bytes(first)
    session.capture_response("ROUND_A", first)
    response_path.write_bytes(corrected)

    selected, _signature = _capture_or_reuse_response(
        session, pilot, "ROUND_A", response_path
    )
    assert selected == corrected
    attempts = sorted(
        name for name in session.inspect()["artifacts"]
        if name.startswith("artifacts/round_a_response_captured/")
    )
    assert len(attempts) == 2
    assert session.load_artifact(attempts[0]) == first
    assert session.load_artifact(attempts[1]) == corrected


def test_response_capture_skips_conflicting_orphan_attempt_after_prejournal_crash(tmp_path: Path) -> None:
    session = GuidedTaskSession.create(tmp_path / "tasks", metadata={})
    session.checkpoint_prompt(
        "ROUND_A",
        "prompt",
        response_filename="round-a.json",
        prompt_context={"prompt_input_payload": {}},
    )
    orphan_dir = session.workspace.path / "artifacts" / "round_a_response_captured"
    orphan_dir.mkdir(parents=True)
    orphan = orphan_dir / "round_a_response_captured_attempt_001.json"
    orphan.write_bytes(b"orphaned bytes from interrupted previous write")
    accepted = b'{"new_attempt": true}'

    session.capture_response("ROUND_A", accepted)

    manifest = session.inspect()
    recorded = [
        name for name in manifest["artifacts"]
        if name.startswith("artifacts/round_a_response_captured/")
    ]
    assert len(recorded) == 1
    assert recorded[0].endswith("round_a_response_captured_attempt_002.json")
    assert orphan.read_bytes() == b"orphaned bytes from interrupted previous write"
    assert session.load_artifact(recorded[0]) == accepted
