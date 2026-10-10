import base64
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.live_provider_evidence_v01 import (
    build_signed_live_evidence,
    verify_signed_live_evidence,
)
from iios_mvp.live_provider_invocation_v01 import build_provider_payload, LiveProviderResponse, parse_json_response
from iios_mvp.live_provider_preflight_v01 import (
    LiveProviderConfig,
    LiveProviderPreflightError,
    load_live_provider_config,
)
from iios_mvp.live_provider_replay_v01 import build_replay_record, verify_replay_record


PRIVATE_B64 = base64.b64encode(b"x" * 32).decode()


def env():
    return {
        "IIOS_LLM_PROVIDER_BASE_URL": "https://api.openai.com/v1/responses",
        "IIOS_LLM_PROVIDER_API_KEY": "secret",
        "IIOS_LLM_PROVIDER_MODEL": "test-model",
        "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64": PRIVATE_B64,
        "IIOS_LLM_PROVIDER_ID": "openai",
        "IIOS_LLM_PROVIDER_VERSION": "responses-contract-2026-10-08",
        "IIOS_LLM_PROVIDER_PROTOCOL": "OPENAI_RESPONSES",
        "IIOS_LLM_PROVIDER_TIMEOUT_SECONDS": "30",
    }


def test_live_provider_config_is_loaded():
    cfg = load_live_provider_config(env())
    assert cfg.base_url.endswith("/v1/responses")
    assert cfg.provider_id == "openai"
    assert cfg.protocol == "OPENAI_RESPONSES"
    assert cfg.auth_mode == "BEARER"
    assert cfg.deployment_mode == "EXTERNAL"


def test_live_provider_config_fails_closed_without_key():
    values = env()
    values.pop("IIOS_LLM_PROVIDER_API_KEY")
    with pytest.raises(LiveProviderPreflightError, match="requires an API key"):
        load_live_provider_config(values)


def test_live_provider_config_requires_https():
    values = env()
    values["IIOS_LLM_PROVIDER_BASE_URL"] = "http://provider.example/v1/responses"
    with pytest.raises(LiveProviderPreflightError, match="must use HTTPS"):
        load_live_provider_config(values)


def test_live_provider_config_allows_self_hosted_loopback_http_without_api_key():
    values = env()
    values["IIOS_LLM_PROVIDER_BASE_URL"] = "http://127.0.0.1:11434/v1/responses"
    values["IIOS_LLM_PROVIDER_AUTH_MODE"] = "NONE"
    values["IIOS_LLM_PROVIDER_DEPLOYMENT_MODE"] = "SELF_HOSTED"
    values.pop("IIOS_LLM_PROVIDER_API_KEY")
    cfg = load_live_provider_config(values)
    assert cfg.auth_mode == "NONE"
    assert cfg.deployment_mode == "SELF_HOSTED"
    assert cfg.base_url == "http://127.0.0.1:11434/v1/responses"


@pytest.mark.parametrize(
    "endpoint,auth_mode,deployment_mode",
    [
        ("http://127.0.0.1:11434/v1/responses", "BEARER", "SELF_HOSTED"),
        ("http://127.0.0.1:11434/v1/responses", "NONE", "EXTERNAL"),
        ("http://192.168.1.20:11434/v1/responses", "NONE", "SELF_HOSTED"),
        ("http://provider.example/v1/responses", "NONE", "SELF_HOSTED"),
    ],
)
def test_live_provider_config_rejects_http_outside_loopback_no_auth(
    endpoint, auth_mode, deployment_mode
):
    values = env()
    values["IIOS_LLM_PROVIDER_BASE_URL"] = endpoint
    values["IIOS_LLM_PROVIDER_AUTH_MODE"] = auth_mode
    values["IIOS_LLM_PROVIDER_DEPLOYMENT_MODE"] = deployment_mode
    if auth_mode == "NONE":
        values.pop("IIOS_LLM_PROVIDER_API_KEY")
    with pytest.raises(LiveProviderPreflightError):
        load_live_provider_config(values)


