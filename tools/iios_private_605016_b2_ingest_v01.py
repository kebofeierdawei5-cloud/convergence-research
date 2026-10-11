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
import re
from pathlib import Path, PurePosixPath
import shutil
import socket
import ssl
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
RECEIPT_SCHEMA_REVIEWED = "IIOS-LOCAL-PRIVATE-B2-PERSISTENCE-0.2"
SOURCE_VINTAGE_REVIEWED_STATUS = "BOUNDED_PUBLIC_AVAILABILITY_ACCEPTED_FOR_PIT"
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


def _classify_python_transport_failure(exc: BaseException) -> str:
    """Return a bounded diagnostic category without exposing URLs, headers or tokens."""
    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, ssl.SSLCertVerificationError):
        return "TLS_CERTIFICATE_VERIFY_FAILED"
    if isinstance(reason, ssl.SSLError):
        return "TLS_HANDSHAKE_FAILED"
    if isinstance(reason, socket.gaierror):
        return "DNS_LOOKUP_FAILED"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "TIMEOUT"
    message = str(reason).lower()
    if "certificate_verify_failed" in message or "certificate verify failed" in message:
        return "TLS_CERTIFICATE_VERIFY_FAILED"
    if "ssl" in message or "tls" in message or "certificate" in message:
        return "TLS_HANDSHAKE_FAILED"
    if "name or service not known" in message or "temporary failure in name resolution" in message:
        return "DNS_LOOKUP_FAILED"
    if "timed out" in message or "timeout" in message:
        return "TIMEOUT"
    if "proxy" in message or "tunnel connection" in message:
        return "PROXY_CONNECT_FAILED"
    if "connection refused" in message:
        return "CONNECTION_REFUSED"
    if "connection reset" in message or "remote end closed" in message:
        return "CONNECTION_RESET"
    if "network is unreachable" in message or "no route to host" in message:
        return "NETWORK_UNREACHABLE"
    return "NETWORK_TRANSPORT_ERROR"


def _classify_curl_transport_failure(stderr: str) -> str:
    """Classify curl stderr without returning its raw text to the operator."""
    message = stderr.lower()
    if "certificate" in message or "ssl certificate problem" in message:
        return "TLS_CERTIFICATE_VERIFY_FAILED"
    if "could not resolve host" in message or "could not resolve proxy" in message:
        return "DNS_LOOKUP_FAILED"
    if "proxy" in message or "tunnel" in message:
        return "PROXY_CONNECT_FAILED"
    if "timed out" in message or "timeout" in message:
        return "TIMEOUT"
    if "connection refused" in message:
        return "CONNECTION_REFUSED"
    if "connection reset" in message:
        return "CONNECTION_RESET"
    if "network is unreachable" in message or "no route to host" in message:
        return "NETWORK_UNREACHABLE"
    return "NETWORK_TRANSPORT_ERROR"


def _parse_artifact_api_response(status: int, location: str = "") -> str:
    if status in {401, 403}:
        raise PrivateIngestError(
            "GITHUB_ACTIONS_ARTIFACT_ACCESS_DENIED_CHECK_TOKEN_ACTIONS_READ"
        )
    if status in {404, 410}:
        raise PrivateIngestError(
            "ATTEMPT10_ARTIFACT_MISSING_OR_EXPIRED_CHECK_CANONICAL_ARTIFACT"
        )
    if status != 302:
        raise PrivateIngestError(f"ATTEMPT10_ARTIFACT_API_HTTP_{status}")
    parsed = urlparse(location)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_REDIRECT_INVALID")
    return location


