from __future__ import annotations

"""End-to-end continuation driver for the non-canonical guided Pilot.

All investment calculations remain delegated to local_investment_pilot_v01.
This module owns only durable stage orchestration and operator hand-off.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from .guided_task_session_v01 import GuidedTaskSession
from .operator_profile_v01 import (
    OperatorProfileError,
    load_operator_profile,
    profile_section_summary,
    save_operator_profile,
    validate_portfolio_context,
    validate_valuation_context,
)
from .task_workspace_v01 import TaskWorkspaceError


def _write_private_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise TaskWorkspaceError("GUIDED_TASK_WORKING_FILE_IS_SYMLINK")
    if path.exists():
        if path.read_bytes() != content:
            raise TaskWorkspaceError(f"GUIDED_TASK_WORKING_FILE_CONFLICT:{path.name}")
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != "nt":
        path.chmod(0o600)


def _latest_response_attempt(session: GuidedTaskSession, phase: str) -> tuple[str, bytes]:
    manifest = session.inspect()
    prefix = f"artifacts/{phase.lower()}_response_captured/"
    names = sorted(name for name in manifest["artifacts"] if name.startswith(prefix))
    if not names:
        raise TaskWorkspaceError(f"GUIDED_TASK_RESPONSE_ATTEMPT_MISSING:{phase}")
    return names[-1], session.load_artifact(names[-1])


def _show_prompt(prompt: str, response_path: Path, *, phase: str) -> None:
    heading = (
        "Round A 价格盲研究提示"
        if phase == "Round A"
        else "Round B 价格感知估值/MIE/预期差提示"
    )
    print(f"\n{heading} 已持久化；请发送给 ChatGPT。")
    if sys.platform == "darwin":
        try:
            subprocess.run(["pbcopy"], input=prompt, text=True, check=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            print("剪贴板复制失败；以下是持久化提示词，请手动复制：")
            print(prompt)
        try:
            subprocess.run(["open", "https://chatgpt.com/"], check=False, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        print(prompt)
    print(f"{phase} 响应文件：{response_path}")


def _capture_or_reuse_response(
    session: GuidedTaskSession, pilot: Any, phase: str, response_path: Path
) -> tuple[bytes, tuple[int, int, str]]:
    """Capture every stable saved version as an immutable attempt."""
    if response_path.is_symlink():
        raise TaskWorkspaceError(f"GUIDED_TASK_{phase}_RESPONSE_FILE_IS_SYMLINK")
    manifest = session.inspect()
    prompt_stage = f"{phase}_PROMPT_READY"
    response_stage = f"{phase}_RESPONSE_CAPTURED"
    if manifest["current_stage"] == prompt_stage:
        current = pilot._response_file_signature(response_path)
        if current is None or current[0] == 0:
            current = pilot._wait_for_response_file_change(
                response_path, previous_signature=current
            )
        raw = response_path.read_bytes()
        signature = pilot._response_file_signature(response_path)
        if signature != current:
            raise TaskWorkspaceError(f"GUIDED_TASK_{phase}_RESPONSE_CHANGED_DURING_CAPTURE")
        session.capture_response(phase, raw)
        return raw, signature

    if manifest["current_stage"] == response_stage:
        _name, raw = _latest_response_attempt(session, phase)
        # A correction may have been saved while the process was offline,
        # after the previous raw attempt was journaled but before validation.
        # Capture that changed file as a new immutable attempt before selecting
        # which bytes to validate; never silently ignore an offline correction.
        current = pilot._response_file_signature(response_path)
        if current is not None and current[0] > 0:
            working_bytes = response_path.read_bytes()
            if working_bytes != raw:
                stable = pilot._response_file_signature(response_path)
                if stable != current:
                    raise TaskWorkspaceError(f"GUIDED_TASK_{phase}_RESPONSE_CHANGED_DURING_CAPTURE")
                session.capture_response(phase, working_bytes)
                return working_bytes, stable
        # No new working-file version exists. Recompute the fingerprint from
        # the immutable accepted attempt rather than trusting mutable metadata.
        import hashlib
        return raw, (len(raw), 0, hashlib.sha256(raw).hexdigest())

    raise TaskWorkspaceError(f"GUIDED_TASK_{phase}_RESPONSE_STAGE_UNEXPECTED")


def _wait_for_corrected_response(
    session: GuidedTaskSession, pilot: Any, phase: str, response_path: Path
) -> tuple[bytes, tuple[int, int, str]]:
    _latest_name, latest_raw = _latest_response_attempt(session, phase)
    current = pilot._response_file_signature(response_path)
    if current is not None and current[0] > 0 and response_path.read_bytes() != latest_raw:
        signature = current
    else:
        signature = pilot._wait_for_response_file_change(
            response_path, previous_signature=current
        )
    raw = response_path.read_bytes()
    if pilot._response_file_signature(response_path) != signature:
        raise TaskWorkspaceError(f"GUIDED_TASK_{phase}_RESPONSE_CHANGED_DURING_CAPTURE")
    session.capture_response(phase, raw)
    return raw, signature


def _validate_round(
    session: GuidedTaskSession,
    pilot: Any,
    phase: str,
    context: Mapping[str, Any],
    response_path: Path,
) -> dict[str, Any]:
    """Validate the latest immutable attempt, allowing append-only repair attempts."""
    template_path = Path(str(context["template_path"]))
    prompt_path = Path(str(context["analysis_prompt_path"]))
    expected_template = (
        json.dumps(context["template_payload"], ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    if template_path.is_symlink() or template_path.read_bytes() != expected_template:
        raise TaskWorkspaceError("GUIDED_TASK_TEMPLATE_SNAPSHOT_HASH_MISMATCH")
    if prompt_path.is_symlink() or prompt_path.read_bytes() != str(context["analysis_prompt_text"]).encode("utf-8"):
        raise TaskWorkspaceError("GUIDED_TASK_ANALYSIS_PROMPT_SNAPSHOT_MISMATCH")
    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    while True:
        raw, signature = _capture_or_reuse_response(session, pilot, phase, response_path)
        try:
            response_object = pilot._extract_json_object(raw.decode("utf-8"))
            base_path = template_path
            if phase == "ROUND_B":
                base_path = Path(str(context["round_a_frozen_path"]))
                if base_path.is_symlink():
                    raise TaskWorkspaceError("GUIDED_TASK_ROUND_A_FROZEN_FILE_IS_SYMLINK")
                frozen_payload = session.load_json_artifact(
                    "artifacts/round_a_validated/round_a_validated_payload.json"
                )
                expected_frozen_bytes = (
                    json.dumps(frozen_payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
                ).encode("utf-8")
                if base_path.read_bytes() != expected_frozen_bytes:
                    raise TaskWorkspaceError("GUIDED_TASK_ROUND_A_FROZEN_FILE_HASH_MISMATCH")
            base_payload = json.loads(base_path.read_text(encoding="utf-8"))
            pilot._validate_research_round_patch(
                response_object, phase=phase, base_payload=base_payload
            )
            merged, response_format, merged_fields = pilot._expand_research_patch_with_template(
                base_path, response_object
            )
            merged.pop("_local_operator_controlled_field_recovery", None)
            merged.pop("_local_research_response_provenance", None)
            restored = pilot._restore_operator_controlled_fields_from_template(
                template_path, merged
            )
            if restored:
                merged["_local_operator_controlled_field_recovery"] = {
                    "status": "RESTORED_BEFORE_VALIDATION",
                    "fields": restored,
                    "source_template": template_path.name,
                    "method": "LOCAL_TEMPLATE_OVERRIDES_AI_RESPONSE",
                    "raw_response_file_modified": False,
                }
            pilot._assert_response_preserves_operator_inputs(template_path, merged)
            if phase == "ROUND_A":
                prompt = session.load_artifact("artifacts/round_a_prompt_ready/prompt.md").decode("utf-8")
                prompt_fp = pilot._text_fingerprint(prompt)
                round_a_prompt_context = session.load_json_artifact(
                    "artifacts/round_a_prompt_ready/prompt_context.json"
                )
                round_a_input = round_a_prompt_context["prompt_input_payload"]
                frozen_artifact = pilot._round_a_frozen_artifact(merged)
                frozen_sha = pilot._canonical_json_sha256(frozen_artifact)
                merged["_local_research_round_a_provenance"] = {
                    "schema_version": pilot.ROUND_A_PROVENANCE_SCHEMA,
                    "phase": "PRICE_BLIND_COMPANY_RESEARCH",
                    "prompt_filename": "round_a_prompt.md",
                    "prompt_text": prompt,
                    "prompt_sha256": prompt_fp["sha256"],
                    "prompt_byte_size": prompt_fp["byte_size"],
                    "prompt_input_payload": round_a_input,
                    "response_filename": response_path.name,
                    "raw_response_text": raw.decode("utf-8"),
                    "response_sha256": signature[2],
                    "response_byte_size": signature[0],
                    "frozen_company_side_artifact": frozen_artifact,
                    "frozen_artifact_sha256": frozen_sha,
                    "formal_forecast_admission": "NOT_ADMITTED",
                    "formal_valuation_admission": "NOT_ADMITTED",
                }
                _write_private_once(
                    Path(str(context["round_a_frozen_path"])),
                    (json.dumps(merged, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"),
                )
            else:
                pilot._prepare_input(merged)
                pilot._validate_guided_research_response(merged)
                round_a_payload = json.loads(Path(str(context["round_a_frozen_path"])).read_text(encoding="utf-8"))
                round_a_provenance = round_a_payload.get("_local_research_round_a_provenance")
                if not isinstance(round_a_provenance, Mapping):
                    raise TaskWorkspaceError("GUIDED_TASK_ROUND_A_PROVENANCE_MISSING")
                prompt = session.load_artifact("artifacts/round_b_prompt_ready/prompt.md").decode("utf-8")
                prompt_fp = pilot._text_fingerprint(prompt)
                round_b_prompt_context = session.load_json_artifact(
                    "artifacts/round_b_prompt_ready/prompt_context.json"
                )
                round_b_input = round_b_prompt_context["prompt_input_payload"]
                frozen = pilot._round_a_frozen_artifact(round_a_payload)
                frozen_sha = pilot._canonical_json_sha256(frozen)
                if frozen_sha != round_b_prompt_context["frozen_artifact_sha256"]:
                    raise TaskWorkspaceError("GUIDED_TASK_ROUND_B_FROZEN_HASH_MISMATCH")
                merged["_local_research_round_a_provenance"] = round_a_provenance
                merged["_local_research_round_b_provenance"] = {
                    "schema_version": pilot.ROUND_B_PROVENANCE_SCHEMA,
                    "phase": "PRICE_AWARE_VALUATION_MIE_EXPECTATION_GAP",
                    "prompt_filename": "round_b_prompt.md",
                    "prompt_text": prompt,
                    "prompt_sha256": prompt_fp["sha256"],
                    "prompt_byte_size": prompt_fp["byte_size"],
                    "prompt_input_payload": round_b_input,
                    "frozen_artifact_sha256": frozen_sha,
                    "response_filename": response_path.name,
                    "response_sha256": signature[2],
                    "response_byte_size": signature[0],
                }
                merged["_local_research_response_provenance"] = {
                    "schema_version": pilot.LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
                    "status": "CAPTURED_RAW_CHATGPT_RESPONSE",
                    "source_filename": "round-b-response-accepted.json",
                    "sha256": signature[2],
                    "byte_size": signature[0],
                    "capture_stage": "ROUND_B_RAW_RESPONSE_HASHED_ON_STABLE_SAVE_BEFORE_LOCAL_TEMPLATE_MERGE_AND_OPERATOR_FIELD_RECOVERY",
                    "validation_status": "ROUND_A_PRICE_BLIND_STAGE_FROZEN; JSON_OBJECT_PARSE_PASSED; RESPONSE_FORMAT="
                    + response_format + "; MERGED_FIELDS=" + ",".join(merged_fields)
                    + "; FULL_RESEARCH_REQUIRED_FIELDS_PASSED_AFTER_OPERATOR_FIELD_RESTORATION",
                    "raw_response_file_modified_by_runner": False,
                }
            session.accept_validated_payload(phase, merged)
            return merged
        except TaskWorkspaceError:
            raise
        except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
            print(f"{phase} 尚未通过校验：{exc}", flush=True)
            repair = pilot._build_response_repair_prompt(
                original_prompt=session.load_artifact(
                    f"artifacts/{phase.lower()}_prompt_ready/prompt.md"
                ).decode("utf-8"),
                response_path=response_path,
                validation_error=str(exc),
            )
            if sys.platform == "darwin":
                try:
                    subprocess.run(["pbcopy"], input=repair, text=True, check=True, timeout=5)
                except (OSError, subprocess.SubprocessError):
                    print("修复提示复制失败；请从终端复制下方提示。")
            print(repair, flush=True)
            print(f"请修正同一个响应文件；历史响应已作为独立 attempt 保存：{response_path}")
            _wait_for_corrected_response(session, pilot, phase, response_path)


def _resolve_operator_context_section(
    pilot: Any,
    *,
    section: str,
    profile: Mapping[str, Any] | None,
) -> Any:
    """Reuse an explicitly opted-in local default, or run the existing operator prompt."""
    key = "portfolio_context" if section == "portfolio" else "valuation_context"
    saved = profile.get(key) if isinstance(profile, Mapping) else None
    has_saved_value = isinstance(profile, Mapping) and key in profile
    if has_saved_value:
        print("\n发现本机个人默认设置：" + profile_section_summary(section, saved), flush=True)
        while True:
            choice = pilot._ask(
                "1 = 复用上次设置（默认）；2 = 修改设置；0 = 本次手动填写、不使用旧设置",
                "1",
            )
            if choice in {"0", "1", "2"}:
                break
            print("请输入 0、1 或 2。")
        if choice == "1":
            return validate_portfolio_context(saved) if section == "portfolio" else validate_valuation_context(saved)

    if section == "portfolio":
        return validate_portfolio_context(pilot._ask_operator_portfolio_context())
    if section == "valuation":
        return validate_valuation_context(pilot._ask_operator_valuation_context())
    raise OperatorProfileError("OPERATOR_PROFILE_SECTION_UNSUPPORTED")


def _maybe_persist_operator_profile(
    pilot: Any,
    *,
    profile: Mapping[str, Any] | None,
    portfolio_context: Any,
    valuation_context: Mapping[str, Any],
) -> None:
    """Save/update defaults only after an explicit opt-in; profile failure never blocks research."""
    portfolio = validate_portfolio_context(portfolio_context)
    valuation = validate_valuation_context(valuation_context)
    changed = (
        profile is None
        or profile.get("portfolio_context") != portfolio
        or profile.get("valuation_context") != valuation
    )
    if not changed:
        return

    if profile is None:
        prompt = (
            "是否将本次组合约束和主估值模型保存为本机默认设置，供以后研究复用？"
            "文件权限为目录 0700 / 文件 0600；文件未加密，不会提交到 GitHub。"
            "请自行确认本机备份或云同步策略。1 = 保存，0 = 仅本次使用"
        )
    else:
        prompt = (
            "本次设置与已保存的个人默认设置不同。是否更新本机默认设置，供以后研究复用？"
            "文件未加密，不会提交到 GitHub。1 = 更新，0 = 保留旧设置"
        )
    choice = pilot._ask(prompt, "0")
    if choice != "1":
        return
    try:
        save_operator_profile(
            portfolio_context=portfolio,
            valuation_context=valuation,
        )
        print("个人默认设置已安全保存到本机私有目录。", flush=True)
    except (OperatorProfileError, OSError) as exc:
        print(
            "个人默认设置未能保存；本次研究继续使用已记录的输入。原因：" + str(exc),
            flush=True,
        )


def run_guided_task(session: GuidedTaskSession, *, output_root: str | Path | None = None) -> dict[str, Any]:
    """Continue the task from its verified durable phase; safe to invoke after restart."""
    from . import local_investment_pilot_v01 as pilot

    context = session.load_json_artifact("artifacts/task_created/task_context.json")
    template_root = Path(str(context["template_root"]))
    work = session.workspace.path / "working"
    if work.is_symlink():
        raise TaskWorkspaceError("GUIDED_TASK_WORKING_DIRECTORY_IS_SYMLINK")
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        work.chmod(0o700)
    template_path = work / "template_snapshot.json"
    prompt_path = work / "analysis_prompt_snapshot.md"
    template_payload = context.get("template_payload")
    prompt_text = context.get("analysis_prompt_text")
    if not isinstance(template_payload, dict) or not isinstance(prompt_text, str):
        raise TaskWorkspaceError("GUIDED_TASK_CONTEXT_SNAPSHOT_MISSING")
    _write_private_once(
        template_path,
        (json.dumps(template_payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"),
    )
    _write_private_once(prompt_path, prompt_text.encode("utf-8"))
    context = dict(context)
    context["template_path"] = str(template_path)
    context["analysis_prompt_path"] = str(prompt_path)
    symbol = str((template_payload.get("case") or {}).get("symbol") or "candidate")
    response_a = work / "round-a-response.json"
    response_b = work / "round-b-response.json"
    frozen_path = work / "round_a_frozen.json"
    context = dict(context)
    context["round_a_frozen_path"] = str(frozen_path)
    run_root = Path(str(output_root or context["output_root"])).expanduser().resolve()
    context["output_root"] = str(run_root)

    with session.locked():
        while True:
            state = session.inspect()
            action = state["resume_stage"]
            if action == "ROUND_A_PROMPT_PENDING":
                prompt = pilot._build_price_blind_round_a_prompt(template_payload)
                _write_private_once(work / "round_a_prompt.md", prompt.encode("utf-8"))
                _write_private_once(response_a, b"")
                session.checkpoint_prompt(
                    "ROUND_A",
                    prompt,
                    response_filename=response_a.name,
                    prompt_context={"prompt_input_payload": pilot._round_a_prompt_input(template_payload)},
                )
                continue
            if action in {"ROUND_A_RESPONSE_PENDING", "ROUND_A_VALIDATION_PENDING"}:
                if state["current_stage"] == "ROUND_A_PROMPT_READY":
                    saved_prompt = session.load_artifact(
                        "artifacts/round_a_prompt_ready/prompt.md"
                    ).decode("utf-8")
                    _show_prompt(saved_prompt, response_a, phase="Round A")
                _validate_round(session, pilot, "ROUND_A", context, response_a)
                continue
            if action == "ROUND_B_PROMPT_PENDING":
                round_a_payload = session.load_json_artifact(
                    "artifacts/round_a_validated/round_a_validated_payload.json"
                )
                frozen_sha = pilot._canonical_json_sha256(
                    pilot._round_a_frozen_artifact(round_a_payload)
                )
                round_a_payload["_local_research_round_a_provenance"] = round_a_payload.get(
                    "_local_research_round_a_provenance"
                )
                _write_private_once(
                    frozen_path,
                    (json.dumps(round_a_payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"),
                )
                base_prompt = prompt_path.read_text(encoding="utf-8")
                round_b_prompt, round_b_prompt_input, built_frozen_sha = pilot._build_price_aware_round_b_prompt(
                    base_prompt=base_prompt, payload=round_a_payload
                )
                if built_frozen_sha != frozen_sha:
                    raise TaskWorkspaceError("GUIDED_TASK_ROUND_A_FROZEN_HASH_MISMATCH")
                _write_private_once(work / "round_b_prompt.md", round_b_prompt.encode("utf-8"))
                _write_private_once(response_b, b"")
                session.checkpoint_prompt(
                    "ROUND_B",
                    round_b_prompt,
                    response_filename=response_b.name,
                    prompt_context={
                        "prompt_input_payload": round_b_prompt_input,
                        "frozen_artifact_sha256": built_frozen_sha,
                    },
                )
                continue
            if action in {"ROUND_B_RESPONSE_PENDING", "ROUND_B_VALIDATION_PENDING"}:
                if state["current_stage"] == "ROUND_B_PROMPT_READY":
                    saved_prompt = session.load_artifact(
                        "artifacts/round_b_prompt_ready/prompt.md"
                    ).decode("utf-8")
                    _show_prompt(saved_prompt, response_b, phase="Round B")
                _validate_round(session, pilot, "ROUND_B", context, response_b)
                continue
            if action == "OPERATOR_CONTEXT_PENDING":
                payload = session.load_json_artifact(
                    "artifacts/round_b_validated/round_b_validated_payload.json"
                )
                pilot._prepare_input(payload)

                has_portfolio = session.has_partial_operator_context("portfolio")
                has_valuation = session.has_partial_operator_context("valuation")
                profile_checked = not (has_portfolio and has_valuation)
                profile = load_operator_profile() if profile_checked else None

                if has_portfolio:
                    portfolio = session.load_partial_operator_context("portfolio")
                else:
                    portfolio = _resolve_operator_context_section(
                        pilot, section="portfolio", profile=profile
                    )
                    session.checkpoint_partial_operator_context("portfolio", portfolio)

                if has_valuation:
                    valuation = session.load_partial_operator_context("valuation")
                else:
                    valuation = _resolve_operator_context_section(
                        pilot, section="valuation", profile=profile
                    )
                    session.checkpoint_partial_operator_context("valuation", valuation)

                if profile_checked:
                    _maybe_persist_operator_profile(
                        pilot,
                        profile=profile,
                        portfolio_context=portfolio,
                        valuation_context=valuation,
                    )

                session.checkpoint_operator_context({
                    "operator_portfolio_context": portfolio,
                    "operator_valuation_context": valuation,
                })
                continue
            if action == "RUN_CREATION_PENDING":
                payload = session.load_json_artifact(
                    "artifacts/round_b_validated/round_b_validated_payload.json"
                )
                operator = session.load_json_artifact(
                    "artifacts/operator_context_captured/operator_context.json"
                )
                if operator.get("operator_portfolio_context") is not None:
                    payload["operator_portfolio_context"] = operator["operator_portfolio_context"]
                payload["operator_valuation_context"] = operator["operator_valuation_context"]
                completed_path = work / "completed_input.json"
                _write_private_once(
                    completed_path,
                    (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"),
                )
                _attempt_name, response = _latest_response_attempt(session, "ROUND_B")
                accepted_response_path = work / "round-b-response-accepted.json"
                _write_private_once(accepted_response_path, response)
                import hashlib
                response_sha = hashlib.sha256(response).hexdigest()
                result = pilot.run_local_investment_pilot(
                    input_path=completed_path,
                    output_root=run_root,
                    research_response_path=accepted_response_path,
                    expected_research_response_sha256=response_sha,
                    expected_research_response_byte_size=len(response),
                    run_id_override=f"local-pilot-{symbol.replace('.', '-')}-{session.task_id}",
                )
                receipt_path = Path(result["run_dir"]) / "pilot_receipt.json"
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                session.checkpoint_run(run_id=result["pilot_id"], receipt=receipt)
                print(json.dumps(pilot._safe(result), ensure_ascii=False, indent=2))
                continue
            if action == "RUN_VERIFICATION_PENDING":
                receipt = session.load_json_artifact(
                    "artifacts/run_created/run_receipt.json"
                )
                run_dir = run_root / str(receipt["pilot_id"])
                verification = pilot.verify_local_pilot_bundle(run_dir)
                session.complete(verification=verification)
                result = dict(verification)
                result["verification_status"] = verification["status"]
                result["status"] = "PILOT_CREATED"
                result["run_dir"] = str(run_dir)
                result["report_path"] = str(run_dir / "report.md")
                result["task_id"] = session.task_id
                return result
            if action == "NO_AUTOMATIC_RESUME":
                return {
                    "status": "TASK_ALREADY_TERMINAL",
                    "task_id": session.task_id,
                    "current_stage": state["current_stage"],
                    "formal_decision_created": False,
                    "auto_execution": False,
                }
            raise TaskWorkspaceError(f"GUIDED_TASK_RESUME_ACTION_UNSUPPORTED:{action}")
