from __future__ import annotations

from copy import deepcopy

from iios_mvp.sotp_multiple_calibration_v01 import build_sotp_multiple_calibration_assessment


DIMENSIONS = (
    "business_model",
    "revenue_mix",
    "end_market_customer",
    "growth_stage",
    "cycle_phase",
    "profit_quality",
    "roic",
    "capital_intensity",
    "leverage",
    "cash_flow_conversion",
    "accounting_basis",
    "earnings_reference_period",
    "pe_measurement_basis",
)


def _fixtures():
    target_profile = {
        "business_model": "Industrial valve design and manufacture",
        "revenue_mix": "70% projects / 30% recurring service",
        "end_market_customer": "Oil and gas, chemicals, power",
        "growth_stage": "Mid-growth",
        "cycle_phase": "Early recovery",
        "profit_quality": "Normalized recurring parent attributable profit",
        "roic": "15%-18%",
        "capital_intensity": "Moderate",
        "leverage": "Net cash",
        "cash_flow_conversion": "FCF / net profit 0.8-1.0",
        "accounting_basis": "PRC GAAP, consolidated parent attributable",
        "earnings_reference_period": "FY2026 normalized",
        "pe_measurement_basis": "NTM normalized parent-attributable P/E",
    }
    evidence = [
        {
            "source_id": source_id,
            "title": f"Evidence {source_id}",
            "source_class": "EXCHANGE_PRIMARY",
            "known_at": "2026-10-30",
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        }
        for source_id in ("E1", "E2", "E3")
    ]

    def peer(entity, pe, evidence_ref, different_growth=False):
        profile = deepcopy(target_profile)
        dimensions = []
        for dimension in DIMENSIONS:
            changed = different_growth and dimension == "growth_stage"
            if changed:
                profile[dimension] = "Mature low growth"
            dimensions.append({
                "dimension": dimension,
                "status": "COMPARABILITY_REVIEW_COMPLETE",
                "comparison": "DIFFERENT" if changed else "SIMILAR",
                "target_value": target_profile[dimension],
                "peer_value": profile[dimension],
                "target_multiple_implication": "TARGET_PREMIUM" if changed else "NEUTRAL",
                "multiple_adjustment_treatment": "SELECTED_PE_ADJUSTED" if changed else "NO_NUMERIC_ADJUSTMENT",
                "evidence_refs": ["E1", evidence_ref],
            })
        return {
            "entity": entity,
            "observed_pe_x": pe,
            "as_of_date": "2026-10-31",
            "evidence_ref": evidence_ref,
            "status": "PEER_COMPARABILITY_COMPLETE",
            "eligible_for_candidate_peer_set": True,
            "dimension_review": dimensions,
        }

    support = {
        "support_type": "COMPARABLE_MULTIPLES",
        "support_summary": "The selected terminal multiple is anchored to the same-basis peer median and explicit target-specific adjustments.",
        "support_evidence_refs": ["E1"],
        "target_comparability_profile": target_profile,
        "comparable_set_status": "COMPARABLE_SET_CAPTURED_NOT_INDEPENDENTLY_VERIFIED",
        "comparable_observations": [
            {"entity": "Peer A", "observed_pe_x": "10", "evidence_ref": "E2"},
            {"entity": "Peer B", "observed_pe_x": "12", "evidence_ref": "E3"},
        ],
        "selected_multiple_bridge": {
            "reference_method": "PEER_MEDIAN",
            "reference_description": "Median of same-accounting, same-period, same-P/E-basis complete comparable peers.",
            "reference_multiple_x": None,
            "reference_evidence_refs": [],
            "adjustments": [
                {
                    "dimension": "growth_stage",
                    "direction": "TARGET_PREMIUM",
                    "adjustment_x": "2",
                    "rationale": "The target has a longer, more visible growth runway than the mature peer, and the selected P/E already reflects this explicit premium.",
                    "evidence_refs": ["E1"],
                }
            ],
            "selected_multiple_explanation": "The terminal P/E equals the same-basis peer median plus an explicit growth-stage premium.",
        },
        "selected_multiple_range": {
            "data_class": "ANALYST_ASSUMPTION",
            "lower_bound_pe_x": "10",
            "upper_bound_pe_x": "16",
            "basis": "Downside peer range to upside normalization range, explicitly selected by analyst.",
            "downside_rationale": "Lower multiple if growth normalizes and the cycle recovery fades.",
            "upside_rationale": "Upper multiple if recurring mix and ROIC persist above peer levels.",
            "evidence_refs": ["E1"],
        },
    }

    sotp_scenarios = {}
    b63_scenarios = {}
    b65_scenarios = {}
    for name in ("bear", "base", "bull"):
        sotp_scenarios[name] = {
            "segments": [
                {
                    "segment_id": "seg_a",
                    "segment_name": "Industrial valves",
                    "attributable_net_profit_cny": {
                        "value": "100",
                        "unit": "CNY",
                        "data_class": "ISSUER_FORECAST",
                        "basis": "Normalized parent-attributable net profit",
                        "evidence_refs": ["E1"],
                    },
                    "pe_multiple_x": {
                        "value": "13",
                        "unit": "x",
                        "data_class": "ANALYST_ASSUMPTION",
                        "basis": "Terminal normalized NTM P/E",
                        "evidence_refs": ["E1", "E2", "E3"],
                        "support_assessment": deepcopy(support),
                    },
                    "segment_equity_value_cny": "1300",
                }
            ],
            "parent_level_adjustments": {
                "capitalized_central_cost_value_cny": "100",
                "net_cash_debt_cny": {"value": "0", "unit": "CNY"},
                "other_adjustments_cny": {"value": "0", "unit": "CNY"},
            },
            "diluted_shares": {"value": "100", "unit": "shares"},
            "total_equity_value_cny": "1200",
            "terminal_value_per_share": "12",
        }
        b63_scenarios[name] = {
            "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
            "multiple_attribution": {
                "common_pe_scale_factor_required": "1.1538461538",
                "required_common_pe_by_segment": [
                    {
                        "segment_id": "seg_a",
                        "selected_sotp_pe_x": "13",
                        "required_pe_under_common_scale_x": "15",
                        "interpretation": "CONDITIONAL_ONLY",
                    }
                ],
            },
        }
        b65_scenarios[name] = {
            "status": "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED",
            "segments": [
                {
                    "segment_id": "seg_a",
                    "segment_name": "Industrial valves",
                    "selected_terminal_pe_x": "13",
                    "peer_set_status": "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED",
                    "eligible_peer_count": 2,
                    "target_comparability_profile": deepcopy(target_profile),
                    "peers": [
                        peer("Peer A", "10", "E2", False),
                        peer("Peer B", "12", "E3", True),
                    ],
                }
            ],
        }
    sotp = {
        "status": "CALCULATED",
        "selected_for_primary_model": True,
        "forecast_period": "2026FY",
        "scenarios": sotp_scenarios,
    }
    b63 = {
        "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
        "scenarios": b63_scenarios,
    }
    b65 = {
        "status": "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED",
        "scenarios": b65_scenarios,
    }
    return sotp, evidence, b63, b65


