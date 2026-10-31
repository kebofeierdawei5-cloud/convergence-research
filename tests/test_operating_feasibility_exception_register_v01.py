from __future__ import annotations

from copy import deepcopy

from iios_mvp.operating_feasibility_exception_register_v01 import (
    B69_SCHEMA,
    B70_SCHEMA,
    B71_SCHEMA,
    build_operating_feasibility_exception_register,
)


def _b69(*, capacity_status="WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL", lenses=None):
    names = lenses or [
        "B61_SINGLE_SEGMENT_THRESHOLD",
        "B63_FULL_B4_VECTOR_THRESHOLD",
    ]
    scenarios = {}
    for scenario in ("bear", "base", "bull"):
        scenarios[scenario] = {
            "requirement_lenses": [
                {
                    "segment_id": "SEG1",
                    "lens": lens,
                    "products": [{
                        "product_id": "P1",
                        "product_name": "Product 1",
                        "capacity_status": capacity_status,
                        "required_production_tonnes_under_unchanged_inventory_movement": "120",
                        "nameplate_capacity_tonnes_per_year": "150",
                        "required_capacity_utilization": "0.8",
                        "remaining_nameplate_capacity_tonnes": "30",
                        "inventory_policy_assumption": "FORWARD_INVENTORY_CHANGE_HELD_AT_B4_LEVEL",
                        "capacity_measure_lineage": {
                            "evidence_refs": ["CAPACITY-SOURCE"],
                        },
                        "demand_feasibility_status": "NOT_IDENTIFIABLE_NO_TYPED_ORDER_BOOK_OR_CUSTOMER_DEMAND_INPUT",
                        "pricing_feasibility_status": "NOT_IDENTIFIABLE_PRICE_ELASTICITY_AND_COMPETITIVE_PRICE_EVIDENCE",
                        "unit_cost_feasibility_status": "NOT_IDENTIFIABLE_COST_CURVE_AND_SAVINGS_PLAN_EVIDENCE",
                    }],
                }
                for lens in names
            ]
        }
    return {
        "schema_version": B69_SCHEMA,
        "forecast_period": "FY2027",
        "scenarios": scenarios,
    }


def _b70(
    *,
    sales_status="LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT",
    sales_record=None,
    capacity_status="EVIDENCE_NOT_PROVIDED",
    funding_status="FUNDING_REQUIREMENT_OR_AVAILABLE_AMOUNT_NOT_IDENTIFIABLE",
    date_status="EVIDENCE_NOT_PROVIDED",
    lenses=None,
):
    names = lenses or [
        "B61_SINGLE_SEGMENT_THRESHOLD",
        "B63_FULL_B4_VECTOR_THRESHOLD",
    ]
    records = []
    if sales_record is not None:
        records.append(sales_record)
    scenarios = {}
    for scenario in ("bear", "base", "bull"):
        scenarios[scenario] = {
            "requirement_lenses": [
                {
                    "segment_id": "SEG1",
                    "lens": lens,
                    "products": [{
                        "product_id": "P1",
                        "comparisons": [
                            {
                                "claim_type": "SUPPORTED_SALES_VOLUME",
                                "status": sales_status,
                                "required_value": "100",
                                "evidence_value": "120" if sales_status == "LINKED_CLAIM_NUMERICALLY_COVERS_REQUIREMENT" else "80",
                                "record_id": (sales_record or {}).get("record_id"),
                                "comparison_direction": "AT_LEAST",
                            },
                            {
                                "claim_type": "SUPPORTED_NET_ASP",
                                "status": "EVIDENCE_NOT_PROVIDED",
                                "required_value": "20",
                                "evidence_value": None,
                            },
                            {
                                "claim_type": "SUPPORTED_UNIT_VARIABLE_COST",
                                "status": "EVIDENCE_NOT_PROVIDED",
                                "required_value": "8",
                                "evidence_value": None,
                            },
                            {
                                "claim_type": "EFFECTIVE_CAPACITY_AVAILABLE",
                                "status": capacity_status,
                                "required_value": "120",
                                "evidence_value": None,
                            },
                        ],
                        "capacity_available_date_comparison": {
                            "claim_type": "CAPACITY_AVAILABLE_DATE",
                            "status": date_status,
                            "required_by_date": "2027-12-31",
                        },
                        "incremental_funding_comparisons": [{
                            "funding_type": "INCREMENTAL_CAPEX_REQUIRED",
                            "status": funding_status,
                            "required_amount_cny": "50",
                            "funded_amount_cny": "30" if funding_status == "LINKED_FUNDING_CLAIM_SHORTFALL" else None,
                        }],
                    }],
                }
                for lens in names
            ]
        }
    return {
        "schema_version": B70_SCHEMA,
        "records": records,
        "scenarios": scenarios,
    }


