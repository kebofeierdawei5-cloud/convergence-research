from __future__ import annotations

from dataclasses import dataclass
import base64
import os

from iios_mvp.provider_runtime_v01 import validate_provider_runtime_policy


class LiveProviderPreflightError(ValueError):
    """Raised when live-provider runtime configuration is not admissible."""


@dataclass(frozen=True)
class LiveProviderConfig:
    base_url: str
    api_key: str
    model: str
    runtime_private_key_b64: str
    provider_id: str
    provider_version: str
    protocol: str
    timeout_seconds: int = 30
    auth_mode: str = "BEARER"
    deployment_mode: str = "EXTERNAL"


REQUIRED_ENV = (
    "IIOS_LLM_PROVIDER_BASE_URL",
    "IIOS_LLM_PROVIDER_MODEL",
    "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64",
    "IIOS_LLM_PROVIDER_ID",
    "IIOS_LLM_PROVIDER_VERSION",
    "IIOS_LLM_PROVIDER_PROTOCOL",
)


def load_live_provider_config(env: dict[str, str] | None = None) -> LiveProviderConfig:
    values = os.environ if env is None else env
    missing = [name for name in REQUIRED_ENV if not str(values.get(name, "")).strip()]
    if missing:
        raise LiveProviderPreflightError(
            "live provider configuration missing: " + ", ".join(missing)
        )
    base_url = str(values["IIOS_LLM_PROVIDER_BASE_URL"]).strip()
    protocol = str(values["IIOS_LLM_PROVIDER_PROTOCOL"]).strip().upper()
    auth_mode = str(values.get("IIOS_LLM_PROVIDER_AUTH_MODE", "BEARER")).strip().upper()
    deployment_mode = str(values.get("IIOS_LLM_PROVIDER_DEPLOYMENT_MODE", "EXTERNAL")).strip().upper()
    try:
        validate_provider_runtime_policy(
            base_url=base_url,
            protocol=protocol,
            auth_mode=auth_mode,
            deployment_mode=deployment_mode,
        )
    except ValueError as exc:
        raise LiveProviderPreflightError(str(exc)) from exc
    model = str(values["IIOS_LLM_PROVIDER_MODEL"]).strip()
    api_key = str(values.get("IIOS_LLM_PROVIDER_API_KEY", "")).strip()
    if auth_mode == "BEARER" and not api_key:
        raise LiveProviderPreflightError("auth_mode BEARER requires an API key")
    if auth_mode == "NONE" and api_key:
        raise LiveProviderPreflightError("auth_mode NONE must not receive an API key")
    provider_id = str(values["IIOS_LLM_PROVIDER_ID"]).strip()
    provider_version = str(values["IIOS_LLM_PROVIDER_VERSION"]).strip()
    private_key = str(values["IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64"]).strip()
    try:
        decoded = base64.b64decode(private_key, validate=True)
    except Exception as exc:
        raise LiveProviderPreflightError(
            "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64 must be valid base64"
        ) from exc
    if len(decoded) != 32:
        raise LiveProviderPreflightError(
            "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64 must decode to 32 bytes"
        )
    try:
        timeout_seconds = int(str(values.get("IIOS_LLM_PROVIDER_TIMEOUT_SECONDS", "30")))
    except ValueError as exc:
        raise LiveProviderPreflightError(
            "IIOS_LLM_PROVIDER_TIMEOUT_SECONDS must be an integer"
        ) from exc
    if timeout_seconds < 1 or timeout_seconds > 300:
        raise LiveProviderPreflightError(
            "IIOS_LLM_PROVIDER_TIMEOUT_SECONDS must be within [1,300]"
        )
    return LiveProviderConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        runtime_private_key_b64=private_key,
        provider_id=provider_id,
        provider_version=provider_version,
        protocol=protocol,
        timeout_seconds=timeout_seconds,
        auth_mode=auth_mode,
        deployment_mode=deployment_mode,
    )


__all__ = ["LiveProviderPreflightError", "LiveProviderConfig", "REQUIRED_ENV", "load_live_provider_config"]