def _curl_config_quote(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_CURL_CONFIG_VALUE_INVALID")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _parse_curl_dumped_headers(raw_headers: str) -> tuple[int | None, str]:
    """Use only the final HTTP response block; never expose signed Location values."""
    status: int | None = None
    location = ""
    for line in raw_headers.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("HTTP/"):
            pieces = stripped.split()
            status = int(pieces[1]) if len(pieces) > 1 and pieces[1].isdigit() else None
            location = ""
            continue
        if status is not None and ":" in line:
            name, value = line.split(":", 1)
            if name.strip().casefold() == "location":
                location = value.strip()
    return status, location


def _request_attempt10_archive_url_with_curl(token: str, python_reason: str) -> str:
    """Use system curl only after Python HTTPS transport fails, with TLS on and no redirects."""
    curl = shutil.which("curl")
    if not curl:
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_UNAVAILABLE"
        ) from None
    if not token or "\r" in token or "\n" in token:
        raise PrivateIngestError("GITHUB_CLI_TOKEN_FORMAT_INVALID") from None

    api_url = (
        f"https://api.github.com/repos/{REPOSITORY_FULL_NAME}/actions/"
        f"artifacts/{ATTEMPT10_ARTIFACT_ID}/zip"
    )
    config = "\n".join((
        f"url = {_curl_config_quote(api_url)}",
        "silent",
        "show-error",
        "max-redirs = 0",
        "connect-timeout = 10",
        "max-time = 30",
        'proto = "=https"',
        'dump-header = "-"',
        'output = "/dev/null"',
        f'header = {_curl_config_quote("Accept: application/vnd.github+json")}',
        f'header = {_curl_config_quote("Authorization: Bearer " + token)}',
        f'header = {_curl_config_quote("X-GitHub-Api-Version: " + GITHUB_API_VERSION)}',
        f'user-agent = {_curl_config_quote("IIOS-private-B2-ingest")}',
        "",
    ))
    # Use curl's stdin config: the bearer token never appears in the OS process arguments.
    try:
        result = subprocess.run(
            [curl, "--config", "-"],
            input=config,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=35,
            check=False,
        )
    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
        reason = _classify_python_transport_failure(exc)
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_{reason}"
        ) from None

    if result.returncode != 0:
        curl_reason = _classify_curl_transport_failure(result.stderr or "")
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_{curl_reason}"
        ) from None
    status, location = _parse_curl_dumped_headers(result.stdout or "")
    if status is None:
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_NO_HTTP_RESPONSE"
        ) from None
    return _parse_artifact_api_response(status, location)


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
        return _parse_artifact_api_response(exc.code, exc.headers.get("Location", ""))
    except PrivateIngestError:
        raise
    except (URLError, TimeoutError, OSError) as exc:
        python_reason = _classify_python_transport_failure(exc)
        return _request_attempt10_archive_url_with_curl(token, python_reason)


def _download_attempt10_archive_with_curl(
    location: str, archive_path: Path, *, python_reason: str
) -> None:
    """Download a validated signed HTTPS URL without GitHub API credentials or redirect downgrade."""
    parsed = urlparse(location)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_REDIRECT_INVALID")
    curl = shutil.which("curl")
    if not curl:
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_UNAVAILABLE"
        ) from None

    try:
        # Pre-create exclusively under the private temporary workspace. Curl truncates
        # this mode-0600 file rather than creating a world-readable archive.
        with archive_path.open("xb"):
            pass
        os.chmod(archive_path, 0o600)
    except OSError:
        raise PrivateIngestError("ATTEMPT10_ARTIFACT_PRIVATE_TEMP_FILE_CREATE_FAILED") from None

    config = "\n".join((
        f"url = {_curl_config_quote(location)}",
        "silent",
        "show-error",
        "fail",
        "location",
        "max-redirs = 5",
        "connect-timeout = 10",
        "max-time = 120",
        'proto = "=https"',
        'proto-redir = "=https"',
        f"max-filesize = {ATTEMPT10_ARTIFACT_SIZE_BYTES}",
        f"output = {_curl_config_quote(str(archive_path))}",
        f'user-agent = {_curl_config_quote("IIOS-private-B2-ingest")}',
        "",
    ))
    # The signed URL remains in curl stdin config, not argv or logs. No Authorization
    # header/token is used for blob storage; redirects are allowed only over HTTPS.
    try:
        result = subprocess.run(
            [curl, "--config", "-"],
            input=config,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=125,
            check=False,
        )
    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
        try:
            archive_path.unlink(missing_ok=True)
        except OSError:
            pass
        reason = _classify_python_transport_failure(exc)
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_{reason}"
        ) from None

    if result.returncode != 0:
        stderr = result.stderr or ""
        match = re.search(r"returned error:\s*(\d{3})", stderr.lower())
        try:
            archive_path.unlink(missing_ok=True)
        except OSError:
            pass
        if match:
            raise PrivateIngestError(
                f"ATTEMPT10_ARTIFACT_DOWNLOAD_HTTP_{match.group(1)}"
            ) from None
        curl_reason = _classify_curl_transport_failure(stderr)
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED_PYTHON_{python_reason}_CURL_{curl_reason}"
        ) from None


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
        response = None
        python_transport_reason = None
        try:
            response = opener.open(request, timeout=120)
        except (URLError, TimeoutError, OSError) as exc:
            python_transport_reason = _classify_python_transport_failure(exc)

        if python_transport_reason is not None:
            _download_attempt10_archive_with_curl(
                location, archive_path, python_reason=python_transport_reason
            )
        else:
            if response is None:
                raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_RESPONSE_MISSING")
            with response:
                if urlparse(response.geturl()).scheme.lower() != "https":
                    raise PrivateIngestError("ATTEMPT10_ARTIFACT_DOWNLOAD_HTTPS_REQUIRED")
                with archive_path.open("xb") as archive_file:
                    os.chmod(archive_path, 0o600)
                    digest = hashlib.sha256()
                    total = 0
                    while True:
                        try:
                            chunk = response.read(1024 * 1024)
                        except (URLError, TimeoutError, OSError) as exc:
                            python_transport_reason = _classify_python_transport_failure(exc)
                            break
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > ATTEMPT10_ARTIFACT_SIZE_BYTES:
                            raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SIZE_MISMATCH")
                        digest.update(chunk)
                        archive_file.write(chunk)
                    if python_transport_reason is None:
                        archive_file.flush()
                        os.fsync(archive_file.fileno())
            if python_transport_reason is not None:
                try:
                    archive_path.unlink(missing_ok=True)
                except OSError:
                    pass
                _download_attempt10_archive_with_curl(
                    location, archive_path, python_reason=python_transport_reason
                )

        actual_size = archive_path.stat().st_size
        if actual_size != ATTEMPT10_ARTIFACT_SIZE_BYTES:
            raise PrivateIngestError("ATTEMPT10_ARTIFACT_ARCHIVE_SIZE_MISMATCH")
        if _sha256(archive_path.read_bytes()) != ATTEMPT10_ARTIFACT_SHA256:
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
        reason = _classify_python_transport_failure(exc)
        raise PrivateIngestError(
            f"ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED_PYTHON_{reason}"
        ) from None
    finally:
        try:
            archive_path.unlink(missing_ok=True)
        except OSError:
            pass


