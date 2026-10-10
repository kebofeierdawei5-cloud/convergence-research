from __future__ import annotations

"""Loopback-first HTTP host for trusted, pre-materialized IIOS request bundles.

The service accepts only a bundle identifier. The bundle, evidence bytes, output
root and runtime factory come from operator-controlled configuration, never the
HTTP request. It delegates the actual investment run to the canonical CLI.
"""

import argparse
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping
import uuid

HOST_VERSION = "IIOS-CANONICAL-HTTP-HOST-0.1"
_BUNDLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$")
_FACTORY_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
_REQUIRED_BUNDLE_FIELDS = (
    "raw_request",
    "company",
    "investment_case",
    "evidence_manifest_path",
    "evidence_root",
    "artifact_type",
    "semantic_prompt",
    "decision_relevance",
)
_MAX_BODY_BYTES = 4096
_MAX_BUNDLE_BYTES = 256 * 1024
_MAX_TIMEOUT_SECONDS = 3600


class HostConfigurationError(ValueError):
    """Raised when host startup configuration is absent or unsafe."""


class HostRequestError(ValueError):
    """Raised when an HTTP request or trusted bundle violates the host contract."""


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolved_under(value: str | Path, root: Path, *, kind: str) -> Path:
    root_path = Path(root).resolve(strict=True)
    supplied = Path(value)
    candidate = supplied if supplied.is_absolute() else root_path / supplied
    resolved = candidate.resolve(strict=True)
    if not _under(resolved, root_path):
        raise HostRequestError("BUNDLE_PATH_OUTSIDE_CONFIGURED_DATA_ROOT")
    if kind == "file" and not resolved.is_file():
        raise HostRequestError("BUNDLE_PATH_NOT_A_FILE")
    if kind == "directory" and not resolved.is_dir():
        raise HostRequestError("BUNDLE_PATH_NOT_A_DIRECTORY")
    return resolved


