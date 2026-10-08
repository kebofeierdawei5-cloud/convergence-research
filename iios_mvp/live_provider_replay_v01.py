from __future__ import annotations

from typing import Any, Mapping
import base64
import hashlib
import json


REPLAY_SCHEMA_VERSION = "IIOS-LIVE-PROVIDER-REPLAY-0.2"


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_replay_record(
    *,
    provider_id: str,
    provider_version: str,
    protocol: str,
    model: str,
    endpoint: str,
    run_id: str,
    case_id: str,
    request_id: str,
    cutoff_date: str,
    request_payload: Mapping[str, Any],
    response_bytes_b64: str,
    http_status: int,
    content_type: str,
    created_at: str,
) -> dict[str, Any]:
    try:
        response_bytes = base64.b64decode(response_bytes_b64, validate=True)
    except Exception as exc:
        raise ValueError("response_bytes_b64 must be valid base64") from exc
    request_bytes = _canonical_json(request_payload)
    core = {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "provider_id": provider_id,
        "provider_version": provider_version,
        "protocol": protocol,
        "model": model,
        "endpoint": endpoint,
        "run_id": run_id,
        "case_id": case_id,
        "request_id": request_id,
        "cutoff_date": cutoff_date,
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "request_payload": dict(request_payload),
        "response_bytes_b64": response_bytes_b64,
        "http_status": int(http_status),
        "content_type": content_type,
        "created_at": created_at,
    }
    return {
        **core,
        "replay_hash": hashlib.sha256(_canonical_json(core)).hexdigest(),
    }


def verify_replay_record(record: Mapping[str, Any]) -> None:
    expected = build_replay_record(
        provider_id=str(record["provider_id"]),
        provider_version=str(record["provider_version"]),
        protocol=str(record["protocol"]),
        model=str(record["model"]),
        endpoint=str(record["endpoint"]),
        run_id=str(record["run_id"]),
        case_id=str(record["case_id"]),
        request_id=str(record["request_id"]),
        cutoff_date=str(record["cutoff_date"]),
        request_payload=record["request_payload"],
        response_bytes_b64=str(record["response_bytes_b64"]),
        http_status=int(record["http_status"]),
        content_type=str(record["content_type"]),
        created_at=str(record["created_at"]),
    )
    if expected["replay_hash"] != record.get("replay_hash"):
        raise ValueError("provider replay hash mismatch")
    if expected["request_sha256"] != record.get("request_sha256"):
        raise ValueError("provider replay request hash mismatch")
    if expected["response_sha256"] != record.get("response_sha256"):
        raise ValueError("provider replay response hash mismatch")


__all__ = ["REPLAY_SCHEMA_VERSION", "build_replay_record", "verify_replay_record"]
