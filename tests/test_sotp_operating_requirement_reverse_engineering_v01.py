from __future__ import annotations

from iios_mvp.sotp_operating_requirement_reverse_engineering_v01 import (
    build_sotp_operating_requirement_reverse_engineering,
)


def _fixtures():
    product = {
        "product_id": "P1",
        "product_name": "Product 1",
        "business_segment_id": "SEG_A",
        "status": "CALCULATED_AND_RECONCILED",
        "forward_scenario": {
            "sales_volume_tonnes": "90",
            "net_asp_cny_per_tonne": "20",
            "variable_cost_cny_per_tonne": "10",
            "measure_lineage": {
                "sales_volume_tonnes": {"data_class": "ISSUER_FORECAST", "basis": "FY2027 sales plan", "evidence_refs": ["E1"], "issues": []},
                "net_asp_cny_per_tonne": {"data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 ASP model", "evidence_refs": ["E2"], "issues": []},
                "variable_cost_cny_per_tonne": {"data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 unit cost model", "evidence_refs": ["E3"], "issues": []},
            },
        },
        "production_inventory_context": {
            "forward_production_tonnes": "90",
            "forward_inventory_change_tonnes": "0",
        },
    }
    financial_forward = {
        "contribution_after_variable_cost_cny": "900",
        "normalized_profit_before_tax_proxy_cny": "500",
        "normalized_modeled_tax_expense_cny": "100",
        "normalized_minority_interest_net_profit_cny": "0",
        "normalized_parent_attributable_net_profit_cny": "400",
        "fixed_cash_opex_cny": "200",
        "depreciation_amortization_cny": "100",
        "finance_cost_cny": "100",
        "tax_rate": "0.2",
        "recurring_non_operating_pre_tax_cny": "0",
        "minority_interest_net_profit_after_tax_cny": "0",
        "minority_interest_nonrecurring_after_tax_cny": "0",
        "measure_lineage": {
            "fixed_cash_opex_cny": {"data_class": "ISSUER_FORECAST", "basis": "FY2027 budget", "evidence_refs": ["F1"], "issues": []},
            "depreciation_amortization_cny": {"data_class": "ISSUER_FORECAST", "basis": "FY2027 D&A plan", "evidence_refs": ["F2"], "issues": []},
            "finance_cost_cny": {"data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 finance cost model", "evidence_refs": ["F3"], "issues": []},
            "tax_rate": {"data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 effective tax rate assumption", "evidence_refs": ["F4"], "issues": []},
            "recurring_non_operating_pre_tax_cny": {"data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 recurring non-op assumption", "evidence_refs": ["F5"], "issues": []},
            "minority_interest_net_profit_after_tax_cny": {"data_class": "ISSUER_FORECAST", "basis": "FY2027 NCI forecast", "evidence_refs": ["F6"], "issues": []},
            "minority_interest_nonrecurring_after_tax_cny": {"data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 NCI normalization", "evidence_refs": ["F7"], "issues": []},
        },
    }
    b4_segment = {"status": "CALCULATED_AND_RECONCILED", "forward_scenario": financial_forward}
    b55_product = {
        **product,
        "historical_baseline": {"sales_volume_tonnes": "85", "net_asp_cny_per_tonne": "19", "variable_cost_cny_per_tonne": "9"},
    }
    return {
        "operating_driver_forecast": {
            "scope": "COMPANY_WIDE",
            "forecast_period": "FY2027",
            "product_lines": [{"product_id": "P1", "business_segment_id": "SEG_A", "capacity_tonnes_per_year": {"value": "150"}}],
            "baseline_transition": {
                "forecast_period": "FY2027",
                "status": "DIAGNOSTIC_CALCULATED",
                "scenarios": {
                    name: {"status": "CALCULATED_AND_RECONCILED", "product_lines": [b55_product]}
                    for name in ("bear", "base", "bull")
                },
                "segment_normalized_earnings_bridge": {
                    "status": "DIAGNOSTIC_CALCULATED",
                    "forecast_period": "FY2027",
                    "scenarios": {
                        name: {"status": "CALCULATED_AND_RECONCILED", "segments": {"SEG_A": b4_segment}}
                        for name in ("bear", "base", "bull")
                    },
                },
            },
        },
        "segment_earnings_reconciliation": {
            "status": "CONDITIONAL_RECONCILIATION_CALCULATED",
            "forecast_period": "FY2027",
            "scenarios": {
                name: {
                    "status": "CALCULATED_CONDITIONAL",
                    "segment_comparisons": [{
                        "segment_id": "SEG_A",
                        "segment_name": "Segment A",
                        "b4_forecast_parent_attributable_normalized_profit_cny": "400",
                        "sotp_selected_attributable_profit_cny": "300",
                        "sotp_selected_pe_multiple_x": "10",
                        "b61_one_at_a_time_required_attributable_profit_cny_signed": "500",
                    }],
                } for name in ("bear", "base", "bull")
            },
        },
        "valuation_gap_attribution": {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "scenarios": {
                name: {
                    "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
                    "earnings_effect_by_segment": [{
                        "segment_id": "SEG_A",
                        "normalized_profit_change_cny": "100",
                        "selected_sotp_pe_x": "10",
                        "earnings_effect_at_selected_pe_cny": "1000",
                        "selected_sotp_segment_value_cny": "3000",
                        "b4_forecast_segment_value_at_selected_pe_cny": "4000",
                    }],
                    "value_pool_waterfall": {
                        "step_3_b4_forecast_pool_at_selected_pes_cny": "4000",
                        "step_5_required_segment_pool_cny": "4500",
                    },
                } for name in ("bear", "base", "bull")
            },
        },
    }