def validate_bundle_id(value: Any) -> str:
    if not isinstance(value, str) or not _BUNDLE_ID_RE.fullmatch(value):
        raise HostRequestError("INVALID_BUNDLE_ID")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HostRequestError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _load_object_bytes(raw: bytes, *, limit: int, error_code: str) -> dict[str, Any]:
    if len(raw) > limit:
        raise HostRequestError(error_code)
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(HostRequestError("NON_FINITE_JSON_NUMBER")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HostRequestError("INVALID_UTF8_JSON") from exc
    if not isinstance(value, dict):
        raise HostRequestError("JSON_OBJECT_REQUIRED")
    return value


def load_trusted_bundle(
    *,
    bundle_id: str,
    bundle_root: str | Path,
    data_root: str | Path,
) -> dict[str, Any]:
    """Load an operator-staged bundle and confine all evidence paths to data_root."""
    identifier = validate_bundle_id(bundle_id)
    root = Path(bundle_root).resolve(strict=True)
    candidate = root / f"{identifier}.json"
    try:
        resolved_bundle = candidate.resolve(strict=True)
    except OSError as exc:
        raise HostRequestError("BUNDLE_NOT_FOUND") from exc
    if not _under(resolved_bundle, root) or not resolved_bundle.is_file():
        raise HostRequestError("BUNDLE_PATH_OUTSIDE_CONFIGURED_BUNDLE_ROOT")
    try:
        raw = resolved_bundle.read_bytes()
    except OSError as exc:
        raise HostRequestError("BUNDLE_READ_FAILED") from exc
    bundle = _load_object_bytes(raw, limit=_MAX_BUNDLE_BYTES, error_code="BUNDLE_TOO_LARGE")
    missing = [
        field for field in _REQUIRED_BUNDLE_FIELDS
        if field not in bundle or bundle[field] in (None, "")
    ]
    if missing:
        raise HostRequestError("BUNDLE_REQUIRED_FIELDS_MISSING:" + ",".join(missing))
    if not isinstance(bundle.get("investment_case"), Mapping):
        raise HostRequestError("INVESTMENT_CASE_OBJECT_REQUIRED")
    if not isinstance(bundle.get("raw_request"), str) or not bundle["raw_request"].strip():
        raise HostRequestError("RAW_REQUEST_REQUIRED")

    data_root_path = Path(data_root).resolve(strict=True)
    manifest_path = _resolved_under(bundle["evidence_manifest_path"], data_root_path, kind="file")
    evidence_root = _resolved_under(bundle["evidence_root"], data_root_path, kind="directory")
    # This endpoint stages intent, not semantic assertions. Facts/inferences are
    # produced only by the registered semantic producer and admitted downstream.
    bundle["semantic_facts"] = []
    bundle["semantic_inferences"] = []
    bundle["semantic_assumptions"] = []
    bundle["semantic_uncertainties"] = []
    bundle["evidence_manifest_path"] = str(manifest_path)
    bundle["evidence_root"] = str(evidence_root)
    return bundle


def load_host_config(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Validate trusted process configuration; no request body may override it."""
    values = os.environ if env is None else env
    required = (
        "IIOS_HOST_BUNDLE_ROOT",
        "IIOS_HOST_DATA_ROOT",
        "IIOS_HOST_OUTPUT_ROOT",
        "IIOS_HOST_AUTH_TOKEN",
        "IIOS_CANONICAL_RUNTIME_FACTORY",
    )
    missing = [name for name in required if not str(values.get(name, "")).strip()]
    if missing:
        raise HostConfigurationError("HOST_CONFIG_MISSING:" + ",".join(missing))

    bundle_root = Path(str(values["IIOS_HOST_BUNDLE_ROOT"])).expanduser().resolve(strict=True)
    data_root = Path(str(values["IIOS_HOST_DATA_ROOT"])).expanduser().resolve(strict=True)
    if not bundle_root.is_dir() or not data_root.is_dir():
        raise HostConfigurationError("HOST_BUNDLE_AND_DATA_ROOTS_MUST_BE_DIRECTORIES")
    output_root = Path(str(values["IIOS_HOST_OUTPUT_ROOT"])).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if not output_root.is_dir():
        raise HostConfigurationError("HOST_OUTPUT_ROOT_MUST_BE_DIRECTORY")

    token = str(values["IIOS_HOST_AUTH_TOKEN"])
    if len(token) < 32:
        raise HostConfigurationError("HOST_AUTH_TOKEN_MUST_BE_AT_LEAST_32_CHARACTERS")
    factory_spec = str(values["IIOS_CANONICAL_RUNTIME_FACTORY"]).strip()
    if not _FACTORY_RE.fullmatch(factory_spec):
        raise HostConfigurationError("INVALID_TRUSTED_RUNTIME_FACTORY_SPEC")

    host = str(values.get("IIOS_HOST_BIND", "127.0.0.1")).strip()
    port_raw = str(values.get("IIOS_HOST_PORT", "8765"))
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise HostConfigurationError("HOST_PORT_MUST_BE_INTEGER") from exc
    if not 1 <= port <= 65535:
        raise HostConfigurationError("HOST_PORT_OUT_OF_RANGE")

    allow_remote = str(values.get("IIOS_HOST_ALLOW_REMOTE", "")).strip().lower() == "true"
    tls_terminated = str(values.get("IIOS_HOST_TLS_TERMINATED", "")).strip().lower() == "true"
    import ipaddress
    import socket
    try:
        bind_ip = ipaddress.ip_address(host)
        loopback = bind_ip.is_loopback
    except ValueError:
        loopback = host.lower() == "localhost"
        if not loopback:
            # Do not do DNS resolution at startup; hostname binds are treated as remote.
            loopback = False
    if not loopback and not (allow_remote and tls_terminated):
        raise HostConfigurationError("REMOTE_BIND_REQUIRES_ALLOW_REMOTE_AND_TLS_TERMINATION")
    return {
        "bundle_root": bundle_root,
        "data_root": data_root,
        "output_root": output_root,
        "token": token,
        "factory_spec": factory_spec,
        "host": host,
        "port": port,
        "timeout_seconds": _host_timeout(values),
        "version": HOST_VERSION,
        "loopback_only": loopback,
    }


def _host_timeout(values: Mapping[str, str]) -> int:
    raw = str(values.get("IIOS_HOST_RUN_TIMEOUT_SECONDS", "600"))
    try:
        timeout = int(raw)
    except ValueError as exc:
        raise HostConfigurationError("HOST_RUN_TIMEOUT_MUST_BE_INTEGER") from exc
    if timeout < 1 or timeout > _MAX_TIMEOUT_SECONDS:
        raise HostConfigurationError("HOST_RUN_TIMEOUT_OUT_OF_RANGE")
    return timeout


def _safe_cli_result(stdout: str, returncode: int) -> dict[str, Any]:
    """Expose only contract result fields, never arbitrary stderr/exception detail."""
    try:
        raw = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    allowed = (
        "status", "run_id", "case_id", "decision_id", "action",
        "human_approval_required", "auto_execution", "run_state",
        "publication_required", "human_report_required",
        "canonical_decision_created", "reason",
    )
    result = {key: raw[key] for key in allowed if key in raw}
    if returncode != 0 or result.get("status") == "BLOCKED":
        result["status"] = "BLOCKED"
        result.setdefault("canonical_decision_created", False)
    result.setdefault("human_approval_required", True)
    result.setdefault("auto_execution", False)
    return result


class _HostServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def make_handler(config: Mapping[str, Any], runner: Callable[..., Any] = subprocess.run):
    """Bind request processing to immutable trusted configuration."""
    class Handler(BaseHTTPRequestHandler):
        server_version = "IIOSCanonicalHost/0.1"
        sys_version = ""

        def _json(self, status: int, body: Mapping[str, Any]) -> None:
            raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return False
            supplied = header[7:]
            return hmac.compare_digest(supplied.encode("utf-8"), str(config["token"]).encode("utf-8"))

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._json(200, {"status": "OK", "host_version": HOST_VERSION})
                return
            if self.path == "/readyz":
                self._json(200, {
                    "status": "CONFIGURED_NOT_PRODUCTION_ACCEPTED",
                    "runtime_factory_configured": True,
                    "runtime_is_invoked_by_readiness_probe": False,
                    "human_approval_required": True,
                    "auto_execution": False,
                })
                return
            self._json(404, {"status": "NOT_FOUND"})

        def do_POST(self) -> None:
            if self.path != "/v1/canonical-runs":
                self._json(404, {"status": "NOT_FOUND"})
                return
            if not self._authorized():
                self._json(401, {"status": "BLOCKED", "reason": "AUTHENTICATION_REQUIRED"})
                return
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"status": "BLOCKED", "reason": "APPLICATION_JSON_REQUIRED"})
                return
            length_raw = self.headers.get("Content-Length")
            try:
                length = int(length_raw or "")
            except ValueError:
                self._json(400, {"status": "BLOCKED", "reason": "CONTENT_LENGTH_REQUIRED"})
                return
            if length <= 0 or length > _MAX_BODY_BYTES:
                self._json(413, {"status": "BLOCKED", "reason": "REQUEST_BODY_SIZE_INVALID"})
                return
            try:
                request_obj = _load_object_bytes(self.rfile.read(length), limit=_MAX_BODY_BYTES, error_code="REQUEST_BODY_TOO_LARGE")
                if set(request_obj) != {"bundle_id"}:
                    raise HostRequestError("REQUEST_MUST_CONTAIN_ONLY_BUNDLE_ID")
                bundle_id = validate_bundle_id(request_obj["bundle_id"])
                bundle = load_trusted_bundle(
                    bundle_id=bundle_id,
                    bundle_root=config["bundle_root"],
                    data_root=config["data_root"],
                )
            except HostRequestError as exc:
                self._json(400, {"status": "BLOCKED", "reason": str(exc)})
                return

            run_id = "host-" + uuid.uuid4().hex
            request_id = "host-request-" + uuid.uuid4().hex
            created_at = datetime.now(timezone.utc).isoformat()
            bundle["run_id"] = run_id
            bundle["request_id"] = request_id
            bundle["created_at"] = created_at

            inbox = Path(config["output_root"]) / "host-inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            bundle_path = inbox / f"{run_id}.request-bundle.json"
            try:
                with bundle_path.open("x", encoding="utf-8", newline="\n") as f:
                    json.dump(bundle, f, ensure_ascii=False, indent=2)
                    f.write("\n")
            except OSError:
                self._json(500, {"status": "BLOCKED", "reason": "REQUEST_BUNDLE_PERSIST_FAILED"})
                return

            env = os.environ.copy()
            # Trusted provider configuration comes from this host's environment.
            # The request cannot set or replace the module factory or any secret.
            env["IIOS_CANONICAL_RUNTIME_FACTORY"] = str(config["factory_spec"])
            command = [
                sys.executable, "-m", "iios_mvp.cli", "canonical-run",
                str(bundle_path), "--out", str(config["output_root"]),
            ]
            try:
                result = runner(
                    command,
                    cwd=str(Path(__file__).resolve().parents[1]),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=int(config["timeout_seconds"]),
                    check=False,
                )
            except subprocess.TimeoutExpired:
                self._json(504, {
                    "status": "BLOCKED",
                    "run_id": run_id,
                    "reason": "CANONICAL_RUN_TIMEOUT",
                    "human_approval_required": True,
                    "auto_execution": False,
                })
                return
            except OSError:
                self._json(502, {
                    "status": "BLOCKED",
                    "run_id": run_id,
                    "reason": "CANONICAL_RUN_PROCESS_UNAVAILABLE",
                    "human_approval_required": True,
                    "auto_execution": False,
                })
                return
            outcome = _safe_cli_result(result.stdout, result.returncode)
            outcome["run_id"] = run_id
            outcome["request_id"] = request_id
            outcome["host_version"] = HOST_VERSION
            outcome["human_approval_required"] = True
            outcome["auto_execution"] = False
            # A canonical-run response is an AI proposal, not publication or approval.
            if result.returncode == 0 and outcome.get("status") not in ("BLOCKED", "ERROR"):
                self._json(202, outcome)
            else:
                self._json(409, outcome)

        def log_message(self, format: str, *args: Any) -> None:
            # Do not log request bodies, bearer credentials, or subprocess diagnostics.
            return

    return Handler


def serve(config: Mapping[str, Any], runner: Callable[..., Any] = subprocess.run) -> None:
    handler = make_handler(config, runner=runner)
    server = _HostServer((str(config["host"]), int(config["port"])), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the IIOS canonical HTTP host")
    parser.add_argument("--check-config", action="store_true", help="validate trusted host configuration and exit")
    args = parser.parse_args(argv)
    try:
        config = load_host_config()
    except (HostConfigurationError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    if args.check_config:
        print(json.dumps({
            "status": "CONFIGURED_NOT_PRODUCTION_ACCEPTED",
            "host_version": HOST_VERSION,
            "bind": config["host"],
            "port": config["port"],
            "loopback_only": config["loopback_only"],
            "runtime_factory_configured": True,
            "production_runtime_invoked": False,
            "human_approval_required": True,
            "auto_execution": False,
        }, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "status": "HOST_STARTING",
        "host_version": HOST_VERSION,
        "bind": config["host"],
        "port": config["port"],
        "loopback_only": config["loopback_only"],
        "runtime_factory_configured": True,
        "production_acceptance": "NOT_CLAIMED",
        "human_approval_required": True,
        "auto_execution": False,
    }, ensure_ascii=False), flush=True)
    serve(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
