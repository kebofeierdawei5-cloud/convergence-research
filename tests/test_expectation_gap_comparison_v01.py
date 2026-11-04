from __future__ import annotations

from decimal import Decimal

from iios_mvp.expectation_gap_comparison_v01 import build_expectation_gap_comparison


def _inputs():
    local = {
        "selected_model_family": "SOTP",
        "currency": "CNY",
        "reference_price": "10",
        "forecast_period": "2027FY",
        "valuation_terminal_date": "2027-12-31",
        "scenarios": {},
        "valuation_gap_attribution": {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "scenarios": {},
        },
        "segment_earnings_reconciliation": {
            "status": "CONDITIONAL_RECONCILIATION_CALCULATED",
            "forecast_period": "2027FY",
            "valuation_terminal_date": "2027-12-31",
            "scenarios": {},
        },
        "operating_requirement_reverse_engineering": {
            "status": "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED",
            "scenarios": {},
        },
    }
    for name in ("bear", "base", "bull"):
        local["scenarios"][name] = {
            "status": "CALCULATED_CONDITIONAL",
            "selected_diluted_shares": "100",
            "selected_capitalized_central_cost_cny": "0",
            "selected_net_cash_debt_cny": "0",
            "selected_other_adjustments_cny": "0",
            "requirements": {
                "required_return": {
                    "annualized_return_rate": "0.12",
                    "without_distributions": {
                        "required_terminal_equity_value_cny": "1200",
                        "required_segment_equity_value_pool_cny": "1200",
                        "selected_segment_equity_value_pool_cny": "1000",
                    },
                },
                "fundamental_target_annualized_return": {"annualized_return_rate": "0.15"},
            },
        }
        local["valuation_gap_attribution"]["scenarios"][name] = {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "value_pool_waterfall": {
                "step_1_selected_sotp_segment_pool_cny": "1000",
                "step_2_b4_earnings_effect_at_selected_pes_cny": "250",
                "step_3_b4_forecast_pool_at_selected_pes_cny": "1250",
                "step_4_common_pe_scale_effect_to_required_pool_cny": "-50",
                "step_5_required_segment_pool_cny": "1200",
                "waterfall_reconciliation_residual_cny": "0",
            },
            "parent_adjustment_attribution": {
                "capitalized_central_cost_load_on_required_segment_pool_cny": "0",
                "net_cash_debt_offset_to_required_segment_pool_cny": "0",
                "other_adjustments_offset_to_required_segment_pool_cny": "0",
            },
            "dilution_attribution": {
                "selected_diluted_shares": "100",
                "required_terminal_value_per_share_cny": "12",
                "required_total_equity_value_cny": "1200",
                "b4_forecast_total_equity_value_cny": "1250",
                "total_equity_gap_cny": "-50",
                "per_share_gap_cny": "-0.5",
            },
            "multiple_attribution": {
                "status": "CONDITIONAL_SENSITIVITY_CALCULATED",
                "required_common_pe_by_segment": [
                    {"segment_id": "seg_a", "required_pe_under_common_scale_x": "15"}
                ],
            },
        }
        local["segment_earnings_reconciliation"]["scenarios"][name] = {
            "status": "CALCULATED_CONDITIONAL",
            "forecast_period": "2027FY",
            "selected_diluted_shares": "100",
            "selected_sotp_segment_equity_value_pool_cny": "1000",
            "b4_forecast_segment_equity_value_pool_at_selected_sotp_pe_cny": "1250",
            "required_segment_equity_value_pool_for_required_return_cny": "1200",
            "b4_forecast_implied_total_equity_value_with_selected_parent_adjustments_cny": "1250",
            "required_terminal_equity_value_for_required_return_cny": "1200",
            "b4_forecast_implied_terminal_value_per_share_cny": "12.5",
            "required_terminal_value_per_share_for_required_return_cny": "12",
            "selected_parent_adjustments": {
                "capitalized_central_cost_cny": "0",
                "net_cash_debt_cny": "0",
                "other_adjustments_cny": "0",
            },
        }
        local["operating_requirement_reverse_engineering"]["scenarios"][name] = {
            "status": "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED",
            "segments": [
                {
                    "segment_id": "seg_a",
                    "segment_name": "Segment A",
                    "b4_forecast_normalized_parent_attributable_profit_cny": "100",
                    "selected_sotp_pe_x": "12.5",
                    "b61_required_profit_lens": {
                        "required_parent_attributable_profit_cny": "90",
                        "reverse_engineering": {
                            "status": "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED",
                            "product_driver_alternatives": [
                                {
                                    "product_id": "p1",
                                    "product_name": "Product 1",
                                    "current_forward_assumptions": {
                                        "sales_volume_tonnes": "100",
                                        "net_asp_cny_per_tonne": "20",
                                        "variable_cost_cny_per_tonne": "10",
                                    },
                                    "single_driver_alternatives": {
                                        "sales_volume_only": {"status": "CALCULATED_CONDITIONAL", "required_sales_volume_tonnes": "90", "change_pct": "-10"},
                                        "net_asp_only": {"status": "CALCULATED_CONDITIONAL", "required_net_asp_cny_per_tonne": "19", "change_pct": "-5"},
                                        "unit_variable_cost_only": {"status": "CALCULATED_CONDITIONAL", "required_variable_cost_cny_per_tonne": "11", "change_pct": "10"},
                                    },
                                }
                            ],
                        },
                    },
                    "b63_full_b4_vector_lens": {
                        "required_parent_attributable_profit_cny": "95",
                        "reverse_engineering": {
                            "status": "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED",
                            "product_driver_alternatives": [],
                        },
                    },
                }
            ],
        }
    return local

