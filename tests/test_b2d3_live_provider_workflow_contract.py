from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "iios_b2d3_real_provider.yml"


def test_b2d3_is_manual_only_and_strict():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "continue-on-error" not in text
    assert "if-no-files-found: error" in text


def test_b2d3_injects_canonical_runtime_contract():
    text = WORKFLOW.read_text(encoding="utf-8")
    required = [
        "IIOS_LLM_PROVIDER_BASE_URL",
        "IIOS_LLM_PROVIDER_API_KEY",
        "IIOS_LLM_PROVIDER_MODEL",
        "IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64",
        "IIOS_LLM_PROVIDER_ID",
        "IIOS_LLM_PROVIDER_VERSION",
        "IIOS_LLM_PROVIDER_PROTOCOL",
        "IIOS_LLM_PROVIDER_AUTH_MODE",
        "IIOS_LLM_PROVIDER_DEPLOYMENT_MODE",
    ]
    for name in required:
        assert name in text


def test_b2d3_requires_real_capture_then_independent_verification():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "python -m iios_mvp.live_provider_evidence_v01" in text
    assert 'record["status"] == "LIVE_RESPONSE_CAPTURED"' in text
    assert "python -m iios_mvp.live_provider_independent_verify_v01" in text
    assert "LIVE_RESPONSE_CAPTURED_AND_INDEPENDENTLY_VERIFIED" in text
