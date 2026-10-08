import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
PREFLIGHT = ROOT / "iios_mvp/live_provider_preflight_v01.py"
ADAPTER = ROOT / "iios_mvp/live_provider_invocation_v01.py"
REPLAY = ROOT / "iios_mvp/live_provider_replay_v01.py"
EVIDENCE = ROOT / "iios_mvp/live_provider_evidence_v01.py"
RUNTIME = ROOT / "iios_mvp/provider_runtime_v01.py"
REPLAY_SCHEMA = ROOT / "schemas/live_provider_replay_v0.2.schema.json"
EVIDENCE_SCHEMA = ROOT / "schemas/live_provider_evidence_v0.1.schema.json"


def source(p): return p.read_text(encoding="utf-8")


def test_rt_b2d_01_secrets_are_explicit_and_fail_closed():
    s = source(PREFLIGHT)
    for token in ("IIOS_LLM_PROVIDER_API_KEY", "IIOS_LLM_PROVIDER_MODEL", "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64"):
        assert token in s
    assert "configuration missing" in s


def test_rt_b2d_02_endpoint_security_is_delegated_to_runtime_boundary():
    s = source(PREFLIGHT)
    runtime = source(RUNTIME)
    assert "validate_provider_runtime_policy" in s
    assert "must use HTTPS unless SELF_HOSTED on loopback" in runtime


def test_rt_b2d_03_timeout_is_bounded():
    assert "[1,300]" in source(PREFLIGHT)


def test_rt_b2d_04_real_protocol_is_explicit():
    s = source(ADAPTER)
    assert "OPENAI_RESPONSES" in s
    assert '"store": False' in s


def test_rt_b2d_05_authorization_is_runtime_policy_controlled():
    s = source(ADAPTER)
    runtime = source(RUNTIME)
    assert "build_provider_auth_headers" in s
    assert 'Authorization": f"Bearer {key}"' in runtime
    assert 'if mode == "NONE"' in runtime


def test_rt_b2d_06_request_response_hashes_are_retained():
    s = source(ADAPTER)
    assert "request_sha256" in s and "response_sha256" in s
    assert "response_bytes=body" in s


def test_rt_b2d_07_replay_binds_case_and_request_identity():
    s = source(REPLAY)
    for token in ("run_id", "case_id", "request_id", "cutoff_date", "replay_hash"):
        assert token in s


def test_rt_b2d_08_runtime_attestation_is_signed():
    s = source(EVIDENCE)
    assert "Ed25519PrivateKey" in s
    assert ".sign(" in s
    assert "attestation_hash" in s


def test_rt_b2d_09_runtime_attestation_is_verifiable():
    s = source(EVIDENCE)
    assert "Ed25519PublicKey" in s
    assert ".verify(" in s


def test_rt_b2d_10_no_api_key_persistence_in_evidence():
    s = source(EVIDENCE)
    assert "api_key" not in s


def test_rt_b2d_11_no_decision_authority():
    s = "".join(source(p) for p in (PREFLIGHT, ADAPTER, REPLAY, EVIDENCE))
    for token in ("DECISION_ADMITTED", "HUMAN_APPROVAL_PENDING", "PUBLISHED", "ORDER"):
        assert token not in s


def test_rt_b2d_12_replay_schema_is_closed():
    schema = json.loads(source(REPLAY_SCHEMA))
    assert schema["additionalProperties"] is False


def test_rt_b2d_13_evidence_schema_is_closed():
    schema = json.loads(source(EVIDENCE_SCHEMA))
    assert schema["additionalProperties"] is False


def test_rt_b2d_14_evidence_does_not_claim_provider_signature():
    s = source(EVIDENCE)
    assert "runtime_public_key_b64" in s
    assert "signature_algorithm" in s
    assert "provider_signature" not in s.lower()


def test_rt_b2d_15_mvp_boundary_is_preserved():
    s = Path(ROOT/"docs/iios/B2_D_LIVE_PROVIDER_PREFLIGHT_20261008.md").read_text(encoding="utf-8")
    assert "B2-E" in s
    assert "SEMANTIC_ADMITTED" in s
    assert "BLOCKED" in s
