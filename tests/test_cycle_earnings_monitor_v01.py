from __future__ import annotations

from iios_mvp.local_investment_pilot_v01 import REPLAY_COMPARISON_FIELDS
from iios_mvp.cycle_earnings_monitor_v01 import (
    CYCLE_EARNINGS_MONITOR_SCHEMA,
    evaluate_cycle_earnings_monitor,
)


def _measure(value: str, *, data_class: str = "ANALYST_ASSUMPTION", basis: str = "明确的情景归一化调整") -> dict:
    return {
        "value": value,
        "unit": "CNY",
        "data_class": data_class,
        "basis": basis,
        "evidence_refs": ["E_ACTUAL"] if data_class == "OBSERVED_ACTUAL" else [],
    }


def _evaluate(raw: dict, b4: dict, evidence: list[dict], **kwargs) -> dict:
    return evaluate_cycle_earnings_monitor(
        raw,
        operating_driver_forecast=b4,
        forecast_valuation={
            "model_family": "EPS_MULTIPLE",
            "model": "EPS_MULTIPLE",
            "entry_value_reference_per_share": "10",
            "scenarios": {
                "bear": {"terminal_value_per_share": "8"},
                "base": {"terminal_value_per_share": "10"},
                "bull": {"terminal_value_per_share": "12"},
            },
        },
        valuation_model_consistency={"primary_model_price_calculation_eligible": True},
        valuation_timing={"status": "PASS"},
        assessment={},
        evidence_register=evidence,
        **kwargs,
    )


