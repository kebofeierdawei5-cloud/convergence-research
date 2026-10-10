from __future__ import annotations

"""Explicit operator-mediated bridge to ChatGPT Free web UI.

No network/API call, browser automation, cookie reuse or provider-origin claim is
made. Exact prompts and pasted JSON responses are hash-bound and immutable.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping

SCHEMA_VERSION = "IIOS-CHATGPT-WEB-HANDOFF-0.1"
ALLOWED_STAGES = {"request-intent", "semantic-thesis"}
DEFAULT_ROOT = ".iios-chatgpt-handoff"
DEFAULT_MODEL_LABEL = "ChatGPT Free web UI; exact model not independently identified"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class ChatGPTChatHandoffError(ValueError):
    """Raised for invalid, unsafe or mismatched operator handoff state."""


class ChatGPTChatHandoffRequired(ChatGPTChatHandoffError):
    """Raised when a generated prompt awaits an operator-copied response."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"CHATGPT_CHAT_RESPONSE_REQUIRED:{task_id}")


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ChatGPTChatHandoffError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _parse_json_object(raw: bytes, *, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ChatGPTChatHandoffError("NON_FINITE_JSON_NUMBER")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ChatGPTChatHandoffError(reason) from exc
    if not isinstance(value, dict):
        raise ChatGPTChatHandoffError("JSON_OBJECT_REQUIRED")
    return value


def _ensure_private_root(root: str | Path) -> Path:
    supplied = Path(root).expanduser()
    if supplied.exists() and supplied.is_symlink():
        raise ChatGPTChatHandoffError("HANDOFF_ROOT_MUST_NOT_BE_SYMLINK")
    supplied.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not supplied.is_dir():
        raise ChatGPTChatHandoffError("HANDOFF_ROOT_MUST_BE_DIRECTORY")
    try:
        supplied.chmod(0o700)
    except OSError:
        pass
    resolved = supplied.resolve()
    for name in ("requests", "responses", "receipts"):
        child = resolved / name
        if child.exists() and child.is_symlink():
            raise ChatGPTChatHandoffError("HANDOFF_CHILD_MUST_NOT_BE_SYMLINK")
        child.mkdir(mode=0o700, exist_ok=True)
        if not child.is_dir():
            raise ChatGPTChatHandoffError("HANDOFF_CHILD_MUST_BE_DIRECTORY")
        try:
            child.chmod(0o700)
        except OSError:
            pass
    return resolved


def _write_immutable(path: Path, raw: bytes, *, collision_reason: str) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    except FileExistsError:
        try:
            if path.read_bytes() == raw:
                return
        except OSError:
            pass
        raise ChatGPTChatHandoffError(collision_reason)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o600)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _task_core(*, stage: str, run_id: str, request_id: str, case_id: str, cutoff_date: str, prompt_sha256: str) -> dict[str, Any]:
    if stage not in ALLOWED_STAGES:
        raise ChatGPTChatHandoffError("UNSUPPORTED_CHATGPT_HANDOFF_STAGE")
    for field, value in (("run_id", run_id), ("request_id", request_id), ("case_id", case_id), ("cutoff_date", cutoff_date)):
        if not isinstance(value, str) or not value.strip():
            raise ChatGPTChatHandoffError(f"{field.upper()}_REQUIRED")
    try:
        normalized_cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ChatGPTChatHandoffError("CUTOFF_DATE_MUST_BE_ISO_DATE") from exc
    if len(prompt_sha256) != 64 or any(c not in "0123456789abcdef" for c in prompt_sha256):
        raise ChatGPTChatHandoffError("PROMPT_SHA256_INVALID")
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "run_id": run_id,
        "request_id": request_id,
        "case_id": case_id,
        "cutoff_date": normalized_cutoff,
        "prompt_sha256": prompt_sha256,
        "execution_channel": "CHATGPT_WEB_FREE_MANUAL",
        "provider_origin_verified": False,
    }


def _paths(root: Path, task_id: str) -> dict[str, Path]:
    if len(task_id) != 64 or any(c not in "0123456789abcdef" for c in task_id):
        raise ChatGPTChatHandoffError("TASK_ID_INVALID")
    return {
        "request": root / "requests" / f"{task_id}.json",
        "prompt": root / "requests" / f"{task_id}.prompt.txt",
        "response": root / "responses" / f"{task_id}.json",
        "receipt": root / "receipts" / f"{task_id}.receipt.json",
    }


