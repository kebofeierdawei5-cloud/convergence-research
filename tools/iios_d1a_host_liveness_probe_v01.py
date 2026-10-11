from __future__ import annotations

"""Probe the loopback IIOS Host health/readiness endpoints; never claim acceptance."""

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import stat

HOST_VERSION = "IIOS-CANONICAL-HTTP-HOST-0.1"
SCHEMA = "IIOS-D1A-HOST-LIVENESS-PROBE-0.1"
MAX_BYTES = 1024 * 1024


def _get(host: str, port: int, path: str, timeout: int) -> tuple[int, bytes, dict]:
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", path, headers={"Accept": "application/json"})
        response = conn.getresponse()
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("HOST_RESPONSE_TOO_LARGE")
        body = json.loads(raw.decode("utf-8"))
        if not isinstance(body, dict):
            raise ValueError("HOST_RESPONSE_NOT_OBJECT")
        return int(response.status), raw, body
    finally:
        conn.close()


def probe_host(host: str = "127.0.0.1", port: int = 8765, timeout: int = 3) -> dict:
    value = str(host).strip().lower()
    try:
        ip = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("HOST_MUST_BE_LOOPBACK_IP") from exc
    if ip.version != 4 or not ip.is_loopback:
        raise ValueError("HOST_MUST_BE_IPV4_LOOPBACK")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("PORT_OUT_OF_RANGE")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 30:
        raise ValueError("TIMEOUT_OUT_OF_RANGE")

    blockers = []
    probes = {}
    expected = {
        "/healthz": lambda b: b.get("status") == "OK" and b.get("host_version") == HOST_VERSION,
        "/readyz": lambda b: (
            b.get("status") == "CONFIGURED_NOT_PRODUCTION_ACCEPTED"
            and b.get("runtime_factory_configured") is True
            and b.get("runtime_is_invoked_by_readiness_probe") is False
            and b.get("human_approval_required") is True
            and b.get("auto_execution") is False
        ),
    }
    for path, contract in expected.items():
        try:
            code, raw, body = _get(value, port, path, timeout)
            ok = code == 200 and contract(body)
            probes[path] = {
                "http_status": code,
                "body_status": body.get("status"),
                "host_version": body.get("host_version"),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "contract_pass": ok,
            }
            if not ok:
                blockers.append(path.lstrip("/") + "_CONTRACT_MISMATCH")
        except (OSError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            code = str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else "ENDPOINT_UNAVAILABLE_OR_INVALID"
            probes[path] = {
                "http_status": None,
                "body_status": None,
                "host_version": None,
                "response_sha256": None,
                "contract_pass": False,
                "error": code,
            }
            blockers.append(path.lstrip("/") + "_BLOCKED")

    ok = not blockers
    return {
        "schema_version": SCHEMA,
        "record_class": "LOCAL_HOST_LIVENESS_OBSERVATION_NOT_PRODUCTION_ACCEPTANCE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "target": {"host": value, "port": port, "loopback_only": True},
        "status": "HOST_LIVENESS_PROBED_NOT_PRODUCTION_ACCEPTED" if ok else "BLOCKED",
        "probes": probes,
        "blockers": blockers,
        "production_host_accepted": False,
        "actual_provider_invocation_performed": False,
        "signed_live_provider_receipt_verified": False,
        "canonical_run_completed": False,
        "complete_run_receipt_created": False,
        "formal_decision_created": False,
        "execution_authorized": False,
        "human_approval_required": True,
        "auto_execution": False,
    }


def _write(path: Path, report: dict) -> None:
    path = path.expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink() or path.parent.is_symlink():
        raise ValueError("OUTPUT_PATH_EXISTS_OR_UNSAFE")
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout-seconds", type=int, default=3)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = probe_host(args.host, args.port, args.timeout_seconds)
        _write(args.out, report)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "production_host_accepted": False}, sort_keys=True))
        return 2
    print(json.dumps({
        "status": report["status"],
        "health": report["probes"]["/healthz"]["body_status"],
        "ready": report["probes"]["/readyz"]["body_status"],
        "production_host_accepted": False,
        "actual_provider_invocation_performed": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "HOST_LIVENESS_PROBED_NOT_PRODUCTION_ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