def _run(sotp, evidence, b63, b65):
    return build_sotp_multiple_calibration_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
        comparable_company_audit=b65,
    )


def test_b66_reconciles_peer_median_plus_explicit_adjustment_to_selected_pe():
    sotp, evidence, b63, b65 = _fixtures()
    result = _run(sotp, evidence, b63, b65)
    assert result["status"] == "CALIBRATION_AND_RANGE_RECONCILED"
    base = result["scenarios"]["base"]
    segment = base["segments"][0]
    assert segment["same_basis_peer_reference"]["median_pe_x"] == "11"
    assert segment["selected_pe_vs_peer_median"]["difference_x"] == "2"
    assert segment["explicit_selected_multiple_bridge"]["status"] == "MULTIPLE_BRIDGE_RECONCILED"
    assert segment["explicit_selected_multiple_bridge"]["explicit_adjustment_sum_x"] == "2"
    assert segment["explicit_selected_multiple_bridge"]["calculated_selected_pe_x"] == "13"
    assert segment["b63_required_common_pe_sensitivity"]["required_common_pe_x"] == "15"
    assert segment["b63_required_common_pe_sensitivity"]["selected_minus_required_pe_x"] == "-2"
    assert result["selected_pes_modified"] is False
    assert result["sotp_values_modified"] is False
    assert result["decision_authority"] is False