def test_provider_protocol_is_explicit():
    values = env()
    values["IIOS_LLM_PROVIDER_PROTOCOL"] = "GENERIC_JSON"
    with pytest.raises(LiveProviderPreflightError, match="unsupported"):
        load_live_provider_config(values)


def test_runtime_private_key_must_be_32_bytes():
    values = env()
    values["IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64"] = base64.b64encode(b"short").decode()
    with pytest.raises(LiveProviderPreflightError, match="32 bytes"):
        load_live_provider_config(values)


def test_openai_responses_payload_is_concrete():
    cfg = load_live_provider_config(env())
    payload = build_provider_payload(config=cfg, prompt="hello")
    assert payload["model"] == "test-model"
    assert payload["store"] is False
    assert payload["input"][0]["role"] == "user"
    assert payload["input"][0]["content"][0]["type"] == "input_text"


def test_invalid_provider_response_is_rejected():
    response = LiveProviderResponse(
        request_sha256="a" * 64,
        response_sha256="b" * 64,
        response_bytes=b"not-json",
        http_status=200,
        content_type="application/json",
    )
    with pytest.raises(Exception, match="not valid UTF-8 JSON|not valid"):
        parse_json_response(response)


def test_provider_replay_hash_is_deterministic():
    record = build_replay_record(
        provider_id="openai",
        provider_version="responses-contract-2026-10-08",
        protocol="OPENAI_RESPONSES",
        model="test-model",
        endpoint="https://api.openai.com/v1/responses",
        run_id="run-1",
        case_id="case-1",
        request_id="request-1",
        cutoff_date="2026-10-08",
        request_payload={"input": "hello"},
        response_bytes_b64=base64.b64encode(b'{"status":"PASS"}').decode(),
        http_status=200,
        content_type="application/json",
        created_at="2026-10-08T00:00:00+00:00",
    )
    verify_replay_record(record)
    assert len(record["replay_hash"]) == 64


def test_provider_replay_tampering_is_blocked():
    record = build_replay_record(
        provider_id="openai",
        provider_version="responses-contract-2026-10-08",
        protocol="OPENAI_RESPONSES",
        model="test-model",
        endpoint="https://api.openai.com/v1/responses",
        run_id="run-1",
        case_id="case-1",
        request_id="request-1",
        cutoff_date="2026-10-08",
        request_payload={"input": "hello"},
        response_bytes_b64=base64.b64encode(b'{"status":"PASS"}').decode(),
        http_status=200,
        content_type="application/json",
        created_at="2026-10-08T00:00:00+00:00",
    )
    tampered = dict(record)
    tampered["response_bytes_b64"] = base64.b64encode(b'{"status":"FAIL"}').decode()
    with pytest.raises(ValueError, match="replay hash mismatch"):
        verify_replay_record(tampered)


