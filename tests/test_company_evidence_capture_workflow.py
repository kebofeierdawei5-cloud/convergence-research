from pathlib import Path
import json
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "iios_company_evidence_capture.yml"
MANIFEST_PATH = ROOT / "manifests" / "company_cases" / "RC-CN-A-002001-20261009.json"


def test_capture_workflow_is_manual_or_dedicated_capture_branch_only():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    triggers = workflow["on"]
    assert "workflow_dispatch" in triggers
    assert "pull_request" not in triggers
    assert triggers["push"]["branches"] == ["route-a-capture/**"]
    assert triggers["push"]["paths"] == ["manifests/capture_requests/**"]
    assert workflow["permissions"]["contents"] == "read"


def test_capture_workflow_uses_path_allowlist_no_secrets_and_no_admission_claim():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'normalized.startswith("manifests/company_cases/")' in text
    assert 'candidate.is_absolute()' in text
    assert '".." in candidate.parts' in text
    assert "secrets." not in text
    assert "B2_PREFLIGHT_BLOCKED_NOT_ADMITTED" in text
    assert "EVIDENCE_ADMISSION=FALSE" in text
    assert "retention-days: 14" in text


def test_capture_workflow_orders_capture_verification_artifact_and_final_gate():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["capture-and-verify"]["steps"]
    names = [step.get("name", step.get("uses", "")) for step in steps]
    capture = next(i for i, name in enumerate(names) if name == "Capture exact public-source bytes")
    verify = next(i for i, name in enumerate(names) if name == "Independently verify captured bytes and receipt")
    upload = next(i for i, name in enumerate(names) if name == "Upload raw evidence, receipt and verifier result")
    gate = next(i for i, name in enumerate(names) if name == "Require complete capture and independent integrity verification")
    assert capture < verify < upload < gate
    assert steps[capture]["continue-on-error"] == "true"
    assert steps[verify]["if"] == "always()"
    assert steps[upload]["if"] == "always()"
    assert steps[gate]["if"] == "always()"


def test_push_capture_request_uses_checkout_glob_not_optional_event_commit_list():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'request_root = root / "manifests" / "capture_requests"' in text
    assert 'request_root.glob("*.json")' in text
    assert "GITHUB_EVENT_PATH" not in text
    assert 'request.get("schema_version") != "IIOS-COMPANY-EVIDENCE-CAPTURE-REQUEST-0.1"' in text
    assert 'manifest.get("case_id") != expected_case_id' in text
    assert "CAPTURE_REQUEST_CASE_ID_MISMATCH" in text



def test_capture_workflow_runs_b2_preflight_before_upload_and_never_requires_provider():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["capture-and-verify"]["steps"]
    names = [step.get("name", step.get("uses", "")) for step in steps]
    verify = next(i for i, name in enumerate(names) if name == "Independently verify captured bytes and receipt")
    preflight = next(i for i, name in enumerate(names) if name == "Run existing B2 Evidence/PIT preflight (not an admission)")
    upload = next(i for i, name in enumerate(names) if name == "Upload raw evidence, receipt and verifier result")
    gate = next(i for i, name in enumerate(names) if name == "Require complete capture and independent integrity verification")
    assert verify < preflight < upload < gate
    assert steps[preflight]["if"] == "always()"
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "IIOS_LLM_PROVIDER_API_KEY" not in text
    assert "B2_PREFLIGHT_OUTCOME" in text
    assert "B2_PREFLIGHT_BLOCKED_NOT_ADMITTED" in text

def test_newhecheng_case_manifest_uses_free_primary_exchange_sources_and_preserves_unknowns():
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert value["case_id"] == "RC-CN-A-002001-20261009"
    assert value["market"] == "CN-A"
    assert value["symbol"] == "002001"
    assert value["cutoff_date"] == "2026-10-09"
    assert len(value["sources"]) == 10
    for source in value["sources"]:
        assert source["url"].startswith("https://")
        assert source["license_status"] == "PUBLIC_ACCESS_REUSE_UNKNOWN"
    issuer = next(source for source in value["sources"] if source["source_id"] == "ISSUER-IR-PAGE-CURRENT")
    assert issuer["known_at"] == ""
    assert issuer["known_at_basis"] == ""
    assert "financial_reality" in [source["field_group"] for source in value["sources"]]
    assert "corporate_disclosures" in [source["field_group"] for source in value["sources"]]
    assert "trust_governance_events" in [source["field_group"] for source in value["sources"]]
    market_sources = [source for source in value["sources"] if source["field_group"] == "market_price"]
    assert len(market_sources) == 4
    assert all(source["source_class"] == "PUBLIC_SECONDARY" for source in market_sources)
    assert all(source["known_at"] == "" and source["known_at_basis"] == "" for source in market_sources)
    assert any(source["source_id"] == "PRICE-SOHU-HISTORY-API" and "/app2/history.up?" in source["url"] for source in market_sources)
    assert any(source["source_id"] == "PRICE-EASTMONEY-KLINE-API" and "push2his.eastmoney.com/api/qt/stock/kline/get?" in source["url"] for source in market_sources)
    assert all("api_key=" not in source["url"].lower() and "token=" not in source["url"].lower() for source in market_sources)
    buyback_progress = next(source for source in value["sources"] if source["source_id"] == "SZSE-2026-BUYBACK-PROGRESS-SEP")
    assert buyback_progress["url"] == "https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-10-09/abbcbfb7-92cb-4e05-a838-aff78aaa8077.PDF"
    assert buyback_progress["field_group"] == "capital_structure"
    assert buyback_progress["known_at"] == "2026-10-09"
    assert buyback_progress["license_status"] == "PUBLIC_ACCESS_REUSE_UNKNOWN"