def test_b76_compares_b4_full_vector_with_b61_b63_price_requirements():
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=_inputs(),
        return_metrics={"scenario_terminal_wealth": {"bear": "8", "base": "13", "bull": "16"}, "expected_annualized_return": "0.16"},
        price_input={"price": "10"},
        forecast_valuation={"probabilities_calibrated": False},
        thesis_break_stress_review={"status": "PASS", "stress_total_return": "-0.4", "stress_downside_pct": "40", "probability_weighted": False},
        external_mie_status="NOT_IDENTIFIABLE",
    )
    assert result["status"] == "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    assert result["price_conditioned_comparison_status"] == "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    assert result["coverage_status"] == "PARTIAL_WIN_PROBABILITY_AND_EVENT_TIMING_NOT_IDENTIFIABLE"
    base = result["scenarios"]["base"]
    assert base["earnings_gap"]["b4_forecast_pool_minus_required_pool_cny"] == "50"
    assert base["arithmetic_reconciliation"]["status"] == "PASS"
    assert base["earnings_gap"]["required_return_annualized_rate"] == "0.12"
    assert base["earnings_gap"]["fundamental_target_annualized_rate"] == "0.15"
    assert abs(float(base["earnings_gap"]["headroom_vs_required_pool_pct"]) - 4.166666666666667) < 1e-12
    assert base["operating_gap"]["status"] == "CONDITIONAL_PRICE_CONDITIONED_OPERATING_ALTERNATIVES"
    segment = base["segment_comparisons"][0]
    assert segment["b4_forecast_minus_b61_requirement_cny"]["difference"] == "10"
    assert segment["b4_forecast_minus_b63_segment_sensitivity_cny"]["difference"] == "5"
    assert segment["b63_required_common_pe_x"] == "15"
    assert segment["b61_driver_alternatives"][0]["price_conditioned_single_driver_alternatives"]["sales_volume_only"]["required_sales_volume_tonnes"] == "90"
    assert result["external_mie_status_unchanged"] == "NOT_IDENTIFIABLE"
    assert result["external_mie_modified"] is False
    assert result["expectation_gap_modified"] is False


def test_b76_does_not_convert_scenario_weights_or_payoff_ratio_into_win_probability():
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=_inputs(),
        return_metrics={"scenario_terminal_wealth": {"bear": "8", "base": "13", "bull": "16"}, "expected_annualized_return": "0.16"},
        price_input={"price": "10"},
        forecast_valuation={"probabilities_calibrated": True},
        thesis_break_stress_review={"status": "PASS", "stress_total_return": "-0.4", "stress_downside_pct": "40", "probability_weighted": False},
        external_mie_status="PASS",
    )
    odds = result["win_odds"]
    assert odds["win_probability_status"] == "NOT_IDENTIFIABLE"
    assert odds["win_probability_range"] is None
    assert odds["probability_weighted_return"]["scenario_probabilities_calibrated"] is False
    assert odds["probability_weighted_return"]["model_declared_probabilities_calibrated"] is True
    assert odds["probability_weighted_return"]["calibration_status"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert odds["payoff_asymmetry"]["base_upside_to_bear_downside_ratio"] == "1.5"
    assert odds["payoff_asymmetry"]["bull_upside_to_bear_downside_ratio"] == "3"
    assert odds["thesis_break_stress"]["probability_weighted"] is False
    assert odds["time_cost"]["holding_period_year_fraction"] is None
    assert result["scenarios"]["base"]["event_timing_gap"]["status"] == "NOT_IDENTIFIABLE"


def test_b76_fails_closed_when_b63_or_b68_is_not_available():
    local = _inputs()
    local["valuation_gap_attribution"]["status"] = "NOT_IDENTIFIABLE"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "10"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
    )
    assert result["status"] == "BLOCKED_BY_B63"
    assert result["scenarios"] == {}
    assert result["external_mie_modified"] is False


