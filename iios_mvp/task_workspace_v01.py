from __future__ import annotations

"""Durable, append-only workspace for the non-canonical local investment Pilot.

The journal is authoritative. task_manifest.json is a rebuildable snapshot.
Artifacts are immutable once accepted; retries must use a new artifact name.
This module does not alter investment calculations or formal decision authority.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
from typing import Any, Iterator, Mapping

TASK_SCHEMA = "IIOS-PILOT-TASK-0.1"
EVENT_SCHEMA = "IIOS-PILOT-TASK-EVENT-0.1"
MANIFEST_FILENAME = "task_manifest.json"
JOURNAL_FILENAME = "transitions.jsonl"
ARTIFACT_DIRNAME = "artifacts"
STAGES = (
    "TASK_CREATED",
    "ROUND_A_PROMPT_READY",
    "ROUND_A_RESPONSE_CAPTURED",
    "ROUND_A_VALIDATED",
    "ROUND_B_PROMPT_READY",
    "ROUND_B_RESPONSE_CAPTURED",
    "ROUND_B_VALIDATED",
    "OPERATOR_CONTEXT_CAPTURED",
    "RUN_CREATED",
    "COMPLETED",
)
TERMINAL_STAGES = {"COMPLETED", "BLOCKED"}
TASK_ID_RE = re.compile(r"^task-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$")
TASK_STATUSES = {"ACTIVE", "INTERRUPTED", "BLOCKED", "COMPLETED"}
ARTIFACT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class TaskWorkspaceError(ValueError):
    """Invalid, corrupted, unsafe, or conflicting task workspace."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_new(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, mode)
    except FileExistsError as exc:
        raise TaskWorkspaceError(f"IMMUTABLE_FILE_ALREADY_EXISTS:{path.name}") from exc
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    if os.name != "nt":
        path.chmod(mode)


def _atomic_snapshot(path: Path, data: bytes) -> None:
    temp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
    _write_new(temp, data)
    os.replace(temp, path)
    if os.name != "nt":
        path.chmod(0o600)


def _write_immutable(path: Path, data: bytes) -> None:
    """Adopt an identical orphan after a crash; never replace different bytes."""
    if path.is_symlink():
        raise TaskWorkspaceError(f"IMMUTABLE_FILE_IS_SYMLINK:{path.name}")
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise TaskWorkspaceError(f"IMMUTABLE_FILE_UNREADABLE:{path.name}") from exc
        if existing != data:
            raise TaskWorkspaceError(f"IMMUTABLE_FILE_ALREADY_EXISTS:{path.name}")
        return
    try:
        _write_new(path, data)
    except TaskWorkspaceError:
        if path.is_symlink() or not path.is_file():
            raise
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise TaskWorkspaceError(f"IMMUTABLE_FILE_UNREADABLE:{path.name}") from exc
        if existing != data:
            raise TaskWorkspaceError(f"IMMUTABLE_FILE_ALREADY_EXISTS:{path.name}")


def _safe_artifact_name(name: str) -> str:
    if not isinstance(name, str) or not ARTIFACT_NAME_RE.fullmatch(name):
        raise TaskWorkspaceError("ARTIFACT_NAME_INVALID")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise TaskWorkspaceError("ARTIFACT_NAME_INVALID")
    return name


def _safe_task_dir(root: str | Path, task_id: str, *, must_exist: bool = True) -> tuple[Path, Path]:
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise TaskWorkspaceError("TASK_ID_INVALID")
    base = Path(root).expanduser().resolve()
    task_dir = base / task_id
    if task_dir.is_symlink():
        raise TaskWorkspaceError("TASK_DIRECTORY_MUST_NOT_BE_SYMLINK")
    if must_exist and not task_dir.is_dir():
        raise TaskWorkspaceError("TASK_NOT_FOUND")
    resolved = task_dir.resolve()
    if resolved.parent != base:
        raise TaskWorkspaceError("TASK_DIRECTORY_ESCAPES_ROOT")
    return base, resolved


def _event_hash(event_without_hash: Mapping[str, Any]) -> str:
    return _sha(_canonical(dict(event_without_hash)))


def _validate_stage_status(stage: Any, status: Any) -> None:
    if not isinstance(stage, str) or (stage not in STAGES and stage != "BLOCKED"):
        raise TaskWorkspaceError("TASK_JOURNAL_STAGE_UNSUPPORTED")
    if not isinstance(status, str) or status not in TASK_STATUSES:
        raise TaskWorkspaceError("TASK_JOURNAL_STATUS_UNSUPPORTED")
    if (stage == "BLOCKED") != (status == "BLOCKED"):
        raise TaskWorkspaceError("TASK_STAGE_STATUS_MISMATCH")
    if (stage == "COMPLETED") != (status == "COMPLETED"):
        raise TaskWorkspaceError("TASK_STAGE_STATUS_MISMATCH")


