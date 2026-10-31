from __future__ import annotations

from decimal import Decimal

import pytest

from iios_mvp.sotp_valuation_gap_attribution_v01 import build_sotp_valuation_gap_attribution


def _b63_inputs():
    segment_rows = [
        {
            "segment_id": "seg_a",
            "earnings_basis": "NORMALIZED_PARENT_ATTRIBUTABLE",
            "attributable_net_profit_cny": {
                "value": "100", "unit": "CNY", "basis": "normalized parent net profit",
                "data_class": "ANALYST_ASSUMPTION", "evidence_refs": ["E1"],
            },
            "pe_multiple_x": {
                "value": "10", "unit": "x", "basis": "terminal normalized multiple",
                "data_class": "ANALYST_ASSUMPTION", "evidence_refs": ["E2"],
            },
            "segment_equity_value_cny": "1000",
        },
        {
            "segment_id": "seg_b",
            "earnings_basis": "NORMALIZED_PARENT_ATTRIBUTABLE",
            "attributable_net_profit_cny": {
                "value": "50", "unit": "CNY", "basis": "normalized parent net profit",
                "data_class": "ANALYST_ASSUMPTION", "evidence_refs": ["E3"],
            },
            "pe_multiple_x": {
                "value": "20", "unit": "x", "basis": "terminal normalized multiple",
                "data_class": "ANALYST_ASSUMPTION", "evidence_refs": ["E4"],
            },
            "segment_equity_value_cny": "1000",
        },
    ]
    sotp_scenario = {
        "segments": [dict(row) for row in segment_rows],
        "segment_equity_value_cny": "2000",
        "parent_level_adjustments": {
            "central_cost_after_tax_cny": {"value": "10", "unit": "CNY"},
            "central_cost_multiple_x": {"value": "10", "unit": "x"},
            "capitalized_central_cost_value_cny": "100",
            "net_cash_debt_cny": {"value": "200", "unit": "CNY"},
            "other_adjustments_cny": {"value": "0", "unit": "CNY"},
        },
        "diluted_shares": {"value": "100", "unit": "shares"},
        "total_equity_value_cny": "2100",
        "terminal_value_per_share": "21",
    }
    sotp = {
        "status": "CALCULATED",
        "selected_for_primary_model": True,
        "forecast_period": "2026FY",
        "scenarios": {name: dict(sotp_scenario) for name in ("bear", "base", "bull")},
    }
    b61_scenario = {
        "status": "CALCULATED_CONDITIONAL",
        "selected_total_equity_value_cny": "2100",
        "selected_sotp_terminal_value_per_share": "21",
        "selected_diluted_shares": "100",
        "selected_capitalized_central_cost_cny": "100",
        "selected_net_cash_debt_cny": "200",
        "selected_other_adjustments_cny": "0",
        "requirements": {
            "required_return": {
                "required_terminal_value_per_share_without_distributions": "115",
                "without_distributions": {
                    "required_terminal_equity_value_cny": "11500",
                    "required_segment_equity_value_pool_cny": "11400",
                    "selected_segment_equity_value_pool_cny": "2000",
                },
            }
        },
    }
    inversion = {
        "selected_model_family": "SOTP",
        "currency": "CNY",
        "forecast_period": "2026FY",
        "status": "CONDITIONAL_SENSITIVITY_CALCULATED",
        "scenarios": {name: dict(b61_scenario) for name in ("bear", "base", "bull")},
        "external_mie_status_unchanged": "NOT_IDENTIFIABLE",
    }
    b62_scenario = {
        "status": "CALCULATED_CONDITIONAL",
        "selected_sotp_segment_equity_value_pool_cny": "2000",
        "b4_forecast_segment_equity_value_pool_at_selected_sotp_pe_cny": "2400",
        "required_segment_equity_value_pool_for_required_return_cny": "11400",
        "b4_forecast_implied_total_equity_value_with_selected_parent_adjustments_cny": "2500",
        "required_terminal_equity_value_for_required_return_cny": "11500",
        "b4_forecast_implied_terminal_value_per_share_cny": "25",
        "required_terminal_value_per_share_for_required_return_cny": "115",
        "segment_comparisons": [
            {
                "segment_id": "seg_a",
                "b4_forecast_parent_attributable_normalized_profit_cny": "120",
                "sotp_selected_attributable_profit_cny": "100",
                "sotp_selected_pe_multiple_x": "10",
                "profit_change_value_effect_at_selected_sotp_pe_cny": "200",
            },
            {
                "segment_id": "seg_b",
                "b4_forecast_parent_attributable_normalized_profit_cny": "60",
                "sotp_selected_attributable_profit_cny": "50",
                "sotp_selected_pe_multiple_x": "20",
                "profit_change_value_effect_at_selected_sotp_pe_cny": "200",
            },
        ],
    }
    b62 = {
        "status": "CONDITIONAL_RECONCILIATION_CALCULATED",
        "forecast_period": "2026FY",
        "scenarios": {name: dict(b62_scenario) for name in ("bear", "base", "bull")},
    }
    return inversion, sotp, b62


