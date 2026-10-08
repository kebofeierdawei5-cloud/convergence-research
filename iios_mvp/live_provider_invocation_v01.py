from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from iios_mvp.live_provider_preflight_v01 import LiveProviderConfig


@dataclass(frozen=True)
class LiveProviderResponse:
    request_sha256: str
    response_sha256: str
    response_bytes: bytes
    http_status: int
    content_type: str


class LiveProviderInvocationError(RuntimeError):
    """Raised when a configured live provider invocation fails."""


def _canonical_request_body(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def invoke_live_provider(
    *,
    config: LiveProviderConfig,
    payload: Mapping[str, Any],
) -> LiveProviderResponse:
    request_body = _canonical_request_body(payload)
    request_hash = hashlib.sha256(request_body).hexdigest()
    req = Request(
        config.base_url,
        data=request_body,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=config.timeout_seconds) as response:
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
    "invoke_live_provider",
    "parse_json_response",
]
