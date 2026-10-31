from __future__ import annotations

from iios_mvp.sotp_value_credibility_audit_v01 import build_sotp_value_credibility_price_audit


def _fixtures():
    sotp, b63, b64, b66 = {}, {}, {}, {}
    for name in ("bear", "base", "bull"):
        sotp[name] = {"segments": [{
            "segment_id": "SEG_A", "segment_name": "Segment A",
            "earnings_basis": "NORMALIZED_PARENT_ATTRIBUTABLE",
            "attributable_net_profit_cny": {"value": "100", "basis": "FY2027 normalized parent profit", "data_class": "ANALYST_ASSUMPTION", "evidence_refs": ["P1"]},
            "pe_multiple_x": {"value": "10", "basis": "NTM normalized P/E", "data_class": "ANALYST_ASSUMPTION", "evidence_refs": ["M1"]},
        }]}
        b63[name] = {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "earnings_effect_by_segment": [{
                "segment_id": "SEG_A", "normalized_profit_change_cny": "10", "selected_sotp_pe_x": "10",
                "earnings_effect_at_selected_pe_cny": "100", "selected_sotp_segment_value_cny": "1000",
                "b4_forecast_segment_value_at_selected_pe_cny": "1100",
            }],
            "value_pool_waterfall": {
                "step_1_selected_sotp_segment_pool_cny": "1000",
                "step_2_b4_earnings_effect_at_selected_pes_cny": "100",
                "step_3_b4_forecast_pool_at_selected_pes_cny": "1100",
                "step_4_common_pe_scale_effect_to_required_pool_cny": "100",
                "step_5_required_segment_pool_cny": "1200",
            },
            "parent_adjustment_attribution": {
                "capitalized_central_cost_load_on_required_segment_pool_cny": "50",
                "net_cash_debt_offset_to_required_segment_pool_cny": "-10",
                "other_adjustments_offset_to_required_segment_pool_cny": "0",
                "net_parent_adjustment_load_cny": "40",
            },
            "dilution_attribution": {
                "selected_diluted_shares": "10", "required_terminal_value_per_share_cny": "116",
                "required_total_equity_value_cny": "1160", "b4_forecast_total_equity_value_cny": "1060",
                "total_equity_gap_cny": "100", "per_share_gap_cny": "10",
            },
            "multiple_attribution": {
                "common_pe_scale_factor_required": str(1200 / 1100),
                "required_common_pe_by_segment": [{"segment_id": "SEG_A", "required_pe_under_common_scale_x": str(10 * 1200 / 1100)}],
            },
        }
        b64[name] = {
            "status": "ASSESSED_DIAGNOSTIC_ONLY",
            "segments": [{
                "segment_id": "SEG_A", "sotp_selected_attributable_profit_cny": "100", "selected_terminal_pe_x": "10",
                "profit_evidence_assessment": {
                    "grade": "G2_BUSINESS_MECHANISM_AND_EVIDENCE_LINKED",
                    "status": "STRUCTURAL_LINKAGE_PRESENT_NOT_SEMANTICALLY_VERIFIED",
                    "grade_reason": "MECHANISM_CHAIN_INDICATORS_AND_REVERSAL_SIGNALS_PRESENT",
                    "data_class": "ANALYST_ASSUMPTION", "basis": "FY2027 normalized profit", "measure_evidence_refs": ["P1"],
                },
                "multiple_evidence_assessment": {
                    "grade": "G4_MULTIPLE_ASSUMPTION_ONLY", "status": "MULTIPLE_ASSUMPTION",
                    "data_class": "ANALYST_ASSUMPTION", "basis": "NTM normalized P/E", "measure_evidence_refs": ["M1"],
                },
            }],
        }
        b66[name] = {
            "status": "CALIBRATION_AND_RANGE_RECONCILED",
            "segments": [{
                "segment_id": "SEG_A", "normalized_parent_attributable_profit_cny": "100", "selected_terminal_pe_x": "10",
                "explicit_selected_multiple_bridge": {
                    "status": "MULTIPLE_BRIDGE_RECONCILED", "reference_method": "PEER_MEDIAN",
                    "reference_description": "Same-basis peer median", "reference_multiple_x": "8",
                    "explicit_adjustment_sum_x": "2", "calculated_selected_pe_x": "10", "operator_selected_pe_x": "10",
                },
            }],
        }
    return {
        "sotp_valuation": {"status": "CALCULATED", "selected_for_primary_model": True, "scenarios": sotp},
        "valuation_gap_attribution": {"status": "CONDITIONAL_ATTRIBUTION_CALCULATED", "scenarios": b63},
        "evidence_grade_assessment": {"status": "ASSESSED_DIAGNOSTIC_ONLY", "scenarios": b64},
        "multiple_calibration_assessment": {"status": "CALIBRATION_AND_RANGE_RECONCILED", "scenarios": b66},
    }


def _run(data):
    return build_sotp_value_credibility_price_audit(**data)