def test_live_evidence_signature_and_replay_binding():
    private = base64.b64encode(b"z" * 32).decode()
    cfg = LiveProviderConfig(
        base_url="https://provider.example/v1/responses",
        api_key="secret",
        model="test-model",
        runtime_private_key_b64=private,
        provider_id="provider-fixture",
        provider_version="fixture-1",
        protocol="OPENAI_RESPONSES",
        timeout_seconds=30,
    )
    from unittest.mock import patch
    from iios_mvp.live_provider_invocation_v01 import LiveProviderResponse
    mocked = LiveProviderResponse(
        request_sha256="0" * 64,
        response_sha256=base64.b64encode(b'{"status":"LIVE_PROVIDER_OK"}').decode()[:64].ljust(64, "0"),
        response_bytes=b'{"status":"LIVE_PROVIDER_OK"}',
        http_status=200,
        content_type="application/json",
    )
    import hashlib
    body = json.dumps(build_provider_payload(config=cfg, prompt="hello"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    mocked = LiveProviderResponse(
        request_sha256=hashlib.sha256(body).hexdigest(),
        response_sha256=hashlib.sha256(mocked.response_bytes).hexdigest(),
        response_bytes=mocked.response_bytes,
        http_status=200,
        content_type="application/json",
    )
    with patch("iios_mvp.live_provider_evidence_v01.invoke_live_provider", return_value=mocked):
        record = build_signed_live_evidence(
            config=cfg,
            run_id="run-1",
            case_id="case-1",
            request_id="request-1",
            cutoff_date="2026-10-08",
            prompt="hello",
        )
    verify_signed_live_evidence(record)


def test_self_hosted_loopback_signed_receipt_passes_independent_verifier():
    from unittest.mock import patch
    import hashlib
    from iios_mvp.live_provider_independent_verify_v01 import verify_live_evidence
    cfg = LiveProviderConfig(
        base_url="http://127.0.0.1:11434/v1/responses",
        api_key="",
        model="test-model",
        runtime_private_key_b64=base64.b64encode(b"z" * 32).decode(),
        provider_id="ollama-self-hosted",
        provider_version="ollama-test;model/test-model",
        protocol="OPENAI_RESPONSES",
        timeout_seconds=30,
        auth_mode="NONE",
        deployment_mode="SELF_HOSTED",
    )
    payload = build_provider_payload(config=cfg, prompt="hello")
    request_bytes = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    response_body = b'{"status":"completed","output_text":"{}"}'
    mocked = LiveProviderResponse(
        request_sha256=hashlib.sha256(request_bytes).hexdigest(),
        response_sha256=hashlib.sha256(response_body).hexdigest(),
        response_bytes=response_body,
        http_status=200,
        content_type="application/json",
    )
    with patch("iios_mvp.live_provider_evidence_v01.invoke_live_provider", return_value=mocked):
        record = build_signed_live_evidence(
            config=cfg,
            run_id="local-run",
            case_id="local-case",
            request_id="local-request",
            cutoff_date="2026-10-10",
            prompt="hello",
        )
    verify_signed_live_evidence(record)
    verified = verify_live_evidence(
        record,
        schema_path=Path(__file__).parents[1] / "schemas/live_provider_evidence_v0.1.schema.json",
    )
    assert record["auth_mode"] == "NONE"
    assert record["deployment_mode"] == "SELF_HOSTED"
    assert verified["status"] == "INDEPENDENT_VERIFIED"


def test_live_evidence_tampering_is_blocked():
    private = base64.b64encode(b"z" * 32).decode()
    cfg = LiveProviderConfig(
        base_url="https://provider.example/v1/responses",
        api_key="secret",
        model="test-model",
        runtime_private_key_b64=private,
        provider_id="provider-fixture",
        provider_version="fixture-1",
        protocol="OPENAI_RESPONSES",
    )
    from unittest.mock import patch
    import hashlib
    payload = build_provider_payload(config=cfg, prompt="hello")
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    response_body = b'{"status":"LIVE_PROVIDER_OK"}'
    mocked = LiveProviderResponse(
        request_sha256=hashlib.sha256(body).hexdigest(),
        response_sha256=hashlib.sha256(response_body).hexdigest(),
        response_bytes=response_body,
        http_status=200,
        content_type="application/json",
    )
    with patch("iios_mvp.live_provider_evidence_v01.invoke_live_provider", return_value=mocked):
        record = build_signed_live_evidence(
            config=cfg,
            run_id="run-1",
            case_id="case-1",
            request_id="request-1",
            cutoff_date="2026-10-08",
            prompt="hello",
        )
    tampered = dict(record)
    tampered["response_bytes_b64"] = base64.b64encode(b'{"status":"ATTACK"}').decode()
    with pytest.raises(ValueError, match="signature failed|hash mismatch|replay binding mismatch"):
        verify_signed_live_evidence(tampered)
