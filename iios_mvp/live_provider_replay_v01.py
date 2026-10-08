from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json


@dataclass(frozen=True)
class ProviderReplayRecord:
    schema_version: str
    provider_id: str
    provider_version: str
    model: str
    endpoint: str
    request_sha256: str
    response_sha256: str
    request_payload: Mapping[str, Any]
    response_bytes_b64: str
    http_status: int
    created_at: str
    replay_hash: str


REPLAY_SCHEMA_VERSION = "IIOS-LIVE-PROVIDER-REPLAY-0.1"


def build_replay_record(
    *,
    provider_id: str,
    provider_version: str,
    model: str,
    endpoint: str,
    request_payload: Mapping[str, Any],
    response_bytes_b64: str,
    http_status: int,
    created_at: str,
) -> dict[str, Any]:
    import base64
    try:
        response_bytes = base64.b64decode(response_bytes_b64, validate=True)
    except Exception as exc:
        raise ValueError("response_bytes_b64 must be valid base64") from exc
    request_bytes = json.dumps(
        request_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    core = {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "provider_id": provider_id,
        "provider_version": provider_version,
        "model": model,
        "endpoint": endpoint,
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "request_payload": dict(request_payload),
        "response_bytes_b64": response_bytes_b64,
        "http_status": int(http_status),
        "created_at": created_at,
    }
    replay_hash = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**core, "replay_hash": replay_hash}


def verify_replay_record(record: Mapping[str, Any]) -> None:
    expected = build_replay_record(
        provider_id=str(record["provider_id"]),
        provider_version=str(record["provider_version"]),
        model=str(record["model"]),
        endpoint=str(record["endpoint"]),
        request_payload=record["request_payload"],
        response_bytes_b64=str(record["response_bytes_b64"]),
        http_status=int(record["http_status"]),
        created_at=str(record["created_at"]),
    )
    if expected["replay_hash"] != record.get("replay_hash"):
        raise ValueError("provider replay hash mismatch")


__all__ = ["ProviderReplayRecord", "REPLAY_SCHEMA_VERSION", "build_replay_record", "verify_replay_record"]
