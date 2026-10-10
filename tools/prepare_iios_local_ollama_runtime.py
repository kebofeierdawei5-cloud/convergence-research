from __future__ import annotations

"""Prepare a private, no-paid-key IIOS runtime configuration for local Ollama.

This creates directories and a protected environment file only. It never creates
company bundles, Evidence admissions, Forecast admissions or Valuation admissions.
"""

import argparse
import base64
from http.client import HTTPException
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

MIN_OLLAMA_RESPONSES_VERSION = (0, 13, 3)
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class LocalRuntimeSetupError(RuntimeError):
    """Raised when a trusted local runtime cannot be safely provisioned."""


def _loopback_base_url(value: str) -> str:
    parsed = urlparse(str(value).strip())
    if parsed.scheme.lower() != "http" or not parsed.hostname:
        raise LocalRuntimeSetupError("OLLAMA_URL_MUST_BE_HTTP_LOOPBACK")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise LocalRuntimeSetupError("OLLAMA_URL_MUST_NOT_CONTAIN_CREDENTIALS_OR_QUERY")
    if parsed.path not in ("", "/"):
        raise LocalRuntimeSetupError("OLLAMA_URL_MUST_BE_ORIGIN_ONLY")
    host = parsed.hostname.strip().lower().rstrip(".")
    if host != "localhost":
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise LocalRuntimeSetupError("OLLAMA_URL_MUST_BE_LOOPBACK")
        except ValueError as exc:
            raise LocalRuntimeSetupError("OLLAMA_URL_MUST_BE_LOOPBACK") from exc
    port = parsed.port
    if port is not None and not 1 <= port <= 65535:
        raise LocalRuntimeSetupError("OLLAMA_PORT_OUT_OF_RANGE")
    authority = f"[{host}]" if ":" in host else host
    if port is not None:
        authority += f":{port}"
    return f"http://{authority}"


def _get_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if not 200 <= int(response.status) < 300:
                raise LocalRuntimeSetupError("OLLAMA_PREFLIGHT_HTTP_STATUS")
            raw = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError) as exc:
        raise LocalRuntimeSetupError("OLLAMA_LOCAL_API_UNAVAILABLE") from exc
    if len(raw) > 1024 * 1024:
        raise LocalRuntimeSetupError("OLLAMA_PREFLIGHT_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalRuntimeSetupError("OLLAMA_PREFLIGHT_RESPONSE_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise LocalRuntimeSetupError("OLLAMA_PREFLIGHT_RESPONSE_MUST_BE_OBJECT")
    return payload


def _version_tuple(value: Any) -> tuple[int, int, int]:
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)", str(value))
    if not match:
        raise LocalRuntimeSetupError("OLLAMA_VERSION_UNRECOGNIZED")
    return tuple(int(match.group(i)) for i in range(1, 4))


def _model_names(payload: dict[str, Any]) -> set[str]:
    models = payload.get("models")
    if not isinstance(models, list):
        raise LocalRuntimeSetupError("OLLAMA_MODEL_LIST_INVALID")
    names: set[str] = set()
    for item in models:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    return names


def _new_keypair_b64() -> tuple[str, str]:
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (
        base64.b64encode(private).decode("ascii"),
        base64.b64encode(public).decode("ascii"),
    )


def _make_private_directory(path: Path) -> None:
    if path.is_symlink():
        raise LocalRuntimeSetupError("WORKSPACE_PATH_MUST_NOT_BE_SYMLINK")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise LocalRuntimeSetupError("WORKSPACE_PATH_MUST_BE_DIRECTORY")
    try:
        path.chmod(0o700)
    except OSError:
        # The env file itself is still created with restrictive permissions.
        pass


def _shell_env_text(values: dict[str, str]) -> str:
    return (
        "# Generated locally; contains private runtime key and host bearer token.\n"
        "# Keep this file out of Git and do not paste it into issue/PR comments.\n"
        + "".join(f"export {key}={shlex.quote(value)}\n" for key, value in values.items())
    )