def _validate_transition(previous: Mapping[str, Any], stage: str, status: str) -> None:
    if previous.get("task_status") in {"BLOCKED", "COMPLETED"}:
        raise TaskWorkspaceError("TASK_JOURNAL_EVENT_AFTER_TERMINAL")
    expected_next = _next_stage(str(previous.get("stage")), str(previous.get("task_status")))
    if stage not in {expected_next, previous.get("stage"), "BLOCKED"}:
        raise TaskWorkspaceError("TASK_JOURNAL_TRANSITION_INVALID")


def _read_journal(task_dir: Path) -> list[dict[str, Any]]:
    path = task_dir / JOURNAL_FILENAME
    if path.is_symlink() or not path.is_file():
        raise TaskWorkspaceError("TASK_JOURNAL_MISSING_OR_UNSAFE")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise TaskWorkspaceError("TASK_JOURNAL_UNREADABLE") from exc
    if raw and not raw.endswith(b"\n"):
        raise TaskWorkspaceError("TASK_JOURNAL_TRAILING_PARTIAL_RECORD")
    events: list[dict[str, Any]] = []
    previous_hash = "0" * 64
    task_id: str | None = None
    for expected_sequence, line in enumerate(raw.splitlines(), start=1):
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TaskWorkspaceError(f"TASK_JOURNAL_RECORD_INVALID:{expected_sequence}") from exc
        if not isinstance(event, dict):
            raise TaskWorkspaceError(f"TASK_JOURNAL_RECORD_NOT_OBJECT:{expected_sequence}")
        supplied_hash = event.pop("event_sha256", None)
        if event.get("event_schema") != EVENT_SCHEMA:
            raise TaskWorkspaceError(f"TASK_JOURNAL_SCHEMA_INVALID:{expected_sequence}")
        if event.get("sequence") != expected_sequence:
            raise TaskWorkspaceError(f"TASK_JOURNAL_SEQUENCE_INVALID:{expected_sequence}")
        if event.get("previous_event_sha256") != previous_hash:
            raise TaskWorkspaceError(f"TASK_JOURNAL_CHAIN_BROKEN:{expected_sequence}")
        calculated = _event_hash(event)
        if supplied_hash != calculated:
            raise TaskWorkspaceError(f"TASK_JOURNAL_HASH_MISMATCH:{expected_sequence}")
        current_task_id = event.get("task_id")
        if not isinstance(current_task_id, str) or not TASK_ID_RE.fullmatch(current_task_id):
            raise TaskWorkspaceError("TASK_JOURNAL_TASK_ID_INVALID")
        if task_id is None:
            task_id = current_task_id
        elif current_task_id != task_id:
            raise TaskWorkspaceError("TASK_JOURNAL_TASK_ID_MISMATCH")
        stage, status = event.get("stage"), event.get("task_status")
        _validate_stage_status(stage, status)
        if expected_sequence == 1:
            if stage != "TASK_CREATED" or status != "ACTIVE":
                raise TaskWorkspaceError("TASK_JOURNAL_INITIAL_EVENT_INVALID")
        else:
            _validate_transition(events[-1], stage, status)
        event["event_sha256"] = supplied_hash
        previous_hash = supplied_hash
        events.append(event)
    if not events or events[0].get("stage") != "TASK_CREATED":
        raise TaskWorkspaceError("TASK_JOURNAL_INITIAL_EVENT_MISSING")
    return events

