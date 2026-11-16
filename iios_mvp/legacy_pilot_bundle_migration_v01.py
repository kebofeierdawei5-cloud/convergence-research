from __future__ import annotations

"""Safe, non-destructive migration snapshots for pre-manifest local pilot runs.

A migration snapshot proves only the bytes copied at migration time. It never
retroactively proves that a legacy run was unchanged since its original run.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any, Mapping

PILOT_RECEIPT_SCHEMA = "IIOS-LOCAL-PILOT-RUN-RECORD-0.1"
PILOT_STATUS = "PILOT_NON_CANONICAL"
SNAPSHOT_SCHEMA = "IIOS-LEGACY-LOCAL-PILOT-MIGRATION-SNAPSHOT-0.1"
REQUIRED_FILES = ("input.json", "analysis.json", "report.md", "pilot_receipt.json")
OPTIONAL_FILES = ("chatgpt_response_raw.txt",)
SNAPSHOT_MANIFEST = "migration_manifest.json"


class LegacyPilotMigrationError(ValueError):
    """A legacy bundle cannot be safely classified or snapshotted."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _outside_repository(path: str | Path, field: str, *, must_exist: bool) -> Path:
    raw = Path(path).expanduser()
    if raw.is_symlink():
        raise LegacyPilotMigrationError(f"{field}_MUST_NOT_BE_SYMLINK")
    try:
        resolved = raw.resolve(strict=must_exist)
    except OSError as exc:
        raise LegacyPilotMigrationError(f"{field}_PATH_UNAVAILABLE") from exc
    try:
        resolved.relative_to(_repo_root())
    except ValueError:
        return resolved
    raise LegacyPilotMigrationError(f"{field}_MUST_BE_OUTSIDE_REPOSITORY")


def _read_regular_file(path: Path, field: str) -> bytes:
    """Read one regular file without following a symlink and detect concurrent writes."""
    if path.is_symlink():
        raise LegacyPilotMigrationError(f"{field}_MUST_NOT_BE_SYMLINK")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise LegacyPilotMigrationError(f"{field}_UNREADABLE") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise LegacyPilotMigrationError(f"{field}_MUST_BE_REGULAR_FILE")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        stable_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        stable_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        payload = b"".join(chunks)
        if stable_before != stable_after or len(payload) != before.st_size:
            raise LegacyPilotMigrationError(f"{field}_CHANGED_WHILE_READING")
        return payload
    finally:
        os.close(descriptor)


