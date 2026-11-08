from __future__ import annotations

"""Guided Pilot phase adapter over the durable task workspace.

This module deliberately owns persistence and resume decisions only. It does
not execute prompts, parse research, or invoke valuation/decision code.
"""

import json
from pathlib import Path
from typing import Any, Mapping

from .task_workspace_v01 import TaskWorkspace, TaskWorkspaceError, create_task, open_task, task_lock

_PHASE_ARTIFACTS = {
    "ROUND_A_PROMPT_READY": "round_a_prompt.md",
    "ROUND_A_VALIDATED": "round_a_validated_payload.json",
    "ROUND_B_PROMPT_READY": "round_b_prompt.md",
    "ROUND_B_VALIDATED": "round_b_validated_payload.json",
    "OPERATOR_CONTEXT_CAPTURED": "operator_context.json",
    "RUN_CREATED": "run_receipt.json",
}


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


class GuidedTaskSession:
    """Typed persistence boundary for each guided Pilot stage."""

    def __init__(self, workspace: TaskWorkspace):
        self.workspace = workspace

    @classmethod
    def create(cls, root: str | Path, *, metadata: Mapping[str, Any]) -> "GuidedTaskSession":
        return cls(create_task(root, metadata=metadata))

    @classmethod
    def open(cls, root: str | Path, task_id: str) -> tuple["GuidedTaskSession", dict[str, Any]]:
        workspace, manifest = open_task(root, task_id, verify_artifacts=True)
        return cls(workspace), manifest

    @property
    def task_id(self) -> str:
        return self.workspace.task_id

    def inspect(self) -> dict[str, Any]:
        return self.workspace.inspect(verify_artifacts=True)

    def checkpoint_context(self, context: Mapping[str, Any]) -> dict[str, Any]:
        """Persist the immutable operator-confirmed task context at TASK_CREATED."""
        current = self.inspect()
        if current["current_stage"] != "TASK_CREATED":
            raise TaskWorkspaceError("GUIDED_TASK_CONTEXT_ALREADY_FROZEN")
        return self.workspace.record(
            "TASK_CREATED",
            artifacts={"task_context.json": _json_bytes(context)},
            details={"context": "operator_confirmed_immutable"},
        )

    def load_json_artifact(self, relative_path: str) -> dict[str, Any]:
        try:
            value = json.loads(self.load_artifact(relative_path).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TaskWorkspaceError(f"GUIDED_TASK_JSON_ARTIFACT_INVALID:{relative_path}") from exc
        if not isinstance(value, dict):
            raise TaskWorkspaceError(f"GUIDED_TASK_JSON_ARTIFACT_NOT_OBJECT:{relative_path}")
        return value

    def _next_attempt_name(self, phase: str, suffix: str) -> str:
        manifest = self.inspect()
        prefix = f"artifacts/{phase.lower()}/"
        attempts = [
            name for name in manifest["artifacts"]
            if name.startswith(prefix) and name.endswith(suffix)
        ]
        return f"{phase.lower()}_attempt_{len(attempts) + 1:03d}{suffix}"

    def checkpoint_prompt(
        self,
        phase: str,
        prompt: str,
        *,
        response_filename: str,
        prompt_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if phase not in {"ROUND_A", "ROUND_B"}:
            raise TaskWorkspaceError("GUIDED_TASK_PHASE_UNSUPPORTED")
        if not isinstance(response_filename, str) or not response_filename or Path(response_filename).name != response_filename or "/" in response_filename or "\\" in response_filename:
            raise TaskWorkspaceError("GUIDED_TASK_RESPONSE_FILENAME_INVALID")
        stage = f"{phase}_PROMPT_READY"
        current = self.inspect()
        if current["resume_stage"] not in {
            f"{phase}_PROMPT_PENDING", f"{phase}_RESPONSE_PENDING"
        } and current["current_stage"] != stage:
            raise TaskWorkspaceError("GUIDED_TASK_PROMPT_STAGE_MISMATCH")
        artifacts: dict[str, bytes] = {"prompt.md": prompt.encode("utf-8")}
        if prompt_context is not None:
            artifacts["prompt_context.json"] = _json_bytes(prompt_context)
        return self.workspace.record(
            stage,
            artifacts=artifacts,
            details={"response_filename": response_filename, "prompt_encoding": "utf-8"},
        )

    def capture_response(self, phase: str, raw_response: bytes) -> dict[str, Any]:
        if phase not in {"ROUND_A", "ROUND_B"}:
            raise TaskWorkspaceError("GUIDED_TASK_PHASE_UNSUPPORTED")
        if not isinstance(raw_response, bytes) or not raw_response.strip():
            raise TaskWorkspaceError("GUIDED_TASK_RAW_RESPONSE_EMPTY_OR_INVALID")
        stage = f"{phase}_RESPONSE_CAPTURED"
        current = self.inspect()
        expected = f"{phase}_RESPONSE_PENDING"
        if current["resume_stage"] != expected and current["current_stage"] != stage:
            raise TaskWorkspaceError("GUIDED_TASK_RESPONSE_STAGE_MISMATCH")
        name = self._next_attempt_name(stage, ".json")
        return self.workspace.record(
            stage,
            artifacts={name: raw_response},
            details={"capture": "immutable_raw_bytes", "attempt_artifact": name},
        )

    def accept_validated_payload(self, phase: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if phase not in {"ROUND_A", "ROUND_B"}:
            raise TaskWorkspaceError("GUIDED_TASK_PHASE_UNSUPPORTED")
        stage = f"{phase}_VALIDATED"
        current = self.inspect()
        if current["resume_stage"] != f"{phase}_VALIDATION_PENDING":
            raise TaskWorkspaceError("GUIDED_TASK_VALIDATION_STAGE_MISMATCH")
        return self.workspace.record(stage, artifacts={
            _PHASE_ARTIFACTS[stage]: _json_bytes(payload)
        }, details={"validation": "caller_asserted_success"})

    def checkpoint_operator_context(self, context: Mapping[str, Any]) -> dict[str, Any]:
        current = self.inspect()
        if current["resume_stage"] != "OPERATOR_CONTEXT_PENDING":
            raise TaskWorkspaceError("GUIDED_TASK_OPERATOR_CONTEXT_STAGE_MISMATCH")
        return self.workspace.record("OPERATOR_CONTEXT_CAPTURED", artifacts={
            _PHASE_ARTIFACTS["OPERATOR_CONTEXT_CAPTURED"]: _json_bytes(context)
        })

    def checkpoint_run(self, *, run_id: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
        current = self.inspect()
        if current["resume_stage"] != "RUN_CREATION_PENDING":
            raise TaskWorkspaceError("GUIDED_TASK_RUN_STAGE_MISMATCH")
        if not run_id or receipt.get("pilot_id") != run_id:
            raise TaskWorkspaceError("GUIDED_TASK_RUN_RECEIPT_ID_MISMATCH")
        return self.workspace.record("RUN_CREATED", artifacts={
            _PHASE_ARTIFACTS["RUN_CREATED"]: _json_bytes(receipt)
        }, details={"run_id": run_id})

    def complete(self, *, verification: Mapping[str, Any]) -> dict[str, Any]:
        current = self.inspect()
        if current["resume_stage"] != "RUN_VERIFICATION_PENDING":
            raise TaskWorkspaceError("GUIDED_TASK_COMPLETION_STAGE_MISMATCH")
        if verification.get("status") != "PILOT_BUNDLE_HASH_CHECK_PASS":
            raise TaskWorkspaceError("GUIDED_TASK_RUN_VERIFICATION_NOT_PASSED")
        return self.workspace.record(
            "COMPLETED", task_status="COMPLETED",
            artifacts={"run_verification.json": _json_bytes(verification)},
        )

    def load_artifact(self, relative_path: str) -> bytes:
        manifest = self.inspect()
        record = manifest["artifacts"].get(relative_path)
        if not isinstance(record, Mapping):
            raise TaskWorkspaceError("GUIDED_TASK_ARTIFACT_NOT_INDEXED")
        path = self.workspace.path / relative_path
        data = path.read_bytes()
        if len(data) != record["byte_size"]:
            raise TaskWorkspaceError("GUIDED_TASK_ARTIFACT_SIZE_MISMATCH")
        return data

    def resume_contract(self) -> dict[str, Any]:
        """Return a verified continuation instruction; never execute it implicitly."""
        manifest = self.inspect()
        action = manifest["resume_stage"]
        required: list[str] = []
        if action == "ROUND_A_RESPONSE_PENDING":
            required = [
                "artifacts/round_a_prompt_ready/prompt.md",
                "artifacts/round_a_prompt_ready/prompt_context.json",
            ]
        elif action == "ROUND_A_VALIDATION_PENDING":
            required = [
                "artifacts/round_a_prompt_ready/prompt.md",
                "artifacts/round_a_prompt_ready/prompt_context.json",
                *[name for name in manifest["artifacts"] if name.startswith("artifacts/round_a_response_captured/")],
            ]
            if len(required) <= 2:
                raise TaskWorkspaceError("GUIDED_TASK_ROUND_A_RESPONSE_ATTEMPT_MISSING")
        elif action == "ROUND_B_PROMPT_PENDING":
            required = ["artifacts/round_a_validated/round_a_validated_payload.json"]
        elif action == "ROUND_B_RESPONSE_PENDING":
            required = [
                "artifacts/round_b_prompt_ready/prompt.md",
                "artifacts/round_b_prompt_ready/prompt_context.json",
                "artifacts/round_a_validated/round_a_validated_payload.json",
            ]
        elif action == "ROUND_B_VALIDATION_PENDING":
            required = [
                "artifacts/round_b_prompt_ready/prompt.md",
                "artifacts/round_b_prompt_ready/prompt_context.json",
                "artifacts/round_a_validated/round_a_validated_payload.json",
                *[name for name in manifest["artifacts"] if name.startswith("artifacts/round_b_response_captured/")],
            ]
            if len(required) <= 3:
                raise TaskWorkspaceError("GUIDED_TASK_ROUND_B_RESPONSE_ATTEMPT_MISSING")
        elif action == "OPERATOR_CONTEXT_PENDING":
            required = ["artifacts/round_a_validated/round_a_validated_payload.json", "artifacts/round_b_validated/round_b_validated_payload.json"]
        elif action == "RUN_CREATION_PENDING":
            required = ["artifacts/operator_context_captured/operator_context.json"]
        elif action == "RUN_VERIFICATION_PENDING":
            required = ["artifacts/run_created/run_receipt.json"]
        for name in required:
            if name not in manifest["artifacts"]:
                raise TaskWorkspaceError(f"GUIDED_TASK_RESUME_ARTIFACT_MISSING:{name}")
            self.load_artifact(name)
        return {
            "task_id": self.task_id,
            "current_stage": manifest["current_stage"],
            "resume_action": action,
            "required_artifacts_verified": required,
            "automatic_execution": False,
            "formal_decision_created": False,
        }

    def locked(self):
        return task_lock(self.workspace)
