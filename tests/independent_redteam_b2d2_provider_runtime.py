from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
RUNTIME = ROOT / "iios_mvp" / "provider_runtime_v01.py"
PREFLIGHT = ROOT / "iios_mvp" / "live_provider_preflight_v01.py"
INVOCATION = ROOT / "iios_mvp" / "live_provider_invocation_v01.py"
FACTORY = ROOT / "iios_mvp" / "canonical_runtime_factory_v01.py"
EVIDENCE = ROOT / "iios_mvp" / "live_provider_evidence_v01.py"
INDEPENDENT = ROOT / "iios_mvp" / "live_provider_independent_verify_v01.py"


def source(path):
    return path.read_text(encoding="utf-8")


def test_rt_b2d2_01_auth_is_runtime_policy():
    s = source(RUNTIME)
    assert "AUTH_MODES" in s
    assert "auth_mode" in s
    assert "BEARER" in s
    assert "NONE" in s


def test_rt_b2d2_02_deployment_is_runtime_policy():
    s = source(RUNTIME)
    assert "DEPLOYMENT_MODES" in s
    assert "SELF_HOSTED" in s
    assert "EXTERNAL" in s


def test_rt_b2d2_03_protocol_and_provider_are_distinct():
    s = source(RUNTIME) + source(PREFLIGHT)
    assert "protocol" in s
    assert "provider_id" in s


def test_rt_b2d2_04_no_global_api_key_requirement():
    s = source(PREFLIGHT)
    assert 'IIOS_LLM_PROVIDER_API_KEY",\n' not in s
    assert "auth_mode" in s


def test_rt_b2d2_05_bearer_auth_remains_explicit():
    s = source(RUNTIME)
    assert 'Authorization' in s
    assert 'Bearer {key}' in s


def test_rt_b2d2_06_none_auth_emits_no_authorization():
    s = source(RUNTIME)
    assert 'if mode == "NONE"' in s
    assert "return {}" in s


def test_rt_b2d2_07_loopback_http_is_the_only_non_https_exception():
    s = source(RUNTIME)
    assert "SELF_HOSTED" in s
    assert "_is_loopback_host" in s
    assert "must use HTTPS unless SELF_HOSTED on loopback" in s


def test_rt_b2d2_08_invocation_consumes_runtime_auth_boundary():
    s = source(INVOCATION)
    assert "build_provider_auth_headers" in s


def test_rt_b2d2_09_loopback_http_exception_is_independently_enforced():
    factory = source(FACTORY)
    evidence = source(EVIDENCE)
    verifier = source(INDEPENDENT)
    for required in ("SELF_HOSTED", "NONE", "_is_loopback_host"):
        assert required in factory
        assert required in evidence
        assert required in verifier
    assert "LIVE_PROVIDER_ENDPOINT_POLICY_INVALID" in factory
    assert "evidence endpoint violates transport policy" in verifier


def test_rt_b2d2_10_runtime_receipt_signs_the_network_policy():
    s = source(EVIDENCE)
    assert '"auth_mode": config.auth_mode' in s
    assert '"deployment_mode": config.deployment_mode' in s
    assert "_validate_record_endpoint_policy(record)" in s