def test_b67_reconciles_value_sources_and_current_price_hurdle():
    result = _run(_fixtures())
    base = result["scenarios"]["base"]
    assert result["status"] == "VALUE_SOURCE_AUDIT_RECONCILED_DIAGNOSTIC_ONLY"
    assert base["selected_value_bridge"]["selected_segment_pool_recalculated_cny"] == "1000"
    assert base["independent_earnings_bridge"]["b4_earnings_effect_at_unchanged_selected_pes_cny"] == "100"
    assert base["multiple_reference_bridge"]["reference_segment_pool_cny"] == "800"
    assert base["multiple_reference_bridge"]["explicit_multiple_adjustment_value_cny"] == "200"
    assert base["parent_adjustment_bridge"]["net_parent_adjustment_load_cny"] == "40"
    assert base["dilution_bridge"]["required_terminal_value_per_share_cny"] == "116"
    assert base["current_price_required_return"]["required_segment_pool_for_return_hurdle_cny"] == "1200"


def test_b67_keeps_profit_and_multiple_grades_separate_without_score():
    base = _run(_fixtures())["scenarios"]["base"]
    segment = base["segments"][0]
    assert segment["profit_evidence"]["grade"].startswith("G2")
    assert segment["multiple_evidence"]["grade"].startswith("G4")
    assert "credibility_score" not in segment
    assert "combined_grade" not in segment


def test_b67_missing_reference_is_partial_not_zero():
    data = _fixtures()
    for row in data["multiple_calibration_assessment"]["scenarios"].values():
        row["segments"][0]["explicit_selected_multiple_bridge"] = {
            "status": "NO_COMPARABLE_REFERENCE_ASSUMPTION_ONLY",
            "reference_method": "NO_COMPARABLE_REFERENCE",
            "reference_multiple_x": None, "explicit_adjustment_sum_x": None,
        }
    result = _run(data)
    assert result["scenarios"]["base"]["multiple_reference_bridge"]["status"] == "PARTIAL_REFERENCE_COVERAGE"
    assert result["scenarios"]["base"]["multiple_reference_bridge"]["full_sotp_reference_pool"] is None
    assert result["status"] == "PARTIAL"


def test_b67_detects_b63_waterfall_mismatch():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["value_pool_waterfall"]["step_4_common_pe_scale_effect_to_required_pool_cny"] = "101"
    result = _run(data)
    assert result["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"
    assert "B67_SELECTED_EARNINGS_AND_REQUIRED_POOL_WATERFALL_MISMATCH" in result["scenarios"]["base"]["issues"]


def test_b67_detects_parent_adjustment_identity_mismatch():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["parent_adjustment_attribution"]["net_parent_adjustment_load_cny"] = "45"
    assert _run(data)["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"


def test_b67_missing_b64_segment_preserves_unknown_grade():
    data = _fixtures()
    data["evidence_grade_assessment"]["scenarios"]["base"]["segments"] = []
    result = _run(data)
    segment = result["scenarios"]["base"]["segments"][0]
    assert segment["profit_evidence"]["grade"] == "G5_UNKNOWN"
    assert segment["multiple_evidence"]["grade"] == "G5_UNKNOWN"
    assert result["scenarios"]["base"]["status"] == "PARTIAL"


def test_b67_blocks_unreconciled_b63_scenario():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["status"] = "PARTIAL"
    assert _run(data)["scenarios"]["base"]["status"] == "BLOCKED_BY_B63_SCENARIO"


def test_b67_requires_exact_segment_universe():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["earnings_effect_by_segment"][0]["segment_id"] = "SEG_B"
    assert _run(data)["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"


def test_b67_is_not_applicable_when_sotp_is_not_selected():
    data = _fixtures()
    data["sotp_valuation"]["selected_for_primary_model"] = False
    assert _run(data)["status"] == "NOT_APPLICABLE_SOTP_NOT_SELECTED_OR_CALCULATED"


def test_b67_recalculates_each_required_common_pe_from_its_selected_pe_and_scale():
    data = _fixtures()
    data["valuation_gap_attribution"]["scenarios"]["base"]["multiple_attribution"]["required_common_pe_by_segment"][0]["required_pe_under_common_scale_x"] = "99"
    result = _run(data)
    base = result["scenarios"]["base"]
    assert base["current_price_required_return"]["status"] == "RECONCILIATION_MISMATCH"
    assert "B67_REQUIRED_COMMON_PE_SEGMENT_RECALCULATION_MISMATCH:SEG_A" in base["issues"]


def test_b67_independently_rechecks_b66_multiple_bridge():
    data = _fixtures()
    data["multiple_calibration_assessment"]["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]["explicit_adjustment_sum_x"] = "3"
    result = _run(data)
    assert result["scenarios"]["base"]["status"] == "RECONCILIATION_MISMATCH"
    assert "B66_REFERENCE_PLUS_ADJUSTMENTS_DO_NOT_RECONCILE" in result["scenarios"]["base"]["issues"]
