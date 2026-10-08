from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from urllib.parse import urlparse


PROVIDER_RUNTIME_VERSION = "IIOS-PROVIDER-RUNTIME-0.1"
AUTH_MODES = {"BEARER", "NONE"}
DEPLOYMENT_MODES = {"EXTERNAL", "SELF_HOSTED"}
PROTOCOLS = {"OPENAI_RESPONSES"}


class ProviderRuntimeBoundaryError(ValueError):
    """Raised when a provider-neutral runtime boundary is not admissible."""


@dataclass(frozen=True)
class ProviderRuntimePolicy:
    auth_mode: str = "BEARER"
    deployment_mode: str = "EXTERNAL"


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.strip().lower().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def validate_provider_runtime_policy(
    *,
    base_url: str,
    protocol: str,
    auth_mode: str = "BEARER",
    deployment_mode: str = "EXTERNAL",
) -> ProviderRuntimePolicy:
    protocol = str(protocol).strip().upper()
    auth_mode = str(auth_mode).strip().upper()
    deployment_mode = str(deployment_mode).strip().upper()

    if protocol not in PROTOCOLS:
        raise ProviderRuntimeBoundaryError("unsupported provider protocol")
    if auth_mode not in AUTH_MODES:
        raise ProviderRuntimeBoundaryError("unsupported provider auth mode")
    if deployment_mode not in DEPLOYMENT_MODES:
        raise ProviderRuntimeBoundaryError("unsupported provider deployment mode")

    parsed = urlparse(str(base_url).strip())
    if not parsed.netloc:
        raise ProviderRuntimeBoundaryError("provider endpoint must include a host")

    if parsed.scheme == "https":
        return ProviderRuntimePolicy(
            auth_mode=auth_mode,
            deployment_mode=deployment_mode,
        )

    if (
        parsed.scheme == "http"
        and deployment_mode == "SELF_HOSTED"
        and _is_loopback_host(parsed.hostname)
    ):
        return ProviderRuntimePolicy(
            auth_mode=auth_mode,
            deployment_mode=deployment_mode,
        )

    raise ProviderRuntimeBoundaryError(
        "provider endpoint must use HTTPS unless SELF_HOSTED on loopback"
    )


def build_provider_auth_headers(*, auth_mode: str, api_key: str) -> dict[str, str]:
    mode = str(auth_mode).strip().upper()
    if mode == "NONE":
        if str(api_key).strip():
            raise ProviderRuntimeBoundaryError(
                "auth_mode NONE must not receive an API key"
            )
        return {}
    if mode == "BEARER":
        key = str(api_key).strip()
        if not key:
            raise ProviderRuntimeBoundaryError(
                "auth_mode BEARER requires an API key"
            )
        return {"Authorization": f"Bearer {key}"}
    raise ProviderRuntimeBoundaryError("unsupported provider auth mode")


__all__ = [
    "PROVIDER_RUNTIME_VERSION",
    "AUTH_MODES",
    "DEPLOYMENT_MODES",
    "PROTOCOLS",
    "ProviderRuntimeBoundaryError",
    "ProviderRuntimePolicy",
    "validate_provider_runtime_policy",
    "build_provider_auth_headers",
]