def prepare_chatgpt_handoff(*, root: str | Path, prompt: str, run_id: str, request_id: str, case_id: str, cutoff_date: str, stage: str) -> dict[str, Any]:
    """Persist one immutable exact-prompt request."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ChatGPTChatHandoffError("PROMPT_REQUIRED")
    prompt_raw = prompt.encode("utf-8")
    prompt_sha = hashlib.sha256(prompt_raw).hexdigest()
    core = _task_core(stage=stage, run_id=run_id, request_id=request_id, case_id=case_id, cutoff_date=cutoff_date, prompt_sha256=prompt_sha)
    task_id = hashlib.sha256(_canonical_bytes(core)).hexdigest()
    task = {**core, "task_id": task_id}
    paths = _paths(_ensure_private_root(root), task_id)
    task_raw = (json.dumps(task, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    _write_immutable(paths["request"], task_raw, collision_reason="CHATGPT_HANDOFF_REQUEST_IMMUTABLE_COLLISION")
    _write_immutable(paths["prompt"], prompt_raw, collision_reason="CHATGPT_HANDOFF_PROMPT_IMMUTABLE_COLLISION")
    return {
        "status": "CHATGPT_CHAT_HANDOFF_REQUIRED",
        "task_id": task_id,
        "stage": stage,
        "run_id": run_id,
        "request_id": request_id,
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "prompt_sha256": prompt_sha,
        "prompt_file": str(paths["prompt"]),
        "request_file": str(paths["request"]),
        "response_file": str(paths["response"]),
        "provider_origin_verified": False,
    }


def _load_task(root: Path, task_id: str) -> tuple[dict[str, Any], dict[str, Path]]:
    paths = _paths(root, task_id)
    try:
        task = _parse_json_object(paths["request"].read_bytes(), reason="HANDOFF_REQUEST_INVALID_JSON")
        prompt_raw = paths["prompt"].read_bytes()
    except OSError as exc:
        raise ChatGPTChatHandoffError("HANDOFF_REQUEST_NOT_FOUND") from exc
    if task.get("task_id") != task_id:
        raise ChatGPTChatHandoffError("HANDOFF_TASK_ID_MISMATCH")
    if hashlib.sha256(prompt_raw).hexdigest() != task.get("prompt_sha256"):
        raise ChatGPTChatHandoffError("HANDOFF_PROMPT_HASH_MISMATCH")
    task_core = {k: v for k, v in task.items() if k != "task_id"}
    if hashlib.sha256(_canonical_bytes(task_core)).hexdigest() != task_id:
        raise ChatGPTChatHandoffError("HANDOFF_REQUEST_HASH_MISMATCH")
    return task, paths


def _load_response_record(root: Path, task_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    task, paths = _load_task(root, task_id)
    try:
        record = _parse_json_object(paths["response"].read_bytes(), reason="CHATGPT_RESPONSE_RECORD_INVALID_JSON")
    except OSError as exc:
        raise ChatGPTChatHandoffRequired(task_id) from exc
    record_hash = record.get("record_sha256")
    record_core = {k: v for k, v in record.items() if k != "record_sha256"}
    if not isinstance(record_hash, str) or hashlib.sha256(_canonical_bytes(record_core)).hexdigest() != record_hash:
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_RECORD_HASH_MISMATCH")
    for field in ("task_id", "stage", "run_id", "request_id", "case_id", "cutoff_date", "prompt_sha256"):
        if record.get(field) != task.get(field):
            raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_TASK_BINDING_MISMATCH")
    if record.get("execution_channel") != "CHATGPT_WEB_FREE_MANUAL" or record.get("provider_origin_verified") is not False:
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_ORIGIN_CLAIM_INVALID")
    response_text = record.get("response_text")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_TEXT_MISSING")
    response_raw = response_text.encode("utf-8")
    if hashlib.sha256(response_raw).hexdigest() != record.get("response_sha256"):
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_HASH_MISMATCH")
    parsed = _parse_json_object(response_raw, reason="CHATGPT_RESPONSE_NOT_STRICT_JSON_OBJECT")
    return task, {"record": record, "parsed": parsed}, paths


def import_chatgpt_response(*, root: str | Path, task_id: str, response_file: str | Path, model_label: str = DEFAULT_MODEL_LABEL) -> dict[str, Any]:
    """Import exact operator-copied JSON; the web origin remains unverified."""
    root_path = _ensure_private_root(root)
    task, paths = _load_task(root_path, task_id)
    try:
        raw = Path(response_file).expanduser().read_bytes()
    except OSError as exc:
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_FILE_UNREADABLE") from exc
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_SIZE_INVALID")
    _parse_json_object(raw, reason="CHATGPT_RESPONSE_NOT_STRICT_JSON_OBJECT")
    try:
        response_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_NOT_UTF8") from exc
    label = str(model_label).strip()
    if not label or len(label) > 200:
        raise ChatGPTChatHandoffError("CHATGPT_MODEL_LABEL_INVALID")
    response_sha = hashlib.sha256(raw).hexdigest()

    if paths["response"].exists():
        _, loaded, _ = _load_response_record(root_path, task_id)
        prior = loaded["record"]
        if prior.get("response_sha256") != response_sha or prior.get("model_label") != label:
            raise ChatGPTChatHandoffError("CHATGPT_RESPONSE_IMMUTABLE_COLLISION")
        return {"status": "ALREADY_IMPORTED", "task_id": task_id, "response_sha256": response_sha, "provider_origin_verified": False, "receipt_file": str(paths["receipt"])}

    record_core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "stage": task["stage"],
        "run_id": task["run_id"],
        "request_id": task["request_id"],
        "case_id": task["case_id"],
        "cutoff_date": task["cutoff_date"],
        "prompt_sha256": task["prompt_sha256"],
        "response_sha256": response_sha,
        "response_text": response_text,
        "execution_channel": "CHATGPT_WEB_FREE_MANUAL",
        "operator_reported_origin": "CHATGPT_FREE_WEB_UI",
        "provider_origin_verified": False,
        "model_label": label,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "integrity_semantics": "HASH_INTEGRITY_ONLY_NOT_PROVIDER_AUTHENTICATION",
    }
    record = {**record_core, "record_sha256": hashlib.sha256(_canonical_bytes(record_core)).hexdigest()}
    _write_immutable(paths["response"], (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(), collision_reason="CHATGPT_RESPONSE_IMMUTABLE_COLLISION")

    receipt_core = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "stage": task["stage"],
        "run_id": task["run_id"],
        "request_id": task["request_id"],
        "case_id": task["case_id"],
        "cutoff_date": task["cutoff_date"],
        "prompt_sha256": task["prompt_sha256"],
        "response_sha256": response_sha,
        "execution_channel": "CHATGPT_WEB_FREE_MANUAL",
        "operator_reported_origin": "CHATGPT_FREE_WEB_UI",
        "provider_origin_verified": False,
        "integrity_semantics": "HASH_INTEGRITY_ONLY_NOT_PROVIDER_AUTHENTICATION",
    }
    receipt = {**receipt_core, "receipt_sha256": hashlib.sha256(_canonical_bytes(receipt_core)).hexdigest()}
    _write_immutable(paths["receipt"], (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(), collision_reason="CHATGPT_OPERATOR_RECEIPT_IMMUTABLE_COLLISION")
    return {
        "status": "IMPORTED_NOT_PROVIDER_AUTHENTICATED",
        "task_id": task_id,
        "stage": task["stage"],
        "response_sha256": response_sha,
        "response_file": str(paths["response"]),
        "receipt_file": str(paths["receipt"]),
        "provider_origin_verified": False,
        "integrity_semantics": "HASH_INTEGRITY_ONLY_NOT_PROVIDER_AUTHENTICATION",
    }


class ChatGPTChatJsonClient:
    """Drop-in generate_json transport; missing replies fail closed into handoff."""

    def __init__(self, *, root: str | Path, model_label: str = DEFAULT_MODEL_LABEL) -> None:
        self.root = str(root)
        self.model_label = str(model_label).strip() or DEFAULT_MODEL_LABEL

    def generate_json(self, *, prompt: str, run_id: str, request_id: str, case_id: str, cutoff_date: str, stage: str) -> Mapping[str, Any]:
        task = prepare_chatgpt_handoff(
            root=self.root,
            prompt=prompt,
            run_id=run_id,
            request_id=request_id,
            case_id=case_id,
            cutoff_date=cutoff_date,
            stage=stage,
        )
        _, loaded, _ = _load_response_record(_ensure_private_root(self.root), task["task_id"])
        return loaded["parsed"]


def _default_root() -> str:
    return os.environ.get("IIOS_CHATGPT_HANDOFF_ROOT", DEFAULT_ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import strict JSON returned by ChatGPT Free web UI")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import-response")
    imp.add_argument("--task-id", required=True)
    imp.add_argument("--response-file", required=True)
    imp.add_argument("--root", default=_default_root())
    imp.add_argument("--model-label", default=os.environ.get("IIOS_CHATGPT_MODEL_LABEL", DEFAULT_MODEL_LABEL))
    args = parser.parse_args(argv)
    try:
        result = import_chatgpt_response(root=args.root, task_id=args.task_id, response_file=args.response_file, model_label=args.model_label)
    except ChatGPTChatHandoffError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