def test_b76_eps_multiple_blocks_when_b60_result_is_missing():
    local = _inputs()
    local["selected_model_family"] = "EPS_MULTIPLE"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics={"scenario_terminal_wealth": {"bear": "8", "base": "13", "bull": "16"}},
        price_input={"price": "10"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
    )
    assert result["status"] == "BLOCKED_BY_B60_RESULT_MISSING"
    assert result["price_conditioned_comparison_status"] == "BLOCKED_BY_B60_RESULT_MISSING"
    assert result["scenarios"] == {}
    assert result["external_mie_modified"] is False
    assert result["win_odds"]["win_probability_status"] == "NOT_IDENTIFIABLE"


def _eps_multiple_inputs():
    local = _inputs()
    local["selected_model_family"] = "EPS_MULTIPLE"
    b60 = {
        "status": "CONDITIONAL_SENSITIVITY_CALCULATED",
        "selected_model_family": "EPS_MULTIPLE",
        "currency": "CNY",
        "forecast_period": "2027FY",
        "valuation_terminal_date": "2027-12-31",
        "annualization_year_fraction": "1",
        "required_return_annualized_rate": "0.10",
        "fundamental_target_annualized_rate": "0.15",
        "reference_price": "30",
        "price_assurance": "OPERATOR_ATTESTED",
        "price_pit_status": "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY",
        "external_mie_status_unchanged": "NOT_IDENTIFIABLE",
        "scenarios": {},
    }
    scenarios = (
        ("bear", "1.60", "160000", "12", "1.50", "18", "2.75", "2.875", "0", "0", "VALIDATED_NO_FUTURE_DISTRIBUTIONS"),
        ("base", "2.35", "235000", "15", "2.30", "34.5", "2.20", "2.30",
         "0.9090909090909090909090909091", "0.8695652173913043478260869565", "VALIDATED_DATED_CASH_FLOWS"),
        ("bull", "2.80", "280000", "18", "2.70", "48.6",
         "1.833333333333333333333333333", "1.916666666666666666666666667", "0", "0",
         "VALIDATED_NO_FUTURE_DISTRIBUTIONS"),
    )
    for name, eps, profit, pe, primary_eps, primary_terminal, hurdle, target, pv_hurdle, pv_target, dist_status in scenarios:
        hurdle_adjusted = hurdle
        target_adjusted = target
        if name == "base":
            hurdle_adjusted = "2.133333333333333333333333333"
            target_adjusted = "2.233333333333333333333333333"
        b60["scenarios"][name] = {
            "status": "CALCULATED_CONDITIONAL",
            "b57_status": "CALCULATED_AND_RECONCILED",
            "b58_status": "EPS_MISMATCH",
            "b58_forecast_period_match": True,
            "b57_forward_period": "2027FY",
            "b57_all_items_parent_attributable_net_profit_proxy_cny": profit,
            "b57_diluted_weighted_average_shares": "100000",
            "b57_all_items_eps_proxy": eps,
            "selected_terminal_pe": pe,
            "primary_eps_actually_used": primary_eps,
            "primary_terminal_value_using_selected_pe": primary_terminal,
            "required_return_eps_without_distributions": hurdle,
            "required_return_eps_with_validated_distributions": hurdle_adjusted,
            "fundamental_target_eps_without_distributions": target,
            "fundamental_target_eps_with_validated_distributions": target_adjusted,
            "present_value_of_validated_cash_distributions_at_hurdle": pv_hurdle,
            "present_value_of_validated_cash_distributions_at_fundamental_target": pv_target,
            "distribution_status": dist_status,
        }
    return local, b60