def _run(data):
    return build_sotp_operating_requirement_reverse_engineering(**data)


def test_b68_reverses_normalized_profit_to_required_segment_contribution():
    result = _run(_fixtures())
    segment = result["scenarios"]["base"]["segments"][0]
    lens = segment["b63_full_b4_vector_lens"]["reverse_engineering"]
    assert lens["contribution_inversion"]["required_contribution_after_variable_cost_cny"] == "962.5"
    assert lens["contribution_inversion"]["contribution_gap_cny"] == "62.5"


def test_b68_reverses_sales_volume_asp_and_variable_cost_as_alternatives():
    result = _run(_fixtures())
    driver = result["scenarios"]["base"]["segments"][0]["b63_full_b4_vector_lens"]["reverse_engineering"]["product_driver_alternatives"][0]
    alternatives = driver["single_driver_alternatives"]
    assert alternatives["sales_volume_only"]["required_sales_volume_tonnes"] == "96.25"
    assert alternatives["net_asp_only"]["required_net_asp_cny_per_tonne"] == "20.69444444444444444444444444"
    assert alternatives["unit_variable_cost_only"]["required_variable_cost_cny_per_tonne"] == "9.30555555555555555555555556"


def test_b68_keeps_b61_and_b63_required_profit_lenses_separate():
    result = _run(_fixtures())
    segment = result["scenarios"]["base"]["segments"][0]
    assert segment["b61_required_profit_lens"]["required_parent_attributable_profit_cny"] == "500"
    assert segment["b63_full_b4_vector_lens"]["required_parent_attributable_profit_cny"] == "450"
    assert segment["b61_required_profit_lens"]["interpretation"].endswith("NON_ADDITIVE")
    assert segment["b63_full_b4_vector_lens"]["interpretation"].endswith("NON_ADDITIVE")


def test_b68_blocks_missing_financial_or_tax_inputs():
    data = _fixtures()
    forward = data["operating_driver_forecast"]["baseline_transition"]["segment_normalized_earnings_bridge"]["scenarios"]["base"]["segments"]["SEG_A"]["forward_scenario"]
    forward["tax_rate"] = None
    result = _run(data)
    assert result["scenarios"]["base"]["segments"][0]["b63_full_b4_vector_lens"]["reverse_engineering"]["status"] == "NOT_IDENTIFIABLE"


def test_b68_uses_piecewise_loss_tax_rule_for_negative_target_profit():
    data = _fixtures()
    row = data["segment_earnings_reconciliation"]["scenarios"]["base"]["segment_comparisons"][0]
    row["b61_one_at_a_time_required_attributable_profit_cny_signed"] = "-100"
    result = _run(data)
    inversion = result["scenarios"]["base"]["segments"][0]["b61_required_profit_lens"]["reverse_engineering"]["contribution_inversion"]
    assert inversion["tax_branch"] == "NONPOSITIVE_TAXABLE_PROFIT_NO_MODELED_CASH_TAX"


def test_b68_preserves_non_identifiable_when_tax_rate_is_one_for_positive_profit():
    data = _fixtures()
    forward = data["operating_driver_forecast"]["baseline_transition"]["segment_normalized_earnings_bridge"]["scenarios"]["base"]["segments"]["SEG_A"]["forward_scenario"]
    forward["tax_rate"] = "1"
    result = _run(data)
    inversion = result["scenarios"]["base"]["segments"][0]["b61_required_profit_lens"]["reverse_engineering"]["contribution_inversion"]
    assert inversion["status"] == "NOT_IDENTIFIABLE"
    assert "FULL_TAX_RATE_PREVENTS_POSITIVE_PROFIT_INVERSION" in inversion["issues"]


