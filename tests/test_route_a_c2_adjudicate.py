from __future__ import annotations

from tools.route_a_c2_adjudicate import (
    CASE_ID,
    CUTOFF_INSTANT,
    EXPECTED_ARCHIVE_SHA256,
    FACT_SPECS,
    SOURCE_VINTAGE,
    _normalize_legacy_payload_defaults,
)


def test_c2_successor_uses_canonical_date_only_start_of_day_cutoff():
    assert CASE_ID == "RC-CN-A-002001-20261009"
    assert CUTOFF_INSTANT == "2026-10-09T00:00:00+08:00"


def test_successor_is_bound_to_the_preserved_run8_archive():
    assert EXPECTED_ARCHIVE_SHA256 == (
        "0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1"
    )


def test_fact_candidates_have_unique_ids_and_exact_source_locators():
    assert len(FACT_SPECS) == 13
    ids = [item["id"] for item in FACT_SPECS]
    assert len(ids) == len(set(ids))
    for item in FACT_SPECS:
        assert item["page"] >= 1
        assert item["printed_page"] >= 1
        assert "." in item["field"]
        assert item["terms"]
        assert item["section"]
        assert item["source"] in SOURCE_VINTAGE
        assert item["value"] is not None
        assert item["claim"]


def test_same_day_buyback_progress_and_unadmitted_prices_are_not_fact_specs():
    excluded_sources = {
        "SZSE-2026-BUYBACK-PROGRESS-SEP",
        "ISSUER-IR-PAGE-CURRENT",
        "PRICE-SOHU-HISTORY",
        "PRICE-EASTMONEY-QUOTE",
        "PRICE-EASTMONEY-KLINE-API",
    }
    assert not any(item["source"] in excluded_sources for item in FACT_SPECS)
    assert {item["field"].split(".", 1)[0] for item in FACT_SPECS} == {
        "security_identity",
        "corporate_disclosures",
        "business_reality",
        "financial_reality",
        "capital_structure",
        "trust_governance_events",
    }


def test_source_vintage_bounds_are_before_the_cutoff_without_claiming_exact_time():
    from research.b2.evidence_contract import parse_temporal

    cutoff = parse_temporal(CUTOFF_INSTANT, "cutoff")
    for source in SOURCE_VINTAGE.values():
        assert parse_temporal(source["known_at"], "known_at") < cutoff
        assert source["known_at"].startswith(source["publication_date"])



def test_legacy_receipt_defaults_are_applied_to_a_copy_only():
    receipt = {
        "case_id": CASE_ID,
        "sources": [{"source_id": "LEGACY-001"}],
    }
    manifest = {
        "case_id": CASE_ID,
        "sources": [{"source_id": "LEGACY-001"}],
    }
    normalized = _normalize_legacy_payload_defaults(receipt, manifest)
    assert "expected_payload_type" not in receipt["sources"][0]
    assert "payload_contract_status" not in receipt["sources"][0]
    assert normalized["sources"][0]["expected_payload_type"] == "ANY"
    assert normalized["sources"][0]["payload_contract_status"] == "NOT_CHECKED"
    assert normalized["sources"][0]["payload_contract_error"] is None


def test_legacy_receipt_adapter_refuses_to_erase_non_default_payload_contract():
    receipt = {
        "case_id": CASE_ID,
        "sources": [{"source_id": "SOURCE-PDF", "expected_payload_type": "PDF"}],
    }
    manifest = {
        "case_id": CASE_ID,
        "sources": [{"source_id": "SOURCE-PDF", "expected_payload_type": "PDF"}],
    }
    try:
        _normalize_legacy_payload_defaults(receipt, manifest)
    except ValueError as exc:
        assert str(exc) == "C2_LEGACY_PAYLOAD_TYPE_NOT_DEFAULT_ANY"
    else:
        raise AssertionError("non-default payload contract must remain blocked")
