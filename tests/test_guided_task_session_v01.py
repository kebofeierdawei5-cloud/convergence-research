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


def test_guided_runner_reopens_same_round_a_prompt_and_captures_offline_response(tmp_path: Path, monkeypatch) -> None:
    import json

    import iios_mvp.local_investment_pilot_v01 as pilot
    from iios_mvp.guided_task_resume_v01 import run_guided_task

    inputs = tmp_path / "inputs"
    output_root = tmp_path / "runs"
    template_result = pilot.create_pilot_template(
        company="山东赫达",
        symbol="002810.SZ",
        market="CN-A",
        as_of_date="2026-10-12",
        current_position_pct="0",
        price="19.74",
        price_observation_date="2026-10-09",
        price_known_at="2026-10-09T15:00:00+08:00",
        price_source_claim="operator supplied test price; not source verified",
        template_root=inputs,
    )
    template_path = Path(template_result["input_template"])
    prompt_path = Path(template_result["analysis_prompt"])
    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    session = GuidedTaskSession.create(inputs / "tasks", metadata={"symbol": "002810.SZ"})
    session.checkpoint_context({
        "company": "山东赫达",
        "symbol": "002810.SZ",
        "market": "CN-A",
        "template_path": str(template_path.resolve()),
        "analysis_prompt_path": str(prompt_path.resolve()),
        "template_payload": template_payload,
        "analysis_prompt_text": prompt_path.read_text(encoding="utf-8"),
        "template_root": str(inputs.resolve()),
        "output_root": str(output_root.resolve()),
    })

    monkeypatch.setattr(
        pilot,
        "_wait_for_response_file_change",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        run_guided_task(session, output_root=output_root)

    first_state = session.inspect()
    assert first_state["current_stage"] == "ROUND_A_PROMPT_READY"
    original_prompt = session.load_artifact(
        "artifacts/round_a_prompt_ready/prompt.md"
    )
    response_path = session.workspace.path / "working" / "round-a-response.json"
    assert response_path.is_file()
    assert response_path.read_bytes() == b""

    # Simulate the operator saving the ChatGPT response while the runner is
    # offline. Reopening must reuse the prompt bytes and capture the response
    # before trying to validate it; it must not rebuild Round A.
    raw_response = b'{"response_mode":"IIOS-RESEARCH-PATCH-0.1","research":{}}'
    response_path.write_bytes(raw_response)
    reopened, manifest = GuidedTaskSession.open(inputs / "tasks", session.task_id)
    assert manifest["resume_stage"] == "ROUND_A_RESPONSE_PENDING"
    monkeypatch.setattr(
        pilot,
        "_build_price_blind_round_a_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Round A prompt must not be regenerated")),
    )
    monkeypatch.setattr(
        pilot,
        "_validate_research_round_patch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        run_guided_task(reopened, output_root=output_root)

    resumed_state = reopened.inspect()
    assert resumed_state["current_stage"] == "ROUND_A_RESPONSE_CAPTURED"
    assert reopened.load_artifact("artifacts/round_a_prompt_ready/prompt.md") == original_prompt
    attempts = [
        name for name in resumed_state["artifacts"]
        if name.startswith("artifacts/round_a_response_captured/")
    ]
    assert len(attempts) == 1
    assert reopened.load_artifact(attempts[0]) == raw_response


def test_guided_runner_resumes_round_b_without_rebuilding_frozen_round_a(tmp_path: Path, monkeypatch) -> None:
    import copy
    import json

    import iios_mvp.local_investment_pilot_v01 as pilot
    from iios_mvp.guided_task_resume_v01 import run_guided_task

    inputs = tmp_path / "inputs"
    output_root = tmp_path / "runs"
    template_result = pilot.create_pilot_template(
        company="山东赫达",
        symbol="002810.SZ",
        market="CN-A",
        as_of_date="2026-10-12",
        current_position_pct="0",
        price="19.74",
        price_observation_date="2026-10-09",
        price_known_at="2026-10-09T15:00:00+08:00",
        price_source_claim="operator supplied test price; not source verified",
        template_root=inputs,
    )
    template_path = Path(template_result["input_template"])
    prompt_path = Path(template_result["analysis_prompt"])
    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    round_a_prompt = pilot._build_price_blind_round_a_prompt(template_payload)
    round_a_raw = '{"response_mode":"IIOS-RESEARCH-PATCH-0.1","research":{}}'
    round_a_prompt_fp = pilot._text_fingerprint(round_a_prompt)
    round_a_response_fp = pilot._text_fingerprint(round_a_raw)
    frozen_artifact = pilot._round_a_frozen_artifact(template_payload)
    frozen_sha = pilot._canonical_json_sha256(frozen_artifact)
    round_a_payload = copy.deepcopy(template_payload)
    round_a_payload["_local_research_round_a_provenance"] = {
        "schema_version": pilot.ROUND_A_PROVENANCE_SCHEMA,
        "phase": "PRICE_BLIND_COMPANY_RESEARCH",
        "prompt_filename": "round-a-prompt.md",
        "prompt_text": round_a_prompt,
        "prompt_sha256": round_a_prompt_fp["sha256"],
        "prompt_byte_size": round_a_prompt_fp["byte_size"],
        "prompt_input_payload": pilot._round_a_prompt_input(template_payload),
        "response_filename": "round-a-response.json",
        "raw_response_text": round_a_raw,
        "response_sha256": round_a_response_fp["sha256"],
        "response_byte_size": round_a_response_fp["byte_size"],
        "frozen_company_side_artifact": frozen_artifact,
        "frozen_artifact_sha256": frozen_sha,
        "formal_forecast_admission": "NOT_ADMITTED",
        "formal_valuation_admission": "NOT_ADMITTED",
    }

    session = GuidedTaskSession.create(inputs / "tasks", metadata={"symbol": "002810.SZ"})
    session.checkpoint_context({
        "company": "山东赫达",
        "symbol": "002810.SZ",
        "market": "CN-A",
        "template_path": str(template_path.resolve()),
        "analysis_prompt_path": str(prompt_path.resolve()),
        "template_payload": template_payload,
        "analysis_prompt_text": prompt_path.read_text(encoding="utf-8"),
        "template_root": str(inputs.resolve()),
        "output_root": str(output_root.resolve()),
    })
    session.checkpoint_prompt(
        "ROUND_A",
        round_a_prompt,
        response_filename="round-a-response.json",
        prompt_context={"prompt_input_payload": pilot._round_a_prompt_input(template_payload)},
    )
    session.capture_response("ROUND_A", round_a_raw.encode("utf-8"))
    session.accept_validated_payload("ROUND_A", round_a_payload)

    monkeypatch.setattr(
        pilot,
        "_build_price_blind_round_a_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("frozen Round A must not be regenerated")),
    )
    monkeypatch.setattr(
        pilot,
        "_wait_for_response_file_change",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        run_guided_task(session, output_root=output_root)

    first_state = session.inspect()
    assert first_state["current_stage"] == "ROUND_B_PROMPT_READY"
    frozen_before_resume = session.load_artifact(
        "artifacts/round_a_validated/round_a_validated_payload.json"
    )
    prompt_before_resume = session.load_artifact(
        "artifacts/round_b_prompt_ready/prompt.md"
    )

    reopened, manifest = GuidedTaskSession.open(inputs / "tasks", session.task_id)
    assert manifest["resume_stage"] == "ROUND_B_RESPONSE_PENDING"
    monkeypatch.setattr(
        pilot,
        "_build_price_aware_round_b_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("saved Round B prompt must not be regenerated")),
    )
    with pytest.raises(KeyboardInterrupt):
        run_guided_task(reopened, output_root=output_root)

    resumed_state = reopened.inspect()
    assert resumed_state["current_stage"] == "ROUND_B_PROMPT_READY"
    assert reopened.load_artifact(
        "artifacts/round_a_validated/round_a_validated_payload.json"
    ) == frozen_before_resume
    assert reopened.load_artifact(
        "artifacts/round_b_prompt_ready/prompt.md"
    ) == prompt_before_resume