def _valid_case() -> tuple[dict, dict, list[dict]]:
    raw = {
        "schema_version": CYCLE_EARNINGS_MONITOR_SCHEMA,
        "industry_cycle": {
            "cycle_id": "chemical_cycle_2026",
            "phase": "RECOVERY",
            "phase_basis": "需求边际改善且行业报价由低位回升",
            "evidence_refs": ["E_ACTUAL"],
            "counter_evidence_refs": ["E_COUNTER"],
            "leading_indicators": [
                {
                    "indicator_id": "demand_growth",
                    "name": "下游订单同比",
                    "direction": "IMPROVING",
                    "observation": "订单同比由负转正",
                    "threshold_or_reversal": "连续两个月同比转负",
                    "review_by": "FY2027Q1",
                    "evidence_refs": ["E_ACTUAL"],
                    "counter_evidence_refs": ["E_COUNTER"],
                }
            ],
            "reversal_signals": [
                {
                    "signal_id": "orders_reverse",
                    "related_indicator_id": "demand_growth",
                    "condition": "下游订单连续两个月同比转负",
                    "threshold": "连续两个月同比小于0",
                    "review_by": "FY2027Q1",
                    "operating_impact": "销量与产能利用率假设下调",
                    "valuation_impact": "下修正常化利润区间并重估估值",
                    "evidence_refs": ["E_COUNTER"],
                }
            ],
        },
        "normalized_earnings": {
            "metric": "NET_PROFIT_CNY",
            "scope": "COMPANY_WIDE",
            "reference_period": "FY2026",
            "period": "FY2027",
            "normalization_basis": "以已披露盈利为基数，逐项调整周期与结构性差异",
            "scenarios": {
                "bear": {
                    "reference_net_profit_cny": {
                        "value": "100", "unit": "CNY", "data_class": "OBSERVED_ACTUAL",
                        "basis": "已披露年度净利润", "evidence_refs": ["E_ACTUAL"],
                    },
                    "adjustments": [{
                        "adjustment_id": "cycle_down",
                        "driver_id": "demand_growth",
                        "rationale": "需求复苏不及预期，回归较低中枢",
                        "amount_cny": _measure("-20"),
                    }],
                    "low_cny": "70", "point_cny": "80", "high_cny": "90",
                    "scenario_basis": "弱复苏情景",
                },
                "base": {
                    "reference_net_profit_cny": {
                        "value": "100", "unit": "CNY", "data_class": "OBSERVED_ACTUAL",
                        "basis": "已披露年度净利润", "evidence_refs": ["E_ACTUAL"],
                    },
                    "adjustments": [{
                        "adjustment_id": "cycle_flat",
                        "driver_id": "demand_growth",
                        "rationale": "中性情景下参考基数无需额外调整",
                        "amount_cny": _measure("0"),
                    }],
                    "low_cny": "90", "point_cny": "100", "high_cny": "110",
                    "scenario_basis": "中性情景",
                },
                "bull": {
                    "reference_net_profit_cny": {
                        "value": "100", "unit": "CNY", "data_class": "OBSERVED_ACTUAL",
                        "basis": "已披露年度净利润", "evidence_refs": ["E_ACTUAL"],
                    },
                    "adjustments": [{
                        "adjustment_id": "cycle_up",
                        "driver_id": "demand_growth",
                        "rationale": "需求持续修复并带动价格和产能利用率改善",
                        "amount_cny": _measure("20"),
                    }],
                    "low_cny": "110", "point_cny": "120", "high_cny": "130",
                    "scenario_basis": "强复苏情景",
                },
            },
        },
        "review_triggers": [{
            "trigger_id": "orders_review",
            "driver_id": "demand_growth",
            "condition": "订单同比连续两个月转负",
            "threshold": "连续两个月同比小于0",
            "review_by": "FY2027Q1",
            "expected_operating_impact": "销量和利用率下修",
            "valuation_path": "重估正常化净利润、EPS与每股价值",
            "review_action": "REESTIMATE_NORMALIZED_EARNINGS",
            "causal_path": [
                "INDUSTRY_CYCLE", "NORMALIZED_EARNINGS", "EPS_OR_FCF",
                "PER_SHARE_VALUE", "POSITION_REVIEW",
            ],
            "evidence_refs": ["E_COUNTER"],
        }],
        "variance_attribution": [
            {
                "scenario": "bear", "attribution_id": "bear_cycle_delta",
                "driver_id": "demand_growth", "review_trigger_id": "orders_review",
                "category": "INDUSTRY_CYCLE", "rationale": "B4 与正常化中枢一致，明确记录零差异",
                "amount_cny": _measure("0"),
            },
            {
                "scenario": "base", "attribution_id": "base_cycle_delta",
                "driver_id": "demand_growth", "review_trigger_id": "orders_review",
                "category": "INDUSTRY_CYCLE", "rationale": "B4 与正常化中枢一致，明确记录零差异",
                "amount_cny": _measure("0"),
            },
            {
                "scenario": "bull", "attribution_id": "bull_cycle_delta",
                "driver_id": "demand_growth", "review_trigger_id": "orders_review",
                "category": "INDUSTRY_CYCLE", "rationale": "B4 与正常化中枢一致，明确记录零差异",
                "amount_cny": _measure("0"),
            },
        ],
        "cash_flow_assessments": [
            {
                "scenario": scenario,
                "attribution_id": f"{scenario}_cycle_delta",
                "driver_id": "demand_growth",
                "review_trigger_id": "orders_review",
                "channel": "NO_DIRECT_CASH_EFFECT",
                "direction": "NO_DIRECT_EFFECT",
                "quantification_status": "NOT_APPLICABLE",
                "rationale": "该净利润归因行不声明独立直接现金流贡献；间接现金转换需在独立路径判断",
                "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
            }
            for scenario in ("bear", "base", "bull")
        ],
        "normalized_fcf": {
            "metric": "UNLEVERED_FCF_PROXY_CNY",
            "method": "B4_UNLEVERED_FCF_PROXY_EBIT_AFTER_TAX_PLUS_DA_MINUS_CASH_CAPEX_MINUS_EFFECTIVE_WC_V0.1",
            "scope": "COMPANY_WIDE",
            "reference_period": "FY2026",
            "period": "FY2027",
            "normalization_basis": "以 FY2026 FCF 为参考，逐项说明周期、资本开支与营运资金正常化假设",
            "scenarios": {
                scenario: {
                    "reference_fcf_cny": {
                        "value": value, "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                        "basis": "正常化 FCF 参考基准，须在正式研究中由可审计数据替换或证明",
                        "evidence_refs": ["E_ACTUAL"],
                    },
                    "cash_components": {
                        "ebit_cny": {
                            "value": {"bear": "50", "base": "60", "bull": "70"}[scenario],
                            "unit": "CNY", "data_class": "ANALYST_ASSUMPTION", "basis": "测试用 EBIT 代理值",
                            "evidence_refs": ["E_ACTUAL"],
                        },
                        "tax_rate": {
                            "value": "0.2", "unit": "ratio", "data_class": "ANALYST_ASSUMPTION",
                            "basis": "测试用税率假设", "evidence_refs": ["E_ACTUAL"],
                        },
                        "depreciation_amortization_cny": {
                            "value": {"bear": "10", "base": "12", "bull": "14"}[scenario],
                            "unit": "CNY", "data_class": "ANALYST_ASSUMPTION", "basis": "测试用折旧摊销代理值",
                            "evidence_refs": ["E_ACTUAL"],
                        },
                        "cash_capex_cny": {
                            "value": "5", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION", "basis": "测试用现金资本开支",
                            "evidence_refs": ["E_ACTUAL"],
                        },
                        "change_working_capital_cny": {
                            "value": "5", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION", "basis": "测试用原始营运资金变动",
                            "evidence_refs": ["E_ACTUAL"],
                        },
                        "effective_change_working_capital_cny": {
                            "value": "5", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION", "basis": "测试用有效营运资金变动",
                            "evidence_refs": ["E_ACTUAL"],
                        },
                        "inventory_cash_impact_proxy_cny": {
                            "value": "0", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION", "basis": "测试用库存现金影响代理",
                            "evidence_refs": ["E_ACTUAL"],
                        },
                        "inventory_working_capital_treatment": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
                        "inventory_reconciliation_status": "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
                    },
                    "adjustments": [
                        {
                            "adjustment_id": f"{scenario}_{category.lower()}_normalization",
                            "driver_id": "demand_growth",
                            "review_trigger_id": "orders_review",
                            "category": category,
                            "rationale": f"测试夹具显式登记 {category} 零调整，不代表真实公司估计",
                            "amount_cny": {
                                "value": "0", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                                "basis": "测试用零调整，不是实际估计",
                                "evidence_refs": ["E_COUNTER"],
                            },
                        }
                        for category in ("CAPEX", "WORKING_CAPITAL", "INVENTORY_MOVEMENT")
                    ],
                    "low_fcf_cny": str(int(value) - 5),
                    "point_fcf_cny": value,
                    "high_fcf_cny": str(int(value) + 5),
                    "scenario_basis": "测试夹具：用于结构和算术验证，不代表公司真实 FCF",
                }
                for scenario, value in (("bear", "40"), ("base", "50"), ("bull", "60"))
            },
        },
        "fcf_variance_attribution": [
            {
                "scenario": scenario,
                "fcf_attribution_id": f"{scenario}_{category.lower()}_measured_gap",
                "driver_id": "demand_growth",
                "review_trigger_id": "orders_review",
                "category": category,
                "rationale": f"测试夹具显式登记 {category} 实测组件差额；仅验证桥接算术",
                "amount_cny": {
                    "value": amount, "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                    "basis": "测试用组件差额，不代表真实公司估计",
                    "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
                },
            }
            for scenario in ("bear", "base", "bull")
            for category, amount in (
                ("OPERATING_CASH_CONVERSION", {"bear": "29", "base": "33", "bull": "39"}[scenario]),
                ("NON_CASH_EARNINGS", {"bear": "-7", "base": "-8", "bull": "-9"}[scenario]),
                ("CAPEX", {"bear": "-15", "base": "-17", "bull": "-20"}[scenario]),
                ("WORKING_CAPITAL", {"bear": "-7", "base": "-8", "bull": "-10"}[scenario]),
                ("INVENTORY_MOVEMENT", "0"),
            )
        ],
    }
    b4 = {
        "scope": "COMPANY_WIDE",
        "forecast_period": "FY2027",
        "scenarios": {
            "bear": {
                "net_profit_cny": "80", "unlevered_fcf_proxy_cny": "40", "financial_outputs_decision_usable": True,
                "ebit_cny": "86.25", "tax_rate": "0.2",
                "cash_capex_cny": "20", "change_working_capital_cny": "12", "effective_change_working_capital_cny": "12",
                "inventory_cash_impact_proxy_cny": "2", "inventory_working_capital_treatment": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
                "inventory_reconciliation_status": "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
                "depreciation_amortization_cny": "3", "finance_cost_cny": "1",
            },
            "base": {
                "net_profit_cny": "100", "unlevered_fcf_proxy_cny": "50", "financial_outputs_decision_usable": True,
                "ebit_cny": "101.25", "tax_rate": "0.2",
                "cash_capex_cny": "22", "change_working_capital_cny": "13", "effective_change_working_capital_cny": "13",
                "inventory_cash_impact_proxy_cny": "3", "inventory_working_capital_treatment": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
                "inventory_reconciliation_status": "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
                "depreciation_amortization_cny": "4", "finance_cost_cny": "2",
            },
            "bull": {
                "net_profit_cny": "120", "unlevered_fcf_proxy_cny": "60", "financial_outputs_decision_usable": True,
                "ebit_cny": "118.75", "tax_rate": "0.2",
                "cash_capex_cny": "25", "change_working_capital_cny": "15", "effective_change_working_capital_cny": "15",
                "inventory_cash_impact_proxy_cny": "4", "inventory_working_capital_treatment": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
                "inventory_reconciliation_status": "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
                "depreciation_amortization_cny": "5", "finance_cost_cny": "3",
            },
        },
    }
    evidence = [
        {"source_id": "E_ACTUAL", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"},
        {"source_id": "E_COUNTER", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"},
    ]
    return raw, b4, evidence


def test_complete_cycle_earnings_review_chain_is_diagnostic_only():
    raw, b4, evidence = _valid_case()
    result = _evaluate(raw, b4, evidence)

    assert result["status"] == "CHAIN_IDENTIFIABLE_NON_ADMITTED"
    assert result["industry_cycle"]["phase"] == "RECOVERY"
    assert result["normalized_earnings"]["scenarios"]["base"]["point_cny"] == "100"
    assert result["b4_comparison"]["scenarios"]["base"]["status"] == "DIAGNOSTIC_COMPARISON_ONLY"
    assert result["valuation_input_eligible"] is False
    assert result["formal_forecast_admission_created"] is False
    assert result["formal_valuation_admission_created"] is False
    assert result["decision_authority"] is False


def test_period_or_scope_mismatch_blocks_comparison_and_chain_pass():
    raw, b4, evidence = _valid_case()
    raw["normalized_earnings"]["period"] = "FY2028"
    result = _evaluate(raw, b4, evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert "NORMALIZED_EARNINGS_PERIOD_MISMATCH_B4" in result["normalized_earnings"]["issues"]
    assert result["b4_comparison"]["status"] != "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT"
    assert result["valuation_input_eligible"] is False


def test_missing_counter_evidence_and_reversal_signal_fail_closed():
    raw, b4, evidence = _valid_case()
    raw["industry_cycle"]["counter_evidence_refs"] = []
    raw["industry_cycle"]["reversal_signals"] = []
    result = _evaluate(raw, b4, evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert any("industry_cycle_counter_evidence:EVIDENCE_REFERENCE_REQUIRED" == issue for issue in result["industry_cycle"]["issues"])
    assert "CYCLE_REVERSAL_SIGNALS_REQUIRED" in result["industry_cycle"]["issues"]


def test_reported_base_plus_signed_adjustments_must_reconcile_to_normalized_point():
    raw, b4, evidence = _valid_case()
    raw["normalized_earnings"]["scenarios"]["base"]["adjustments"][0]["amount_cny"]["value"] = "15"
    result = _evaluate(raw, b4, evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert any("NORMALIZED_POINT_DOES_NOT_RECONCILE_TO_REFERENCE_PLUS_ADJUSTMENTS" in issue for issue in result["normalized_earnings"]["issues"])


def test_after_cutoff_evidence_does_not_support_cycle_or_normalized_earnings():
    raw, b4, evidence = _valid_case()
    result = _evaluate(raw, b4, evidence, after_cutoff_evidence_ids=["E_COUNTER", "E_ACTUAL"])

    assert result["status"] == "REVIEW_REQUIRED"
    assert any("EVIDENCE_SOURCE_AFTER_CUTOFF:E_COUNTER" in issue for issue in result["industry_cycle"]["issues"])
    assert any("EVIDENCE_SOURCE_AFTER_CUTOFF:E_ACTUAL" in issue for issue in result["normalized_earnings"]["issues"])
    assert result["valuation_input_eligible"] is False


def test_unknown_input_keeps_all_downstream_authority_false():
    result = evaluate_cycle_earnings_monitor(None, operating_driver_forecast={}, assessment={}, evidence_register=[])

    assert result["status"] == "NOT_IDENTIFIABLE"
    assert result["valuation_input_eligible"] is False
    assert result["formal_forecast_admission_created"] is False
    assert result["formal_valuation_admission_created"] is False
    assert result["decision_authority"] is False


def test_cycle_earnings_monitor_is_in_replay_comparison_contract():
    assert "cycle_earnings_monitor" in REPLAY_COMPARISON_FIELDS


def test_missing_b4_scenario_profit_blocks_aggregate_comparison_status():
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["base"]["net_profit_cny"] = None
    result = _evaluate(raw, b4, evidence)
    assert result["b4_comparison"]["status"] == "NOT_COMPARABLE_PERIOD_SCOPE_OR_NORMALIZED_EARNINGS_INCOMPLETE"
    assert result["status"] == "REVIEW_REQUIRED"


def test_primary_per_share_value_context_requires_eligible_model_and_timing():
    raw, b4, evidence = _valid_case()
    result = evaluate_cycle_earnings_monitor(
        raw,
        operating_driver_forecast=b4,
        forecast_valuation={"model_family": "EPS_MULTIPLE", "entry_value_reference_per_share": "10", "scenarios": {"bear": {"terminal_value_per_share": "8"}, "base": {"terminal_value_per_share": "10"}, "bull": {"terminal_value_per_share": "12"}}},
        valuation_model_consistency={"primary_model_price_calculation_eligible": False},
        valuation_timing={"status": "UNKNOWN"},
        assessment={}, evidence_register=evidence,
    )
    assert result["per_share_value"]["status"] == "NOT_IDENTIFIABLE"
    assert "PRIMARY_MODEL_PRICE_CALCULATION_NOT_ELIGIBLE" in result["per_share_value"]["issues"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_b4_minus_normalized_delta_reconciles_to_named_driver_attributions():
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["bear"]["net_profit_cny"] = "85"
    bear_attribution = next(row for row in raw["variance_attribution"] if row["scenario"] == "bear")
    bear_attribution["amount_cny"]["value"] = "5"
    result = _evaluate(raw, b4, evidence)
    bear = result["variance_attribution"]["scenarios"]["bear"]
    assert bear["b4_minus_normalized_net_profit_cny"] == "5"
    assert bear["attributed_total_cny"] == "5"
    assert bear["unattributed_residual_cny"] == "0"
    assert bear["status"] == "RECONCILED_DIAGNOSTIC_ONLY"
    assert result["variance_attribution"]["valuation_input_eligible"] is False


def test_unexplained_variance_residual_blocks_chain_pass():
    raw, b4, evidence = _valid_case()
    bear_attribution = next(row for row in raw["variance_attribution"] if row["scenario"] == "bear")
    bear_attribution["amount_cny"]["value"] = "10"
    result = _evaluate(raw, b4, evidence)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["variance_attribution"]["scenarios"]["bear"]["unattributed_residual_cny"] == "-10"
    assert "VARIANCE_ATTRIBUTION_DOES_NOT_RECONCILE_TO_B4_MINUS_NORMALIZED" in result["variance_attribution"]["scenarios"]["bear"]["issues"]


def test_variance_attribution_must_link_to_matching_review_trigger():
    raw, b4, evidence = _valid_case()
    raw["variance_attribution"][0]["review_trigger_id"] = "missing_trigger"
    result = _evaluate(raw, b4, evidence)
    assert result["status"] == "REVIEW_REQUIRED"
    assert any("ATTRIBUTION_REVIEW_TRIGGER_UNRESOLVED" in issue for issue in result["variance_attribution"]["issues"])


def test_missing_variance_attribution_does_not_claim_explanation():
    raw, b4, evidence = _valid_case()
    raw["variance_attribution"] = []
    result = _evaluate(raw, b4, evidence)
    assert result["variance_attribution"]["status"] == "REVIEW_REQUIRED"
    assert "VARIANCE_ATTRIBUTIONS_REQUIRED_FOR_COMPARABLE_SCENARIO" in result["variance_attribution"]["issues"]
    assert result["status"] == "REVIEW_REQUIRED"


def _eps_transmission_inputs() -> tuple[dict, dict]:
    bridge = {
        "status": "CALCULATED",
        "primary_eps_price_calculation_eligible": True,
        "forecast_period": "FY2027",
        "valuation_terminal_date": "2027-12-31",
        "currency": "CNY",
        "scenarios": {
            "bear": {"status": "CALCULATED", "eps_match": True, "diluted_shares": {"value": "10", "unit": "shares"}},
            "base": {"status": "CALCULATED", "eps_match": True, "diluted_shares": {"value": "10", "unit": "shares"}},
            "bull": {"status": "CALCULATED", "eps_match": True, "diluted_shares": {"value": "10", "unit": "shares"}},
        },
    }
    adapter = {
        "status": "CALCULATED",
        "selected_for_primary_model": True,
        "forecast_period": "FY2027",
        "valuation_terminal_date": "2027-12-31",
        "currency": "CNY",
        "scenarios": {
            "bear": {"pe_multiple_x": {"value": "10", "unit": "x"}, "terminal_value_per_share": "8"},
            "base": {"pe_multiple_x": {"value": "10", "unit": "x"}, "terminal_value_per_share": "10"},
            "bull": {"pe_multiple_x": {"value": "10", "unit": "x"}, "terminal_value_per_share": "12"},
        },
    }
    return bridge, adapter


def test_variance_transmission_calculates_only_conditional_eps_and_constant_pe_sensitivity() -> None:
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["bear"]["net_profit_cny"] = "85"
    b4["scenarios"]["base"]["net_profit_cny"] = "95"
    b4["scenarios"]["bull"]["net_profit_cny"] = "130"
    amounts = {"bear": "5", "base": "-5", "bull": "10"}
    for item in raw["variance_attribution"]:
        item["amount_cny"] = _measure(amounts[item["scenario"]])
    bridge, adapter = _eps_transmission_inputs()

    result = _evaluate(raw, b4, evidence, eps_earnings_bridge=bridge, eps_multiple_valuation=adapter)
    transmission = result["variance_transmission"]

    assert transmission["status"] == "ALL_SCENARIOS_CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY"
    assert transmission["valuation_input_eligible"] is False
    assert transmission["scenarios"]["bear"]["implied_eps_sensitivity_per_share"] == "0.5"
    assert transmission["scenarios"]["bear"]["constant_pe_value_sensitivity_per_share"] == "5.0"
    assert transmission["scenarios"]["base"]["implied_eps_sensitivity_per_share"] == "-0.5"
    assert transmission["scenarios"]["base"]["constant_pe_value_sensitivity_per_share"] == "-5.0"
    assert transmission["scenarios"]["bull"]["implied_eps_sensitivity_per_share"] == "1"
    assert transmission["scenarios"]["bull"]["constant_pe_value_sensitivity_per_share"] == "10"
    assert transmission["scenarios"]["bear"]["items"][0]["review_trigger_id"] == "orders_review"


def test_variance_transmission_fails_closed_on_cny_hkd_mismatch() -> None:
    raw, b4, evidence = _valid_case()
    bridge, adapter = _eps_transmission_inputs()
    bridge["currency"] = "HKD"

    result = _evaluate(raw, b4, evidence, eps_earnings_bridge=bridge, eps_multiple_valuation=adapter)
    transmission = result["variance_transmission"]

    assert transmission["status"] == "REVIEW_REQUIRED"
    assert transmission["scenarios"]["base"]["status"] == "NOT_IDENTIFIABLE"
    assert transmission["scenarios"]["base"]["implied_eps_sensitivity_per_share"] is None
    assert transmission["scenarios"]["base"]["constant_pe_value_sensitivity_per_share"] is None
    assert "EPS_BRIDGE_CURRENCY_MUST_BE_CNY_FOR_CNY_NET_PROFIT_DELTA" in transmission["issues"]


def test_variance_transmission_blocked_when_upstream_attribution_is_unreconciled() -> None:
    raw, b4, evidence = _valid_case()
    raw["variance_attribution"] = [row for row in raw["variance_attribution"] if row["scenario"] != "base"]
    bridge, adapter = _eps_transmission_inputs()

    result = _evaluate(raw, b4, evidence, eps_earnings_bridge=bridge, eps_multiple_valuation=adapter)
    transmission = result["variance_transmission"]

    assert transmission["status"] == "BLOCKED_UPSTREAM_VARIANCE_ATTRIBUTION_NOT_RECONCILED"
    assert transmission["scenarios"]["base"]["implied_eps_sensitivity_per_share"] is None
    assert transmission["scenarios"]["base"]["items"] == []
    assert "UPSTREAM_VARIANCE_ATTRIBUTION_NOT_RECONCILED" in transmission["issues"]


def test_variance_transmission_requires_selected_eps_multiple_adapter() -> None:
    raw, b4, evidence = _valid_case()
    bridge, adapter = _eps_transmission_inputs()
    adapter["selected_for_primary_model"] = False

    result = _evaluate(raw, b4, evidence, eps_earnings_bridge=bridge, eps_multiple_valuation=adapter)
    transmission = result["variance_transmission"]

    assert transmission["status"] == "REVIEW_REQUIRED"
    assert transmission["scenarios"]["bull"]["constant_pe_value_sensitivity_per_share"] is None
    assert "PRIMARY_EPS_MULTIPLE_ADAPTER_NOT_CALCULATED_AND_SELECTED" in transmission["issues"]


def test_variance_transmission_is_not_applicable_to_sotp() -> None:
    raw, b4, evidence = _valid_case()
    bridge, adapter = _eps_transmission_inputs()
    result = evaluate_cycle_earnings_monitor(
        raw,
        operating_driver_forecast=b4,
        forecast_valuation={
            "model_family": "SOTP",
            "model": "SOTP",
            "entry_value_reference_per_share": "10",
            "scenarios": {
                "bear": {"terminal_value_per_share": "8"},
                "base": {"terminal_value_per_share": "10"},
                "bull": {"terminal_value_per_share": "12"},
            },
        },
        valuation_model_consistency={"primary_model_price_calculation_eligible": True},
        valuation_timing={"status": "PASS"},
        evidence_register=evidence,
        eps_earnings_bridge=bridge,
        eps_multiple_valuation=adapter,
    )
    transmission = result["variance_transmission"]

    assert transmission["status"] == "REVIEW_REQUIRED"
    assert transmission["scenarios"]["base"]["constant_pe_value_sensitivity_per_share"] is None
    assert "CURRENT_PRIMARY_MODEL_IS_NOT_EPS_MULTIPLE" in transmission["issues"]


def test_cash_flow_path_is_separate_from_profit_variance_and_not_fcf_reconciled() -> None:
    raw, b4, evidence = _valid_case()
    result = _evaluate(raw, b4, evidence)
    cash_path = result["cash_flow_path"]

    assert cash_path["status"] == "CASH_FLOW_PATH_LINKS_COMPLETE_DIAGNOSTIC_ONLY"
    assert cash_path["normalized_fcf_comparison_available"] is False
    assert cash_path["fcf_variance_reconciled"] is False
    assert cash_path["cash_flow_amounts_aggregated"] is False
    assert len(cash_path["scenarios"]["bear"]) == 1
    assert cash_path["scenarios"]["bear"][0]["attribution_id"] == "bear_cycle_delta"
    assert result["status"] == "CHAIN_IDENTIFIABLE_NON_ADMITTED"


def test_cash_flow_path_rejects_trigger_or_driver_drift_from_profit_attribution() -> None:
    raw, b4, evidence = _valid_case()
    raw["cash_flow_assessments"][1]["review_trigger_id"] = "orders_reverse"
    result = _evaluate(raw, b4, evidence)

    assert result["cash_flow_path"]["status"] == "REVIEW_REQUIRED"
    assert "CASH_FLOW_TRIGGER_DOES_NOT_MATCH_PROFIT_ATTRIBUTION" in result["cash_flow_path"]["issues"][0] or any(
        "CASH_FLOW_TRIGGER_DOES_NOT_MATCH_PROFIT_ATTRIBUTION" in issue
        for issue in result["cash_flow_path"]["issues"]
    )
    assert result["status"] == "REVIEW_REQUIRED"


def test_quantified_working_capital_effect_requires_usable_b4_cash_context() -> None:
    raw, b4, evidence = _valid_case()
    assessment = raw["cash_flow_assessments"][1]
    b4["scenarios"]["base"]["financial_outputs_decision_usable"] = False
    assessment.update({
        "channel": "WORKING_CAPITAL",
        "direction": "IMPROVES_FCF",
        "quantification_status": "QUANTIFIED",
        "cash_flow_effect_cny": _measure("5"),
    })
    result = _evaluate(raw, b4, evidence)
    cash_item = result["cash_flow_path"]["scenarios"]["base"][0]

    assert cash_item["status"] == "REVIEW_REQUIRED"
    assert cash_item["cash_flow_effect_cny"] is None
    assert "B4_CASH_CONTEXT_NOT_DECISION_USABLE" in cash_item["issues"]


def test_cash_flow_path_rejects_missing_or_after_cutoff_evidence() -> None:
    raw, b4, evidence = _valid_case()
    raw["cash_flow_assessments"][0]["evidence_refs"] = ["MISSING_SOURCE"]
    result = _evaluate(raw, b4, evidence)

    assert result["cash_flow_path"]["status"] == "REVIEW_REQUIRED"
    assert any("EVIDENCE_REFERENCE_UNRESOLVED:MISSING_SOURCE" in issue for issue in result["cash_flow_path"]["issues"])
    assert result["valuation_input_eligible"] is False


def test_cash_flow_path_quantified_effect_requires_explicit_fcf_direction_sign() -> None:
    raw, b4, evidence = _valid_case()
    assessment = raw["cash_flow_assessments"][2]
    assessment.update({
        "channel": "CAPEX",
        "direction": "IMPROVES_FCF",
        "quantification_status": "QUANTIFIED",
        "cash_flow_effect_cny": _measure("-7"),
    })
    result = _evaluate(raw, b4, evidence)
    cash_item = result["cash_flow_path"]["scenarios"]["bull"][0]

    assert cash_item["status"] == "REVIEW_REQUIRED"
    assert cash_item["cash_flow_effect_cny"] is None
    assert "NEGATIVE_FCF_EFFECT_DIRECTION_MISMATCH" in cash_item["issues"]


def test_cash_flow_evidence_must_overlap_linked_review_trigger_evidence() -> None:
    raw, b4, evidence = _valid_case()
    raw["cash_flow_assessments"][0]["evidence_refs"] = ["E_ACTUAL"]
    result = _evaluate(raw, b4, evidence)

    assert result["cash_flow_path"]["status"] == "REVIEW_REQUIRED"
    assert any(
        "CASH_FLOW_EVIDENCE_NOT_SHARED_WITH_REVIEW_TRIGGER" in issue
        for issue in result["cash_flow_path"]["issues"]
    )
    assert result["status"] == "REVIEW_REQUIRED"


def test_quantified_cash_flow_assessment_preserves_typed_basis_and_evidence() -> None:
    raw, b4, evidence = _valid_case()
    raw["review_triggers"][0]["evidence_refs"] = ["E_ACTUAL", "E_COUNTER"]
    for row in b4["scenarios"].values():
        row.update({
            "financial_outputs_decision_usable": True,
            "cash_capex_cny": "20",
            "change_working_capital_cny": "12",
            "effective_change_working_capital_cny": "12",
            "inventory_cash_impact_proxy_cny": "2",
            "inventory_working_capital_treatment": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
            "inventory_reconciliation_status": "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
            "depreciation_amortization_cny": "3",
            "finance_cost_cny": "1",
            "unlevered_fcf_proxy_cny": "40",
        })
    assessment = raw["cash_flow_assessments"][1]
    amount = _measure("5", basis="相对正常化营运资金假设，库存周转改善释放现金")
    amount["evidence_refs"] = ["E_ACTUAL"]
    assessment.update({
        "channel": "WORKING_CAPITAL",
        "direction": "IMPROVES_FCF",
        "quantification_status": "QUANTIFIED",
        "cash_flow_effect_cny": amount,
        "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
    })
    result = _evaluate(raw, b4, evidence)
    item = result["cash_flow_path"]["scenarios"]["base"][0]

    assert result["cash_flow_path"]["status"] == "CASH_FLOW_PATH_LINKS_COMPLETE_DIAGNOSTIC_ONLY"
    assert item["status"] == "CLASSIFIED_DIAGNOSTIC_ONLY"
    assert item["cash_flow_effect_cny"] == "5"
    assert item["cash_flow_effect_basis"] == "相对正常化营运资金假设，库存周转改善释放现金"
    assert item["cash_flow_effect_data_class"] == "ANALYST_ASSUMPTION"
    assert item["cash_flow_effect_evidence_refs"] == ["E_ACTUAL"]
    assert result["cash_flow_path"]["cash_flow_amounts_aggregated"] is False
    assert result["cash_flow_path"]["fcf_variance_reconciled"] is False


def test_normalized_fcf_bridge_reconciles_reference_adjustments_and_required_components() -> None:
    raw, b4, evidence = _valid_case()
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["status"] == "FCF_VARIANCE_RECONCILED_DIAGNOSTIC_ONLY"
    assert fcf["normalized_fcf"]["status"] == "NORMALIZED_FCF_BRIDGE_RECONCILED_DIAGNOSTIC_ONLY"
    assert fcf["b4_comparison"]["status"] == "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT"
    assert fcf["variance_attribution"]["status"] == "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY"
    assert fcf["normalized_fcf_comparison_available"] is True
    assert fcf["fcf_variance_reconciled"] is True
    assert fcf["valuation_input_eligible"] is False
    assert set(row["category"] for row in fcf["normalized_fcf"]["scenarios"]["base"]["adjustments"]) == {
        "CAPEX", "WORKING_CAPITAL", "INVENTORY_MOVEMENT"
    }


def test_normalized_fcf_reference_plus_adjustments_must_reconcile_within_cny_one() -> None:
    raw, b4, evidence = _valid_case()
    raw["normalized_fcf"]["scenarios"]["base"]["point_fcf_cny"] = "55"
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["status"] == "REVIEW_REQUIRED"
    assert fcf["normalized_fcf"]["scenarios"]["base"]["status"] == "REVIEW_REQUIRED"
    assert any(
        "NORMALIZED_FCF_REFERENCE_PLUS_ADJUSTMENTS_DO_NOT_RECONCILE_WITHIN_CNY_1" in issue
        for issue in fcf["normalized_fcf"]["scenarios"]["base"]["issues"]
    )
    assert fcf["valuation_input_eligible"] is False


def test_component_mismatches_block_even_when_fcf_total_residual_is_zero() -> None:
    raw, b4, evidence = _valid_case()
    deliberately_misclassified = {
        "OPERATING_CASH_CONVERSION": "10",
        "NON_CASH_EARNINGS": "-10",
        "CAPEX": "5",
        "WORKING_CAPITAL": "-5",
        "INVENTORY_MOVEMENT": "0",
    }
    for item in raw["fcf_variance_attribution"]:
        if item["scenario"] == "base":
            item["amount_cny"] = {
                "value": deliberately_misclassified[item["category"]],
                "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                "basis": "测试用错误分类；总和为零但各组件与实测值不符",
                "evidence_refs": ["E_COUNTER"],
            }
    result = _evaluate(raw, b4, evidence)
    row = result["normalized_fcf_bridge"]["variance_attribution"]["scenarios"]["base"]

    assert row["b4_minus_normalized_fcf_cny"] == "0"
    assert row["attributed_total_cny"] == "0"
    assert row["unattributed_residual_cny"] == "0"
    assert row["status"] == "REVIEW_REQUIRED"
    assert any("FCF_VARIANCE_CATEGORY_CONTRIBUTION_MISMATCH" in issue for issue in row["issues"])
    assert result["normalized_fcf_bridge"]["fcf_variance_reconciled"] is False


def test_fcf_variance_can_reconcile_signed_component_deltas_with_excluded_inventory() -> None:
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["base"].update({
        "unlevered_fcf_proxy_cny": "45",
        "cash_capex_cny": "27",
        "change_working_capital_cny": "10",
        "effective_change_working_capital_cny": "13",
        "inventory_cash_impact_proxy_cny": "3",
        "inventory_working_capital_treatment": "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
        "inventory_reconciliation_status": "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL",
    })
    normalized_components = raw["normalized_fcf"]["scenarios"]["base"]["cash_components"]
    normalized_components["inventory_working_capital_treatment"] = "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL"
    normalized_components["inventory_reconciliation_status"] = "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL"
    normalized_components["inventory_cash_impact_proxy_cny"]["value"] = "0"
    signed = {
        "OPERATING_CASH_CONVERSION": "33",
        "NON_CASH_EARNINGS": "-8",
        "CAPEX": "-22",
        "WORKING_CAPITAL": "-5",
        "INVENTORY_MOVEMENT": "-3",
    }
    for item in raw["fcf_variance_attribution"]:
        if item["scenario"] == "base":
            item["amount_cny"] = {
                "value": signed[item["category"]], "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                "basis": f"测试用 {item['category']} 实测组件差额",
                "evidence_refs": ["E_COUNTER"],
            }
    result = _evaluate(raw, b4, evidence)
    row = result["normalized_fcf_bridge"]["variance_attribution"]["scenarios"]["base"]
    component_row = result["normalized_fcf_bridge"]["component_variance_bridge"]["scenarios"]["base"]

    assert row["b4_minus_normalized_fcf_cny"] == "-5"
    assert row["attributed_total_cny"] == "-5"
    assert row["unattributed_residual_cny"] == "0"
    assert row["status"] == "RECONCILED_DIAGNOSTIC_ONLY"
    assert component_row["contributions_cny"]["WORKING_CAPITAL"] == "-5"
    assert component_row["contributions_cny"]["INVENTORY_MOVEMENT"] == "-3"
    assert result["normalized_fcf_bridge"]["fcf_variance_reconciled"] is True


def test_b4_fcf_proxy_must_reconcile_to_its_cash_components() -> None:
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["base"]["unlevered_fcf_proxy_cny"] = "51"
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["b4_comparison"]["status"] == "NOT_COMPARABLE"
    assert "BASE:B4_FCF_CASH_COMPONENT_FORMULA_MISMATCH_WITHIN_CNY_1" in fcf["b4_comparison"]["issues"]
    assert fcf["fcf_variance_reconciled"] is False


def test_each_attribution_category_must_match_measured_component_contribution() -> None:
    raw, b4, evidence = _valid_case()
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]
    row = fcf["variance_attribution"]["scenarios"]["base"]

    assert row["status"] == "RECONCILED_DIAGNOSTIC_ONLY"
    assert row["component_attribution_reconciliation"]["OPERATING_CASH_CONVERSION"]["status"] == "RECONCILED"
    assert row["component_attribution_reconciliation"]["NON_CASH_EARNINGS"]["status"] == "RECONCILED"
    assert row["component_attribution_reconciliation"]["CAPEX"]["status"] == "RECONCILED"
    assert row["component_attribution_reconciliation"]["WORKING_CAPITAL"]["status"] == "RECONCILED"
    assert row["component_attribution_reconciliation"]["INVENTORY_MOVEMENT"]["attributed_category_total_cny"] == "0"


def test_included_inventory_is_not_counted_again_outside_effective_working_capital() -> None:
    raw, b4, evidence = _valid_case()
    result = _evaluate(raw, b4, evidence)
    bridge = result["normalized_fcf_bridge"]["component_variance_bridge"]["scenarios"]["base"]

    assert bridge["status"] == "COMPONENTS_RECONCILED_DIAGNOSTIC_ONLY"
    assert bridge["contributions_cny"]["WORKING_CAPITAL"] == "-8"
    assert bridge["contributions_cny"]["INVENTORY_MOVEMENT"] == "0"
    assert "避免重复计算" in bridge["inventory_component_basis"]


def test_mixed_inventory_treatments_block_componentwise_fcf_reconciliation() -> None:
    raw, b4, evidence = _valid_case()
    normalized_components = raw["normalized_fcf"]["scenarios"]["base"]["cash_components"]
    normalized_components["inventory_working_capital_treatment"] = "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL"
    normalized_components["inventory_reconciliation_status"] = "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL"
    normalized_components["inventory_cash_impact_proxy_cny"]["value"] = "0"
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]
    bridge = fcf["component_variance_bridge"]["scenarios"]["base"]

    assert bridge["status"] == "REVIEW_REQUIRED"
    assert "B4_NORMALIZED_INVENTORY_TREATMENT_MISMATCH" in bridge["issues"]
    assert fcf["fcf_variance_reconciled"] is False


def test_missing_measured_component_category_blocks_fcf_variance_reconciliation() -> None:
    raw, b4, evidence = _valid_case()
    raw["fcf_variance_attribution"] = [
        item for item in raw["fcf_variance_attribution"]
        if not (item["scenario"] == "base" and item["category"] == "NON_CASH_EARNINGS")
    ]
    result = _evaluate(raw, b4, evidence)
    row = result["normalized_fcf_bridge"]["variance_attribution"]["scenarios"]["base"]

    assert row["status"] == "REVIEW_REQUIRED"
    assert "FCF_VARIANCE_COMPONENT_COVERAGE_MISSING:NON_CASH_EARNINGS" in row["issues"]
    assert "FCF_ATTRIBUTED_COMPONENT_TOTAL_MISSING:NON_CASH_EARNINGS" in row["issues"]
    assert result["normalized_fcf_bridge"]["fcf_variance_reconciled"] is False


def test_b4_excluded_inventory_raw_working_capital_plus_proxy_must_match_effective_total() -> None:
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["base"].update({
        "change_working_capital_cny": "10",
        "effective_change_working_capital_cny": "13",
        "inventory_cash_impact_proxy_cny": "2",
        "inventory_working_capital_treatment": "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
        "inventory_reconciliation_status": "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL",
    })
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["b4_comparison"]["status"] == "NOT_COMPARABLE"
    assert "BASE:B4_NONINVENTORY_WC_PLUS_INVENTORY_PROXY_MISMATCH" in fcf["b4_comparison"]["issues"]
    assert fcf["fcf_variance_reconciled"] is False


def test_normalized_fcf_period_mismatch_blocks_b4_comparison() -> None:
    raw, b4, evidence = _valid_case()
    raw["normalized_fcf"]["period"] = "FY2028"
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["b4_comparison"]["status"] == "NOT_COMPARABLE"
    assert "NORMALIZED_FCF_PERIOD_MISMATCH_B4" in fcf["b4_comparison"]["issues"]
    assert fcf["normalized_fcf_comparison_available"] is False
    assert fcf["fcf_variance_reconciled"] is False


def test_normalized_fcf_requires_explicit_capex_working_capital_and_inventory_coverage() -> None:
    raw, b4, evidence = _valid_case()
    raw["normalized_fcf"]["scenarios"]["bull"]["adjustments"] = [
        row for row in raw["normalized_fcf"]["scenarios"]["bull"]["adjustments"]
        if row["category"] != "INVENTORY_MOVEMENT"
    ]
    result = _evaluate(raw, b4, evidence)
    issues = result["normalized_fcf_bridge"]["normalized_fcf"]["scenarios"]["bull"]["issues"]

    assert result["normalized_fcf_bridge"]["normalized_fcf"]["status"] == "REVIEW_REQUIRED"
    assert "NORMALIZED_FCF_COMPONENT_COVERAGE_MISSING:INVENTORY_MOVEMENT" in issues


def test_fcf_variance_amount_evidence_must_overlap_review_trigger_evidence() -> None:
    raw, b4, evidence = _valid_case()
    raw["fcf_variance_attribution"][0]["amount_cny"]["evidence_refs"] = ["E_ACTUAL"]
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["variance_attribution"]["status"] == "REVIEW_REQUIRED"
    assert any(
        "FCF_ATTRIBUTION_EVIDENCE_NOT_SHARED_WITH_TRIGGER" in issue
        for issue in fcf["variance_attribution"]["issues"]
    )
    assert fcf["fcf_variance_reconciled"] is False


def test_normalized_fcf_method_must_match_pinned_b4_proxy_formula() -> None:
    raw, b4, evidence = _valid_case()
    raw["normalized_fcf"]["method"] = "UNLEVERED_FCF_FROM_NET_PROFIT"
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["normalized_fcf"]["status"] == "REVIEW_REQUIRED"
    assert "NORMALIZED_FCF_METHOD_MISMATCH_B4_PROXY_FORMULA" in fcf["normalized_fcf"]["issues"]
    assert fcf["normalized_fcf_comparison_available"] is False
    assert fcf["valuation_input_eligible"] is False


def test_b4_fcf_comparison_requires_cash_capex_and_effective_working_capital_components() -> None:
    raw, b4, evidence = _valid_case()
    b4["scenarios"]["base"]["effective_change_working_capital_cny"] = None
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["b4_comparison"]["status"] == "NOT_COMPARABLE"
    assert "BASE:B4_FCF_COMPONENT_NOT_IDENTIFIABLE:effective_change_working_capital_cny" in fcf["b4_comparison"]["issues"]
    assert fcf["fcf_variance_reconciled"] is False


def test_normalized_fcf_component_formula_must_reconcile_to_reported_point() -> None:
    raw, b4, evidence = _valid_case()
    raw["normalized_fcf"]["scenarios"]["base"]["cash_components"]["cash_capex_cny"]["value"] = "15"
    result = _evaluate(raw, b4, evidence)
    scenario = result["normalized_fcf_bridge"]["normalized_fcf"]["scenarios"]["base"]

    assert scenario["status"] == "REVIEW_REQUIRED"
    assert scenario["cash_components"]["calculated_fcf_point_cny"] == "40.0"
    assert any(
        "CASH_COMPONENT:NORMALIZED_FCF_CASH_COMPONENT_FORMULA_MISMATCH_WITHIN_CNY_1" in issue
        for issue in scenario["issues"]
    )
    assert result["normalized_fcf_bridge"]["fcf_variance_reconciled"] is False


def test_inventory_excluded_from_working_capital_requires_addback_reconciliation() -> None:
    raw, b4, evidence = _valid_case()
    components = raw["normalized_fcf"]["scenarios"]["base"]["cash_components"]
    components["inventory_working_capital_treatment"] = "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL"
    components["inventory_reconciliation_status"] = "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL"
    components["inventory_cash_impact_proxy_cny"]["value"] = "3"
    components["effective_change_working_capital_cny"]["value"] = "6"
    result = _evaluate(raw, b4, evidence)
    scenario = result["normalized_fcf_bridge"]["normalized_fcf"]["scenarios"]["base"]

    assert scenario["status"] == "REVIEW_REQUIRED"
    assert any(
        "CASH_COMPONENT:NORMALIZED_FCF_NONINVENTORY_WC_PLUS_INVENTORY_PROXY_MISMATCH" in issue
        for issue in scenario["issues"]
    )
    assert result["normalized_fcf_bridge"]["valuation_input_eligible"] is False


def test_zero_inventory_movement_status_is_valid_without_double_counting() -> None:
    raw, b4, evidence = _valid_case()
    components = raw["normalized_fcf"]["scenarios"]["base"]["cash_components"]
    components["inventory_working_capital_treatment"] = "NOT_APPLICABLE"
    components["inventory_reconciliation_status"] = "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED"
    b4["scenarios"]["base"]["inventory_working_capital_treatment"] = "NOT_APPLICABLE"
    b4["scenarios"]["base"]["inventory_reconciliation_status"] = "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED"
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]

    assert fcf["status"] == "FCF_VARIANCE_RECONCILED_DIAGNOSTIC_ONLY"
    assert fcf["b4_comparison"]["status"] == "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT"
    assert fcf["fcf_variance_reconciled"] is True


def test_normalized_unlevered_fcf_rejects_financing_flow_as_an_adjustment_category() -> None:
    raw, b4, evidence = _valid_case()
    raw["normalized_fcf"]["scenarios"]["base"]["adjustments"][0]["category"] = "FINANCING_CASH_FLOW"
    result = _evaluate(raw, b4, evidence)
    row = result["normalized_fcf_bridge"]["normalized_fcf"]["scenarios"]["base"]

    assert row["status"] == "REVIEW_REQUIRED"
    assert any(
        "NORMALIZED_FCF_ADJUSTMENT_CATEGORY_UNSUPPORTED" in issue
        for issue in row["issues"]
    )
    assert result["normalized_fcf_bridge"]["valuation_input_eligible"] is False



def _driver_component_measure(
    *,
    measure_id: str,
    driver_id: str,
    category: str,
    component_basis: str,
    b4_value: str,
    normalized_value: str,
) -> dict:
    return {
        "measure_id": measure_id,
        "category": category,
        "driver_id": driver_id,
        "component_basis": component_basis,
        "basis": "用项目明细分别核对 B4 与正常化组件贡献，不从类别总差额倒推分项",
        "b4_value_cny": {
            "value": b4_value, "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
            "basis": "B4 驱动级组件测量；由独立项目明细形成",
            "evidence_refs": ["E_ACTUAL"],
        },
        "normalized_value_cny": {
            "value": normalized_value, "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
            "basis": "正常化驱动级组件测量；由独立项目明细形成",
            "evidence_refs": ["E_COUNTER"],
        },
    }


def _split_base_capex_into_two_drivers(raw: dict) -> tuple[dict, dict]:
    raw["industry_cycle"]["leading_indicators"].append({
        "indicator_id": "capex_upgrade",
        "name": "扩产项目资本开支",
        "direction": "MIXED",
        "observation": "项目建设和投产节奏仍需逐项核对",
        "threshold_or_reversal": "项目预算或投产日程显著偏离",
        "review_by": "FY2027Q1",
        "evidence_refs": ["E_ACTUAL"],
        "counter_evidence_refs": ["E_COUNTER"],
    })
    raw["review_triggers"].append({
        "trigger_id": "capex_upgrade_review",
        "driver_id": "capex_upgrade",
        "condition": "扩产项目预算或投产日程显著偏离",
        "threshold": "项目预算偏差超过既定容差",
        "review_by": "FY2027Q1",
        "expected_operating_impact": "重估投产节奏和维护/扩产资本开支",
        "valuation_path": "重估 FCF 与每股价值",
        "review_action": "REBUILD_VALUATION",
        "causal_path": [
            "INDUSTRY_CYCLE", "NORMALIZED_EARNINGS", "EPS_OR_FCF",
            "PER_SHARE_VALUE", "POSITION_REVIEW",
        ],
        "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
    })
    original = next(
        row for row in raw["fcf_variance_attribution"]
        if row["scenario"] == "base" and row["category"] == "CAPEX"
    )
    original.update({
        "fcf_attribution_id": "base_capex_maintenance",
        "driver_id": "demand_growth",
        "review_trigger_id": "orders_review",
        "amount_cny": {
            "value": "-9", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
            "basis": "B4 维护性资本开支 12、正常化维护性资本开支 3",
            "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
        },
        "driver_component_measure": _driver_component_measure(
            measure_id="base_capex_maintenance_measure",
            driver_id="demand_growth",
            category="CAPEX",
            component_basis="CASH_CAPEX",
            b4_value="12",
            normalized_value="3",
        ),
    })
    second = {
        "scenario": "base",
        "fcf_attribution_id": "base_capex_expansion",
        "driver_id": "capex_upgrade",
        "review_trigger_id": "capex_upgrade_review",
        "category": "CAPEX",
        "rationale": "独立项目明细显示扩产资本开支差额",
        "amount_cny": {
            "value": "-8", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
            "basis": "B4 扩产资本开支 10、正常化扩产资本开支 2",
            "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
        },
        "driver_component_measure": _driver_component_measure(
            measure_id="base_capex_expansion_measure",
            driver_id="capex_upgrade",
            category="CAPEX",
            component_basis="CASH_CAPEX",
            b4_value="10",
            normalized_value="2",
        ),
    }
    raw["fcf_variance_attribution"].append(second)
    return raw, second


def test_b50_independent_driver_level_component_decomposition_reconciles_both_sides() -> None:
    raw, b4, evidence = _valid_case()
    raw, second = _split_base_capex_into_two_drivers(raw)
    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]
    base = fcf["variance_attribution"]["scenarios"]["base"]

    assert fcf["status"] == "FCF_VARIANCE_RECONCILED_DIAGNOSTIC_ONLY"
    assert base["status"] == "RECONCILED_DIAGNOSTIC_ONLY"
    capex = base["component_attribution_reconciliation"]["CAPEX"]
    assert capex["measured_component_contribution_cny"] == "-17"
    assert capex["attributed_category_total_cny"] == "-17"
    assert capex["residual_cny"] == "0"
    driver_rows = [row for row in base["items"] if row["category"] == "CAPEX"]
    assert {row["driver_id"] for row in driver_rows} == {"demand_growth", "capex_upgrade"}
    assert {row["amount_cny"] for row in driver_rows} == {"-9", "-8"}
    assert all(row["driver_component_measure"]["status"] == "COMPONENT_MEASURE_IDENTIFIABLE" for row in driver_rows)
    assert fcf["valuation_input_eligible"] is False


def test_b50_driver_decomposition_must_reconcile_b4_and_normalized_side_totals_separately() -> None:
    raw, b4, evidence = _valid_case()
    raw, second = _split_base_capex_into_two_drivers(raw)
    # Preserve the net difference (-17), but make both gross side sums wrong:
    # B4 = 23 instead of 22 and normalized = 6 instead of 5.
    first = next(
        row for row in raw["fcf_variance_attribution"]
        if row["scenario"] == "base" and row["fcf_attribution_id"] == "base_capex_maintenance"
    )
    first["driver_component_measure"]["b4_value_cny"]["value"] = "13"
    first["driver_component_measure"]["normalized_value_cny"]["value"] = "3"
    first["amount_cny"]["value"] = "-10"
    second["driver_component_measure"]["b4_value_cny"]["value"] = "10"
    second["driver_component_measure"]["normalized_value_cny"]["value"] = "3"
    second["amount_cny"]["value"] = "-7"

    result = _evaluate(raw, b4, evidence)
    fcf = result["normalized_fcf_bridge"]
    base = fcf["variance_attribution"]["scenarios"]["base"]

    assert base["b4_minus_normalized_fcf_cny"] == "0"
    assert base["status"] == "REVIEW_REQUIRED"
    assert "FCF_DRIVER_COMPONENT_B4_SIDE_DOES_NOT_RECONCILE:CAPEX" in base["issues"]
    assert "FCF_DRIVER_COMPONENT_NORMALIZED_SIDE_DOES_NOT_RECONCILE:CAPEX" in base["issues"]
    assert fcf["fcf_variance_reconciled"] is False


def test_b50_driver_component_claimed_contribution_must_match_computed_difference() -> None:
    raw, b4, evidence = _valid_case()
    raw, second = _split_base_capex_into_two_drivers(raw)
    second["amount_cny"]["value"] = "-5"
    result = _evaluate(raw, b4, evidence)
    base = result["normalized_fcf_bridge"]["variance_attribution"]["scenarios"]["base"]

    assert base["status"] == "REVIEW_REQUIRED"
    assert any(
        "FCF_DRIVER_COMPONENT_DECLARED_AMOUNT_MISMATCH_WITHIN_CNY_1" in issue
        for issue in base["issues"]
    )
    assert result["normalized_fcf_bridge"]["fcf_variance_reconciled"] is False


def test_b50_multiple_component_rows_without_independent_measurements_remain_blocked() -> None:
    raw, b4, evidence = _valid_case()
    original = next(
        row for row in raw["fcf_variance_attribution"]
        if row["scenario"] == "base" and row["category"] == "CAPEX"
    )
    duplicate = dict(original)
    duplicate["fcf_attribution_id"] = "base_capex_duplicate_unmeasured"
    duplicate["amount_cny"] = {
        "value": "-8", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
        "basis": "未附独立驱动级组件测量",
        "evidence_refs": ["E_ACTUAL", "E_COUNTER"],
    }
    raw["fcf_variance_attribution"].append(duplicate)
    result = _evaluate(raw, b4, evidence)
    base = result["normalized_fcf_bridge"]["variance_attribution"]["scenarios"]["base"]

    assert base["status"] == "REVIEW_REQUIRED"
    assert any(
        "FCF_MULTIPLE_ATTRIBUTIONS_FOR_COMPONENT_CATEGORY_NOT_INDEPENDENTLY_MEASURED:CAPEX" in issue
        for issue in base["issues"]
    )
    assert result["normalized_fcf_bridge"]["fcf_variance_reconciled"] is False