def test_b66_computes_segment_and_all_sotp_multiple_range_sensitivity():
    sotp, evidence, b63, b65 = _fixtures()
    result = _run(sotp, evidence, b63, b65)
    base = result["scenarios"]["base"]
    segment = base["segments"][0]
    assert segment["segment_equity_value_sensitivity_cny"] == {
        "lower_range": "1000",
        "selected": "1300",
        "upper_range": "1600",
        "status": "CALCULATED",
    }
    aggregate = base["aggregate_sensitivity"]
    assert aggregate["lower_terminal_value_per_share_cny"] == "9"
    assert aggregate["selected_terminal_value_per_share_cny"] == "12"
    assert aggregate["upper_terminal_value_per_share_cny"] == "15"
    assert aggregate["parent_adjustments_unchanged"] is True
    assert aggregate["diluted_shares_unchanged"] == "100"


def test_b66_excludes_peers_with_incompatible_pe_measurement_basis_from_median():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b65["scenarios"][name]["segments"][0]["peers"][1]
        for dimension in peer["dimension_review"]:
            if dimension["dimension"] == "pe_measurement_basis":
                dimension["comparison"] = "DIFFERENT"
                dimension["peer_value"] = "TTM reported P/E"
        peer["status"] = "PEER_COMPARABILITY_COMPLETE"
    result = _run(sotp, evidence, b63, b65)
    base_segment = result["scenarios"]["base"]["segments"][0]
    anchor = base_segment["same_basis_peer_reference"]
    assert anchor["peer_count"] == 1
    assert anchor["median_pe_x"] is None
    assert base_segment["explicit_selected_multiple_bridge"]["status"] == "PARTIAL"


def test_b66_fails_when_explicit_adjustments_do_not_reconcile_to_selected_pe():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        adjustment = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]["adjustments"][0]
        adjustment["adjustment_x"] = "3"
    result = _run(sotp, evidence, b63, b65)
    base_segment = result["scenarios"]["base"]["segments"][0]
    assert base_segment["explicit_selected_multiple_bridge"]["status"] == "PARTIAL"
    assert "REFERENCE_PLUS_EXPLICIT_ADJUSTMENTS_DO_NOT_RECONCILE_TO_SELECTED_PE" in base_segment["explicit_selected_multiple_bridge"]["issues"]