def _json_object(payload: bytes, field: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LegacyPilotMigrationError(f"{field}_JSON_UNREADABLE") from exc
    if not isinstance(value, dict):
        raise LegacyPilotMigrationError(f"{field}_MUST_BE_JSON_OBJECT")
    return value


def _fingerprint(payload: bytes) -> dict[str, Any]:
    return {"sha256": hashlib.sha256(payload).hexdigest(), "byte_size": len(payload)}


def _private_directory(path: Path, field: str) -> None:
    if path.is_symlink():
        raise LegacyPilotMigrationError(f"{field}_MUST_NOT_BE_SYMLINK")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise LegacyPilotMigrationError(f"{field}_MUST_BE_DIRECTORY")
    if os.name != "nt":
        path.chmod(0o700)
        if path.stat().st_mode & 0o077:
            raise LegacyPilotMigrationError(f"{field}_PERMISSIONS_NOT_PRIVATE")


def classify_legacy_pilot_bundle(run_path: str | Path) -> dict[str, Any]:
    """Classify a run as legacy-unverifiable or manifest-bearing; never returns PASS."""
    run_dir = _outside_repository(run_path, "LEGACY_RUN_DIRECTORY", must_exist=True)
    if not run_dir.is_dir():
        raise LegacyPilotMigrationError("LEGACY_RUN_DIRECTORY_REQUIRED")

    receipt_bytes = _read_regular_file(run_dir / "pilot_receipt.json", "LEGACY_RECEIPT")
    receipt = _json_object(receipt_bytes, "LEGACY_RECEIPT")
    if receipt.get("receipt_schema") != PILOT_RECEIPT_SCHEMA:
        raise LegacyPilotMigrationError("LEGACY_RECEIPT_SCHEMA_MISMATCH")
    if receipt.get("status") != PILOT_STATUS:
        raise LegacyPilotMigrationError("LEGACY_RECEIPT_NOT_PILOT_NON_CANONICAL")
    if receipt.get("pilot_id") != run_dir.name:
        raise LegacyPilotMigrationError("LEGACY_RECEIPT_PILOT_ID_MISMATCH")

    files: dict[str, bytes] = {}
    for name in REQUIRED_FILES:
        files[name] = _read_regular_file(run_dir / name, f"LEGACY_FILE_{name}")
    if not files["report.md"].strip():
        raise LegacyPilotMigrationError("LEGACY_REPORT_EMPTY")
    input_payload = _json_object(files["input.json"], "LEGACY_INPUT")
    analysis_payload = _json_object(files["analysis.json"], "LEGACY_ANALYSIS")

    for field, expected in (
        ("input_file", "input.json"),
        ("analysis_file", "analysis.json"),
        ("report_file", "report.md"),
    ):
        if field in receipt and receipt[field] != expected:
            raise LegacyPilotMigrationError(f"LEGACY_RECEIPT_FILENAME_MISMATCH:{field}")

    if "file_manifest" in receipt:
        manifest = receipt.get("file_manifest")
        if not isinstance(manifest, Mapping):
            raise LegacyPilotMigrationError("LEGACY_MANIFEST_FIELD_PRESENT_BUT_INVALID")
        return {
            "classification": "MANIFEST_PRESENT_REQUIRES_STRICT_VERIFICATION",
            "pilot_id": run_dir.name,
            "historical_hash_verification": "NOT_EVALUATED",
            "research_rounds_status": (
                "PRESENT_BUT_UNVERIFIED"
                if receipt.get("research_rounds") is not None or analysis_payload.get("research_rounds") is not None
                else "NOT_CAPTURED_OR_UNKNOWN"
            ),
            "files": list(REQUIRED_FILES),
        }

    optional_present: list[str] = []
    for name in OPTIONAL_FILES:
        candidate = run_dir / name
        if candidate.exists() or candidate.is_symlink():
            _read_regular_file(candidate, f"LEGACY_FILE_{name}")
            optional_present.append(name)

    rounds_present = (
        receipt.get("research_rounds") is not None
        or analysis_payload.get("research_rounds") is not None
        or input_payload.get("_local_research_round_a_provenance") is not None
    )
    return {
        "classification": "LEGACY_UNVERIFIABLE",
        "reason": "HISTORICAL_HASH_MANIFEST_NOT_RECORDED",
        "pilot_id": run_dir.name,
        "historical_hash_verification": "UNVERIFIABLE_NO_ORIGINAL_FILE_MANIFEST",
        "migration_snapshot_integrity": "NOT_YET_CREATED",
        "research_rounds_status": "PRESENT_BUT_UNVERIFIED" if rounds_present else "NOT_CAPTURED_OR_UNKNOWN",
        "files": [*REQUIRED_FILES, *optional_present],
    }


def verify_legacy_pilot_migration_snapshot(snapshot_path: str | Path) -> dict[str, Any]:
    """Verify a migration-time snapshot against its separate, immutable manifest."""
    snapshot_dir = _outside_repository(snapshot_path, "MIGRATION_SNAPSHOT_DIRECTORY", must_exist=True)
    if not snapshot_dir.is_dir():
        raise LegacyPilotMigrationError("MIGRATION_SNAPSHOT_DIRECTORY_REQUIRED")
    manifest_bytes = _read_regular_file(snapshot_dir / SNAPSHOT_MANIFEST, "MIGRATION_MANIFEST")
    manifest = _json_object(manifest_bytes, "MIGRATION_MANIFEST")
    if manifest.get("schema_version") != SNAPSHOT_SCHEMA:
        raise LegacyPilotMigrationError("MIGRATION_MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("snapshot_integrity") != "VERIFIED_AT_MIGRATION_TIME":
        raise LegacyPilotMigrationError("MIGRATION_SNAPSHOT_STATUS_INVALID")
    file_manifest = manifest.get("files")
    if not isinstance(file_manifest, Mapping) or not set(REQUIRED_FILES).issubset(file_manifest):
        raise LegacyPilotMigrationError("MIGRATION_SNAPSHOT_FILE_MANIFEST_INVALID")
    allowed = set(REQUIRED_FILES) | set(OPTIONAL_FILES)
    if set(file_manifest) - allowed:
        raise LegacyPilotMigrationError("MIGRATION_SNAPSHOT_UNEXPECTED_FILE_ENTRY")

    verified: list[dict[str, Any]] = []
    for name, expected in file_manifest.items():
        if not isinstance(expected, Mapping):
            raise LegacyPilotMigrationError(f"MIGRATION_SNAPSHOT_FILE_RECORD_INVALID:{name}")
        payload = _read_regular_file(snapshot_dir / name, f"MIGRATION_SNAPSHOT_FILE_{name}")
        actual = _fingerprint(payload)
        if actual != {"sha256": expected.get("sha256"), "byte_size": expected.get("byte_size")}:
            raise LegacyPilotMigrationError(f"MIGRATION_SNAPSHOT_HASH_MISMATCH:{name}")
        verified.append({"name": name, **actual})

    receipt_fp = file_manifest.get("pilot_receipt.json")
    if not isinstance(receipt_fp, Mapping) or manifest.get("source_receipt_sha256") != receipt_fp.get("sha256"):
        raise LegacyPilotMigrationError("MIGRATION_SOURCE_RECEIPT_BINDING_MISMATCH")
    return {
        "status": "LEGACY_MIGRATION_SNAPSHOT_HASH_CHECK_PASS",
        "pilot_id": manifest.get("source_pilot_id"),
        "snapshot_id": snapshot_dir.name,
        "historical_hash_verification": manifest.get("historical_hash_verification"),
        "snapshot_integrity": manifest.get("snapshot_integrity"),
        "verified_files": verified,
    }


def create_legacy_pilot_migration_snapshot(
    run_path: str | Path,
    archive_root: str | Path,
) -> dict[str, Any]:
    """Copy legacy bundle bytes to a no-clobber private snapshot and hash at migration time."""
    classification = classify_legacy_pilot_bundle(run_path)
    if classification["classification"] != "LEGACY_UNVERIFIABLE":
        raise LegacyPilotMigrationError("MIGRATION_ALLOWED_ONLY_FOR_MANIFESTLESS_LEGACY_RUN")

    run_dir = _outside_repository(run_path, "LEGACY_RUN_DIRECTORY", must_exist=True)
    archive_dir = _outside_repository(archive_root, "MIGRATION_ARCHIVE_ROOT", must_exist=False)
    _private_directory(archive_dir, "MIGRATION_ARCHIVE_ROOT")

    names = list(classification["files"])
    payloads = {
        name: _read_regular_file(run_dir / name, f"LEGACY_FILE_{name}")
        for name in names
    }
    receipt = _json_object(payloads["pilot_receipt.json"], "LEGACY_RECEIPT")
    if "file_manifest" in receipt:
        raise LegacyPilotMigrationError("LEGACY_RECEIPT_FORMAT_CHANGED_DURING_MIGRATION")

    fingerprints = {name: _fingerprint(payload) for name, payload in payloads.items()}
    source_receipt_sha = fingerprints["pilot_receipt.json"]["sha256"]
    snapshot_id = f"{run_dir.name}__{source_receipt_sha[:12]}"
    target = archive_dir / snapshot_id

    if target.exists() or target.is_symlink():
        existing = verify_legacy_pilot_migration_snapshot(target)
        if (
            existing.get("pilot_id") != run_dir.name
            or not (target / SNAPSHOT_MANIFEST).is_file()
            or _json_object((target / SNAPSHOT_MANIFEST).read_bytes(), "MIGRATION_MANIFEST").get("source_receipt_sha256")
            != source_receipt_sha
        ):
            raise LegacyPilotMigrationError("MIGRATION_SNAPSHOT_TARGET_CONFLICT")
        return {
            **existing,
            "status": "LEGACY_MIGRATION_SNAPSHOT_REUSED",
            "snapshot_path": str(target),
            "reused": True,
        }

    staging = Path(tempfile.mkdtemp(prefix=".legacy-migration-", dir=archive_dir))
    if os.name != "nt":
        staging.chmod(0o700)
    try:
        for name, payload in payloads.items():
            destination = staging / name
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = os.open(destination, flags, 0o600)
            try:
                view = memoryview(payload)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise LegacyPilotMigrationError(f"MIGRATION_SNAPSHOT_WRITE_FAILED:{name}")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            if _fingerprint(payload) != _fingerprint(_read_regular_file(destination, f"SNAPSHOT_FILE_{name}")):
                raise LegacyPilotMigrationError(f"MIGRATION_SNAPSHOT_COPY_MISMATCH:{name}")

        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        manifest = {
            "schema_version": SNAPSHOT_SCHEMA,
            "snapshot_id": snapshot_id,
            "source_pilot_id": run_dir.name,
            "created_at_utc": created_at,
            "historical_hash_verification": "UNVERIFIABLE_NO_ORIGINAL_FILE_MANIFEST",
            "snapshot_integrity": "VERIFIED_AT_MIGRATION_TIME",
            "snapshot_hash_algorithm": "SHA-256",
            "source_receipt_sha256": source_receipt_sha,
            "research_rounds_status": classification["research_rounds_status"],
            "files": fingerprints,
            "note": (
                "These hashes were calculated from the copied bytes at migration time. "
                "They do not prove the original run bundle was unchanged since its original creation."
            ),
        }
        manifest_payload = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        manifest_path = staging / SNAPSHOT_MANIFEST
        descriptor = os.open(
            manifest_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            os.write(descriptor, manifest_payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if os.name != "nt":
            staging.chmod(0o700)
        try:
            os.rename(staging, target)
        except OSError:
            if target.exists() or target.is_symlink():
                raise LegacyPilotMigrationError("MIGRATION_SNAPSHOT_TARGET_CONFLICT")
            raise
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise

    verified = verify_legacy_pilot_migration_snapshot(target)
    return {
        **verified,
        "status": "LEGACY_MIGRATION_SNAPSHOT_CREATED",
        "snapshot_path": str(target),
        "reused": False,
    }