def test_b68_marks_negative_required_unit_cost_as_not_feasible():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["value_pool_waterfall"]["step_5_required_segment_pool_cny"] = "20000"
    result = _run(data)
    driver = result["scenarios"]["base"]["segments"][0]["b63_full_b4_vector_lens"]["reverse_engineering"]["product_driver_alternatives"][0]
    assert driver["single_driver_alternatives"]["unit_variable_cost_only"]["status"] == "NOT_FEASIBLE_NEGATIVE_REQUIRED_UNIT_COST"


def test_b68_does_not_equate_sales_volume_with_production_or_inventory_release():
    result = _run(_fixtures())
    driver = result["scenarios"]["base"]["segments"][0]["b63_full_b4_vector_lens"]["reverse_engineering"]["product_driver_alternatives"][0]
    assert driver["single_driver_alternatives"]["sales_volume_only"]["production_and_inventory_feasibility"] == "NOT_IDENTIFIABLE_WITHOUT_EXPLICIT_PRODUCTION_INVENTORY_RELEASE_POLICY"


def test_b68_blocks_non_company_wide_b4_scope():
    data = _fixtures()
    data["operating_driver_forecast"]["scope"] = "PROJECT_INCREMENTAL"
    assert _run(data)["status"] == "NOT_COMPARABLE_SCOPE"


def test_b68_rejects_segment_universe_mismatch():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["earnings_effect_by_segment"][0]["segment_id"] = "SEG_B"
    assert _run(data)["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"


def test_b68_rechecks_actual_b63_profit_and_value_bridge_fields():
    data = _fixtures()
    row = data["valuation_gap_attribution"]["scenarios"]["base"]["earnings_effect_by_segment"][0]
    row["earnings_effect_at_selected_pe_cny"] = "999"
    result = _run(data)
    assert result["scenarios"]["base"]["status"] == "PARTIAL"
    assert "B68_B4_B62_B63_SEGMENT_PROFIT_VALUE_BRIDGE_MISMATCH:SEG_A" in result["scenarios"]["base"]["issues"]


def test_b68_rechecks_b62_selected_pe_against_b63_selected_pe():
    data = _fixtures()
    data["segment_earnings_reconciliation"]["scenarios"]["base"]["segment_comparisons"][0]["sotp_selected_pe_multiple_x"] = "11"
    result = _run(data)
    assert result["scenarios"]["base"]["status"] == "PARTIAL"
    assert "B68_B4_B62_B63_SEGMENT_PROFIT_VALUE_BRIDGE_MISMATCH:SEG_A" in result["scenarios"]["base"]["issues"]


def test_b68_accepts_two_nci_measures_with_the_same_typed_data_class():
    data = _fixtures()
    forward = data["operating_driver_forecast"]["baseline_transition"]["segment_normalized_earnings_bridge"]["scenarios"]["base"]["segments"]["SEG_A"]["forward_scenario"]
    forward["measure_lineage"]["minority_interest_net_profit_after_tax_cny"] = {
        "data_class": "ISSUER_FORECAST", "basis": "FY2027 total NCI", "evidence_refs": ["F6"], "issues": []
    }
    forward["measure_lineage"]["minority_interest_nonrecurring_after_tax_cny"] = {
        "data_class": "ISSUER_FORECAST", "basis": "FY2027 non-recurring NCI", "evidence_refs": ["F7"], "issues": []
    }
    result = _run(data)
    base = result["scenarios"]["base"]
    reverse = base["segments"][0]["b63_full_b4_vector_lens"]["reverse_engineering"]
    assert reverse["contribution_inversion"]["financial_measure_lineage"]["normalized_minority_interest_net_profit_cny"]["status"] == "DERIVED_FROM_TWO_TYPED_NCI_MEASURES"


def test_b68_requires_exact_b4_b55_product_universe():
    data = _fixtures()
    data["operating_driver_forecast"]["baseline_transition"]["scenarios"]["base"]["product_lines"] = []
    result = _run(data)
    assert result["scenarios"]["base"]["status"] == "PARTIAL"
    assert "B68_B4_B55_PRODUCT_UNIVERSE_MISMATCH" in result["scenarios"]["base"]["issues"]


def test_b68_missing_product_driver_keeps_segment_reverse_engineering_unknown():
    data = _fixtures()
    data["operating_driver_forecast"]["baseline_transition"]["scenarios"]["base"]["product_lines"][0]["forward_scenario"]["net_asp_cny_per_tonne"] = None
    result = _run(data)
    segment = result["scenarios"]["base"]["segments"][0]
    assert segment["b63_full_b4_vector_lens"]["reverse_engineering"]["status"] == "NOT_IDENTIFIABLE"
