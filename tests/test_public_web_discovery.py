from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.public_web_discovery import (
    PublicWebDiscoveryError,
    discover_public_web,
    verify_discovery_record,
)


def test_public_search_candidates_are_returned_without_llm_or_api_key(monkeypatch):
    calls = {}

    def fake_search(**kwargs):
        calls.update(kwargs)
        return [
            {"title": "SZSE H1 report", "href": "https://disc.static.szse.cn/report.pdf", "body": "Official report"},
            {"title": "Duplicate", "url": "https://disc.static.szse.cn/report.pdf#page=1", "snippet": "same URL"},
            {"title": "Unsafe local", "href": "https://127.0.0.1/admin", "body": "should be rejected"},
            {"title": "Plain HTTP", "href": "http://example.org/item", "body": "not suitable for Route A HTTPS capture"},
        ]

    record = discover_public_web(
        "site:disc.static.szse.cn 002001 半年报",
        region="cn-zh",
        max_results=10,
        backend="auto",
        search_fn=fake_search,
        captured_at="2026-10-09T10:00:00+00:00",
    )
    verify_discovery_record(record)

    assert calls["query"] == "site:disc.static.szse.cn 002001 半年报"
    assert calls["region"] == "cn-zh"
    assert calls["backend"] == "auto"
    assert record["status"] == "RESULTS_FOUND"
    assert record["contract"]["provider_api_key_required"] is False
    assert record["contract"]["evidence_admission"] is False
    assert record["contract"]["pit_admission"] is False
    assert len(record["results"]) == 2
    assert record["results"][0]["url"] == "https://disc.static.szse.cn/report.pdf"
    assert record["results"][0]["https_candidate"] is True
    assert record["results"][1]["https_candidate"] is False
    assert record["discarded_candidate_count"] == 2


def test_public_search_error_is_auditable_but_never_promoted_to_evidence():
    def unavailable(**kwargs):
        raise TimeoutError("fixture timeout")

    record = discover_public_web("newhecheng official annual report", search_fn=unavailable)
    verify_discovery_record(record)
    assert record["status"] == "SEARCH_UNAVAILABLE"
    assert record["failure_code"] == "TimeoutError"
    assert record["results"] == []
    assert record["contract"]["source_bytes_captured"] is False
    assert record["contract"]["evidence_admission"] is False




def test_default_search_falls_back_to_no_key_public_bing(monkeypatch):
    def ddgs_down(**kwargs):
        raise RuntimeError("public search engines unavailable")

    def bing_ok(**kwargs):
        assert kwargs["backend"] == "bing-html"
        return [{"title": "Official SZSE", "href": "https://disc.static.szse.cn/002001.pdf", "body": "exchange PDF"}]

    monkeypatch.setattr("tools.public_web_discovery._ddgs_search", ddgs_down)
    record = discover_public_web(
        "site:disc.static.szse.cn 002001",
        bing_fn=bing_ok,
        captured_at="2026-10-09T11:30:00+00:00",
    )
    verify_discovery_record(record)
    assert record["status"] == "RESULTS_FOUND"
    assert record["backend_used"] == "bing_html_fallback"
    assert record["failure_code"] is None
    assert record["results"][0]["url"] == "https://disc.static.szse.cn/002001.pdf"
    assert record["contract"]["provider_api_key_required"] is False
    assert record["contract"]["evidence_admission"] is False


def test_both_public_search_backends_fail_with_auditable_diagnostic(monkeypatch):
    def ddgs_down(**kwargs):
        raise RuntimeError("ddgs fixture outage")

    def bing_down(**kwargs):
        raise PublicWebDiscoveryError("BING_HTTP_STATUS_403")

    monkeypatch.setattr("tools.public_web_discovery._ddgs_search", ddgs_down)
    record = discover_public_web("newhecheng official report", bing_fn=bing_down)
    verify_discovery_record(record)
    assert record["status"] == "SEARCH_UNAVAILABLE"
    assert record["backend_used"] == "none"
    assert record["failure_code"].startswith("PUBLIC_SEARCH_BACKENDS_UNAVAILABLE")
    assert "DDGS=RuntimeError" in record["failure_code"]
    assert "BING_HTTP_STATUS_403" in record["failure_code"]
    assert record["contract"]["evidence_admission"] is False

def test_empty_results_is_not_a_successful_search_result():
    record = discover_public_web("nonexistent fixture query", search_fn=lambda **kwargs: [])
    verify_discovery_record(record)
    assert record["status"] == "NO_RESULTS"
    assert record["results"] == []
    assert record["contract"]["pit_admission"] is False


def test_discovery_record_hash_detects_mutation():
    record = discover_public_web(
        "newhecheng annual report",
        search_fn=lambda **kwargs: [{"title": "Report", "href": "https://example.org/report.pdf", "body": "report"}],
    )
    tampered = json.loads(json.dumps(record))
    tampered["results"][0]["url"] = "https://attacker.example/other.pdf"
    with pytest.raises(PublicWebDiscoveryError, match="DISCOVERY_RECORD_HASH_MISMATCH"):
        verify_discovery_record(tampered)


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "https://user:pass@example.org/report.pdf",
    "https://localhost/private",
    "https://127.0.0.1/admin",
    "https://192.168.1.1/private",
])
def test_non_public_or_unsafe_locators_are_not_search_candidates(url):
    record = discover_public_web("fixture query", search_fn=lambda **kwargs: [{"title": "x", "href": url}])
    verify_discovery_record(record)
    assert record["results"] == []
    assert record["discarded_candidate_count"] == 1


def test_invalid_queries_and_limits_fail_closed():
    with pytest.raises(PublicWebDiscoveryError, match="QUERY_MUST_BE"):
        discover_public_web(" ")
    with pytest.raises(PublicWebDiscoveryError, match="MAX_RESULTS"):
        discover_public_web("query", max_results=50)
    with pytest.raises(PublicWebDiscoveryError, match="REGION_MUST"):
        discover_public_web("query", region="China")


def test_public_web_discovery_does_not_reference_llm_provider_configuration():
    source = (Path(__file__).parents[1] / "tools" / "public_web_discovery.py").read_text(encoding="utf-8")
    assert "IIOS_LLM_PROVIDER_API_KEY" not in source
    assert "api.openai.com" not in source
    assert "secrets." not in source
