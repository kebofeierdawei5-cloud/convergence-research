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
    }
    b4 = {
        "scope": "COMPANY_WIDE",
        "forecast_period": "FY2027",
        "scenarios": {
            "bear": {"net_profit_cny": "80"},
            "base": {"net_profit_cny": "100"},
            "bull": {"net_profit_cny": "120"},
        },
    }
    evidence = [
        {"source_id": "E_ACTUAL", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"},
        {"source_id": "E_COUNTER", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"},
    ]
    return raw, b4, evidence


def test_complete_cycle_earnings_review_chain_is_diagnostic_only():
    raw, b4, evidence = _valid_case()
    result = evaluate_cycle_earnings_monitor(raw, operating_driver_forecast=b4, assessment={}, evidence_register=evidence)

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
    result = evaluate_cycle_earnings_monitor(raw, operating_driver_forecast=b4, assessment={}, evidence_register=evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert "NORMALIZED_EARNINGS_PERIOD_MISMATCH_B4" in result["normalized_earnings"]["issues"]
    assert result["b4_comparison"]["status"] != "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT"
    assert result["valuation_input_eligible"] is False


def test_missing_counter_evidence_and_reversal_signal_fail_closed():
    raw, b4, evidence = _valid_case()
    raw["industry_cycle"]["counter_evidence_refs"] = []
    raw["industry_cycle"]["reversal_signals"] = []
    result = evaluate_cycle_earnings_monitor(raw, operating_driver_forecast=b4, assessment={}, evidence_register=evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert any("industry_cycle_counter_evidence:EVIDENCE_REFERENCE_REQUIRED" == issue for issue in result["industry_cycle"]["issues"])
    assert "CYCLE_REVERSAL_SIGNALS_REQUIRED" in result["industry_cycle"]["issues"]


def test_reported_base_plus_signed_adjustments_must_reconcile_to_normalized_point():
    raw, b4, evidence = _valid_case()
    raw["normalized_earnings"]["scenarios"]["base"]["adjustments"][0]["amount_cny"]["value"] = "15"
    result = evaluate_cycle_earnings_monitor(raw, operating_driver_forecast=b4, assessment={}, evidence_register=evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert any("NORMALIZED_POINT_DOES_NOT_RECONCILE_TO_REFERENCE_PLUS_ADJUSTMENTS" in issue for issue in result["normalized_earnings"]["issues"])


def test_after_cutoff_evidence_does_not_support_cycle_or_normalized_earnings():
    raw, b4, evidence = _valid_case()
    result = evaluate_cycle_earnings_monitor(
        raw, operating_driver_forecast=b4, assessment={}, evidence_register=evidence,
        after_cutoff_evidence_ids=["E_COUNTER"],
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert any("EVIDENCE_SOURCE_AFTER_CUTOFF:E_COUNTER" in issue for issue in result["industry_cycle"]["issues"])
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
