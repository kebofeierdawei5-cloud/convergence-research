import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.iios_d1a_host_acceptance_preflight_v01 import build_preflight_report


def _env(tmp_path: Path):
    bundle = tmp_path / "bundles"; bundle.mkdir()
    data = tmp_path / "data"; data.mkdir()
    output = tmp_path / "outputs"
    admission = tmp_path / "admissions"; admission.mkdir()
    key = Ed25519PrivateKey.generate()
    private = base64.b64encode(key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )).decode("ascii")
    public = base64.b64encode(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )).decode("ascii")
    values = {
        "IIOS_HOST_BUNDLE_ROOT":str(bundle),
        "IIOS_HOST_DATA_ROOT":str(data),
        "IIOS_HOST_OUTPUT_ROOT":str(output),
        "IIOS_HOST_AUTH_TOKEN":"t" * 48,
        "IIOS_HOST_BIND":"127.0.0.1",
        "IIOS_HOST_PORT":"18765",
        "IIOS_CANONICAL_RUNTIME_FACTORY":"iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime",
        "IIOS_CANONICAL_ADMISSION_ROOT":str(admission),
        "IIOS_LLM_PROVIDER_BASE_URL":"http://127.0.0.1:11434",
        "IIOS_LLM_PROVIDER_MODEL":"test-model-name",
        "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64":private,
        "IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64":public,
        "IIOS_LLM_PROVIDER_ID":"local-ollama",
        "IIOS_LLM_PROVIDER_VERSION":"test",
        "IIOS_LLM_PROVIDER_PROTOCOL":"OPENAI_RESPONSES",
        "IIOS_LLM_PROVIDER_AUTH_MODE":"NONE",
        "IIOS_LLM_PROVIDER_DEPLOYMENT_MODE":"SELF_HOSTED",
    }
    return values, private, public


def test_preflight_pass_never_claims_production_acceptance_or_prints_secrets(tmp_path):
    env, private, public = _env(tmp_path)
    report = build_preflight_report(env)
    encoded = json.dumps(report)
    assert report["status"] == "CONFIG_PREFLIGHT_PASS_NOT_PRODUCTION_ACCEPTED"
    assert all(report["checks"].values())
    assert report["production_acceptance"] is False
    assert report["actual_provider_invocation_performed"] is False
    assert report["run_receipt_created"] is False
    assert private not in encoded
    assert public not in encoded
    assert env["IIOS_HOST_AUTH_TOKEN"] not in encoded


def test_preflight_blocks_keypair_mismatch(tmp_path):
    env, _, _ = _env(tmp_path)
    other = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    env["IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64"] = base64.b64encode(other).decode("ascii")
    report = build_preflight_report(env)
    assert report["status"] == "BLOCKED"
    assert "RUNTIME_KEYPAIR_PIN_MISMATCH_OR_MISSING" in report["blockers"]


def test_preflight_blocks_manual_web_factory(tmp_path):
    env, _, _ = _env(tmp_path)
    env["IIOS_CANONICAL_RUNTIME_FACTORY"] = "iios_mvp.chatgpt_chat_runtime_v01:build_chatgpt_chat_runtime"
    report = build_preflight_report(env)
    assert report["status"] == "BLOCKED"
    assert "TRUSTED_FACTORY_NOT_CANONICAL_PROVIDER_FACTORY" in report["blockers"]


def test_preflight_blocks_missing_admission_root(tmp_path):
    env, _, _ = _env(tmp_path)
    env["IIOS_CANONICAL_ADMISSION_ROOT"] = str(tmp_path / "not-there")
    report = build_preflight_report(env)
    assert report["status"] == "BLOCKED"
    assert report["checks"]["canonical_admission_root_exists"] is False
