import base64
import json

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.live_provider_preflight_v01 import (
    LiveProviderPreflightError,
    load_live_provider_config,
)
from iios_mvp.live_provider_invocation_v01 import LiveProviderResponse, parse_json_response
from iios_mvp.live_provider_replay_v01 import build_replay_record, verify_replay_record


PRIVATE_B64 = base64.b64encode(b"x" * 32).decode()


def env():
    return {
        "IIOS_LLM_PROVIDER_BASE_URL": "https://provider.example/v1/semantic",
        "IIOS_LLM_PROVIDER_API_KEY": "secret",
        "IIOS_LLM_PROVIDER_MODEL": "model-1",
        "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64": PRIVATE_B64,
        "IIOS_LLM_PROVIDER_TIMEOUT_SECONDS": "30",
    }


def test_live_provider_config_is_loaded():
    cfg = load_live_provider_config(env())
    assert cfg.base_url.endswith("/v1/semantic")
    assert cfg.timeout_seconds == 30


def test_live_provider_config_fails_closed_without_key():
    values = env()
    values.pop("IIOS_LLM_PROVIDER_API_KEY")
    with pytest.raises(LiveProviderPreflightError, match="configuration missing"):
        load_live_provider_config(values)


def test_live_provider_config_requires_https():
    values = env()
    values["IIOS_LLM_PROVIDER_BASE_URL"] = "http://provider.example/v1/semantic"
    with pytest.raises(LiveProviderPreflightError, match="https URL"):
        load_live_provider_config(values)


def test_runtime_private_key_must_be_32_bytes():
    values = env()
    values["IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64"] = base64.b64encode(b"short").decode()
    with pytest.raises(LiveProviderPreflightError, match="32 bytes"):
        load_live_provider_config(values)


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
        provider_id="provider-1",
        provider_version="1.0",
        model="model-1",
        endpoint="https://provider.example/v1/semantic",
        request_payload={"input": "hello"},
        response_bytes_b64=base64.b64encode(b'{"status":"PASS"}').decode(),
        http_status=200,
        created_at="2026-10-08T00:00:00+00:00",
    )
    verify_replay_record(record)
    assert len(record["replay_hash"]) == 64


def test_provider_replay_tampering_is_blocked():
    record = build_replay_record(
        provider_id="provider-1",
        provider_version="1.0",
        model="model-1",
        endpoint="https://provider.example/v1/semantic",
        request_payload={"input": "hello"},
        response_bytes_b64=base64.b64encode(b'{"status":"PASS"}').decode(),
        http_status=200,
        created_at="2026-10-08T00:00:00+00:00",
    )
    tampered = dict(record)
    tampered["response_bytes_b64"] = base64.b64encode(b'{"status":"FAIL"}').decode()
    with pytest.raises(ValueError, match="replay hash mismatch"):
        verify_replay_record(tampered)


def test_replay_hash_binds_request_and_response():
    first = build_replay_record(
        provider_id="provider-1", provider_version="1.0", model="model-1",
        endpoint="https://provider.example/v1/semantic",
        request_payload={"input": "hello"},
        response_bytes_b64=base64.b64encode(b'{"status":"PASS"}').decode(),
        http_status=200, created_at="2026-10-08T00:00:00+00:00",
    )
    second = build_replay_record(
        provider_id="provider-1", provider_version="1.0", model="model-1",
        endpoint="https://provider.example/v1/semantic",
        request_payload={"input": "changed"},
        response_bytes_b64=base64.b64encode(b'{"status":"PASS"}').decode(),
        http_status=200, created_at="2026-10-08T00:00:00+00:00",
    )
    assert first["request_sha256"] != second["request_sha256"]


def test_live_provider_response_schema_shape():
    payload = {
        "request_payload": {"input": "hello"},
        "response_bytes_b64": base64.b64encode(b'{"status":"PASS"}').decode(),
    }
    assert set(payload) == {"request_payload", "response_bytes_b64"}