def _price_evidence(manifest: Mapping[str, Any]) -> dict[str, Any]:
    records = [
        item for item in manifest.get("evidence", [])
        if isinstance(item, Mapping) and item.get("evidence_id") == PRICE_EVIDENCE_ID
    ]
    if len(records) != 1:
        raise PrivateIngestError("OFFICIAL_PRICE_EVIDENCE_RECORD_MISSING_OR_DUPLICATED")
    return dict(records[0])


def _source_vintage_state(
    manifest: Mapping[str, Any],
    *,
    raw_root: Path,
    repository_root: str | Path,
) -> dict[str, Any]:
    """Return the replay-verified PIT source-vintage state for old or successor candidates."""
    price = _price_evidence(manifest)
    adjudication = manifest.get("source_vintage_adjudication")
    if adjudication is None:
        if (
            price.get("known_at") != "2026-10-08T15:00:00+08:00"
            or "MARKET_SESSION_CLOSE_EVENT_TIME" not in str(price.get("known_at_basis", ""))
        ):
            raise PrivateIngestError("EXISTING_PRIVATE_SOURCE_VINTAGE_NEEDS_ADJUDICATION")
        return {
            "source_vintage_status": "REVIEW_REQUIRED_EXACT_ENDPOINT_FIRST_PUBLIC_TIMESTAMP",
            "source_vintage_review_required": True,
            "exact_first_public_timestamp_verified": False,
            "adjudication_sha256": None,
            "public_availability_upper_bound": None,
        }

    try:
        import_root = Path(repository_root).expanduser().resolve(strict=True)
    except OSError as exc:
        raise PrivateIngestError("CORE_VALIDATOR_REPOSITORY_ROOT_MISSING") from exc
    if not import_root.is_dir():
        raise PrivateIngestError("CORE_VALIDATOR_REPOSITORY_ROOT_MISSING")
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
    try:
        from research.b2.source_vintage_policy import validate_source_vintage_adjudication

        state = validate_source_vintage_adjudication(
            manifest,
            raw_root=raw_root,
            expected_price_sha256=EXPECTED_PRICE_RAW_SHA256,
        )
    except ValueError as exc:
        raise PrivateIngestError(str(exc)) from exc
    return state


