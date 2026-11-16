from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from iios_mvp.legacy_pilot_bundle_migration_v01 import (
    LegacyPilotMigrationError,
    classify_legacy_pilot_bundle,
    create_legacy_pilot_migration_snapshot,
    verify_legacy_pilot_migration_snapshot,
)


def _write_json(path: Path, payload: object) -> bytes:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(encoded)
    if os.name != "nt":
        path.chmod(0o600)
    return encoded


def _legacy_bundle(tmp_path: Path, *, pilot_id: str = "local-pilot-LEGACY-20261012T141631Z") -> Path:
    run_dir = tmp_path / pilot_id
    run_dir.mkdir(mode=0o700)
    if os.name != "nt":
        run_dir.chmod(0o700)
    _write_json(run_dir / "input.json", {"schema_version": "legacy-input", "case": {"symbol": "002810.SZ"}})
    _write_json(run_dir / "analysis.json", {"schema_version": "legacy-analysis", "pilot_id": pilot_id})
    (run_dir / "report.md").write_text("# Legacy report\nHistorical content.\n", encoding="utf-8")
    if os.name != "nt":
        (run_dir / "report.md").chmod(0o600)
    _write_json(
        run_dir / "pilot_receipt.json",
        {
            "receipt_schema": "IIOS-LOCAL-PILOT-RUN-RECORD-0.1",
            "status": "PILOT_NON_CANONICAL",
            "pilot_id": pilot_id,
            "input_file": "input.json",
            "analysis_file": "analysis.json",
            "report_file": "report.md",
        },
    )
    return run_dir


def test_manifestless_receipt_is_classified_as_legacy_not_pass(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    result = classify_legacy_pilot_bundle(run_dir)

    assert result["classification"] == "LEGACY_UNVERIFIABLE"
    assert result["historical_hash_verification"] == "UNVERIFIABLE_NO_ORIGINAL_FILE_MANIFEST"
    assert result["migration_snapshot_integrity"] == "NOT_YET_CREATED"
    assert "PILOT_BUNDLE_HASH_CHECK_PASS" not in result.values()


def test_snapshot_hashes_exact_copied_bytes_and_leaves_source_unchanged(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    archive_root = tmp_path / "private" / "legacy-migrations"
    source_before = {
        name: (run_dir / name).read_bytes()
        for name in ("input.json", "analysis.json", "report.md", "pilot_receipt.json")
    }

    result = create_legacy_pilot_migration_snapshot(run_dir, archive_root)
    snapshot = Path(result["snapshot_path"])

    assert result["status"] == "LEGACY_MIGRATION_SNAPSHOT_CREATED"
    assert result["historical_hash_verification"] == "UNVERIFIABLE_NO_ORIGINAL_FILE_MANIFEST"
    assert result["snapshot_integrity"] == "VERIFIED_AT_MIGRATION_TIME"
    assert verify_legacy_pilot_migration_snapshot(snapshot)["status"] == "LEGACY_MIGRATION_SNAPSHOT_HASH_CHECK_PASS"
    assert (snapshot / "pilot_receipt.json").read_bytes() == source_before["pilot_receipt.json"]
    assert "file_manifest" not in json.loads((run_dir / "pilot_receipt.json").read_text(encoding="utf-8"))
    for name, original_bytes in source_before.items():
        assert (run_dir / name).read_bytes() == original_bytes
        assert (snapshot / name).read_bytes() == original_bytes
    if os.name != "nt":
        assert snapshot.stat().st_mode & 0o077 == 0
        for name in source_before:
            assert (snapshot / name).stat().st_mode & 0o077 == 0


def test_snapshot_creation_is_idempotent_and_never_overwrites(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    archive_root = tmp_path / "private" / "legacy-migrations"

    first = create_legacy_pilot_migration_snapshot(run_dir, archive_root)
    second = create_legacy_pilot_migration_snapshot(run_dir, archive_root)

    assert second["status"] == "LEGACY_MIGRATION_SNAPSHOT_REUSED"
    assert second["reused"] is True
    assert second["snapshot_path"] == first["snapshot_path"]


def test_manifest_key_present_but_null_is_not_downgraded_to_legacy(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    receipt_path = run_dir / "pilot_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["file_manifest"] = None
    _write_json(receipt_path, receipt)

    with pytest.raises(LegacyPilotMigrationError, match="LEGACY_MANIFEST_FIELD_PRESENT_BUT_INVALID"):
        classify_legacy_pilot_bundle(run_dir)


def test_manifest_bearing_run_is_not_eligible_for_legacy_migration(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    receipt_path = run_dir / "pilot_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["file_manifest"] = {}
    _write_json(receipt_path, receipt)

    classified = classify_legacy_pilot_bundle(run_dir)
    assert classified["classification"] == "MANIFEST_PRESENT_REQUIRES_STRICT_VERIFICATION"
    with pytest.raises(LegacyPilotMigrationError, match="MIGRATION_ALLOWED_ONLY_FOR_MANIFESTLESS_LEGACY_RUN"):
        create_legacy_pilot_migration_snapshot(run_dir, tmp_path / "archive")


def test_tampered_snapshot_is_blocked(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    result = create_legacy_pilot_migration_snapshot(run_dir, tmp_path / "archive")
    snapshot = Path(result["snapshot_path"])
    (snapshot / "analysis.json").write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(LegacyPilotMigrationError, match="MIGRATION_SNAPSHOT_HASH_MISMATCH:analysis.json"):
        verify_legacy_pilot_migration_snapshot(snapshot)


def test_symlinked_legacy_payload_is_blocked(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("POSIX symlink semantics are required for this security test")
    run_dir = _legacy_bundle(tmp_path)
    external = tmp_path / "outside-report.md"
    external.write_text("not the original report", encoding="utf-8")
    (run_dir / "report.md").unlink()
    (run_dir / "report.md").symlink_to(external)

    with pytest.raises(LegacyPilotMigrationError, match="LEGACY_FILE_report.md_MUST_NOT_BE_SYMLINK"):
        classify_legacy_pilot_bundle(run_dir)


def test_empty_legacy_report_is_not_snapshotted(tmp_path: Path) -> None:
    run_dir = _legacy_bundle(tmp_path)
    (run_dir / "report.md").write_bytes(b"")

    with pytest.raises(LegacyPilotMigrationError, match="LEGACY_REPORT_EMPTY"):
        create_legacy_pilot_migration_snapshot(run_dir, tmp_path / "archive")
