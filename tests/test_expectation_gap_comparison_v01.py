from __future__ import annotations

from iios_mvp.expectation_gap_comparison_v01 import build_expectation_gap_comparison


def _inputs():
    local = {
        "selected_model_family": "SOTP",
        "valuation_gap_attribution": {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "scenarios": {},
        },
        "segment_earnings_reconciliation": {
            "status": "CONDITIONAL_RECONCILIATION_CALCULATED",
            "scenarios": {},
        },
        "operating_requirement_reverse_engineering": {
            "status": "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED",
            "scenarios": {},
        },
    }
    for name in ("bear", "base", "bull"):
        local["valuation_gap_attribution"]["scenarios"][name] = {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "value_pool_waterfall": {
                "step_3_b4_forecast_pool_at_selected_pes_cny": "1250",
                "step_5_required_segment_pool_cny": "1200",
            },
            "multiple_attribution": {
                "status": "CONDITIONAL_SENSITIVITY_CALCULATED",
                "required_common_pe_by_segment": [
                    {
                        "segment_id": "seg_a",
                        "required_pe_under_common_scale_x": "15",
                    }
                ],
            },
        }
        local["segment_earnings_reconciliation"]["scenarios"][name] = {
            "status": "CALCULATED_CONDITIONAL",
            "forecast_period": "2027FY",
            "b4_forecast_implied_terminal_value_per_share_cny": "12.5",
            "required_terminal_value_per_share_for_required_return_cny": "12",
        }
        local["operating_requirement_reverse_engineering"]["scenarios"][name] = {
            "status": "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED",
            "segments": [
                {
                    "segment_id": "seg_a",
                    "segment_name": "Segment A",
                    "b4_forecast_normalized_parent_attributable_profit_cny": "100",
                    "selected_sotp_pe_x": "13",
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
    base = result["scenarios"]["base"]
    assert base["earnings_gap"]["b4_forecast_pool_minus_required_pool_cny"] == "50"
    assert base["earnings_gap"]["headroom_vs_required_pool_pct"] == "4.166666666666666666666666667"
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
    assert odds["payoff_asymmetry"]["base_upside_to_bear_downside_ratio"] == "1.5"
    assert odds["payoff_asymmetry"]["bull_upside_to_bear_downside_ratio"] == "3"
    assert odds["thesis_break_stress"]["probability_weighted"] is False
    assert odds["time_cost"]["holding_period_year_fraction"] is None
    assert result["scenarios"]["base"]["event_timing_gap"]["status"] == "NOT_IDENTIFIABLE"


def test_b76_fails_closed_when_b63_or_b68_is_not_available():
    local = _inputs()
    local["valuation_gap_attribution"]["status"] = "PARTIAL"
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
