from __future__ import annotations

import pytest

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


def test_operator_attested_price_completes_only_the_price_group_without_web_reaudit(tmp_path):
    from research.b2.company_evidence import build_company_evidence_manifest
    from tools.iios_operator_market_price_attestation_v01 import build_operator_market_price_bundle
    from tools.route_a_c2_adjudicate import _append_operator_market_price_attestation

    bundle = tmp_path / "attestation"
    build_operator_market_price_bundle(
        case_id=CASE_ID,
        market="CN-A",
        symbol="002001",
        company="浙江新和成股份有限公司",
        cutoff_date=CUTOFF_INSTANT,
        observation_date="2026-10-08",
        close_price="123.45",
        currency="CNY",
        source_ref="OPERATOR-PROVIDED:synthetic test source",
        out_dir=bundle,
        operator_confirmed=True,
        known_by_cutoff_confirmed=True,
        attested_at="2026-10-11T12:00:00+08:00",
    )
    root = tmp_path / "rawroot"
    root.mkdir()
    evidence = []
    raw_artifacts = []
    record = _append_operator_market_price_attestation(
        root=root,
        bundle_dir=bundle,
        evidence=evidence,
        raw_artifacts=raw_artifacts,
    )
    manifest = build_company_evidence_manifest(
        case_id=CASE_ID,
        market="CN-A",
        symbol="002001",
        company="浙江新和成股份有限公司",
        cutoff_date=CUTOFF_INSTANT,
        evidence=evidence,
        raw_artifacts=raw_artifacts,
        required_field_groups=["market_price"],
        raw_root=root,
    )
    assert record["provenance_class"] == "OPERATOR_ATTESTED_MARKET_DATA"
    assert manifest["status"] == "PASS"
    assert manifest["validation_errors"] == []
    assert (root / "operator_attestations" / "operator_market_price_attestation.json").is_file()


def test_operator_price_bundle_is_bound_to_c2_security_and_date(tmp_path):
    from tools.iios_operator_market_price_attestation_v01 import build_operator_market_price_bundle
    from tools.route_a_c2_adjudicate import _append_operator_market_price_attestation

    bundle = tmp_path / "attestation"
    build_operator_market_price_bundle(
        case_id=CASE_ID,
        market="CN-A",
        symbol="000001",
        company="WRONG",
        cutoff_date=CUTOFF_INSTANT,
        observation_date="2026-10-08",
        close_price="123.45",
        currency="CNY",
        source_ref="OPERATOR-PROVIDED:synthetic test source",
        out_dir=bundle,
        operator_confirmed=True,
        known_by_cutoff_confirmed=True,
        attested_at="2026-10-11T12:00:00+08:00",
    )
    root = tmp_path / "rawroot"
    root.mkdir()
    with pytest.raises(ValueError, match="C2_OPERATOR_PRICE_BINDING_MISMATCH:symbol"):
        _append_operator_market_price_attestation(
            root=root,
            bundle_dir=bundle,
            evidence=[],
            raw_artifacts=[],
        )
