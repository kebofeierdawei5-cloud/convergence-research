from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from iios_mvp.live_provider_preflight_v01 import LiveProviderConfig
from iios_mvp.provider_runtime_v01 import build_provider_auth_headers


@dataclass(frozen=True)
class LiveProviderResponse:
    request_sha256: str
    response_sha256: str
    response_bytes: bytes
    http_status: int
    content_type: str


class LiveProviderInvocationError(RuntimeError):
    """Raised when a configured live provider invocation fails."""


class _RejectRedirectHandler(HTTPRedirectHandler):
    """Reject every redirect so the configured HTTPS endpoint stays exact."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LiveProviderInvocationError("live provider redirects are not permitted")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_provider_payload(*, config: LiveProviderConfig, prompt: str) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required")
    if config.protocol == "OPENAI_RESPONSES":
        return {
            "model": config.model,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            "store": False,
        }
    raise ValueError("unsupported live provider protocol")


def invoke_live_provider(
    *,
    config: LiveProviderConfig,
    payload: Mapping[str, Any],
) -> LiveProviderResponse:
    request_body = _canonical_json(payload)
    request_hash = hashlib.sha256(request_body).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    headers.update(
        build_provider_auth_headers(
            auth_mode=config.auth_mode,
            api_key=config.api_key,
        )
    )
    req = Request(
        config.base_url,
        data=request_body,
        headers=headers,
        method="POST",
    )
    try:
        opener = build_opener(_RejectRedirectHandler)
        with opener.open(req, timeout=config.timeout_seconds) as response:
            body = response.read()
            return LiveProviderResponse(
                request_sha256=request_hash,
                response_sha256=hashlib.sha256(body).hexdigest(),
                response_bytes=body,
                http_status=int(response.status),
                content_type=str(response.headers.get("Content-Type", "")),
            )
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise LiveProviderInvocationError("live provider invocation failed") from exc


def parse_json_response(response: LiveProviderResponse) -> Mapping[str, Any]:
    try:
        parsed = json.loads(response.response_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveProviderInvocationError("live provider response is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise LiveProviderInvocationError("live provider response JSON must be an object")
    return parsed


__all__ = [
    "LiveProviderResponse",
    "LiveProviderInvocationError",
    "build_provider_payload",
    "invoke_live_provider",
    "parse_json_response",
]
