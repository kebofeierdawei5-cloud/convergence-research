from __future__ import annotations

"""Persist the real 605016 B2/PIT candidate in a local private data root.

This tool never writes market data into the public repository. It first runs
the established official-HTTPS adjudicator in a temporary workspace, then
revalidates the exact candidate with the Investment Core-owned validator.
Only raw files referenced by the passing manifest are copied to the private
vault. The resulting record is a durable candidate, not proof of production
Host acceptance or a cryptographically signed admission.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

REPOSITORY_FULL_NAME = "kebofeierdawei5-cloud/convergence-research"
ATTEMPT10_RUN_ID = "38026139364"
ATTEMPT10_ARTIFACT_NAME = "iios-company-evidence-38026139364"
CASE_ID = "RC-CN-A-605016-20261009"
CUTOFF_DATE = "2026-10-09"
PRICE_EVIDENCE_ID = "605016-SSE-HTTPS-DAILY-CLOSE-20261008"
EXPECTED_PRICE_RAW_SHA256 = "45c8eece737c57ec11deb34ad099dcc8f9f88f9c5e080be53992d2ec707b3480"
RECEIPT_SCHEMA = "IIOS-LOCAL-PRIVATE-B2-PERSISTENCE-0.1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ATTEMPT10_FILES = (
    "intake_manifest.json",
    "COMPANY_EVIDENCE_INTAKE_RECEIPT.json",
    "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json",
)


class PrivateIngestError(ValueError):
    """Raised when source verification or private persistence cannot be trusted."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrivateIngestError(f"{label}_UNREADABLE") from exc
    if not isinstance(value, dict):
        raise PrivateIngestError(f"{label}_MUST_BE_OBJECT")
    return value


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _preflight_private_root(root: str | Path, *, repository_root: str | Path) -> Path:
    supplied = Path(root).expanduser()
    if supplied.is_symlink():
        raise PrivateIngestError("PRIVATE_ROOT_MUST_NOT_BE_SYMLINK")
    repository = Path(repository_root).resolve(strict=True)
    resolved = supplied.resolve(strict=False)
    if resolved == repository or _is_under(resolved, repository):
        raise PrivateIngestError("PRIVATE_ROOT_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY")
    if resolved == Path(resolved.anchor):
        raise PrivateIngestError("PRIVATE_ROOT_CANNOT_BE_FILESYSTEM_ROOT")
    if supplied.exists() and not supplied.is_dir():
        raise PrivateIngestError("PRIVATE_ROOT_MUST_BE_DIRECTORY")
    if supplied.exists() and hasattr(os, "getuid"):
        if supplied.stat().st_uid != os.getuid():
            raise PrivateIngestError("PRIVATE_ROOT_MUST_BE_OWNED_BY_CURRENT_USER")
    return resolved


def _make_private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise PrivateIngestError("PRIVATE_DIRECTORY_TYPE_UNSAFE")
    if hasattr(os, "getuid") and path.stat().st_uid != os.getuid():
        raise PrivateIngestError("PRIVATE_DIRECTORY_OWNER_MISMATCH")
    os.chmod(path, 0o700)
    if os.name != "nt" and (path.stat().st_mode & 0o077):
        raise PrivateIngestError("PRIVATE_DIRECTORY_PERMISSIONS_TOO_OPEN")


