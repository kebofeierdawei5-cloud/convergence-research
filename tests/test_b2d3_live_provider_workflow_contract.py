from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "iios_b2d3_real_provider.yml"


def test_b2d3_workflow_is_valid_yaml_and_manual_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["name"] == "IIOS B2-D3 Real Provider Live Evidence"
    assert list(workflow["on"].keys()) == ["workflow_dispatch"]
    assert set(workflow["jobs"]) == {"preflight", "live_and_verify"}
    for job_id, job in workflow["jobs"].items():
        secret_values = [str(v) for v in job.get("env", {}).values() if "secrets." in str(v)]
        if secret_values:
            assert job.get("if") == "github.event_name == 'workflow_dispatch'", job_id


def test_b2d3_is_manual_only_and_strict():
    text = WORKFLOW.read_text(encoding="utf-8")
    trigger_block = text.split("permissions:", 1)[0]
    assert "workflow_dispatch:" in trigger_block
    assert "push:" not in trigger_block
    assert "pull_request:" not in trigger_block
    assert "continue-on-error" not in text
    assert "if-no-files-found: error" in text


def test_b2d3_all_provider_jobs_fail_closed_on_non_dispatch_events():
    text = WORKFLOW.read_text(encoding="utf-8")
    guard = "if: github.event_name == 'workflow_dispatch'"
    secret_ref = "$" + "{{ secrets."
    assert text.count(guard) == 2
    assert text.index("preflight:") < text.index(guard) < text.index("IIOS_LLM_PROVIDER_API_KEY: " + secret_ref)
    assert text.index("live_and_verify:") < text.rindex(guard) < text.rindex("IIOS_LLM_PROVIDER_API_KEY: " + secret_ref)


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



def test_b2d3_transport_rejects_redirects():
    from iios_mvp.live_provider_invocation_v01 import LiveProviderInvocationError, _RejectRedirectHandler

    handler = _RejectRedirectHandler()
    from urllib.request import Request
    with __import__("pytest").raises(LiveProviderInvocationError, match="redirects are not permitted"):
        handler.redirect_request(
            Request("https://provider.example/v1/responses"),
            None,
            302,
            "Found",
            {},
            "http://provider.example/v1/responses",
        )