def _manifest_from_events(task_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    latest = events[-1]
    artifacts: dict[str, Any] = {}
    for event in events:
        for name, record in (event.get("artifacts") or {}).items():
            artifacts[name] = record
    return {
        "task_schema": TASK_SCHEMA,
        "task_id": task_id,
        "created_at": events[0]["created_at"],
        "updated_at": latest["created_at"],
        "revision": len(events),
        "current_stage": latest["stage"],
        "task_status": latest["task_status"],
        "last_event_sha256": latest["event_sha256"],
        "artifacts": artifacts,
        "resume_stage": _resume_action(latest["stage"], latest["task_status"]),
        "formal_decision_created": False,
        "execution_authorized": False,
        "auto_execution": False,
    }


def _next_stage(stage: str, status: str) -> str:
    """Return the next journal stage allowed after the current completed event."""
    if status == "BLOCKED" or stage in TERMINAL_STAGES:
        return "NO_AUTOMATIC_RESUME"
    if stage not in STAGES:
        return "REVIEW_REQUIRED"
    index = STAGES.index(stage)
    return STAGES[min(index + 1, len(STAGES) - 1)]


def _resume_action(stage: str, status: str) -> str:
    """Return the operation to resume, not merely the next event name."""
    if status == "BLOCKED" or stage in TERMINAL_STAGES:
        return "NO_AUTOMATIC_RESUME"
    actions = {
        "TASK_CREATED": "ROUND_A_PROMPT_PENDING",
        "ROUND_A_PROMPT_READY": "ROUND_A_RESPONSE_PENDING",
        "ROUND_A_RESPONSE_CAPTURED": "ROUND_A_VALIDATION_PENDING",
        "ROUND_A_VALIDATED": "ROUND_B_PROMPT_PENDING",
        "ROUND_B_PROMPT_READY": "ROUND_B_RESPONSE_PENDING",
        "ROUND_B_RESPONSE_CAPTURED": "ROUND_B_VALIDATION_PENDING",
        "ROUND_B_VALIDATED": "OPERATOR_CONTEXT_PENDING",
        "OPERATOR_CONTEXT_CAPTURED": "RUN_CREATION_PENDING",
        "RUN_CREATED": "RUN_VERIFICATION_PENDING",
    }
    return actions.get(stage, "REVIEW_REQUIRED")


def _verify_artifacts(task_dir: Path, manifest: Mapping[str, Any]) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise TaskWorkspaceError("TASK_ARTIFACT_INDEX_INVALID")
    for name, record in artifacts.items():
        safe_name = str(name)
        if not isinstance(name, str) or not isinstance(record, Mapping):
            raise TaskWorkspaceError(f"TASK_ARTIFACT_RECORD_INVALID:{safe_name}")
        rel = record.get("path")
        if not isinstance(rel, str) or rel != name:
            raise TaskWorkspaceError(f"TASK_ARTIFACT_PATH_INVALID:{safe_name}")
        posix = PurePosixPath(rel)
        if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts) or not rel.startswith(ARTIFACT_DIRNAME + "/"):
            raise TaskWorkspaceError(f"TASK_ARTIFACT_PATH_UNSAFE:{safe_name}")
        _safe_artifact_name(posix.name)
        path = task_dir
        for part in posix.parts:
            path = path / part
            if path.is_symlink():
                raise TaskWorkspaceError(f"TASK_ARTIFACT_PATH_COMPONENT_IS_SYMLINK:{safe_name}")
        if not path.is_file():
            raise TaskWorkspaceError(f"TASK_ARTIFACT_MISSING:{safe_name}")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise TaskWorkspaceError(f"TASK_ARTIFACT_UNREADABLE:{safe_name}") from exc
        if _sha(data) != record.get("sha256") or len(data) != record.get("byte_size"):
            raise TaskWorkspaceError(f"TASK_ARTIFACT_HASH_MISMATCH:{safe_name}")


