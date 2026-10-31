from __future__ import annotations

from iios_mvp.operating_feasibility_evidence_v01 import (
    INPUT_SCHEMA,
    build_operating_feasibility_evidence_assessment,
)


def _b69():
    products = [{
        "product_id": "P1",
        "required_sales_volume_tonnes": "100",
        "required_net_asp_cny_per_tonne": "20",
        "required_unit_variable_cost_cny_per_tonne": "10",
        "required_production_tonnes_under_unchanged_inventory_movement": "120",
    }]
    lens = {
        "lens": "B61_SINGLE_SEGMENT_THRESHOLD",
        "required_parent_attributable_profit_cny": "500",
        "products": products,
        "non_additive": True,
    }
    second_lens = {
        **lens,
        "lens": "B63_FULL_B4_VECTOR_THRESHOLD",
        "required_parent_attributable_profit_cny": "600",
    }
    return {
        "forecast_period": "FY2027",
        "scenarios": {
            scenario: {
                "requirement_lenses": [lens, second_lens] if scenario == "base" else [],
            }
            for scenario in ("bear", "base", "bull")
        },
    }


def _source(source_id, *, time_status="PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED", source_class="ISSUER_PRIMARY", domain_status="ISSUER_DOMAIN_NOT_INDEPENDENTLY_VERIFIED"):
    return {
        "source_id": source_id,
        "title": f"Source {source_id}",
        "source_class": source_class,
        "source_ref": f"https://issuer.example/{source_id}",
        "source_domain_class_status": domain_status,
        "time_status": time_status,
        "summary": f"Primary evidence {source_id}",
        "formal_evidence_pit_admission": False,
    }


def _record(record_id, claim_type, value, source_id, *, product_id="P1", scenario="base", period="FY2027", unit=None, data_class="ISSUER_FORECAST", comparison_basis=None):
    units = {
        "SUPPORTED_SALES_VOLUME": "tonnes",
        "SUPPORTED_NET_ASP": "CNY/tonne",
        "SUPPORTED_UNIT_VARIABLE_COST": "CNY/tonne",
        "EFFECTIVE_CAPACITY_AVAILABLE": "tonnes/year",
        "CAPACITY_AVAILABLE_DATE": "date",
        "INCREMENTAL_CAPEX_REQUIRED": "CNY",
        "INCREMENTAL_CAPEX_FUNDED": "CNY",
        "INCREMENTAL_WORKING_CAPITAL_REQUIRED": "CNY",
        "INCREMENTAL_WORKING_CAPITAL_FUNDED": "CNY",
    }
    row = {
        "record_id": record_id,
        "claim_type": claim_type,
        "product_id": product_id,
        "scenario": scenario,
        "forecast_period": period,
        "value": value,
        "unit": unit or units[claim_type],
        "data_class": data_class,
        "basis": f"Explicit {claim_type} claim for FY2027",
        "evidence_refs": [source_id],
    }
    if comparison_basis:
        row["comparison_basis"] = comparison_basis
    return row


def _fixture(records):
    source_ids = sorted({ref for row in records for ref in row.get("evidence_refs", [])})
    return {
        "raw_evidence": {
            "schema_version": INPUT_SCHEMA,
            "records": records,
        },
        "b69_audit": _b69(),
        "evidence_register": [_source(source_id) for source_id in source_ids],
        "unresolved_evidence_refs": [],
        "after_cutoff_evidence_refs": [],
        "uncertain_timing_evidence_refs": [],
    }


def _run(records, **overrides):
    data = _fixture(records)
    data.update(overrides)
    return build_operating_feasibility_evidence_assessment(**data)


def _product(result):
    lens = result["scenarios"]["base"]["requirement_lenses"][0]
    return lens["products"][0]


def test_b70_missing_input_preserves_evidence_not_provided():
    result = build_operating_feasibility_evidence_assessment(
        raw_evidence=None,
        b69_audit=_b69(),
        evidence_register=[],
    )
    assert result["status"] == "EVIDENCE_NOT_PROVIDED"
    assert result["overall_operational_feasibility_status"] == "NOT_IDENTIFIABLE"