def _sales_record(
    *,
    record_id="R-SALES",
    data_class="ISSUER_FORECAST",
    status="PIT_COMPATIBLE_PRIMARY_LINKED_CLAIM_NOT_FORMALLY_ADMITTED",
    claim_type="SUPPORTED_SALES_VOLUME",
    scenario="base",
    refs=None,
):
    return {
        "record_id": record_id,
        "claim_type": claim_type,
        "product_id": "P1",
        "scenario": scenario,
        "forecast_period": "FY2027",
        "value": "120",
        "unit": "tonnes",
        "data_class": data_class,
        "basis": "Customer order / issuer forecast",
        "evidence_refs": refs or ["E1"],
        "status": status,
    }


def _b71(*, review_status="HUMAN_SEMANTIC_REVIEW_SUPPORTED_CONDITIONALLY", record_id="R-SALES", independent=True):
    return {
        "schema_version": B71_SCHEMA,
        "reviews": [{
            "review_id": "REV-1",
            "record_id": record_id,
            "status": review_status,
            "review_independence_conditionally_declared": independent,
        }],
    }


def _run(*, b69=None, b70=None, b71=None):
    record = _sales_record()
    return build_operating_feasibility_exception_register(
        b69_audit=_b69() if b69 is None else b69,
        b70_assessment=_b70(sales_record=record) if b70 is None else b70,
        b71_review=_b71() if b71 is None else b71,
    )


def _base_sale_rows(result):
    return [
        row for row in result["requirement_rows"]
        if row["scenario"] == "base"
        and row["requirement_type"] == "SUPPORTED_SALES_VOLUME"
    ]


def test_b72_rejects_missing_or_mismatched_upstream_schemas():
    result = build_operating_feasibility_exception_register(
        b69_audit={},
        b70_assessment={},
        b71_review={},
    )
    assert result["status"] == "INPUT_SCHEMA_BLOCKED"
    assert "B69_SCHEMA_MISSING_OR_MISMATCH" in result["issues"]


def test_b72_separates_numerical_coverage_from_missing_semantic_review():
    record = _sales_record()
    result = _run(
        b70=_b70(sales_record=record),
        b71={"schema_version": B71_SCHEMA, "reviews": []},
    )
    row = _base_sale_rows(result)[0]
    assert row["evidence_linkage_status"] == "LINKED_VALUE_COVERS_NUMERICAL_REQUIREMENT"
    assert row["semantic_review_status"] == "SEMANTIC_REVIEW_NOT_PROVIDED"
    assert row["exception_status"] == "NUMERICAL_LINKAGE_ONLY_REVIEW_PENDING"
    assert row["formal_evidence_pit_admission"] is False


def test_b72_marks_independently_reviewed_numeric_coverage_as_conditional_only():
    result = _run()
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "CONDITIONALLY_SUPPORTED_NOT_FORMALLY_ADMITTED"
    assert row["review_independence_conditionally_declared"] is True
    assert row["requirement_is_operationally_proven"] is False