def test_b63_reconciles_earnings_multiple_parent_adjustment_and_dilution_layers():
    inversion, sotp, b62 = _b63_inputs()
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["status"] == "CONDITIONAL_ATTRIBUTION_CALCULATED"
    base = result["scenarios"]["base"]
    assert base["status"] == "CONDITIONAL_ATTRIBUTION_CALCULATED"
    waterfall = base["value_pool_waterfall"]
    assert waterfall["step_1_selected_sotp_segment_pool_cny"] == "2000"
    assert waterfall["step_2_b4_earnings_effect_at_selected_pes_cny"] == "400"
    assert waterfall["step_3_b4_forecast_pool_at_selected_pes_cny"] == "2400"
    assert waterfall["step_4_common_pe_scale_effect_to_required_pool_cny"] == "9000"
    assert waterfall["step_5_required_segment_pool_cny"] == "11400"
    assert waterfall["waterfall_reconciliation_residual_cny"] == "0"
    multiple = base["multiple_attribution"]
    assert multiple["common_pe_scale_factor_required"] == "4.75"
    by_segment = {row["segment_id"]: row for row in multiple["required_common_pe_by_segment"]}
    assert by_segment["seg_a"]["required_pe_under_common_scale_x"] == "47.50"
    assert by_segment["seg_b"]["required_pe_under_common_scale_x"] == "95.00"
    assert by_segment["seg_a"]["selected_pe_evidence_refs"] == ["E2"]
    parent = base["parent_adjustment_attribution"]
    assert parent["capitalized_central_cost_load_on_required_segment_pool_cny"] == "100"
    assert parent["net_cash_debt_offset_to_required_segment_pool_cny"] == "-200"
    assert parent["net_parent_adjustment_load_cny"] == "-100"
    dilution = base["dilution_attribution"]
    assert dilution["required_total_equity_value_cny"] == "11500"
    assert dilution["b4_forecast_total_equity_value_cny"] == "2500"
    assert Decimal(dilution["break_even_diluted_shares_at_b4_forecast_equity"]) == Decimal("2500") / Decimal("115")
    assert dilution["additional_required_equity_for_plus_one_percent_shares_cny"] == "115.00"
    assert result["external_mie_modified"] is False
    assert result["sotp_input_modified"] is False
    assert result["b61_input_modified"] is False
    assert result["decision_authority"] is False


def test_b63_blocks_capitalized_parent_cost_mismatch_against_b61_copy():
    inversion, sotp, b62 = _b63_inputs()
    sotp["scenarios"]["base"]["parent_level_adjustments"]["capitalized_central_cost_value_cny"] = "101"
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    base = result["scenarios"]["base"]
    assert base["status"] == "RECONCILIATION_MISMATCH"
    assert any("B61_CENTRAL_COST_VS_SOTP_MISMATCH" in item for item in base["issues"])


def test_b63_blocks_diluted_share_count_mismatch():
    inversion, sotp, b62 = _b63_inputs()
    inversion["scenarios"]["base"]["selected_diluted_shares"] = "101"
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"
    assert "B61_SHARES_VS_SOTP_MISMATCH" in result["scenarios"]["base"]["issues"]


def test_b63_blocks_segment_universe_mismatch():
    inversion, sotp, b62 = _b63_inputs()
    b62["scenarios"]["base"]["segment_comparisons"].pop()
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"
    assert any("SEGMENT_POOL_RECALCULATION" in item or "UNIVERSE_MISMATCH" in item for item in result["scenarios"]["base"]["issues"])


def test_b63_blocks_wrong_earnings_basis_before_value_gap_attribution():
    inversion, sotp, b62 = _b63_inputs()
    sotp["scenarios"]["base"]["segments"][0]["earnings_basis"] = "ALL_ITEMS_PARENT_PROFIT"
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"
    assert "SOTP_EARNINGS_BASIS_NOT_NORMALIZED_PARENT_ATTRIBUTABLE:seg_a" in result["scenarios"]["base"]["issues"]


def test_b63_requires_same_forecast_period_across_b61_b62_and_sotp():
    inversion, sotp, b62 = _b63_inputs()
    b62["forecast_period"] = "2027FY"
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["status"] == "FORECAST_PERIOD_MISMATCH"


def test_b63_does_not_apply_to_non_sotp_primary_model():
    inversion, sotp, b62 = _b63_inputs()
    inversion["selected_model_family"] = "EPS_MULTIPLE"
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["status"] == "NOT_APPLICABLE_NOT_SOTP"
    assert result["scenarios"] == {}


def test_b63_keeps_multiple_sensitivity_explicit_when_forecast_value_pool_cannot_support_a_positive_scale():
    inversion, sotp, b62 = _b63_inputs()
    b62["scenarios"]["base"]["b4_forecast_segment_equity_value_pool_at_selected_sotp_pe_cny"] = "0"
    b62["scenarios"]["base"]["b4_forecast_implied_total_equity_value_with_selected_parent_adjustments_cny"] = "100"
    b62["scenarios"]["base"]["b4_forecast_implied_terminal_value_per_share_cny"] = "1"
    b62["scenarios"]["base"]["segment_comparisons"][0]["b4_forecast_parent_attributable_normalized_profit_cny"] = "-10"
    b62["scenarios"]["base"]["segment_comparisons"][0]["profit_change_value_effect_at_selected_sotp_pe_cny"] = "-1100"
    b62["scenarios"]["base"]["segment_comparisons"][1]["b4_forecast_parent_attributable_normalized_profit_cny"] = "5"
    b62["scenarios"]["base"]["segment_comparisons"][1]["profit_change_value_effect_at_selected_sotp_pe_cny"] = "-900"
    result = build_sotp_valuation_gap_attribution(
        local_sotp_inversion=inversion,
        sotp_valuation=sotp,
        segment_earnings_reconciliation=b62,
    )
    assert result["status"] == "PARTIAL"
    assert result["scenarios"]["base"]["status"] == "PARTIAL"
    assert result["scenarios"]["base"]["multiple_attribution"]["status"] == "NOT_IDENTIFIABLE"
    assert result["scenarios"]["base"]["multiple_attribution"]["common_pe_scale_factor_required"] is None
