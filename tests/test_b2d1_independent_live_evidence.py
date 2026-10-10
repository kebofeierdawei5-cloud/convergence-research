import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iios_mvp.live_provider_independent_verify_v01 import (
    IndependentVerificationError,
    verify_live_evidence,
)

ROOT = Path(__file__).parents[1]


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_record(*, endpoint="https://provider.example/v1/responses", auth_mode=None, deployment_mode=None):
    private_key = Ed25519PrivateKey.generate()
    public_key_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    request_payload = {
        "model": "test-model",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
        "store": False,
    }
    response_bytes = b'{"status":"LIVE_PROVIDER_OK","id":"resp_123"}'
    replay_core = {
        "schema_version": "IIOS-LIVE-PROVIDER-REPLAY-0.2",
        "provider_id": "provider-fixture",
        "provider_version": "fixture-1",
        "protocol": "OPENAI_RESPONSES",
        "model": "test-model",
        "endpoint": endpoint,
        "run_id": "run-1",
        "case_id": "case-1",
        "request_id": "request-1",
        "cutoff_date": "2026-10-08",
        "request_sha256": hashlib.sha256(canonical_bytes(request_payload)).hexdigest(),
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "request_payload": request_payload,
        "response_bytes_b64": base64.b64encode(response_bytes).decode("ascii"),
        "http_status": 200,
        "content_type": "application/json",
        "created_at": "2026-10-08T00:00:00+00:00",
    }
    core = {
        "schema_version": "IIOS-LIVE-PROVIDER-EVIDENCE-0.1",
        "status": "LIVE_RESPONSE_CAPTURED",
        "run_id": "run-1",
        "case_id": "case-1",
        "request_id": "request-1",
        "cutoff_date": "2026-10-08",
        "provider_id": "provider-fixture",
        "provider_version": "fixture-1",
        "protocol": "OPENAI_RESPONSES",
        "model": "test-model",
        "endpoint": "https://provider.example/v1/responses",
        "request_sha256": replay_core["request_sha256"],
        "response_sha256": replay_core["response_sha256"],
        "request_payload": request_payload,
        "response_bytes_b64": replay_core["response_bytes_b64"],
        "http_status": 200,
        "content_type": "application/json",
        "replay_hash": hashlib.sha256(canonical_bytes(replay_core)).hexdigest(),
        "runtime_public_key_b64": public_key_b64,
        "created_at": replay_core["created_at"],
    }
    if auth_mode is not None:
        core["auth_mode"] = auth_mode
    if deployment_mode is not None:
        core["deployment_mode"] = deployment_mode
    signature = private_key.sign(canonical_bytes(core))
    return {
        **core,
        "attestation_hash": hashlib.sha256(canonical_bytes(core)).hexdigest(),
        "signature_algorithm": "Ed25519",
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }


def test_independent_verifier_accepts_valid_record():
    record = build_record()
    result = verify_live_evidence(
        record,
        schema_path=ROOT / "schemas/live_provider_evidence_v0.1.schema.json",
    )
    assert result["status"] == "INDEPENDENT_VERIFIED"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.__setitem__("response_bytes_b64", base64.b64encode(b'{"status":"ATTACK"}').decode("ascii")),
        lambda r: r.__setitem__("request_payload", {"model": "tampered"}),
        lambda r: r.__setitem__("signature_b64", base64.b64encode(b"x" * 64).decode("ascii")),
        lambda r: r.__setitem__("endpoint", "http://provider.example/v1/responses"),
    ],
)
def test_independent_verifier_blocks_tampering(mutation):
    record = build_record()
    mutation(record)
    with pytest.raises(IndependentVerificationError):
        verify_live_evidence(
            record,
            schema_path=ROOT / "schemas/live_provider_evidence_v0.1.schema.json",
        )


def test_independent_verifier_rejects_unknown_field():
    record = build_record()
    record["unexpected"] = "forged"
    with pytest.raises(IndependentVerificationError, match="schema validation"):
        verify_live_evidence(
            record,
            schema_path=ROOT / "schemas/live_provider_evidence_v0.1.schema.json",
        )


def test_independent_verifier_has_no_runtime_provider_dependency():
    source = (ROOT / "iios_mvp/live_provider_independent_verify_v01.py").read_text(encoding="utf-8")
    assert "live_provider_evidence_v01" not in source
    assert "live_provider_invocation_v01" not in source
    assert "live_provider_replay_v01" not in source


def test_independent_verifier_accepts_self_hosted_loopback_http_without_auth():
    record = build_record(
        endpoint="http://127.0.0.1:11434/v1/responses",
        auth_mode="NONE",
        deployment_mode="SELF_HOSTED",
    )
    result = verify_live_evidence(
        record,
        schema_path=ROOT / "schemas/live_provider_evidence_v0.1.schema.json",
    )
    assert result["status"] == "INDEPENDENT_VERIFIED"


@pytest.mark.parametrize(
    "endpoint,auth_mode,deployment_mode",
    [
        ("http://provider.example/v1/responses", "NONE", "SELF_HOSTED"),
        ("http://192.168.1.20:11434/v1/responses", "NONE", "SELF_HOSTED"),
        ("http://127.0.0.1:11434/v1/responses", "BEARER", "SELF_HOSTED"),
        ("http://127.0.0.1:11434/v1/responses", "NONE", "EXTERNAL"),
        ("http://127.0.0.1:11434/v1/responses", None, None),
    ],
)
def test_independent_verifier_rejects_http_outside_narrow_local_policy(
    endpoint, auth_mode, deployment_mode
):
    record = build_record(
        endpoint=endpoint,
        auth_mode=auth_mode,
        deployment_mode=deployment_mode,
    )
    with pytest.raises(IndependentVerificationError):
        verify_live_evidence(
            record,
            schema_path=ROOT / "schemas/live_provider_evidence_v0.1.schema.json",
        )