def test_b72_never_upgrades_numeric_coverage_when_human_review_contradicts_claim():
    result = _run(b71=_b71(review_status="SEMANTIC_REVIEW_CONTRADICTED"))
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "CLAIM_CONTRADICTED_BY_HUMAN_REVIEW"


def test_b72_distinguishes_numeric_requirement_gap_from_missing_evidence():
    record = _sales_record()
    result = _run(
        b70=_b70(
            sales_status="LINKED_CLAIM_NUMERICALLY_BELOW_REQUIREMENT",
            sales_record=record,
        ),
        b71=_b71(),
    )
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "QUANTIFIED_REQUIREMENT_GAP"
    assert row["required_value"] == "100"
    assert row["evidence_value"] == "80"


def test_b72_does_not_treat_absent_claim_as_negative_evidence():
    result = _run(
        b70=_b70(sales_status="EVIDENCE_NOT_PROVIDED", sales_record=None),
        b71={"schema_version": B71_SCHEMA, "reviews": []},
    )
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "EVIDENCE_NOT_PROVIDED"


def test_b72_keeps_analyst_assumption_out_of_operating_evidence():
    assumption = _sales_record(
        record_id="R-ASSUMPTION",
        data_class="ANALYST_ASSUMPTION",
        status="NOT_IDENTIFIABLE",
    )
    result = _run(
        b70=_b70(
            sales_status="CLAIM_NOT_ELIGIBLE_FOR_COMPARISON",
            sales_record=assumption,
        ),
        b71={"schema_version": B71_SCHEMA, "reviews": []},
    )
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "ANALYST_ASSUMPTION_ONLY_NOT_CORROBORATION"


def test_b72_keeps_duplicate_claims_ambiguous_and_never_sums_them():
    records = [
        _sales_record(record_id="R-SALES-1"),
        _sales_record(record_id="R-SALES-2"),
    ]
    b70 = _b70(sales_status="AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED")
    b70["records"] = records
    result = _run(b70=b70, b71={"schema_version": B71_SCHEMA, "reviews": []})
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "AMBIGUOUS_DUPLICATE_CLAIMS_NOT_SUMMED"


def test_b72_categorizes_unresolved_reviewer_independence_separately():
    result = _run(b71=_b71(review_status="SEMANTIC_REVIEW_INDEPENDENCE_UNRESOLVED", independent=False))
    row = _base_sale_rows(result)[0]
    assert row["exception_status"] == "REVIEW_INDEPENDENCE_UNRESOLVED"


def test_b72_records_funding_shortfall_as_a_distinct_exception():
    result = _run(b70=_b70(
        sales_record=_sales_record(),
        funding_status="LINKED_FUNDING_CLAIM_SHORTFALL",
    ))
    rows = [
        row for row in result["requirement_rows"]
        if row["scenario"] == "base" and row["requirement_type"] == "INCREMENTAL_CAPEX_REQUIRED"
    ]
    assert rows
    assert rows[0]["exception_status"] == "INCREMENTAL_FUNDING_SHORTFALL"


def test_b72_records_late_expansion_date_as_a_distinct_exception():
    result = _run(b70=_b70(
        sales_record=_sales_record(),
        date_status="LINKED_CLAIM_AVAILABLE_AFTER_FORECAST_END",
    ))
    rows = [
        row for row in result["requirement_rows"]
        if row["scenario"] == "base" and row["requirement_type"] == "CAPACITY_AVAILABLE_DATE"
    ]
    assert rows[0]["exception_status"] == "EXPANSION_AVAILABLE_AFTER_FORECAST_PERIOD"


def test_b72_preserves_b69_nameplate_capacity_constraint():
    result = _run(b69=_b69(capacity_status="EXCEEDS_NAMEPLATE_CAPACITY"))
    rows = [
        row for row in result["requirement_rows"]
        if row["scenario"] == "base" and row["requirement_type"] == "B69_NAMEPLATE_CAPACITY_ARITHMETIC"
    ]
    assert rows[0]["exception_status"] == "NAMEPLATE_CAPACITY_CONSTRAINT"


