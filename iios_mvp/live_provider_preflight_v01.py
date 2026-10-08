from __future__ import annotations

from dataclasses import dataclass
import base64
import os
from urllib.parse import urlparse


class LiveProviderPreflightError(ValueError):
    """Raised when live-provider runtime configuration is not admissible."""


@dataclass(frozen=True)
class LiveProviderConfig:
    base_url: str
    api_key: str
    model: str
    runtime_private_key_b64: str
    timeout_seconds: int = 30


REQUIRED_ENV = (
    "IIOS_LLM_PROVIDER_BASE_URL",
    "IIOS_LLM_PROVIDER_API_KEY",
    "IIOS_LLM_PROVIDER_MODEL",
    "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64",
)


def load_live_provider_config(env: dict[str, str] | None = None) -> LiveProviderConfig:
    values = os.environ if env is None else env
    missing = [name for name in REQUIRED_ENV if not str(values.get(name, "")).strip()]
    if missing:
        raise LiveProviderPreflightError(
            "live provider configuration missing: " + ", ".join(missing)
        )
    base_url = str(values["IIOS_LLM_PROVIDER_BASE_URL"]).strip()
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise LiveProviderPreflightError("IIOS_LLM_PROVIDER_BASE_URL must be an https URL")
    model = str(values["IIOS_LLM_PROVIDER_MODEL"]).strip()
    api_key = str(values["IIOS_LLM_PROVIDER_API_KEY"]).strip()
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
        timeout_seconds=timeout_seconds,
    )


__all__ = ["LiveProviderPreflightError", "LiveProviderConfig", "REQUIRED_ENV", "load_live_provider_config"]
