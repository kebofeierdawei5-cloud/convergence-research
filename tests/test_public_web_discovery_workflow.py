from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "iios_public_web_discovery.yml"


def test_public_web_discovery_is_manual_or_dedicated_search_branch_and_read_only():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert list(workflow["on"]) == ["workflow_dispatch", "push"]
    assert workflow["on"]["push"]["branches"] == ["route-a-search/**"]
    assert workflow["on"]["push"]["paths"] == ["manifests/search_requests/**"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["jobs"]["discover"]["permissions"]["contents"] == "read"


def test_push_search_request_resolution_is_bounded_and_not_based_on_event_file_lists():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'request_root = root / "manifests" / "search_requests"' in text
    assert 'request_root.glob("*.json")' in text
    assert 'request.get("schema_version") != "IIOS-PUBLIC-WEB-DISCOVERY-REQUEST-0.1"' in text
    assert "GITHUB_EVENT_PATH" not in text
    assert "SEARCH_QUERY_MUST_BE_SINGLE_LINE" in text
    assert "SEARCH_MAX_RESULTS_OUT_OF_RANGE" in text


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