def test_b72_does_not_call_conditional_nameplate_fit_operational_approval():
    result = _run(b69=_b69(capacity_status="WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL"))
    rows = [
        row for row in result["requirement_rows"]
        if row["scenario"] == "base" and row["requirement_type"] == "B69_NAMEPLATE_CAPACITY_ARITHMETIC"
    ]
    assert rows[0]["exception_status"] == "CONDITIONAL_NAMEPLATE_FIT_ONLY"
    assert rows[0]["requirement_is_operationally_proven"] is False


def test_b72_keeps_demand_pricing_and_cost_curve_unknown_even_if_one_driver_claim_passes():
    result = _run()
    rows = [
        row for row in result["requirement_rows"]
        if row["scenario"] == "base"
        and row["requirement_type"] in {
            "CUSTOMER_DEMAND_SUSTAINABILITY_AND_ELASTICITY",
            "PRICE_ELASTICITY_AND_COMPETITIVE_RESPONSE",
            "COST_CURVE_AND_SAVINGS_EXECUTION",
        }
    ]
    assert len(rows) == 6  # three uncovered dimensions in each of two alternative lenses
    assert all(row["exception_status"] == "NOT_IDENTIFIABLE_UNCOVERED_DIMENSION" for row in rows)


def test_b72_keeps_b61_and_b63_lenses_separate_and_non_additive():
    result = _run()
    assert result["cross_lens_aggregation_performed"] is False
    assert result["non_additive_lenses_preserved"] is True
    names = {
        lens["lens"]
        for lens in result["scenarios"]["base"]["requirement_lenses"]
    }
    assert names == {
        "B61_SINGLE_SEGMENT_THRESHOLD",
        "B63_FULL_B4_VECTOR_THRESHOLD",
    }


def test_b72_never_changes_overall_decision_or_admission_authority():
    result = _run()
    assert result["overall_operational_feasibility_status"] == (
        "NOT_IDENTIFIABLE_PENDING_COMPLETE_OPERATING_COVERAGE_AND_FORMAL_ADMISSION"
    )
    assert result["formal_evidence_pit_admission_created"] is False
    assert result["forecast_or_valuation_admission_created"] is False
    assert result["decision_authority"] is False
    assert result["execution_authority"] is False
    assert result["required_return_or_target_entry_modified"] is False
    assert result["portfolio_constraints_or_decision_modified"] is False


def test_b72_generates_explicit_open_remediation_and_closure_criteria():
    result = _run()
    row = _base_sale_rows(result)[0]
    assert row["remediation"]["status"] == "OPEN_REMEDIATION_REQUIRED"
    assert row["remediation"]["owner_role"]
    assert row["remediation"]["next_action"]
    assert row["remediation"]["closure_evidence_required"]
    assert row["remediation"]["automatically_closed"] is False


def test_b72_marks_every_unresolved_requirement_as_open_not_closed():
    result = _run()
    assert result["summary"]["all_remediation_tasks_start_open"] is True
    assert result["summary"]["no_exception_is_automatically_closed"] is True
    assert all(
        row["remediation"]["status"] == "OPEN_REMEDIATION_REQUIRED"
        for row in result["requirement_rows"]
    )


def test_b72_does_not_mutate_b69_b70_or_b71_inputs():
    b69 = _b69()
    b70 = _b70(sales_record=_sales_record())
    b71 = _b71()
    before = deepcopy((b69, b70, b71))
    _run(b69=b69, b70=b70, b71=b71)
    assert (b69, b70, b71) == before


def test_b72_does_not_create_weighted_scores_or_scenario_probabilities():
    result = _run()
    assert "probability" not in result
    assert "composite_score" not in result
    assert "weighted_feasibility_score" not in result
    assert result["summary"]["cross_lens_aggregation_performed"] is False
