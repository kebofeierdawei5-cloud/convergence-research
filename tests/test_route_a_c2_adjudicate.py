from __future__ import annotations

from tools.route_a_c2_adjudicate import (
    CASE_ID,
    CUTOFF_INSTANT,
    EXPECTED_ARCHIVE_SHA256,
    FACT_SPECS,
    SOURCE_VINTAGE,
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