def _adjudicate_source_vintage_manifest(
    manifest: Mapping[str, Any],
    *,
    raw_root: Path,
    repository_root: str | Path,
    core_validator: Callable[..., list[str]] | None = None,
) -> dict[str, Any]:
    """Create/replay the deterministic official-rule upper-bound adjudication."""
    try:
        import_root = Path(repository_root).expanduser().resolve(strict=True)
    except OSError as exc:
        raise PrivateIngestError("CORE_VALIDATOR_REPOSITORY_ROOT_MISSING") from exc
    if not import_root.is_dir():
        raise PrivateIngestError("CORE_VALIDATOR_REPOSITORY_ROOT_MISSING")
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
    try:
        from research.b2.source_vintage_policy import adjudicate_605016_source_vintage

        return adjudicate_605016_source_vintage(
            manifest,
            raw_root=raw_root,
            expected_price_sha256=EXPECTED_PRICE_RAW_SHA256,
            core_validator=core_validator,
        )
    except ValueError as exc:
        raise PrivateIngestError(str(exc)) from exc


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
                "source_origin_adjudication", "source_vintage_adjudication_id",
                "first_public_time_precision",
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
    if isinstance(manifest.get("source_vintage_adjudication"), Mapping):
        stable["source_vintage_adjudication"] = manifest["source_vintage_adjudication"]
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

    # First validate the whole manifest's path/hash contract, then load and
    # verify every unique source byte object, and only then create/write the
    # private destination. This keeps malformed later declarations from
    # producing even a partial staged copy.
    normalized: list[tuple[Mapping[str, Any], PurePosixPath, str]] = []
    path_contracts: dict[str, tuple[int, str]] = {}
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise PrivateIngestError("RAW_ARTIFACT_DECLARATION_INVALID")
        relative = _safe_relative_path(declaration.get("relative_path"))
        relative_key = relative.as_posix()
        expected_size = declaration.get("expected_size_bytes")
        expected_hash = declaration.get("expected_sha256")
        if (
            type(expected_size) is not int
            or expected_size < 0
            or not isinstance(expected_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
        ):
            raise PrivateIngestError("RAW_ARTIFACT_DECLARATION_INVALID")
        contract = (expected_size, expected_hash)
        previous = path_contracts.get(relative_key)
        if previous is not None and previous != contract:
            raise PrivateIngestError("RAW_ARTIFACT_PATH_CONTRACT_CONFLICT")
        path_contracts[relative_key] = contract
        normalized.append((declaration, relative, relative_key))

    source_bytes: dict[str, bytes] = {}
    for _declaration, relative, relative_key in normalized:
        if relative_key in source_bytes:
            continue
        unresolved_source = source_base
        for part in relative.parts:
            unresolved_source = unresolved_source / part
            if unresolved_source.is_symlink():
                raise PrivateIngestError("RAW_ARTIFACT_SOURCE_SYMLINK_FORBIDDEN")
        try:
            source = unresolved_source.resolve(strict=True)
        except FileNotFoundError as exc:
            raise PrivateIngestError("RAW_ARTIFACT_SOURCE_MISSING") from exc
        try:
            source.relative_to(source_base)
        except ValueError as exc:
            raise PrivateIngestError("RAW_ARTIFACT_PATH_ESCAPE") from exc
        if not source.is_file():
            raise PrivateIngestError("RAW_ARTIFACT_SOURCE_NOT_REGULAR_FILE")
        source_bytes[relative_key] = source.read_bytes()

    # Compare each manifest declaration to the fully read-and-hashed source
    # bytes before any destination directory or output file is created.
    for declaration, _relative, relative_key in normalized:
        raw = source_bytes[relative_key]
        expected_size = declaration.get("expected_size_bytes")
        expected_hash = declaration.get("expected_sha256")
        if len(raw) != expected_size or _sha256(raw) != expected_hash:
            raise PrivateIngestError("RAW_ARTIFACT_EXACT_BYTES_MISMATCH")

    _make_private_directory(destination_root)
    written_paths: set[str] = set()
    for _declaration, relative, relative_key in normalized:
        # The bytes were captured and validated before writes, so every written
        # byte is exactly the byte sequence whose size/hash the manifest names.
        if relative_key in written_paths:
            continue
        target = destination_root.joinpath(*relative.parts)
        _make_private_directory(target.parent)
        try:
            with target.open("xb") as handle:
                handle.write(source_bytes[relative_key])
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(target, 0o600)
        except FileExistsError as exc:
            raise PrivateIngestError("RAW_ARTIFACT_WRITE_COLLISION") from exc
        written_paths.add(relative_key)
    # Backward-compatible receipt field: the count is evidence declarations,
    # not unique physical raw files; shared source bytes are only written once.
    return len(normalized)


def _validate_core(
    manifest: Mapping[str, Any],
    raw_root: Path,
    validator: Callable[..., list[str]] | None,
    repository_root: str | Path = REPOSITORY_ROOT,
) -> list[str]:
    if validator is None:
        # Every entry point (including read-only --verify-existing) must establish
        # the same repository import environment. Ingest used to do this only as
        # an incidental side effect of importing the adjudicator; offline replay
        # skips that branch and could fail with ModuleNotFoundError before it
        # inspected the persisted candidate.
        try:
            import_root = Path(repository_root).expanduser().resolve(strict=True)
        except OSError:
            raise PrivateIngestError("CORE_VALIDATOR_REPOSITORY_ROOT_MISSING") from None
        if not import_root.is_dir():
            raise PrivateIngestError("CORE_VALIDATOR_REPOSITORY_ROOT_MISSING")
        import_root_text = str(import_root)
        if import_root_text not in sys.path:
            sys.path.insert(0, import_root_text)
        from iios_mvp.canonical_evidence_admission_v01 import validate_company_evidence_manifest
        validator = validate_company_evidence_manifest
    return list(validator(manifest, raw_root=raw_root, require_raw_verification=True))


def _validate_existing_candidate(
    candidate_dir: Path,
    *,
    validator: Callable[..., list[str]] | None,
    repository_root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    manifest_path = candidate_dir / "company_evidence_manifest.json"
    raw_root = candidate_dir / "evidence_root"
    manifest = _read_object(manifest_path, "EXISTING_PRIVATE_MANIFEST")
    errors = _validate_core(manifest, raw_root, validator, repository_root=repository_root)
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


def _verify_private_candidate_contents(
    candidate_dir: Path,
    *,
    validator: Callable[..., list[str]] | None,
    repository_root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    """Check persisted metadata, privacy, exact file set and original Core/PIT validator."""
    _verify_private_tree_permissions(candidate_dir, label="PRIVATE_CANDIDATE")
    existing = _validate_existing_candidate(
        candidate_dir, validator=validator, repository_root=repository_root
    )
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
    manifest_path = candidate_dir / "company_evidence_manifest.json"
    manifest_sha = _sha256(manifest_path.read_bytes())
    raw_root = candidate_dir / "evidence_root"
    vintage = _source_vintage_state(
        manifest, raw_root=raw_root, repository_root=repository_root
    )
    expected_schema = RECEIPT_SCHEMA_REVIEWED if not vintage["source_vintage_review_required"] else RECEIPT_SCHEMA
    if receipt.get("schema_version") != expected_schema:
        raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_SCHEMA_MISMATCH")
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
        "source_vintage_review_required": vintage["source_vintage_review_required"],
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
    if not vintage["source_vintage_review_required"]:
        expected_receipt.update({
            "source_vintage_status": SOURCE_VINTAGE_REVIEWED_STATUS,
            "source_vintage_adjudication_sha256": vintage["adjudication_sha256"],
            "official_price_known_at": vintage["public_availability_upper_bound"],
            "official_price_known_at_basis": _price_evidence(manifest)["known_at_basis"],
        })
    for field, expected_value in expected_receipt.items():
        if receipt.get(field) != expected_value:
            raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_SEMANTICS_MISMATCH:" + field)
    if not isinstance(receipt.get("created_at"), str) or not receipt["created_at"].strip():
        raise PrivateIngestError("EXISTING_PRIVATE_RECEIPT_CREATED_AT_MISSING")

    declarations = manifest.get("raw_artifacts")
    if not isinstance(declarations, list) or not declarations:
        raise PrivateIngestError("EXISTING_PRIVATE_RAW_DECLARATIONS_MISSING")
    expected_paths: set[str] = set()
    persisted_path_contracts: dict[str, tuple[Any, Any]] = {}
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise PrivateIngestError("EXISTING_PRIVATE_RAW_DECLARATION_INVALID")
        relative = _safe_relative_path(declaration.get("relative_path")).as_posix()
        contract = (declaration.get("expected_size_bytes"), declaration.get("expected_sha256"))
        previous = persisted_path_contracts.get(relative)
        if previous is not None and previous != contract:
            raise PrivateIngestError("EXISTING_PRIVATE_RAW_PATH_CONTRACT_CONFLICT")
        persisted_path_contracts[relative] = contract
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
        # Legacy field means declaration count; shared raw paths are counted separately.
        "raw_artifact_count": len(declarations),
        "raw_artifact_declaration_count": len(declarations),
        "unique_raw_file_count": len(expected_paths),
        "raw_artifact_count_semantics": "MANIFEST_DECLARATIONS_NOT_UNIQUE_FILES",
        "evidence_record_count": len(manifest.get("evidence") or []),
        "core_validator_status": "PASS",
        "source_vintage_status": (
            SOURCE_VINTAGE_REVIEWED_STATUS if not vintage["source_vintage_review_required"]
            else "REVIEW_REQUIRED_EXACT_ENDPOINT_FIRST_PUBLIC_TIMESTAMP"
        ),
        "source_vintage_review_required": vintage["source_vintage_review_required"],
        "exact_first_public_timestamp_verified": False,
        "source_vintage_adjudication_sha256": vintage.get("adjudication_sha256"),
        "public_availability_upper_bound": vintage.get("public_availability_upper_bound"),
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
        _verify_private_candidate_contents(
            candidate, validator=core_validator, repository_root=repository_root
        )
        for candidate in sorted(candidate_dirs, key=lambda item: item.name)
    ]
    return {
        "status": "VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "candidate_count": len(verified),
        "candidates": verified,
        "official_source_refetched": False,
        "active_candidate_fingerprint": next(
            (item["candidate_fingerprint"] for item in reversed(verified)
             if item.get("source_vintage_review_required") is False),
            verified[-1]["candidate_fingerprint"],
        ),
        "source_vintage_review_required": next(
            (item["source_vintage_review_required"] for item in reversed(verified)
             if item.get("source_vintage_review_required") is False),
            True,
        ),
        "source_vintage_status": next(
            (item["source_vintage_status"] for item in reversed(verified)
             if item.get("source_vintage_review_required") is False),
            "REVIEW_REQUIRED_EXACT_ENDPOINT_FIRST_PUBLIC_TIMESTAMP",
        ),
        "exact_first_public_timestamp_verified": False,
        "formal_signed_admission_created": False,
        "production_host_accepted": False,
        "bundle_created": False,
        "decision_created": False,
        "human_approval_required": True,
        "auto_execution": False,
    }


def _persist_source_vintage_successor(
    *,
    source_candidate_dir: Path,
    manifest: Mapping[str, Any],
    private_root: Path,
    repository_root: str | Path,
    core_validator: Callable[..., list[str]] | None,
) -> dict[str, Any]:
    """Atomically persist a new immutable candidate while retaining its predecessor."""
    raw_declarations = manifest.get("raw_artifacts")
    if not isinstance(raw_declarations, list) or not raw_declarations:
        raise PrivateIngestError("SOURCE_VINTAGE_SUCCESSOR_RAW_DECLARATIONS_MISSING")
    vintage = _source_vintage_state(
        manifest,
        raw_root=source_candidate_dir / "evidence_root",
        repository_root=repository_root,
    )
    if vintage["source_vintage_review_required"]:
        raise PrivateIngestError("SOURCE_VINTAGE_SUCCESSOR_NOT_ADJUDICATED")
    fingerprint = _candidate_fingerprint(manifest)
    case_root = source_candidate_dir.parent
    destination = case_root / fingerprint
    if destination == source_candidate_dir:
        raise PrivateIngestError("SOURCE_VINTAGE_SUCCESSOR_MUST_BE_NEW_IMMUTABLE_CANDIDATE")
    if destination.is_symlink():
        raise PrivateIngestError("EXISTING_PRIVATE_CANDIDATE_MUST_NOT_BE_SYMLINK")
    if destination.exists():
        checked = _verify_private_candidate_contents(
            destination, validator=core_validator, repository_root=repository_root
        )
        if checked["candidate_fingerprint"] != fingerprint or checked["source_vintage_review_required"]:
            raise PrivateIngestError("IMMUTABLE_SOURCE_VINTAGE_SUCCESSOR_CONFLICT")
        return {
            "status": "ALREADY_SOURCE_VINTAGE_ADJUDICATED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
            **checked,
            "case_id": CASE_ID,
            "cutoff_date": CUTOFF_DATE,
            "official_source_refetched": False,
            "attempt10_downloaded": False,
            "previous_candidate_retained": True,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "bundle_created": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }

    _make_private_directory(private_root)
    stage_root = Path(tempfile.mkdtemp(prefix=".iios-source-vintage-stage-", dir=private_root))
    os.chmod(stage_root, 0o700)
    payload_root = stage_root / fingerprint
    _make_private_directory(payload_root)
    evidence_destination = payload_root / "evidence_root"
    try:
        copied_count = _copy_exact_artifacts(
            source_root=source_candidate_dir / "evidence_root",
            destination_root=evidence_destination,
            declarations=raw_declarations,
        )
        if copied_count != len(raw_declarations):
            raise PrivateIngestError("SOURCE_VINTAGE_SUCCESSOR_RAW_DECLARATION_COUNT_MISMATCH")

        manifest_out = payload_root / "company_evidence_manifest.json"
        with manifest_out.open("xb") as handle:
            handle.write((json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(manifest_out, 0o600)

        copied_manifest = _read_object(manifest_out, "SOURCE_VINTAGE_SUCCESSOR_MANIFEST")
        persisted_errors = _validate_core(
            copied_manifest,
            evidence_destination,
            core_validator,
            repository_root=repository_root,
        )
        if persisted_errors:
            raise PrivateIngestError(
                "SOURCE_VINTAGE_SUCCESSOR_CORE_VALIDATOR_BLOCKED:" + ",".join(persisted_errors[:8])
            )
        checked_vintage = _source_vintage_state(
            copied_manifest,
            raw_root=evidence_destination,
            repository_root=repository_root,
        )
        if checked_vintage["adjudication_sha256"] != vintage["adjudication_sha256"]:
            raise PrivateIngestError("SOURCE_VINTAGE_SUCCESSOR_ADJUDICATION_HASH_CHANGED")

        price = _price_evidence(copied_manifest)
        receipt_core = {
            "schema_version": RECEIPT_SCHEMA_REVIEWED,
            "status": "PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
            "case_id": CASE_ID,
            "cutoff_date": CUTOFF_DATE,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate_fingerprint": fingerprint,
            "manifest_sha256": _sha256(manifest_out.read_bytes()),
            "manifest_audit_sha256": (copied_manifest.get("audit") or {}).get("manifest_sha256"),
            "official_price_source_sha256": EXPECTED_PRICE_RAW_SHA256,
            "official_price_observation_date": "2026-10-08",
            "official_price_known_at": price.get("known_at"),
            "official_price_known_at_basis": price.get("known_at_basis"),
            "exact_first_public_timestamp_verified": False,
            "source_vintage_review_required": False,
            "source_vintage_status": SOURCE_VINTAGE_REVIEWED_STATUS,
            "source_vintage_adjudication_sha256": checked_vintage["adjudication_sha256"],
            "evidence_record_count": len(copied_manifest.get("evidence") or []),
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
            handle.write((json.dumps(receipt, ensure_ascii=False, indent=2) + "\\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(receipt_out, 0o600)

        # Full privacy, receipt, raw-tree, fingerprint and Core replay before promotion.
        _verify_private_candidate_contents(
            payload_root, validator=core_validator, repository_root=repository_root
        )
        os.replace(payload_root, destination)
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise
    shutil.rmtree(stage_root, ignore_errors=True)

    checked = _verify_private_candidate_contents(
        destination, validator=core_validator, repository_root=repository_root
    )
    return {
        "status": "SOURCE_VINTAGE_ADJUDICATED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
        **checked,
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "official_source_refetched": False,
        "attempt10_downloaded": False,
        "previous_candidate_retained": True,
        "formal_signed_admission_created": False,
        "production_host_accepted": False,
        "bundle_created": False,
        "decision_created": False,
        "human_approval_required": True,
        "auto_execution": False,
    }


def adjudicate_existing_private_b2_candidate(
    *,
    private_root: str | Path,
    repository_root: str | Path = REPOSITORY_ROOT,
    core_validator: Callable[..., list[str]] | None = None,
) -> dict[str, Any]:
    """Create a bounded source-vintage successor using only an already stored private candidate."""
    private_root_path = _preflight_private_root(private_root, repository_root=repository_root)
    existing = verify_existing_private_b2_candidate(
        private_root=private_root_path,
        repository_root=repository_root,
        core_validator=core_validator,
    )
    reviewed = [
        item for item in existing["candidates"]
        if item.get("source_vintage_review_required") is False
        and item.get("source_vintage_status") == SOURCE_VINTAGE_REVIEWED_STATUS
    ]
    if reviewed:
        if len(reviewed) != 1:
            raise PrivateIngestError("SOURCE_VINTAGE_REVIEWED_CANDIDATE_AMBIGUOUS")
        active = reviewed[0]
        return {
            "status": "ALREADY_SOURCE_VINTAGE_ADJUDICATED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED",
            **active,
            "case_id": CASE_ID,
            "cutoff_date": CUTOFF_DATE,
            "official_source_refetched": False,
            "attempt10_downloaded": False,
            "previous_candidate_retained": True,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "bundle_created": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }

    unreviewed = [
        item for item in existing["candidates"]
        if item.get("source_vintage_review_required") is True
    ]
    if len(unreviewed) != 1:
        raise PrivateIngestError("SOURCE_VINTAGE_UNREVIEWED_CANDIDATE_AMBIGUOUS")
    source_fingerprint = unreviewed[0]["candidate_fingerprint"]
    case_root = private_root_path / "cases" / CASE_ID
    source_candidate_dir = case_root / source_fingerprint
    original_manifest = _read_object(
        source_candidate_dir / "company_evidence_manifest.json",
        "EXISTING_PRIVATE_MANIFEST",
    )
    successor_manifest = _adjudicate_source_vintage_manifest(
        original_manifest,
        raw_root=source_candidate_dir / "evidence_root",
        repository_root=repository_root,
        core_validator=core_validator,
    )
    return _persist_source_vintage_successor(
        source_candidate_dir=source_candidate_dir,
        manifest=successor_manifest,
        private_root=private_root_path,
        repository_root=repository_root,
        core_validator=core_validator,
    )


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
        _price_record_preflight(manifest, ephemeral_report)
        manifest = _adjudicate_source_vintage_manifest(
            manifest,
            raw_root=raw_root,
            repository_root=repository_root,
            core_validator=core_validator,
        )
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        price = _price_evidence(manifest)
        core_errors = _validate_core(
            manifest, raw_root, core_validator, repository_root=repository_root
        )
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
            existing = _verify_private_candidate_contents(
                destination, validator=core_validator, repository_root=repository_root
            )
            if existing["candidate_fingerprint"] != fingerprint:
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
                "raw_artifact_declaration_count": len(raw_declarations),
                "unique_raw_file_count": len({
                    _safe_relative_path(item.get("relative_path")).as_posix()
                    for item in raw_declarations if isinstance(item, Mapping)
                }),
                "raw_artifact_count_semantics": "MANIFEST_DECLARATIONS_NOT_UNIQUE_FILES",
                "evidence_record_count": len(manifest.get("evidence") or []),
                "core_validator_status": "PASS",
                "source_vintage_status": existing["source_vintage_status"],
                "source_vintage_adjudication_sha256": existing.get("source_vintage_adjudication_sha256"),
                "public_availability_upper_bound": existing.get("public_availability_upper_bound"),
                "exact_first_public_timestamp_verified": False,
                "source_vintage_review_required": existing["source_vintage_review_required"],
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
            persisted_errors = _validate_core(
                copied_manifest, evidence_destination, core_validator,
                repository_root=repository_root,
            )
            if persisted_errors:
                raise PrivateIngestError("PERSISTED_CORE_VALIDATOR_BLOCKED:" + ",".join(persisted_errors[:8]))
            if copied_count != len(raw_declarations):
                raise PrivateIngestError("PERSISTED_RAW_ARTIFACT_COUNT_MISMATCH")

            receipt_core = {
                "schema_version": RECEIPT_SCHEMA_REVIEWED,
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
                "official_price_known_at_basis": price.get("known_at_basis"),
                "exact_first_public_timestamp_verified": False,
                "source_vintage_review_required": False,
                "source_vintage_status": SOURCE_VINTAGE_REVIEWED_STATUS,
                "source_vintage_adjudication_sha256": (
                    manifest["source_vintage_adjudication"]["adjudication_sha256"]
                ),
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
            _validate_existing_candidate(
                payload_root, validator=core_validator, repository_root=repository_root
            )
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
        final_verified = _verify_private_candidate_contents(
            destination, validator=core_validator, repository_root=repository_root
        )
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
            "raw_artifact_declaration_count": copied_count,
            "unique_raw_file_count": len({
                _safe_relative_path(item.get("relative_path")).as_posix()
                for item in raw_declarations if isinstance(item, Mapping)
            }),
            "raw_artifact_count_semantics": "MANIFEST_DECLARATIONS_NOT_UNIQUE_FILES",
            "evidence_record_count": len(manifest.get("evidence") or []),
            "core_validator_status": "PASS",
            "source_vintage_status": final_verified["source_vintage_status"],
            "source_vintage_adjudication_sha256": final_verified.get("source_vintage_adjudication_sha256"),
            "public_availability_upper_bound": final_verified.get("public_availability_upper_bound"),
            "exact_first_public_timestamp_verified": False,
            "source_vintage_review_required": final_verified["source_vintage_review_required"],
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify-existing",
        action="store_true",
        help="Read and revalidate existing local private candidates without fetching source data.",
    )
    mode.add_argument(
        "--adjudicate-source-vintage",
        action="store_true",
        help="Create an immutable rule-bounded successor from existing local raw bytes; no source fetch.",
    )
    args = parser.parse_args()
    try:
        if args.verify_existing:
            result = verify_existing_private_b2_candidate(
                private_root=args.private_root,
                repository_root=args.repository_root,
            )
        elif args.adjudicate_source_vintage:
            result = adjudicate_existing_private_b2_candidate(
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