def prepare_local_runtime(
    *,
    workspace: str | Path,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = 4,
) -> dict[str, str]:
    """Verify a local Ollama endpoint/model, then create a private host env file."""
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+:[A-Za-z0-9._-]+", model.strip()):
        raise LocalRuntimeSetupError("MODEL_NAME_MUST_INCLUDE_EXPLICIT_TAG")
    if not 1 <= int(timeout_seconds) <= 30:
        raise LocalRuntimeSetupError("PREFLIGHT_TIMEOUT_OUT_OF_RANGE")
    base_url = _loopback_base_url(ollama_url)
    version_payload = _get_json(f"{base_url}/api/version", int(timeout_seconds))
    version_text = str(version_payload.get("version", "")).strip()
    if not version_text or _version_tuple(version_text) < MIN_OLLAMA_RESPONSES_VERSION:
        raise LocalRuntimeSetupError("OLLAMA_VERSION_BELOW_RESPONSES_API_MINIMUM")
    names = _model_names(_get_json(f"{base_url}/api/tags", int(timeout_seconds)))
    if model not in names:
        raise LocalRuntimeSetupError("REQUESTED_OLLAMA_MODEL_NOT_INSTALLED")

    root = Path(workspace).expanduser()
    if root.exists() and root.is_symlink():
        raise LocalRuntimeSetupError("WORKSPACE_PATH_MUST_NOT_BE_SYMLINK")
    root = root.resolve()
    _make_private_directory(root)
    for name in ("bundles", "data", "outputs", "admissions", "secrets"):
        path = root / name
        if path.exists() and path.is_symlink():
            raise LocalRuntimeSetupError("WORKSPACE_CHILD_MUST_NOT_BE_SYMLINK")
        _make_private_directory(path)

    env_path = root / "secrets" / "host.env"
    if env_path.exists():
        raise LocalRuntimeSetupError("HOST_ENV_ALREADY_EXISTS_NOT_OVERWRITTEN")
    private_b64, public_b64 = _new_keypair_b64()
    endpoint = f"{base_url}/v1/responses"
    values = {
        "IIOS_HOST_BUNDLE_ROOT": str(root / "bundles"),
        "IIOS_HOST_DATA_ROOT": str(root / "data"),
        "IIOS_HOST_OUTPUT_ROOT": str(root / "outputs"),
        "IIOS_HOST_AUTH_TOKEN": secrets.token_urlsafe(36),
        "IIOS_HOST_BIND": "127.0.0.1",
        "IIOS_HOST_PORT": "8765",
        "IIOS_HOST_RUN_TIMEOUT_SECONDS": "600",
        "IIOS_CANONICAL_RUNTIME_FACTORY": "iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime",
        "IIOS_CANONICAL_ADMISSION_ROOT": str(root / "admissions"),
        "IIOS_LLM_PROVIDER_BASE_URL": endpoint,
        "IIOS_LLM_PROVIDER_MODEL": model.strip(),
        "IIOS_LLM_PROVIDER_ID": "ollama-self-hosted",
        "IIOS_LLM_PROVIDER_VERSION": f"ollama/{version_text};model/{model.strip()}",
        "IIOS_LLM_PROVIDER_PROTOCOL": "OPENAI_RESPONSES",
        "IIOS_LLM_PROVIDER_AUTH_MODE": "NONE",
        "IIOS_LLM_PROVIDER_DEPLOYMENT_MODE": "SELF_HOSTED",
        "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64": private_b64,
        "IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64": public_b64,
        "IIOS_LLM_PROVIDER_TIMEOUT_SECONDS": "300",
    }
    payload = _shell_env_text(values).encode("utf-8")
    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            env_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    try:
        env_path.chmod(0o600)
    except OSError as exc:
        env_path.unlink(missing_ok=True)
        raise LocalRuntimeSetupError("HOST_ENV_FILE_PERMISSIONS_COULD_NOT_BE_HARDENED") from exc

    return {
        "status": "LOCAL_RUNTIME_CONFIGURED_NOT_PRODUCTION_ACCEPTED",
        "workspace": str(root),
        "env_file": str(env_path),
        "provider_version": values["IIOS_LLM_PROVIDER_VERSION"],
        "model": model.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".iios-local")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-seconds", type=int, default=4)
    args = parser.parse_args()
    try:
        result = prepare_local_runtime(
            workspace=args.workspace,
            ollama_url=args.ollama_url,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
        )
    except LocalRuntimeSetupError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