def test_b70_rejects_wrong_input_schema():
    data = _fixture([])
    data["raw_evidence"]["schema_version"] = "WRONG"
    result = build_operating_feasibility_evidence_assessment(**data)
    assert result["status"] == "INVALID_INPUT_SCHEMA"


def test_b70_links_primary_pit_compatible_claims_to_exact_threshold():
    records = [
        _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1"),
        _record("R2", "SUPPORTED_NET_ASP", "22", "S2"),
        _record("R3", "SUPPORTED_UNIT_VARIABLE_COST", "9", "S3"),
        _record("R4", "EFFECTIVE_CAPACITY_AVAILABLE", "125", "S4"),
    ]
    result = _run(records)
    product = _product(result)
    assert [row["status"] for row in product["comparisons"]] == [
        "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT",
        "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT",
        "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT",
        "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT",
    ]
    assert result["eligible_linked_record_count"] == 4
    assert result["formal_evidence_pit_admission_created"] is False
    assert result["source_content_semantically_verified"] is False


def test_b70_reports_quantitative_shortfall_and_does_not_upgrade_to_pass():
    records = [_record("R1", "SUPPORTED_SALES_VOLUME", "90", "S1")]
    result = _run(records)
    assert _product(result)["comparisons"][0]["status"] == "LINKED_CLAIM_NUMERICALLY_BELOW_REQUIREMENT"
    assert result["status"] == "LINKED_EVIDENCE_IDENTIFIES_CONDITION_GAP"
    assert result["overall_operational_feasibility_status"] == "NOT_IDENTIFIABLE_PENDING_HUMAN_SOURCE_CONTENT_REVIEW_AND_COMPLETE_COVERAGE"


def test_b70_blocks_after_cutoff_evidence_reference():
    record = _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1")
    data = _fixture([record])
    data["evidence_register"] = [_source("S1", time_status="AFTER_CUTOFF")]
    data["after_cutoff_evidence_refs"] = ["S1"]
    result = build_operating_feasibility_evidence_assessment(**data)
    assert result["records"][0]["status"] == "NOT_IDENTIFIABLE"
    assert _product(result)["comparisons"][0]["status"] == "CLAIM_NOT_ELIGIBLE_FOR_COMPARISON"


def test_b70_blocks_nonprimary_source_class():
    record = _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1")
    data = _fixture([record])
    data["evidence_register"] = [_source("S1", source_class="MEDIA")]
    result = build_operating_feasibility_evidence_assessment(**data)
    assert result["records"][0]["status"] == "NOT_IDENTIFIABLE"
    assert any("NOT_PRIMARY_SOURCE_CLASS" in issue for issue in result["records"][0]["issues"])


def test_b70_analyst_assumption_is_not_operating_evidence():
    record = _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1", data_class="ANALYST_ASSUMPTION")
    result = _run([record])
    assert result["records"][0]["status"] == "NOT_IDENTIFIABLE"
    assert "ANALYST_ASSUMPTION_CANNOT_CORROBORATE_OPERATING_FEASIBILITY" in result["records"][0]["issues"]


def test_b70_does_not_sum_duplicate_overlapping_claims():
    records = [
        _record("R1", "SUPPORTED_SALES_VOLUME", "60", "S1"),
        _record("R2", "SUPPORTED_SALES_VOLUME", "60", "S2"),
    ]
    result = _run(records)
    comparison = _product(result)["comparisons"][0]
    assert comparison["status"] == "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED"
    assert len(result["duplicate_claim_keys"]) == 1


def test_b70_requires_exact_forecast_period_and_scenario_match():
    record = _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1", period="FY2028")
    result = _run([record])
    comparison = _product(result)["comparisons"][0]
    assert comparison["status"] == "EVIDENCE_NOT_PROVIDED"