def test_b76_eps_multiple_compares_b4_all_items_eps_with_b60_hurdle_eps():
    local, b60 = _eps_multiple_inputs()
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics={
            "scenario_terminal_wealth": {"bear": "24", "base": "33", "bull": "42"},
            "annualization_year_fraction": "1",
            "horizon_years": "1",
            "expected_annualized_return": "0.12",
            "expected_annualized_return_method": "SUBMITTED_SCENARIO_WEIGHTS",
        },
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review={"status": "PASS", "stress_total_return": "-0.4", "stress_downside_pct": "40"},
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    assert result["status"] == "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    assert result["price_conditioned_comparison_status"] == "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    comparison = result["eps_multiple_comparison"]
    assert comparison["status"] == "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    assert comparison["forecast_period"] == "2027FY"
    assert comparison["valuation_terminal_date"] == "2027-12-31"
    base = comparison["scenarios"]["base"]
    required = base["required_return"]["without_distributions"]
    assert required["forecast_eps_cny_per_share"] == "2.35"
    assert Decimal(required["required_eps_cny_per_share"]) == Decimal("2.2")
    assert required["forecast_minus_required_cny_per_share"] == "0.15"
    assert abs(float(required["headroom_vs_required_pct"]) - 6.818181818181818) < 1e-12
    assert required["direction"] == "B4_FORECAST_ABOVE_REQUIREMENT"
    assert abs(float(base["required_return"]["with_validated_distributions"]["required_eps_cny_per_share"]) - 2.1333333333333333) < 1e-12
    assert base["fundamental_target"]["without_distributions"]["required_eps_cny_per_share"] == "2.30"
    assert base["arithmetic_reconciliation"]["status"] == "PASS"
    assert result["win_odds"]["win_probability_status"] == "NOT_IDENTIFIABLE"
    assert result["win_odds"]["payoff_asymmetry"]["base_upside_to_bear_downside_ratio"] == "0.5"
    assert result["win_odds"]["payoff_asymmetry"]["bull_upside_to_bear_downside_ratio"] == "2"
    assert result["win_odds"]["thesis_break_stress"]["stress_downside_pct"] == "40"
    assert result["win_odds"]["time_cost"]["holding_period_year_fraction"] == "1"
    assert comparison["external_mie_modified"] is False
    assert comparison["decision_authority"] is False


def test_b76_eps_multiple_period_mismatch_keeps_gap_unknown():
    local, b60 = _eps_multiple_inputs()
    b60["scenarios"]["base"]["b58_forecast_period_match"] = False
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    comparison = result["eps_multiple_comparison"]
    assert comparison["status"] == "PARTIAL"
    base = comparison["scenarios"]["base"]
    assert base["status"] == "NOT_IDENTIFIABLE"
    assert "B4_B57_B58_B60_FORECAST_PERIOD_NOT_CONFIRMED_MATCH" in base["issues"]
    assert base["required_return"] == {}


def test_b76_eps_multiple_does_not_use_unvalidated_distribution_adjustment():
    local, b60 = _eps_multiple_inputs()
    b60["scenarios"]["base"]["distribution_status"] = "NOT_VALIDATED_OR_NOT_AVAILABLE"
    b60["scenarios"]["base"]["required_return_eps_with_validated_distributions"] = "1.9"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    adjusted = result["eps_multiple_comparison"]["scenarios"]["base"]["required_return"]["with_validated_distributions"]
    assert adjusted["status"] == "NOT_IDENTIFIABLE"
    assert adjusted["required_eps_cny_per_share"] is None
    assert adjusted["forecast_minus_required_cny_per_share"] is None


def test_b76_eps_multiple_blocks_non_reconciled_b57_eps():
    local, b60 = _eps_multiple_inputs()
    b60["scenarios"]["base"]["b57_status"] = "PARTIAL"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    base = result["eps_multiple_comparison"]["scenarios"]["base"]
    assert base["status"] == "NOT_IDENTIFIABLE"
    assert "B57_COMPANY_WIDE_EARNINGS_EPS_BRIDGE_NOT_RECONCILED" in base["issues"]
    assert base["required_return"] == {}


def test_b76_eps_multiple_blocks_price_reference_mismatch():
    local, b60 = _eps_multiple_inputs()
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "31"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    comparison = result["eps_multiple_comparison"]
    assert result["status"] == "PRICE_REFERENCE_MISMATCH"
    assert comparison["price_reference_status"] == "MISMATCH"
    assert comparison["scenarios"] == {}


def test_b76_eps_multiple_recomputes_b57_profit_over_diluted_shares():
    local, b60 = _eps_multiple_inputs()
    b60["scenarios"]["base"]["b57_all_items_parent_attributable_net_profit_proxy_cny"] = "236000"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    base = result["eps_multiple_comparison"]["scenarios"]["base"]
    assert base["status"] == "ARITHMETIC_RECONCILIATION_MISMATCH"
    assert base["arithmetic_reconciliation"]["b57_profit_divided_by_shares"] == "MISMATCH"
    assert base["required_return"] == {}


def test_b76_eps_multiple_recomputes_required_return_eps():
    local, b60 = _eps_multiple_inputs()
    b60["scenarios"]["base"]["required_return_eps_without_distributions"] = "2.25"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    base = result["eps_multiple_comparison"]["scenarios"]["base"]
    assert base["status"] == "ARITHMETIC_RECONCILIATION_MISMATCH"
    assert base["arithmetic_reconciliation"]["required_return_eps"] == "MISMATCH"
    assert base["required_return"] == {}