class TaskWorkspace:
    def __init__(self, root: Path, task_dir: Path, task_id: str):
        self.root = root
        self.path = task_dir
        self.task_id = task_id

    @property
    def manifest_path(self) -> Path:
        return self.path / MANIFEST_FILENAME

    @property
    def journal_path(self) -> Path:
        return self.path / JOURNAL_FILENAME

    def inspect(self, *, verify_artifacts: bool = True) -> dict[str, Any]:
        events = _read_journal(self.path)
        if events[0].get("task_id") != self.task_id:
            raise TaskWorkspaceError("TASK_JOURNAL_TASK_ID_MISMATCH")
        expected = _manifest_from_events(self.task_id, events)
        manifest_path = self.manifest_path
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise TaskWorkspaceError("TASK_MANIFEST_MISSING_OR_UNSAFE")
        try:
            actual = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskWorkspaceError("TASK_MANIFEST_UNREADABLE") from exc
        if actual != expected:
            # The append-only journal is authoritative. A crash after fsync of
            # the event but before snapshot replacement leaves a stale manifest;
            # rebuild that derived file rather than losing the committed event.
            _atomic_snapshot(manifest_path, _canonical(expected) + b"\n")
        if verify_artifacts:
            _verify_artifacts(self.path, expected)
        return expected

    def record(
        self,
        stage: str,
        *,
        task_status: str = "ACTIVE",
        artifacts: Mapping[str, bytes | str] | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if stage not in STAGES and stage != "BLOCKED":
            raise TaskWorkspaceError("TASK_STAGE_UNSUPPORTED")
        if task_status not in TASK_STATUSES:
            raise TaskWorkspaceError("TASK_STATUS_UNSUPPORTED")
        _validate_stage_status(stage, task_status)
        current = self.inspect()
        if current["task_status"] in {"BLOCKED", "COMPLETED"}:
            raise TaskWorkspaceError("TASK_ALREADY_TERMINAL")
        expected_next = _next_stage(current["current_stage"], current["task_status"])
        if stage not in {expected_next, current["current_stage"], "BLOCKED"}:
            raise TaskWorkspaceError(f"TASK_STAGE_TRANSITION_INVALID:{current['current_stage']}->{stage}")
        artifact_records: dict[str, Any] = {}
        for raw_name, raw_content in (artifacts or {}).items():
            name = _safe_artifact_name(raw_name)
            content = raw_content.encode("utf-8") if isinstance(raw_content, str) else bytes(raw_content)
            rel = f"{ARTIFACT_DIRNAME}/{stage.lower()}/{name}"
            artifact_root = self.path / ARTIFACT_DIRNAME
            stage_root = artifact_root / stage.lower()
            if artifact_root.is_symlink() or stage_root.is_symlink():
                raise TaskWorkspaceError("TASK_ARTIFACT_DIRECTORY_MUST_NOT_BE_SYMLINK")
            target = self.path / rel
            _write_immutable(target, content)
            artifact_records[rel] = {
                "path": rel,
                "sha256": _sha(content),
                "byte_size": len(content),
            }
        events = _read_journal(self.path)
        previous_hash = events[-1]["event_sha256"]
        body = {
            "event_schema": EVENT_SCHEMA,
            "sequence": len(events) + 1,
            "task_id": self.task_id,
            "created_at": _now(),
            "stage": stage,
            "task_status": task_status,
            "previous_event_sha256": previous_hash,
            "artifacts": artifact_records,
            "details": dict(details or {}),
        }
        event = dict(body)
        event["event_sha256"] = _event_hash(body)
        line = _canonical(event) + b"\n"
        fd = os.open(self.journal_path, os.O_WRONLY | os.O_APPEND)
        try:
            with os.fdopen(fd, "ab") as stream:
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise TaskWorkspaceError("TASK_JOURNAL_APPEND_FAILED") from exc
        refreshed = _read_journal(self.path)
        snapshot = _manifest_from_events(self.task_id, refreshed)
        _atomic_snapshot(self.manifest_path, _canonical(snapshot) + b"\n")
        return snapshot


def create_task(
    root: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    task_id: str | None = None,
) -> TaskWorkspace:
    base = Path(root).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        base.chmod(0o700)
    identifier = task_id or (
        "task-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)
    )
    if not TASK_ID_RE.fullmatch(identifier):
        raise TaskWorkspaceError("TASK_ID_INVALID")
    task_dir = base / identifier
    try:
        task_dir.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise TaskWorkspaceError("TASK_ALREADY_EXISTS") from exc
    if os.name != "nt":
        task_dir.chmod(0o700)
    workspace = TaskWorkspace(base, task_dir, identifier)
    initial = {
        "event_schema": EVENT_SCHEMA,
        "sequence": 1,
        "task_id": identifier,
        "created_at": _now(),
        "stage": "TASK_CREATED",
        "task_status": "ACTIVE",
        "previous_event_sha256": "0" * 64,
        "artifacts": {},
        "details": dict(metadata or {}),
    }
    event = dict(initial)
    event["event_sha256"] = _event_hash(initial)
    _write_new(workspace.journal_path, _canonical(event) + b"\n")
    manifest = _manifest_from_events(identifier, [event])
    _write_new(workspace.manifest_path, _canonical(manifest) + b"\n")
    return workspace


def open_task(root: str | Path, task_id: str, *, verify_artifacts: bool = True) -> tuple[TaskWorkspace, dict[str, Any]]:
    base, task_dir = _safe_task_dir(root, task_id)
    workspace = TaskWorkspace(base, task_dir, task_id)
    return workspace, workspace.inspect(verify_artifacts=verify_artifacts)


@contextmanager
def task_lock(workspace: TaskWorkspace) -> Iterator[None]:
    """Exclusive process lock; POSIX kernels release it automatically after crashes."""
    lock_path = workspace.path / ".resume.lock"
    if os.name != "nt":
        import fcntl

        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise TaskWorkspaceError("TASK_LOCK_FILE_UNAVAILABLE") from exc
        try:
            if lock_path.is_symlink():
                raise TaskWorkspaceError("TASK_LOCK_FILE_MUST_NOT_BE_SYMLINK")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise TaskWorkspaceError("TASK_ALREADY_OPEN_IN_ANOTHER_PROCESS") from exc
            with os.fdopen(fd, "r+", encoding="utf-8") as stream:
                stream.seek(0)
                stream.truncate()
                stream.write(json.dumps({"pid": os.getpid(), "created_at": _now()}))
                stream.flush()
                os.fsync(stream.fileno())
                yield
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
        return

    # Windows fallback: exclusive-create lock. A process crash can leave a
    # stale marker, so recovery remains fail-closed rather than guessing.
    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise TaskWorkspaceError("TASK_ALREADY_OPEN_OR_STALE_LOCK_REQUIRES_REVIEW") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "created_at": _now()}))
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