def test_b70_checks_capacity_ramp_date_and_funding_pairs():
    records = [
        _record("R1", "CAPACITY_AVAILABLE_DATE", "2028-03-31", "S1"),
        _record("R2", "INCREMENTAL_CAPEX_REQUIRED", "100", "S2", comparison_basis="INCREMENTAL_TO_B4_FORWARD_PLAN"),
        _record("R3", "INCREMENTAL_CAPEX_FUNDED", "80", "S3", comparison_basis="INCREMENTAL_TO_B4_FORWARD_PLAN"),
        _record("R4", "INCREMENTAL_WORKING_CAPITAL_REQUIRED", "40", "S4", comparison_basis="INCREMENTAL_TO_B4_FORWARD_PLAN"),
        _record("R5", "INCREMENTAL_WORKING_CAPITAL_FUNDED", "50", "S5", comparison_basis="INCREMENTAL_TO_B4_FORWARD_PLAN"),
    ]
    result = _run(records)
    product = _product(result)
    assert product["capacity_available_date_comparison"]["status"] == "LINKED_CLAIM_AVAILABLE_AFTER_FORECAST_END"
    assert [row["status"] for row in product["incremental_funding_comparisons"]] == [
        "LINKED_FUNDING_CLAIM_SHORTFALL",
        "LINKED_FUNDING_CLAIM_COVERS_REQUIREMENT",
    ]


def test_b70_requires_incremental_basis_for_funding_records():
    record = _record("R1", "INCREMENTAL_CAPEX_REQUIRED", "100", "S1")
    result = _run([record])
    assert result["records"][0]["status"] == "NOT_IDENTIFIABLE"
    assert "INCREMENTAL_COMPARISON_BASIS_REQUIRED" in result["records"][0]["issues"]


def test_b70_duplicate_record_ids_are_invalidated():
    records = [
        _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1"),
        _record("R1", "SUPPORTED_NET_ASP", "22", "S2"),
    ]
    result = _run(records)
    assert all(row["status"] == "NOT_IDENTIFIABLE" for row in result["records"])
    assert result["duplicate_record_ids"] == ["R1"]


def test_b70_requires_source_domain_class_not_to_mismatch():
    record = _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1")
    data = _fixture([record])
    data["evidence_register"] = [_source("S1", domain_status="SOURCE_CLASS_DOMAIN_MISMATCH")]
    result = build_operating_feasibility_evidence_assessment(**data)
    assert result["records"][0]["status"] == "NOT_IDENTIFIABLE"
    assert "EVIDENCE_REFERENCE_SOURCE_DOMAIN_CLASS_MISMATCH:S1" in result["records"][0]["issues"]


def test_b70_capacity_available_date_requires_full_year_forecast_period():
    record = _record("R1", "CAPACITY_AVAILABLE_DATE", "2027-06-30", "S1", period="2027H1")
    data = _fixture([record])
    data["b69_audit"]["forecast_period"] = "2027H1"
    result = build_operating_feasibility_evidence_assessment(**data)
    comparison = _product(result)["capacity_available_date_comparison"]
    assert comparison["status"] == "FORECAST_PERIOD_END_NOT_IDENTIFIABLE"


def test_b70_duplicate_evidence_register_source_ids_are_not_accepted():
    record = _record("R1", "SUPPORTED_SALES_VOLUME", "110", "S1")
    data = _fixture([record])
    data["evidence_register"] = [_source("S1"), _source("S1")]
    result = build_operating_feasibility_evidence_assessment(**data)
    assert result["records"][0]["status"] == "NOT_IDENTIFIABLE"
    assert "EVIDENCE_REFERENCE_DUPLICATE_SOURCE_ID:S1" in result["records"][0]["issues"]


def test_b70_late_expansion_date_overrides_sufficient_capacity_quantity():
    records = [
        _record("R1", "EFFECTIVE_CAPACITY_AVAILABLE", "200", "S1"),
        _record("R2", "CAPACITY_AVAILABLE_DATE", "2028-03-31", "S2"),
    ]
    result = _run(records)
    capacity = _product(result)["comparisons"][3]
    assert capacity["status"] == "LINKED_CAPACITY_AVAILABLE_AFTER_FORECAST_END_NOT_COVERAGE"
