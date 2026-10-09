from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "iios_public_web_discovery.yml"


def test_public_web_discovery_is_manual_only_and_read_only():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert list(workflow["on"]) == ["workflow_dispatch"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["jobs"]["discover"]["permissions"]["contents"] == "read"


def test_public_web_discovery_has_no_llm_secrets_or_provider_endpoints():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "api.openai.com" not in text
    assert "secrets." not in text
    assert "IIOS_LLM_PROVIDER_API_KEY" not in text
    assert "python -m pip install --disable-pip-version-check ddgs" in text
    assert "candidate receipt" in text


def test_search_failure_keeps_receipt_upload_and_never_claims_admission():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["discover"]["steps"]
    names = [step.get("name", step.get("uses", "")) for step in steps]
    search = next(i for i, name in enumerate(names) if name == "Run public web discovery (candidate URLs only)")
    verify = next(i for i, name in enumerate(names) if name == "Verify discovery record contract")
    upload = next(i for i, name in enumerate(names) if name == "Upload the search-result candidate receipt")
    gate = next(i for i, name in enumerate(names) if name == "Require at least one public search candidate")
    assert steps[search]["continue-on-error"] == "true"
    assert steps[verify]["if"] == "always()"
    assert steps[upload]["if"] == "always()"
    assert steps[gate]["if"] == "always()"
    assert search < verify < upload < gate