def test_b66_fails_when_premium_discount_sign_conflicts_with_adjustment_direction():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        adjustment = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]["adjustments"][0]
        adjustment["adjustment_x"] = "-2"
    result = _run(sotp, evidence, b63, b65)
    bridge = result["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]
    assert "PREMIUM_ADJUSTMENT_MUST_BE_POSITIVE:growth_stage" in bridge["issues"]
    assert bridge["status"] == "PARTIAL"


def test_b66_requires_adjustment_evidence_to_be_attached_and_cutoff_compatible():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        adjustment = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]["adjustments"][0]
        adjustment["evidence_refs"] = ["UNRESOLVED"]
    result = _run(sotp, evidence, b63, b65)
    bridge = result["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]
    assert "REFERENCE_NOT_ATTACHED_TO_SELECTED_PE_MEASURE:UNRESOLVED" in bridge["issues"]
    assert bridge["status"] == "PARTIAL"


def test_b66_requires_selected_pe_to_fall_inside_explicit_analyst_range():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        range_input = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_range"]
        range_input["lower_bound_pe_x"] = "14"
    result = _run(sotp, evidence, b63, b65)
    band = result["scenarios"]["base"]["segments"][0]["analyst_multiple_range"]
    assert "SELECTED_PE_OUTSIDE_ANALYST_RANGE" in band["issues"]
    assert band["status"] == "PARTIAL"
    assert result["scenarios"]["base"]["aggregate_sensitivity"]["status"] == "NOT_IDENTIFIABLE"


def test_b66_does_not_call_missing_peer_anchor_a_reconciled_multiple_bridge():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        b65["scenarios"][name]["status"] = "PARTIAL"
        for peer in b65["scenarios"][name]["segments"][0]["peers"]:
            peer["status"] = "PEER_COMPARABILITY_PARTIAL"
            peer["eligible_for_candidate_peer_set"] = False
        bridge = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]
        bridge["reference_method"] = "NO_COMPARABLE_REFERENCE"
        bridge["reference_description"] = "No verified same-basis peer anchor exists for this segment."
        bridge["adjustments"] = []
    b65["status"] = "PARTIAL"
    result = _run(sotp, evidence, b63, b65)
    base = result["scenarios"]["base"]
    assert base["segments"][0]["explicit_selected_multiple_bridge"]["status"] == "NO_COMPARABLE_REFERENCE_ASSUMPTION_ONLY"
    assert base["status"] == "PARTIAL"
    assert result["status"] == "PARTIAL"


def test_b66_rejects_no_comparable_reference_when_same_basis_peer_anchor_exists():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        bridge = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]
        bridge["reference_method"] = "NO_COMPARABLE_REFERENCE"
        bridge["reference_description"] = "No verified same-basis peer anchor exists for this segment."
        bridge["adjustments"] = []
    result = _run(sotp, evidence, b63, b65)
    bridge = result["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]
    assert "NO_COMPARABLE_REFERENCE_CONFLICTS_WITH_IDENTIFIED_SAME_BASIS_PEERS" in bridge["issues"]
    assert bridge["status"] == "PARTIAL"


def test_b66_supports_an_explicit_historical_reference_when_evidence_is_resolved():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        bridge = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]
        bridge["reference_method"] = "HISTORICAL_SELF_RANGE"
        bridge["reference_description"] = "Five-year same-definition normalized P/E median at the previous cycle midpoint."
        bridge["reference_multiple_x"] = "12"
        bridge["reference_evidence_refs"] = ["E2"]
        bridge["adjustments"][0]["adjustment_x"] = "1"
    result = _run(sotp, evidence, b63, b65)
    base_segment = result["scenarios"]["base"]["segments"][0]
    assert base_segment["explicit_selected_multiple_bridge"]["status"] == "MULTIPLE_BRIDGE_RECONCILED"
    assert base_segment["explicit_selected_multiple_bridge"]["reference_multiple_x"] == "12"
    assert base_segment["explicit_selected_multiple_bridge"]["calculated_selected_pe_x"] == "13"


def test_b66_blocks_sotp_calibration_when_b63_or_b65_is_not_available():
    sotp, evidence, b63, b65 = _fixtures()
    b63["status"] = "BLOCKED"
    result = _run(sotp, evidence, b63, b65)
    assert result["status"] == "BLOCKED_BY_B63"
    assert result["scenarios"] == {}

    sotp, evidence, b63, b65 = _fixtures()
    b65["status"] = "BLOCKED"
    result = _run(sotp, evidence, b63, b65)
    assert result["status"] == "BLOCKED_BY_B65"
    assert result["scenarios"] == {}


def test_b66_is_not_applicable_when_sotp_is_not_primary_model():
    sotp, evidence, b63, b65 = _fixtures()
    sotp["selected_for_primary_model"] = False
    result = _run(sotp, evidence, b63, b65)
    assert result["status"] == "NOT_APPLICABLE_SOTP_NOT_SELECTED"
    assert result["scenarios"] == {}


