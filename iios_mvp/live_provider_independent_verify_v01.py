from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator

VERIFIER_VERSION = "IIOS-LIVE-PROVIDER-INDEPENDENT-VERIFIER-0.1"
REQUIRED_FIELDS = {
    "schema_version",
    "status",
    "run_id",
    "case_id",
    "request_id",
    "cutoff_date",
    "provider_id",
    "provider_version",
    "protocol",
    "model",
    "endpoint",
    "request_sha256",
    "response_sha256",
    "request_payload",
    "response_bytes_b64",
    "http_status",
    "content_type",
    "replay_hash",
    "runtime_public_key_b64",
    "created_at",
    "attestation_hash",
    "signature_algorithm",
    "signature_b64",
}
SIGNATURE_FIELDS = {"attestation_hash", "signature_algorithm", "signature_b64"}

class IndependentVerificationError(ValueError):
    """Raised when a live-provider evidence artifact fails independent verification."""

def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

def _decode_b64(value: str, label: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise IndependentVerificationError(f"{label} must be valid base64") from exc

def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndependentVerificationError("evidence file is not valid UTF-8 JSON") from exc
    if not isinstance(record, Mapping):
        raise IndependentVerificationError("evidence JSON must be an object")
    return record

def _validate_schema(record: Mapping[str, Any], schema_path: Path) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndependentVerificationError("evidence schema could not be loaded") from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda e: list(e.path))
    if errors:
        raise IndependentVerificationError(
            "evidence schema validation failed: " + "; ".join(str(e.message) for e in errors)
        )

def _rebuild_replay_core(record: Mapping[str, Any]) -> dict[str, Any]:
    response_bytes = _decode_b64(str(record["response_bytes_b64"]), "response_bytes_b64")
    request_payload = record["request_payload"]
    if not isinstance(request_payload, Mapping):
        raise IndependentVerificationError("request_payload must be an object")
    request_bytes = _canonical_bytes(request_payload)
    return {
        "schema_version": "IIOS-LIVE-PROVIDER-REPLAY-0.2",
        "provider_id": str(record["provider_id"]),
        "provider_version": str(record["provider_version"]),
        "protocol": str(record["protocol"]),
        "model": str(record["model"]),
        "endpoint": str(record["endpoint"]),
        "run_id": str(record["run_id"]),
        "case_id": str(record["case_id"]),
        "request_id": str(record["request_id"]),
        "cutoff_date": str(record["cutoff_date"]),
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "request_payload": dict(request_payload),
        "response_bytes_b64": str(record["response_bytes_b64"]),
        "http_status": int(record["http_status"]),
        "content_type": str(record["content_type"]),
        "created_at": str(record["created_at"]),
    }

def verify_live_evidence(
    record: Mapping[str, Any],
    *,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    missing = sorted(REQUIRED_FIELDS.difference(record))
    if missing:
        raise IndependentVerificationError(
            "live provider evidence missing fields: " + ", ".join(missing)
        )

    if schema_path is not None:
        _validate_schema(record, schema_path)

    if record["schema_version"] != "IIOS-LIVE-PROVIDER-EVIDENCE-0.1":
        raise IndependentVerificationError("unsupported evidence schema")
    if record["status"] != "LIVE_RESPONSE_CAPTURED":
        raise IndependentVerificationError("evidence is not marked LIVE_RESPONSE_CAPTURED")
    if record["protocol"] != "OPENAI_RESPONSES":
        raise IndependentVerificationError("unsupported provider protocol")
    if urlparse(str(record["endpoint"])).scheme != "https":
        raise IndependentVerificationError("evidence endpoint is not HTTPS")
    if record["signature_algorithm"] != "Ed25519":
        raise IndependentVerificationError("unsupported signature algorithm")

    response_bytes = _decode_b64(str(record["response_bytes_b64"]), "response_bytes_b64")
    if hashlib.sha256(response_bytes).hexdigest() != str(record["response_sha256"]):
        raise IndependentVerificationError("response SHA-256 mismatch")

    request_payload = record["request_payload"]
    if not isinstance(request_payload, Mapping):
        raise IndependentVerificationError("request_payload must be an object")
    request_sha256 = hashlib.sha256(_canonical_bytes(request_payload)).hexdigest()
    if request_sha256 != str(record["request_sha256"]):
        raise IndependentVerificationError("request SHA-256 mismatch")

    core = {key: value for key, value in record.items() if key not in SIGNATURE_FIELDS}
    attestation_hash = hashlib.sha256(_canonical_bytes(core)).hexdigest()
    if attestation_hash != str(record["attestation_hash"]):
        raise IndependentVerificationError("attestation hash mismatch")

    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            _decode_b64(str(record["runtime_public_key_b64"]), "runtime_public_key_b64")
        )
        signature = _decode_b64(str(record["signature_b64"]), "signature_b64")
        public_key.verify(signature, _canonical_bytes(core))
    except IndependentVerificationError:
        raise
    except Exception as exc:
        raise IndependentVerificationError("Ed25519 signature verification failed") from exc

    replay_core = _rebuild_replay_core(record)
    replay_hash = hashlib.sha256(_canonical_bytes(replay_core)).hexdigest()
    if replay_hash != str(record["replay_hash"]):
        raise IndependentVerificationError("replay hash mismatch")
    if replay_core["request_sha256"] != str(record["request_sha256"]):
        raise IndependentVerificationError("replay request hash mismatch")
    if replay_core["response_sha256"] != str(record["response_sha256"]):
        raise IndependentVerificationError("replay response hash mismatch")

    return {
        "status": "INDEPENDENT_VERIFIED",
        "verifier_version": VERIFIER_VERSION,
        "run_id": str(record["run_id"]),
        "case_id": str(record["case_id"]),
        "request_id": str(record["request_id"]),
        "response_sha256": str(record["response_sha256"]),
        "replay_hash": str(record["replay_hash"]),
        "attestation_hash": str(record["attestation_hash"]),
    }

def verify_live_evidence_file(
    evidence_path: str | Path,
    *,
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    evidence = Path(evidence_path)
    schema = (
        Path(schema_path)
        if schema_path is not None
        else Path(__file__).parents[1] / "schemas/live_provider_evidence_v0.1.schema.json"
    )
    return verify_live_evidence(_load_json(evidence), schema_path=schema)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--schema", default="")
    args = parser.parse_args()
    try:
        result = verify_live_evidence_file(
            args.evidence,
            schema_path=args.schema or None,
        )
    except IndependentVerificationError as exc:
        print(json.dumps(
            {
                "status": "INDEPENDENT_VERIFICATION_FAILED",
                "verifier_version": VERIFIER_VERSION,
                "reason": str(exc),
            },
            ensure_ascii=False,
            sort_keys=True,
        ))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
