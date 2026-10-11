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
import stat
import subprocess
import sys
import tempfile
import zipfile
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

REPOSITORY_FULL_NAME = "kebofeierdawei5-cloud/convergence-research"
ATTEMPT10_RUN_ID = "38026139364"
ATTEMPT10_ARTIFACT_NAME = "iios-company-evidence-38026139364"
ATTEMPT10_ARTIFACT_ID = "11660285551"
ATTEMPT10_ARTIFACT_SIZE_BYTES = 8526921
ATTEMPT10_ARTIFACT_SHA256 = "19916fee166b45a04430e4d2bb3131be2f0beab3140df4820793099d7d413f5c"
GITHUB_API_VERSION = "2022-11-28"
MAX_ATTEMPT10_ARCHIVE_FILES = 2000
MAX_ATTEMPT10_UNPACKED_BYTES = 100 * 1024 * 1024
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


def _extract_verified_attempt10_archive(
    archive_path: Path,
    destination: Path,
    *,
    expected_sha256: str = ATTEMPT10_ARTIFACT_SHA256,
    expected_size_bytes: int = ATTEMPT10_ARTIFACT_SIZE_BYTES,
) -> Path:
    """Verify the pinned artifact ZIP before safely extracting regular files only."""
    if archive_path.is_symlink() or not archive_path.is_file():
        raise PrivateIngestError("ATTEMPT10_ARCHIVE_NOT_REGULAR_FILE")
    actual_size = archive_path.stat().st_size
    if actual_size != expected_size_bytes:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SIZE_MISMATCH")
    if _sha256(archive_path.read_bytes()) != expected_sha256:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SHA256_MISMATCH")

    _make_private_directory(destination)
    destination_resolved = destination.resolve(strict=True)
    seen: set[str] = set()
    total_unpacked = 0
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ATTEMPT10_ARCHIVE_FILES:
                raise PrivateIngestError("ATTEMPT10_ARCHIVE_FILE_COUNT_INVALID")
            for info in infos:
                raw_name = info.filename
                if not raw_name or "\\" in raw_name:
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_PATH_INVALID")
                name = raw_name[:-1] if info.is_dir() and raw_name.endswith("/") else raw_name
                path = PurePosixPath(name)
                if (
                    not name or path.is_absolute()
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or (path.parts and ":" in path.parts[0])
                ):
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_PATH_UNSAFE")
                normalized = path.as_posix() + ("/" if info.is_dir() else "")
                if normalized in seen:
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_DUPLICATE_PATH")
                seen.add(normalized)

                unix_mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(unix_mode)
                if stat.S_ISLNK(unix_mode) or (file_type not in {0, stat.S_IFREG, stat.S_IFDIR}):
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_SPECIAL_FILE_FORBIDDEN")
                if info.is_dir():
                    target = destination.joinpath(*path.parts)
                    try:
                        target.resolve(strict=False).relative_to(destination_resolved)
                    except ValueError as exc:
                        raise PrivateIngestError("ATTEMPT10_ARCHIVE_PATH_ESCAPE") from exc
                    _make_private_directory(target)
                    continue

                total_unpacked += info.file_size
                if info.file_size < 0 or total_unpacked > MAX_ATTEMPT10_UNPACKED_BYTES:
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_UNPACKED_SIZE_LIMIT")
                target = destination.joinpath(*path.parts)
                try:
                    target.resolve(strict=False).relative_to(destination_resolved)
                except ValueError as exc:
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_PATH_ESCAPE") from exc
                _make_private_directory(target.parent)
                try:
                    with archive.open(info, "r") as source, target.open("xb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                        output.flush()
                        os.fsync(output.fileno())
                    os.chmod(target, 0o600)
                except FileExistsError as exc:
                    raise PrivateIngestError("ATTEMPT10_ARCHIVE_DUPLICATE_PATH") from exc
    except zipfile.BadZipFile as exc:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_INVALID_ZIP") from exc

    candidates = list(destination.rglob("intake_manifest.json"))
    if len(candidates) != 1:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_LAYOUT_AMBIGUOUS")
    return _preflight_attempt10(candidates[0].parent)


class _NoRedirect(HTTPRedirectHandler):
    """Return the API's 302 so credentials are never forwarded to blob storage."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _HTTPSOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() != "https":
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_attempt10_archive_url(token: str) -> str:
    api_url = (
        f"https://api.github.com/repos/{REPOSITORY_FULL_NAME}/actions/"
        f"artifacts/{ATTEMPT10_ARTIFACT_ID}/zip"
    )
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "IIOS-private-B2-ingest",
        },
    )
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            raise PrivateIngestError("ATTEMPT10_ARTIFACT_REDIRECT_EXPECTED")
    except HTTPError as exc:
        if exc.code == 302:
            location = exc.headers.get("Location", "")
        elif exc.code in {401, 403}:
            raise PrivateIngestError(
                "GITHUB_ACTIONS_ARTIFACT_ACCESS_DENIED_CHECK_TOKEN_ACTIONS_READ"
            ) from None
        elif exc.code in {404, 410}:
            raise PrivateIngestError(
                "ATTEMPT10_ARTIFACT_MISSING_OR_EXPIRED_CHECK_CANONICAL_ARTIFACT"
            ) from None
        else:
            raise PrivateIngestError(
                f"ATTEMPT10_ARTIFACT_API_HTTP_{exc.code}"
            ) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED") from None
    parsed = urlparse(location)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_REDIRECT_INVALID")
    return location


def _download_attempt10(destination: Path) -> Path:
    gh = shutil.which("gh")
    if not gh:
        raise PrivateIngestError("GITHUB_CLI_REQUIRED_INSTALL_GH_AND_AUTHENTICATE")
    token_result = subprocess.run(
        [gh, "auth", "token", "--hostname", "github.com"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    token = token_result.stdout.strip() if token_result.returncode == 0 else ""
    if not token:
        raise PrivateIngestError("GITHUB_CLI_TOKEN_UNAVAILABLE_RUN_GH_AUTH_LOGIN")

    _make_private_directory(destination)
    archive_path = destination.parent / "attempt10-artifact.zip"
    try:
        location = _request_attempt10_archive_url(token)
        request = Request(location, headers={"User-Agent": "IIOS-private-B2-ingest"})
        opener = build_opener(_HTTPSOnlyRedirect())
        with opener.open(request, timeout=120) as response:
            if urlparse(response.geturl()).scheme.lower() != "https":
                raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_HTTPS_REQUIRED")
            with archive_path.open("xb") as archive_file:
                os.chmod(archive_path, 0o600)
                digest = hashlib.sha256()
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > ATTEMPT10_ARTIFACT_SIZE_BYTES:
                        raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SIZE_MISMATCH")
                    digest.update(chunk)
                    archive_file.write(chunk)
                archive_file.flush()
                os.fsync(archive_file.fileno())
        if total != ATTEMPT10_ARTIFACT_SIZE_BYTES:
            raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SIZE_MISMATCH")
        if digest.hexdigest() != ATTEMPT10_ARTIFACT_SHA256:
            raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SHA256_MISMATCH")
        return _extract_verified_attempt10_archive(archive_path, destination)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise PrivateIngestError(
                "GITHUB_ACTIONS_ARTIFACT_ACCESS_DENIED_CHECK_TOKEN_ACTIONS_READ"
            ) from None
        if exc.code in {404, 410}:
            raise PrivateIngestError(
                "ATTEMPT10_ARTIFACT_MISSING_OR_EXPIRED_CHECK_CANONICAL_ARTIFACT"
            ) from None
        raise PrivateIngestError(f"ATTEMPT10_ARTIFACT_DOWNLOAD_HTTP_{exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED") from None
    finally:
        try:
            archive_path.unlink(missing_ok=True)
        except OSError:
            pass


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



def _require_private_entry(path: Path, *, label: str) -> None:
    """Reject symlinks, unexpected file types, loose POSIX modes and owner drift."""
    if path.is_symlink():
        raise PrivateIngestError(label + "_MUST_NOT_BE_SYMLINK")
    if not path.exists():
        raise PrivateIngestError(label + "_MISSING")
    if not path.is_dir() and not path.is_file():
        raise PrivateIngestError(label + "_TYPE_UNSAFE")
    if hasattr(os, "getuid") and path.stat().st_uid != os.getuid():
        raise PrivateIngestError(label + "_OWNER_MISMATCH")
    if os.name != "nt" and (path.stat().st_mode & 0o077):
        kind = "DIRECTORY" if path.is_dir() else "FILE"
        raise PrivateIngestError(label + "_" + kind + "_PERMISSIONS_TOO_OPEN")


def _verify_private_tree_permissions(root: Path, *, label: str) -> None:
    """Walk without following symlinks and enforce private modes for every entry."""
    _require_private_entry(root, label=label)
    if not root.is_dir():
        raise PrivateIngestError(label + "_MUST_BE_DIRECTORY")
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in directories:
            _require_private_entry(current_path / name, label=label)
        for name in files:
            _require_private_entry(current_path / name, label=label)


def _verify_private_candidate_contents(candidate_dir: Path, *, validator: Callable[..., list[str]] | None) -> dict[str, Any]:
    """Check persisted metadata, privacy, exact file set and original Core/PIT validator."""
    _verify_private_tree_permissions(candidate_dir, label="PRIVATE_CANDIDATE")
    existing = _validate_existing_candidate(candidate_dir, validator=validator)
    manifest = existing["manifest"]
    receipt = existing["receipt"]

    if manifest.get("case_id") != CASE_ID:
        raise PrivateIngestError("EXISTING_PRIVATE_CASE_ID_MISMATCH")
    if manifest.get("cutoff_date") != CUTOFF_DATE:
        raise PrivateIngestError("EXISTING_PRIVATE_CUTOFF_MISMATCH")
    if str(manifest.get("market", "")).upper() != "CN-A" or str(manifest.get("symbol", "")) != "605016":
        raise PrivateIngestError("EXISTING_PRIVATE_SECURITY_IDENTITY_MISMATCH")
    if manifest.get("status") != "PASS" or manifest.get("validation_errors") != []:
        raise PrivateIngestError("EXISTING_PRIVATE_MANIFEST_STATUS_INVALID")
    if manifest.get("required_field_groups") != list(REQUIRED_FIELD_GROUPS_FOR_REPORT):
        raise PrivateIngestError("EXISTING_PRIVATE_REQUIRED_GROUPS_MISMATCH")

    fingerprint = _candidate_fingerprint(manifest)
    if candidate_dir.name != fingerprint:
        raise PrivateIngestError("EXISTING_PRIVATE_DIRECTORY_FINGERPRINT_MISMATCH")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_SCHEMA_MISMATCH")

    manifest_path = candidate_dir / "company_evidence_manifest.json"
    manifest_sha = _sha256(manifest_path.read_bytes())
    expected_receipt = {
        "status": "PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "candidate_fingerprint": fingerprint,
        "manifest_sha256": manifest_sha,
        "manifest_audit_sha256": (manifest.get("audit") or {}).get("manifest_sha256"),
        "official_price_source_sha256": EXPECTED_PRICE_RAW_SHA256,
        "official_price_observation_date": "2026-10-08",
        "exact_first_public_timestamp_verified": False,
        "source_vintage_review_required": True,
        "evidence_record_count": len(manifest.get("evidence") or []),
        "raw_artifact_count": len(manifest.get("raw_artifacts") or []),
        "admitted_field_group_count": len(REQUIRED_FIELD_GROUPS_FOR_REPORT),
        "missing_required_field_group_count": 0,
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
    for field, expected_value in expected_receipt.items():
        if receipt.get(field) != expected_value:
            raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_SEMANTICS_MISMATCH:" + field)
    if not isinstance(receipt.get("created_at"), str) or not receipt["created_at"].strip():
        raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_CREATED_AT_MISSING")

    raw_root = candidate_dir / "evidence_root"
    declarations = manifest.get("raw_artifacts")
    if not isinstance(declarations, list) or not declarations:
        raise PrivateIngestError("EXISTING_PRIVATE_RAW_DECLARATIONS_MISSING")
    expected_paths: set[str] = set()
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise PrivateIngestError("EXISTING_PRIVATE_RAW_DECLARATION_INVALID")
        relative = _safe_relative_path(declaration.get("relative_path")).as_posix()
        if relative in expected_paths:
            raise PrivateIngestError("EXISTING_PRIVATE_RAW_PATH_DUPLICATED")
        expected_paths.add(relative)
    actual_paths = {
        path.relative_to(raw_root).as_posix()
        for path in raw_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise PrivateIngestError("EXISTING_PRIVATE_RAW_FILE_SET_MISMATCH")

    return {
        "candidate_fingerprint": fingerprint,
        "manifest_sha256": manifest_sha,
        "raw_artifact_count": len(declarations),
        "evidence_record_count": len(manifest.get("evidence") or []),
        "core_validator_status": "PASS",
        "source_vintage_review_required": True,
        "exact_first_public_timestamp_verified": False,
        "formal_signed_admission_created": False,
        "production_host_accepted": False,
        "decision_created": False,
        "human_approval_required": True,
        "auto_execution": False,
    }


def verify_existing_private_b2_candidate(
    *,
    private_root: str | Path,
    repository_root: str | Path = REPOSITORY_ROOT,
    core_validator: Callable[..., list[str]] | None = None,
) -> dict[str, Any]:
    """Verify only the already-persisted private candidate; never fetch source data."""
    private_root_path = _preflight_private_root(private_root, repository_root=repository_root)
    if not private_root_path.exists():
        raise PrivateIngestError("PRIVATE_CASE_STORE_MISSING")
    _require_private_entry(private_root_path, label="PRIVATE_ROOT")
    cases_root = private_root_path / "cases"
    case_root = cases_root / CASE_ID
    _require_private_entry(cases_root, label="PRIVATE_CASES_ROOT")
    _require_private_entry(case_root, label="PRIVATE_CASE_ROOT")
    if not cases_root.is_dir() or not case_root.is_dir():
        raise PrivateIngestError("PRIVATE_CASE_STORE_LAYOUT_INVALID")

    candidate_dirs: list[Path] = []
    for entry in case_root.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            raise PrivateIngestError("PRIVATE_CASE_ENTRY_TYPE_UNSAFE")
        name = entry.name
        if len(name) != 64 or any(char not in "0123456789abcdef" for char in name):
            raise PrivateIngestError("PRIVATE_CANDIDATE_DIRECTORY_NAME_INVALID")
        candidate_dirs.append(entry)
    if not candidate_dirs:
        raise PrivateIngestError("PRIVATE_B2_CANDIDATE_NOT_FOUND")

    verified = [
        _verify_private_candidate_contents(candidate, validator=core_validator)
        for candidate in sorted(candidate_dirs, key=lambda item: item.name)
    ]
    return {
        "status": "VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "candidate_count": len(verified),
        "candidates": verified,
        "official_source_refetched": False,
        "source_vintage_review_required": True,
        "exact_first_public_timestamp_verified": False,
        "formal_signed_admission_created": False,
        "production_host_accepted": False,
        "bundle_created": False,
        "decision_created": False,
        "human_approval_required": True,
        "auto_execution": False,
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
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="Read and revalidate an existing local private candidate without fetching source data.",
    )
    args = parser.parse_args()
    try:
        if args.verify_existing:
            result = verify_existing_private_b2_candidate(
                private_root=args.private_root,
                repository_root=args.repository_root,
            )
        else:
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
    except ValueError as exc:
        # Validation/source errors are expected blocked outcomes, not tracebacks.
        # Emit only a stable uppercase error code; never expose source bytes or paths.
        raw_reason = str(exc)
        import re
        reason = raw_reason if re.fullmatch(r"[A-Z0-9_:-]{1,160}", raw_reason) else "SOURCE_OR_VALIDATION_FAILED"
        blocked_result = {
            "status": "BLOCKED",
            "reason": reason,
            "private_store_written": False,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "bundle_created": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }
        # Only aliases and sanitized categories are emitted; never print URLs,
        # raw OS errors, response headers, source bytes or local paths.
        safe_diagnostics = getattr(exc, "safe_diagnostics", None)
        if isinstance(safe_diagnostics, list) and safe_diagnostics:
            diagnostic_field = getattr(exc, "diagnostic_field", "source_fetch_diagnostics")
            blocked_result[diagnostic_field] = safe_diagnostics
        print(json.dumps(blocked_result, ensure_ascii=False, indent=2))
        return 2
    except Exception as exc:
        # Fail closed without exposing a traceback, input values, or local paths.
        print(json.dumps({
            "status": "BLOCKED",
            "reason": "UNEXPECTED_PRIVATE_INGEST_FAILURE",
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