def test_b66_rejects_literal_unknown_critical_pe_basis_from_peer_anchor():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b65["scenarios"][name]["segments"][0]["peers"][1]
        peer["dimension_review"] = [
            {
                **row,
                "peer_value": "UNKNOWN",
                "comparison": "SIMILAR",
            } if row["dimension"] == "pe_measurement_basis" else row
            for row in peer["dimension_review"]
        ]
    result = _run(sotp, evidence, b63, b65)
    anchor = result["scenarios"]["base"]["segments"][0]["same_basis_peer_reference"]
    assert anchor["peer_count"] == 1
    assert anchor["median_pe_x"] is None
    assert any("pe_measurement_basis:BASIS_VALUE_UNKNOWN" in item["reasons"] for item in anchor["excluded_from_numeric_anchor"])


def test_b66_crosschecks_selected_pe_against_b65_and_b63():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        b65["scenarios"][name]["segments"][0]["selected_terminal_pe_x"] = "14"
        b63["scenarios"][name]["multiple_attribution"]["required_common_pe_by_segment"][0]["selected_sotp_pe_x"] = "12"
    result = _run(sotp, evidence, b63, b65)
    issues = result["scenarios"]["base"]["issues"]
    assert "B65_SELECTED_PE_VS_SOTP_INPUT_MISMATCH:seg_a" in issues
    assert "B63_SELECTED_PE_VS_SOTP_INPUT_MISMATCH:seg_a" in issues
    assert result["scenarios"]["base"]["status"] == "PARTIAL"


def test_b66_blocks_non_analyst_class_for_selected_terminal_pe():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["data_class"] = "ISSUER_FORECAST"
    result = _run(sotp, evidence, b63, b65)
    bridge = result["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]
    assert "SELECTED_TERMINAL_PE_MUST_BE_ANALYST_ASSUMPTION:ISSUER_FORECAST" in bridge["issues"]
    assert bridge["status"] == "PARTIAL"


def test_b66_does_not_reconcile_unknown_selected_multiple_rationale():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        bridge = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]
        bridge["selected_multiple_explanation"] = "UNKNOWN"
    result = _run(sotp, evidence, b63, b65)
    bridge = result["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]
    assert "SELECTED_MULTIPLE_EXPLANATION_MISSING" in bridge["issues"]
    assert bridge["status"] == "PARTIAL"


def test_b66_adjustment_source_must_support_the_specific_b65_dimension_and_direction():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        adjustment = sotp["scenarios"][name]["segments"][0]["pe_multiple_x"]["support_assessment"]["selected_multiple_bridge"]["adjustments"][0]
        # E2 belongs to the P/E measure and to Peer A's neutral growth-stage row,
        # but not to the only same-basis peer that declared a target growth premium.
        adjustment["evidence_refs"] = ["E2"]
    result = _run(sotp, evidence, b63, b65)
    bridge = result["scenarios"]["base"]["segments"][0]["explicit_selected_multiple_bridge"]
    assert "ADJUSTMENT_EVIDENCE_NOT_TIED_TO_B65_DIMENSION:growth_stage:TARGET_PREMIUM" in bridge["issues"]
    assert bridge["status"] == "PARTIAL"


def test_b66_reconciles_declared_segment_value_pool_before_aggregate_sensitivity():
    sotp, evidence, b63, b65 = _fixtures()
    for name in ("bear", "base", "bull"):
        sotp["scenarios"][name]["segment_equity_value_cny"] = "1299"
    result = _run(sotp, evidence, b63, b65)
    aggregate = result["scenarios"]["base"]["aggregate_sensitivity"]
    assert aggregate["status"] == "RECONCILIATION_MISMATCH"
    assert "SELECTED_SOTP_SEGMENT_POOL_DOES_NOT_RECONCILE" in aggregate["issues"]
    assert result["scenarios"]["base"]["status"] == "PARTIAL"
