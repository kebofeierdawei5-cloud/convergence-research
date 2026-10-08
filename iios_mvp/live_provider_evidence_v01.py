from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping
import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from iios_mvp.live_provider_invocation_v01 import build_provider_payload, invoke_live_provider
from iios_mvp.live_provider_preflight_v01 import load_live_provider_config
from iios_mvp.live_provider_replay_v01 import build_replay_record, verify_replay_record

LIVE_PROVIDER_EVIDENCE_SCHEMA_VERSION = "IIOS-LIVE-PROVIDER-EVIDENCE-0.1"


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_private_key(private_key_b64: str) -> Ed25519PrivateKey:
    raw = base64.b64decode(private_key_b64, validate=True)
    if len(raw) != 32:
        raise ValueError("runtime private key must decode to 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(raw)


def _utc(value: str | None = None) -> str:
    parsed = datetime.now(timezone.utc) if value is None else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("created_at must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def build_signed_live_evidence(
    *,
    config: Any,
    run_id: str,
    case_id: str,
    request_id: str,
    cutoff_date: str,
    prompt: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    date.fromisoformat(cutoff_date)
    payload = build_provider_payload(config=config, prompt=prompt)
    response = invoke_live_provider(config=config, payload=payload)
    replay = build_replay_record(
        provider_id=config.provider_id,
        provider_version=config.provider_version,
        protocol=config.protocol,
        model=config.model,
        endpoint=config.base_url,
        run_id=run_id,
        case_id=case_id,
        request_id=request_id,
        cutoff_date=cutoff_date,
        request_payload=payload,
        response_bytes_b64=base64.b64encode(response.response_bytes).decode("ascii"),
        http_status=response.http_status,
        content_type=response.content_type,
        created_at=_utc(created_at),
    )
    verify_replay_record(replay)
    private_key = _load_private_key(config.runtime_private_key_b64)
    public_key_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    core = {
        "schema_version": LIVE_PROVIDER_EVIDENCE_SCHEMA_VERSION,
        "status": "LIVE_RESPONSE_CAPTURED",
        "run_id": run_id,
        "case_id": case_id,
        "request_id": request_id,
        "cutoff_date": cutoff_date,
        "provider_id": config.provider_id,
        "provider_version": config.provider_version,
        "protocol": config.protocol,
        "model": config.model,
        "endpoint": config.base_url,
        "request_sha256": response.request_sha256,
        "response_sha256": response.response_sha256,
        "request_payload": payload,
        "response_bytes_b64": base64.b64encode(response.response_bytes).decode("ascii"),
        "http_status": response.http_status,
        "content_type": response.content_type,
        "replay_hash": replay["replay_hash"],
        "runtime_public_key_b64": public_key_b64,
        "created_at": replay["created_at"],
    }
    attestation_hash = hashlib.sha256(_canonical_bytes(core)).hexdigest()
    signature_b64 = base64.b64encode(private_key.sign(_canonical_bytes(core))).decode("ascii")
    return {**core, "attestation_hash": attestation_hash, "signature_algorithm": "Ed25519", "signature_b64": signature_b64}


def verify_signed_live_evidence(record: Mapping[str, Any]) -> None:
    required = {
        "schema_version","status","run_id","case_id","request_id","cutoff_date",
        "provider_id","provider_version","protocol","model","endpoint",
        "request_sha256","response_sha256","request_payload","response_bytes_b64",
        "http_status","content_type","replay_hash","runtime_public_key_b64","created_at",
        "attestation_hash","signature_algorithm","signature_b64",
    }
    missing = sorted(required.difference(record))
    if missing:
        raise ValueError("live provider evidence missing fields: " + ", ".join(missing))
    if record["schema_version"] != LIVE_PROVIDER_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("unsupported live provider evidence schema")
    if record["status"] != "LIVE_RESPONSE_CAPTURED":
        raise ValueError("live provider evidence status is not admitted")
    if record["signature_algorithm"] != "Ed25519":
        raise ValueError("unsupported live provider evidence signature algorithm")
    core = {k: v for k, v in record.items() if k not in {"attestation_hash","signature_algorithm","signature_b64"}}
    expected_hash = hashlib.sha256(_canonical_bytes(core)).hexdigest()
    if record["attestation_hash"] != expected_hash:
        raise ValueError("live provider evidence attestation hash mismatch")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(record["runtime_public_key_b64"], validate=True)
        )
        public_key.verify(
            base64.b64decode(record["signature_b64"], validate=True),
            _canonical_bytes(core),
        )
    except Exception as exc:
        raise ValueError("live provider evidence signature verification failed") from exc

    response_bytes = base64.b64decode(record["response_bytes_b64"], validate=True)
    if hashlib.sha256(response_bytes).hexdigest() != record["response_sha256"]:
        raise ValueError("live provider evidence response hash mismatch")
    expected_replay = build_replay_record(
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
    if expected_replay["replay_hash"] != record["replay_hash"]:
        raise ValueError("live provider evidence replay binding mismatch")


def run_smoke_from_environment() -> dict[str, Any]:
    config = load_live_provider_config()
    run_id = os.environ.get("IIOS_B2D_LIVE_RUN_ID", "b2d-live-smoke-20261008")
    case_id = os.environ.get("IIOS_B2D_LIVE_CASE_ID", "B2D-LIVE-SMOKE-20261008")
    request_id = os.environ.get("IIOS_B2D_LIVE_REQUEST_ID", "b2d-live-request-20261008")
    cutoff = os.environ.get("IIOS_B2D_LIVE_CUTOFF_DATE", "2026-10-08")
    prompt = os.environ.get(
        "IIOS_B2D_LIVE_SMOKE_PROMPT",
        'Return exactly this JSON object and nothing else: {"status":"LIVE_PROVIDER_OK","marker":"IIOS-B2-D"}',
    )
    record = build_signed_live_evidence(
        config=config,
        run_id=run_id,
        case_id=case_id,
        request_id=request_id,
        cutoff_date=cutoff,
        prompt=prompt,
    )
    verify_signed_live_evidence(record)
    return record


if __name__ == "__main__":
    print(json.dumps(run_smoke_from_environment(), ensure_ascii=False, sort_keys=True, indent=2))


__all__ = [
    "LIVE_PROVIDER_EVIDENCE_SCHEMA_VERSION",
    "build_signed_live_evidence",
    "verify_signed_live_evidence",
    "run_smoke_from_environment",
]