def test_b76_sotp_partial_common_multiple_does_not_block_value_pool_comparison():
    local = _inputs()
    local["valuation_gap_attribution"]["status"] = "PARTIAL"
    local["valuation_gap_attribution"]["scenarios"]["base"]["status"] = "PARTIAL"
    local["valuation_gap_attribution"]["scenarios"]["base"]["issues"] = [
        "COMMON_PE_SCALE_NOT_IDENTIFIABLE_NONPOSITIVE_VALUE_POOL"
    ]
    local["valuation_gap_attribution"]["scenarios"]["base"]["multiple_attribution"] = {
        "status": "NOT_IDENTIFIABLE",
        "required_common_pe_by_segment": [],
    }
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "10"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
    )
    base = result["scenarios"]["base"]
    assert result["status"] == "PARTIAL"
    assert base["status"] == "PARTIAL"
    assert base["earnings_gap"]["b4_forecast_pool_minus_required_pool_cny"] == "50"
    assert abs(float(base["earnings_gap"]["headroom_vs_required_pool_pct"]) - 4.166666666666667) < 1e-12
    assert base["valuation_gap"]["status"] == "NOT_IDENTIFIABLE_OR_PARTIAL"


def test_b76_sotp_waterfall_mismatch_keeps_value_gap_unknown():
    local = _inputs()
    local["valuation_gap_attribution"]["scenarios"]["base"]["value_pool_waterfall"]["step_4_common_pe_scale_effect_to_required_pool_cny"] = "-49"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "10"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
    )
    base = result["scenarios"]["base"]
    assert base["status"] == "RECONCILIATION_MISMATCH"
    assert base["arithmetic_reconciliation"]["status"] == "MISMATCH"
    assert base["earnings_gap"]["b4_forecast_pool_minus_required_pool_cny"] is None
    assert base["earnings_gap"]["direction"] == "UNKNOWN"


def test_b76_eps_multiple_recomputes_primary_eps_times_terminal_pe():
    local, b60 = _eps_multiple_inputs()
    b60["scenarios"]["base"]["primary_terminal_value_using_selected_pe"] = "34"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    base = result["eps_multiple_comparison"]["scenarios"]["base"]
    assert base["status"] == "ARITHMETIC_RECONCILIATION_MISMATCH"
    assert base["arithmetic_reconciliation"]["primary_eps_times_pe"] == "MISMATCH"
    assert base["required_return"] == {}


def test_b76_sotp_b68_vector_mismatch_keeps_value_gap_unknown():
    local = _inputs()
    local["operating_requirement_reverse_engineering"]["scenarios"]["base"]["segments"][0][
        "b4_forecast_normalized_parent_attributable_profit_cny"
    ] = "99"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "10"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
    )
    base = result["scenarios"]["base"]
    assert base["status"] == "RECONCILIATION_MISMATCH"
    assert base["arithmetic_reconciliation"]["checks"][
        "b68_full_vector_recomputed_pool_matches_b63_step_3"
    ] == "MISMATCH"
    assert base["earnings_gap"]["b4_forecast_pool_minus_required_pool_cny"] is None


def test_b76_sotp_blocks_when_b61_reference_price_differs_from_structured_price():
    local = _inputs()
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "11"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
    )
    assert result["status"] == "PRICE_REFERENCE_MISMATCH"
    assert result["price_reference_status"] == "MISMATCH"
    assert result["scenarios"] == {}


def test_b76_eps_multiple_accepts_reconciled_forward_eps_with_unknown_history():
    local, b60 = _eps_multiple_inputs()
    for row in b60["scenarios"].values():
        row["b57_status"] = "FORWARD_ALL_ITEMS_EPS_CALCULATED_HISTORICAL_NORMALIZATION_NOT_IDENTIFIABLE"
        row["b58_status"] = "MATCH"
    result = build_expectation_gap_comparison(
        local_sotp_recalculation=local,
        return_metrics=None,
        price_input={"price": "30"},
        forecast_valuation={},
        thesis_break_stress_review=None,
        external_mie_status="NOT_IDENTIFIABLE",
        local_eps_multiple_recalculation=b60,
    )
    comparison = result["eps_multiple_comparison"]
    assert comparison["status"] == "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    assert comparison["scenarios"]["base"]["status"] == "CALCULATED"
    assert comparison["scenarios"]["base"]["arithmetic_reconciliation"]["status"] == "PASS"