def _preflight_attempt10(root: str | Path) -> Path:
    base = Path(root).resolve(strict=True)
    if not base.is_dir():
        raise PrivateIngestError("ATTEMPT10_ROOT_MUST_BE_DIRECTORY")
    for name in REQUIRED_ATTEMPT10_FILES:
        path = base / name
        if not path.is_file() or path.is_symlink():
            raise PrivateIngestError("ATTEMPT10_REQUIRED_FILE_MISSING:" + name)
        try:
            path.resolve(strict=True).relative_to(base)
        except ValueError as exc:
            raise PrivateIngestError("ATTEMPT10_PATH_ESCAPE") from exc

    intake = _read_object(base / "intake_manifest.json", "ATTEMPT10_INTAKE")
    receipt = _read_object(base / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json", "ATTEMPT10_RECEIPT")
    verification = _read_object(base / "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json", "ATTEMPT10_VERIFICATION")
    if intake.get("case_id") != CASE_ID:
        raise PrivateIngestError("ATTEMPT10_CASE_ID_MISMATCH")
    if str(intake.get("symbol")) != "605016" or intake.get("cutoff_date") != CUTOFF_DATE:
        raise PrivateIngestError("ATTEMPT10_SECURITY_OR_CUTOFF_MISMATCH")
    sources = intake.get("sources")
    receipt_sources = receipt.get("sources")
    if not isinstance(sources, list) or len(sources) != 12:
        raise PrivateIngestError("ATTEMPT10_SOURCE_COUNT_MISMATCH")
    if not isinstance(receipt_sources, list) or len(receipt_sources) != 12:
        raise PrivateIngestError("ATTEMPT10_RECEIPT_SOURCE_COUNT_MISMATCH")
    if receipt.get("status") != "CAPTURED_NOT_ADMITTED":
        raise PrivateIngestError("ATTEMPT10_CAPTURE_RECEIPT_STATUS_UNEXPECTED")
    if verification.get("raw_bytes_verified") != 12 or verification.get("payload_contract_mismatches") != 0:
        raise PrivateIngestError("ATTEMPT10_INDEPENDENT_VERIFICATION_NOT_PASS")
    return base


def _download_attempt10(destination: Path) -> Path:
    gh = shutil.which("gh")
    if not gh:
        raise PrivateIngestError("GITHUB_CLI_REQUIRED_INSTALL_GH_AND_AUTHENTICATE")
    auth = subprocess.run(
        [gh, "auth", "status", "--hostname", "github.com"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if auth.returncode != 0:
        raise PrivateIngestError("GITHUB_CLI_AUTH_REQUIRED_RUN_GH_AUTH_LOGIN")
    _make_private_directory(destination)
    command = [
        gh, "run", "download", ATTEMPT10_RUN_ID,
        "--repo", REPOSITORY_FULL_NAME,
        "--name", ATTEMPT10_ARTIFACT_NAME,
        "--dir", str(destination),
    ]
    result = subprocess.run(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    if result.returncode != 0:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_FAILED_CHECK_GITHUB_ACTIONS_ACCESS")
    candidates = list(destination.rglob("intake_manifest.json"))
    if len(candidates) != 1:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_LAYOUT_AMBIGUOUS")
    return _preflight_attempt10(candidates[0].parent)


def _candidate_fingerprint(manifest: Mapping[str, Any]) -> str:
    """Stable content identity that does not change solely with retrieval time."""
    evidence_projection = []
    for item in manifest.get("evidence", []):
        if not isinstance(item, Mapping):
            raise PrivateIngestError("EVIDENCE_RECORD_INVALID_FOR_FINGERPRINT")
        evidence_projection.append({
            key: item.get(key)
            for key in (
                "evidence_id", "subject_id", "field_id", "claim_type", "value",
                "unit", "basis", "observation_date", "known_at", "known_at_basis",
                "published_at", "source_ref", "artifact_id", "content_sha256",
                "exact_bytes", "provenance_class", "status", "license_status",
                "source_origin_adjudication",
            )
        })
    evidence_projection.sort(key=lambda item: str(item["evidence_id"]))
    raw_projection = []
    for item in manifest.get("raw_artifacts", []):
        if not isinstance(item, Mapping):
            raise PrivateIngestError("RAW_ARTIFACT_DECLARATION_INVALID")
        raw_projection.append({
            "evidence_id": item.get("evidence_id"),
            "expected_size_bytes": item.get("expected_size_bytes"),
            "expected_sha256": item.get("expected_sha256"),
            "relative_path": item.get("relative_path"),
        })
    raw_projection.sort(key=lambda item: str(item["evidence_id"]))
    stable = {
        "case_id": manifest.get("case_id"),
        "cutoff_date": manifest.get("cutoff_date"),
        "schema_version": manifest.get("schema_version"),
        "required_field_groups": manifest.get("required_field_groups"),
        "evidence": evidence_projection,
        "raw_artifacts": raw_projection,
    }
    return _sha256(_canonical_bytes(stable))


def _price_record_preflight(
    manifest: Mapping[str, Any], ephemeral_report: Mapping[str, Any]
) -> dict[str, Any]:
    source = ephemeral_report.get("official_price_source")
    if not isinstance(source, Mapping):
        raise PrivateIngestError("OFFICIAL_PRICE_SOURCE_REPORT_MISSING")
    if source.get("transport") != "HTTPS_TLS_VERIFIED":
        raise PrivateIngestError("OFFICIAL_PRICE_TRANSPORT_NOT_VERIFIED")
    if source.get("raw_sha256") != EXPECTED_PRICE_RAW_SHA256:
        raise PrivateIngestError("OFFICIAL_PRICE_RAW_HASH_MISMATCH")
    if source.get("observation_date") != "2026-10-08":
        raise PrivateIngestError("OFFICIAL_PRICE_OBSERVATION_DATE_MISMATCH")
    if source.get("numeric_quote_value_in_report") is not False:
        raise PrivateIngestError("NUMERIC_QUOTE_VALUE_MUST_NOT_BE_EXPOSED_IN_REPORT")

    matches = [
        item for item in manifest.get("evidence", [])
        if isinstance(item, Mapping) and item.get("evidence_id") == PRICE_EVIDENCE_ID
    ]
    if len(matches) != 1:
        raise PrivateIngestError("OFFICIAL_PRICE_EVIDENCE_RECORD_MISSING_OR_DUPLICATED")
    price = matches[0]
    if (
        price.get("field_id") != "market_price.close"
        or price.get("observation_date") != "2026-10-08"
        or price.get("content_sha256") != EXPECTED_PRICE_RAW_SHA256
        or price.get("status") != "ADMITTED"
        or price.get("provenance_class") != "SOURCE_VINTAGE_VERIFIED"
    ):
        raise PrivateIngestError("OFFICIAL_PRICE_EVIDENCE_BINDING_MISMATCH")
    if str(price.get("known_at_basis", "")).find("MARKET_SESSION_CLOSE_EVENT_TIME") < 0:
        raise PrivateIngestError("OFFICIAL_PRICE_KNOWN_AT_BASIS_MISSING")
    parsed = urlparse(str(price.get("source_ref") or ""))
    if parsed.scheme != "https" or parsed.hostname != "yunhq.sse.com.cn":
        raise PrivateIngestError("OFFICIAL_PRICE_SOURCE_ORIGIN_MISMATCH")
    return price


def _safe_relative_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise PrivateIngestError("RAW_ARTIFACT_RELATIVE_PATH_REQUIRED")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise PrivateIngestError("RAW_ARTIFACT_RELATIVE_PATH_UNSAFE")
    if path.parts[0] != "raw":
        raise PrivateIngestError("RAW_ARTIFACT_PATH_MUST_BE_UNDER_RAW")
    return path


def _copy_exact_artifacts(
    *, source_root: Path, destination_root: Path, declarations: list[Any]
) -> int:
    source_base = source_root.resolve(strict=True)
    _make_private_directory(destination_root)
    seen: set[str] = set()
    copied = 0
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise PrivateIngestError("RAW_ARTIFACT_DECLARATION_INVALID")
        relative = _safe_relative_path(declaration.get("relative_path"))
        relative_key = relative.as_posix()
        if relative_key in seen:
            raise PrivateIngestError("RAW_ARTIFACT_PATH_DUPLICATED")
        seen.add(relative_key)
        source = (source_base / Path(*relative.parts)).resolve(strict=True)
        try:
            source.relative_to(source_base)
        except ValueError as exc:
            raise PrivateIngestError("RAW_ARTIFACT_PATH_ESCAPE") from exc
        if not source.is_file() or source.is_symlink():
            raise PrivateIngestError("RAW_ARTIFACT_SOURCE_NOT_REGULAR_FILE")
        raw = source.read_bytes()
        expected_size = declaration.get("expected_size_bytes")
        expected_hash = declaration.get("expected_sha256")
        if (
            not isinstance(expected_size, int)
            or len(raw) != expected_size
            or not isinstance(expected_hash, str)
            or _sha256(raw) != expected_hash
        ):
            raise PrivateIngestError("RAW_ARTIFACT_EXACT_BYTES_MISMATCH")
        target = destination_root.joinpath(*relative.parts)
        _make_private_directory(target.parent)
        try:
            with target.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(target, 0o600)
        except FileExistsError as exc:
            raise PrivateIngestError("RAW_ARTIFACT_WRITE_COLLISION") from exc
        copied += 1
    return copied


def _validate_core(
    manifest: Mapping[str, Any], raw_root: Path, validator: Callable[..., list[str]] | None
) -> list[str]:
    if validator is None:
        from iios_mvp.canonical_evidence_admission_v01 import validate_company_evidence_manifest
        validator = validate_company_evidence_manifest
    return list(validator(manifest, raw_root=raw_root, require_raw_verification=True))


def _validate_existing_candidate(
    candidate_dir: Path, *, validator: Callable[..., list[str]] | None
) -> dict[str, Any]:
    manifest_path = candidate_dir / "company_evidence_manifest.json"
    raw_root = candidate_dir / "evidence_root"
    manifest = _read_object(manifest_path, "EXISTING_PRIVATE_MANIFEST")
    errors = _validate_core(manifest, raw_root, validator)
    if errors:
        raise PrivateIngestError("EXISTING_PRIVATE_CANDIDATE_FAILED_CORE_REPLAY")
    receipt = _read_object(candidate_dir / "PRIVATE_B2_PERSISTENCE_RECEIPT.json", "EXISTING_PRIVATE_RECEIPT")
    expected_receipt_hash = receipt.get("receipt_sha256")
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if not isinstance(expected_receipt_hash, str) or _sha256(_canonical_bytes(core)) != expected_receipt_hash:
        raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_HASH_MISMATCH")
    if receipt.get("candidate_fingerprint") != _candidate_fingerprint(manifest):
        raise PrivateIngestError("EXISTING_PRIVATE_CANDIDATE_FINGERPRINT_MISMATCH")
    return {
        "manifest": manifest,
        "receipt": receipt,
        "manifest_sha256": _sha256(manifest_path.read_bytes()),
    }


def ingest_private_b2_candidate(
    *,
    private_root: str | Path,
    repository_root: str | Path = REPOSITORY_ROOT,
    attempt10_root: str | Path | None = None,
    adjudicator: Callable[[Path, Path], dict[str, Any]] | None = None,
    core_validator: Callable[..., list[str]] | None = None,
) -> dict[str, Any]:
    """Run unchanged B2 adjudication, repeat Core validation, and persist privately."""
    private_root_path = _preflight_private_root(private_root, repository_root=repository_root)

    with tempfile.TemporaryDirectory(prefix="iios-605016-private-ingest-work-") as work:
        work_root = Path(work)
        if attempt10_root is None:
            input_root = _download_attempt10(work_root / "attempt10")
        else:
            input_root = _preflight_attempt10(attempt10_root)

        adjudication_root = work_root / "official-https-b2"
        if adjudicator is None:
            if str(repository_root) not in sys.path:
                sys.path.insert(0, str(repository_root))
            from tools.route_a_605016_official_https_b2_adjudicate import adjudicate
            adjudicator = adjudicate
        ephemeral_report = adjudicator(input_root, adjudication_root)
        if not isinstance(ephemeral_report, Mapping):
            raise PrivateIngestError("EPHEMERAL_ADJUDICATION_REPORT_INVALID")
        if (
            ephemeral_report.get("overall") != "PASS_EPHEMERAL_B2"
            or ephemeral_report.get("core_b2", {}).get("candidate_manifest_status") != "PASS"
            or ephemeral_report.get("core_b2", {}).get("missing_required_field_groups") != []
        ):
            raise PrivateIngestError("EPHEMERAL_B2_DID_NOT_PASS")

        manifest_path = adjudication_root / "base-b2" / "COMBINED_B2_CANDIDATE_MANIFEST.json"
        raw_root = adjudication_root / "base-b2" / "combined-evidence-root"
        manifest = _read_object(manifest_path, "EPHEMERAL_B2_MANIFEST")
        if manifest.get("case_id") != CASE_ID or manifest.get("cutoff_date") != CUTOFF_DATE:
            raise PrivateIngestError("EPHEMERAL_B2_CASE_OR_CUTOFF_MISMATCH")
        if manifest.get("status") != "PASS":
            raise PrivateIngestError("EPHEMERAL_B2_MANIFEST_STATUS_NOT_PASS")
        if manifest.get("validation_errors") != []:
            raise PrivateIngestError("EPHEMERAL_B2_MANIFEST_HAS_ERRORS")
        if not isinstance(manifest.get("audit"), Mapping):
            raise PrivateIngestError("EPHEMERAL_B2_AUDIT_MISSING")
        price = _price_record_preflight(manifest, ephemeral_report)
        core_errors = _validate_core(manifest, raw_root, core_validator)
        if core_errors:
            raise PrivateIngestError("CORE_OWNED_B2_PIT_VALIDATOR_BLOCKED:" + ",".join(core_errors[:8]))

        fingerprint = _candidate_fingerprint(manifest)
        raw_declarations = manifest.get("raw_artifacts")
        if not isinstance(raw_declarations, list) or not raw_declarations:
            raise PrivateIngestError("PASSING_MANIFEST_RAW_ARTIFACTS_REQUIRED")

        # Do not create even the private root unless actual source material and
        # both validators have passed. The root is populated by immutable data.
        root_was_missing = not private_root_path.exists()
        _make_private_directory(private_root_path)
        cases_root = private_root_path / "cases"
        case_root = cases_root / CASE_ID
        _make_private_directory(cases_root)
        _make_private_directory(case_root)
        destination = case_root / fingerprint

        if destination.is_symlink():
            raise PrivateIngestError("EXISTING_PRIVATE_CANDIDATE_MUST_NOT_BE_SYMLINK")
        if destination.exists():
            existing = _validate_existing_candidate(destination, validator=core_validator)
            if _candidate_fingerprint(existing["manifest"]) != fingerprint:
                raise PrivateIngestError("IMMUTABLE_PRIVATE_CANDIDATE_CONFLICT")
            return {
                "status": "ALREADY_PERSISTED_CORE_VALIDATED_NOT_PRODUCTION_ACCEPTED",
                "case_id": CASE_ID,
                "cutoff_date": CUTOFF_DATE,
                "candidate_fingerprint": fingerprint,
                "manifest_sha256": existing["manifest_sha256"],
                "manifest_path": str(destination / "company_evidence_manifest.json"),
                "evidence_root": str(destination / "evidence_root"),
                "raw_artifact_count": len(raw_declarations),
                "evidence_record_count": len(manifest.get("evidence") or []),
                "core_validator_status": "PASS",
                "exact_first_public_timestamp_verified": False,
                "source_vintage_review_required": True,
                "formal_signed_admission_created": False,
                "production_host_accepted": False,
                "bundle_created": False,
                "decision_created": False,
                "human_approval_required": True,
                "auto_execution": False,
            }

        stage_root = Path(tempfile.mkdtemp(prefix=".iios-private-stage-", dir=private_root_path))
        os.chmod(stage_root, 0o700)
        payload_root = stage_root / "payload"
        payload_root.mkdir(mode=0o700)
        evidence_destination = payload_root / "evidence_root"
        try:
            copied_count = _copy_exact_artifacts(
                source_root=raw_root,
                destination_root=evidence_destination,
                declarations=raw_declarations,
            )
            manifest_out = payload_root / "company_evidence_manifest.json"
            with manifest_out.open("xb") as handle:
                handle.write(manifest_path.read_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(manifest_out, 0o600)
            copied_manifest = _read_object(manifest_out, "PERSISTED_B2_MANIFEST")
            persisted_errors = _validate_core(copied_manifest, evidence_destination, core_validator)
            if persisted_errors:
                raise PrivateIngestError("PERSISTED_CORE_VALIDATOR_BLOCKED:" + ",".join(persisted_errors[:8]))
            if copied_count != len(raw_declarations):
                raise PrivateIngestError("PERSISTED_RAW_ARTIFACT_COUNT_MISMATCH")

            receipt_core = {
                "schema_version": RECEIPT_SCHEMA,
                "status": "PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
                "case_id": CASE_ID,
                "cutoff_date": CUTOFF_DATE,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "candidate_fingerprint": fingerprint,
                "manifest_sha256": _sha256(manifest_out.read_bytes()),
                "manifest_audit_sha256": manifest["audit"]["manifest_sha256"],
                "official_price_source_sha256": EXPECTED_PRICE_RAW_SHA256,
                "official_price_observation_date": "2026-10-08",
                "official_price_known_at": price.get("known_at"),
                "official_price_known_at_basis": "MARKET_SESSION_CLOSE_EVENT_TIME; the endpoint does not disclose the exact first-public timestamp for the historical row.",
                "exact_first_public_timestamp_verified": False,
                "source_vintage_review_required": True,
                "evidence_record_count": len(manifest.get("evidence") or []),
                "raw_artifact_count": copied_count,
                "admitted_field_group_count": len(REQUIRED_FIELD_GROUPS_FOR_REPORT),
                "missing_required_field_group_count": 0,
                "core_validator": "iios_mvp.canonical_evidence_admission_v01.validate_company_evidence_manifest",
                "core_validator_status": "PASS",
                "storage_scope": "LOCAL_PRIVATE_INTERNAL_USE_ONLY",
                "source_reuse_disposition": "RESTRICTED_NO_REDISTRIBUTION; private internal research use only",
                "receipt_is_cryptographically_signed": False,
                "formal_signed_admission_created": False,
                "production_host_accepted": False,
                "bundle_created": False,
                "decision_created": False,
                "human_approval_required": True,
                "auto_execution": False,
            }
            receipt = dict(receipt_core)
            receipt["receipt_sha256"] = _sha256(_canonical_bytes(receipt_core))
            receipt_out = payload_root / "PRIVATE_B2_PERSISTENCE_RECEIPT.json"
            with receipt_out.open("xb") as handle:
                handle.write((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(receipt_out, 0o600)

            # Re-read and validate the self-contained payload before atomic promotion.
            _validate_existing_candidate(payload_root, validator=core_validator)
            os.replace(payload_root, destination)
            shutil.rmtree(stage_root, ignore_errors=True)
        except Exception:
            shutil.rmtree(stage_root, ignore_errors=True)
            if root_was_missing:
                try:
                    case_root.rmdir()
                    cases_root.rmdir()
                    private_root_path.rmdir()
                except OSError:
                    pass
            raise

        final_manifest = destination / "company_evidence_manifest.json"
        return {
            "status": "PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
            "case_id": CASE_ID,
            "cutoff_date": CUTOFF_DATE,
            "candidate_fingerprint": fingerprint,
            "manifest_sha256": _sha256(final_manifest.read_bytes()),
            "manifest_path": str(final_manifest),
            "evidence_root": str(destination / "evidence_root"),
            "receipt_path": str(destination / "PRIVATE_B2_PERSISTENCE_RECEIPT.json"),
            "raw_artifact_count": copied_count,
            "evidence_record_count": len(manifest.get("evidence") or []),
            "core_validator_status": "PASS",
            "exact_first_public_timestamp_verified": False,
            "source_vintage_review_required": True,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "bundle_created": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }


# Keep this display count contract-owned; never print evidence values or raw content.
REQUIRED_FIELD_GROUPS_FOR_REPORT = (
    "security_identity",
    "market_price",
    "corporate_disclosures",
    "business_reality",
    "financial_reality",
    "capital_structure",
    "trust_governance_events",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Persist a verified 605016 B2 candidate in a local private data root."
    )
    default_root = Path.home() / "Library" / "Application Support" / "IIOS" / "private-data"
    parser.add_argument("--private-root", type=Path, default=default_root)
    parser.add_argument(
        "--attempt10-root",
        type=Path,
        default=None,
        help="Optional already-downloaded genuine Attempt 10 artifact directory; normally omitted.",
    )
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args()
    try:
        result = ingest_private_b2_candidate(
            private_root=args.private_root,
            repository_root=args.repository_root,
            attempt10_root=args.attempt10_root,
        )
    except PrivateIngestError as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "reason": str(exc),
            "private_store_written": False,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "bundle_created": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }, ensure_ascii=False, indent=2))
        return 2
    except (OSError, subprocess.SubprocessError) as exc:
        # Do not print exception strings: they may disclose local paths or command output.
        print(json.dumps({
            "status": "BLOCKED",
            "reason": "LOCAL_IO_OR_SUBPROCESS_FAILURE",
            "error_type": type(exc).__name__,
            "private_store_written": False,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "bundle_created": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
