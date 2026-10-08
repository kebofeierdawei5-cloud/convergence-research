import ast
import json
from pathlib import Path

ROOT=Path(__file__).parents[1]
PREFLIGHT=ROOT/"iios_mvp/live_provider_preflight_v01.py"
ADAPTER=ROOT/"iios_mvp/live_provider_invocation_v01.py"
REPLAY=ROOT/"iios_mvp/live_provider_replay_v01.py"
SCHEMA=ROOT/"schemas/live_provider_replay_v0.1.schema.json"


def text(p): return p.read_text(encoding="utf-8")


def test_rt_b2d_01_secret_names_are_explicit_and_fail_closed():
    s=text(PREFLIGHT)
    for token in ("IIOS_LLM_PROVIDER_API_KEY","IIOS_LLM_PROVIDER_MODEL","IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64"):
        assert token in s
    assert "configuration missing" in s


def test_rt_b2d_02_https_only():
    assert 'parsed.scheme != "https"' in text(PREFLIGHT)


def test_rt_b2d_03_timeout_is_bounded():
    s=text(PREFLIGHT)
    assert "[1,300]" in s


def test_rt_b2d_04_provider_request_is_https_bearer_post():
    s=text(ADAPTER)
    assert 'Authorization": f"Bearer {config.api_key}"' in s
    assert 'method="POST"' in s


def test_rt_b2d_05_request_and_response_hashes_exist():
    s=text(ADAPTER)
    assert "request_sha256" in s
    assert "response_sha256" in s


def test_rt_b2d_06_raw_response_bytes_are_preserved():
    s=text(ADAPTER)
    assert "response_bytes=body" in s


def test_rt_b2d_07_replay_hash_covers_request_and_response():
    s=text(REPLAY)
    assert "request_sha256" in s
    assert "response_sha256" in s
    assert "response_bytes_b64" in s
    assert "replay_hash" in s


def test_rt_b2d_08_replay_verification_rebuilds_record():
    assert "expected = build_replay_record(" in text(REPLAY)


def test_rt_b2d_09_no_decision_authority():
    s=text(ADAPTER)+text(PREFLIGHT)+text(REPLAY)
    for token in ("DECISION_ADMITTED","HUMAN_APPROVAL_PENDING","PUBLISHED","ORDER"):
        assert token not in s


def test_rt_b2d_10_replay_schema_is_closed():
    schema=json.loads(text(SCHEMA))
    assert schema["additionalProperties"] is False


def test_rt_b2d_11_replay_schema_binds_hashes():
    schema=json.loads(text(SCHEMA))
    for field in ("request_sha256","response_sha256","replay_hash"):
        assert schema["properties"][field]["pattern"] == "^[0-9a-f]{64}$"


def test_rt_b2d_12_live_execution_is_not_claimed_by_preflight():
    s=Path(ROOT/"docs/iios/B2_D_LIVE_PROVIDER_PREFLIGHT_20261008.md").read_text(encoding="utf-8")
    assert "BLOCKED" in s
    assert "does not" in s
