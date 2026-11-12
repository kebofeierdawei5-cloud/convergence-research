from __future__ import annotations

from copy import deepcopy

from iios_mvp.sotp_evidence_grade_v01 import build_sotp_evidence_grade_assessment
from iios_mvp.sotp_valuation_v01 import SOTP_METHOD, SOTP_VALUATION_SCHEMA, evaluate_sotp_valuation


def _fixtures():
    e1 = {
        "source_id": "E1",
        "title": "Exchange-filed annual operating disclosure",
        "source_class": "EXCHANGE_PRIMARY",
        "source_domain_class_status": "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED",
        "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        "known_at": "2026-03-20",
        "summary": "Disclosed capacity utilization and product sales facts.",
    }
    e2 = {
        "source_id": "E2",
        "title": "Peer valuation observation set",
        "source_class": "REPRODUCIBLE_PUBLIC_DATA",
        "source_domain_class_status": "SOURCE_CLASS_NOT_PRIMARY",
        "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        "known_at": "2026-06-30",
        "summary": "Dated market valuation observation.",
    }
    e3 = {
        "source_id": "E3",
        "title": "Issuer operating indicator disclosure",
        "source_class": "ISSUER_PRIMARY",
        "source_domain_class_status": "ISSUER_DOMAIN_NOT_INDEPENDENTLY_VERIFIED",
        "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        "known_at": "2026-04-15",
        "summary": "Order conversion, operating rate and realized margin observations.",
    }
    e4 = {
        "source_id": "E4",
        "title": "Analyst multiple rationale",
        "source_class": "ANALYST_ASSUMPTION",
        "source_domain_class_status": "SOURCE_CLASS_NOT_PRIMARY",
        "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        "known_at": "2026-06-30",
        "summary": "Analyst valuation assumption reference.",
    }
    e5 = {
        "source_id": "E5",
        "title": "Second peer valuation observation",
        "source_class": "REPRODUCIBLE_PUBLIC_DATA",
        "source_domain_class_status": "SOURCE_CLASS_NOT_PRIMARY",
        "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        "known_at": "2026-06-30",
        "summary": "Second dated market valuation observation.",
    }

    segment_a = {
        "segment_id": "seg_a",
        "segment_name": "Industrial valves",
        "earnings_basis": "NORMALIZED_PARENT_ATTRIBUTABLE",
        "attributable_net_profit_cny": {
            "value": "100",
            "unit": "CNY",
            "data_class": "ISSUER_FORECAST",
            "basis": "Normalized attributable profit informed by disclosed operating facts",
            "evidence_refs": ["E1"],
            "support_assessment": {
                "support_type": "DISCLOSED_FACTS",
                "support_summary": "Filed capacity utilization and sales facts are explicitly linked to the segment revenue and normalized profit forecast.",
                "support_evidence_refs": ["E1"],
                "mechanism_chain": [],
                "key_operating_indicators": ["Capacity utilization", "Sales volume"],
                "derivation_steps": [],
                "counter_evidence_refs": [],
                "reversal_signals": ["Utilization falls for two consecutive reporting periods."],
            },
        },
        "pe_multiple_x": {
            "value": "12",
            "unit": "x",
            "data_class": "ANALYST_ASSUMPTION",
            "basis": "Terminal normalized P/E selected by analyst",
            "evidence_refs": ["E2", "E5"],
            "support_assessment": {
                "support_type": "COMPARABLE_MULTIPLES",
                "support_summary": "Two dated peers are recorded as reference observations, not as proof of fair value.",
                "support_evidence_refs": ["E2", "E5"],
                "target_comparability_profile": {
                    "business_model": "Industrial valve design and manufacture",
                },
                "comparable_observations": [
                    {
                        "entity": "Peer A",
                        "as_of_date": "2026-06-30",
                        "observed_pe_x": "11",
                        "evidence_ref": "E2",
                        "comparability_adjustment": "Peer has lower recurring service revenue and lower ROIC.",
                        "date_alignment_rationale": "Historical reference date is retained for structural pass-through coverage.",
                        "peer_comparability_profile": {"business_model": "Industrial valve manufacturing"},
                        "dimension_assessments": {"business_model": {"comparison": "DIFFERENT"}},
                    },
                    {
                        "entity": "Peer B",
                        "as_of_date": "2026-06-30",
                        "observed_pe_x": "14",
                        "evidence_ref": "E5",
                        "comparability_adjustment": "Peer has higher growth but greater customer concentration.",
                    },
                ],
            },
        },
    }
    segment_b = {
        "segment_id": "seg_b",
        "segment_name": "Industrial automation",
        "earnings_basis": "NORMALIZED_PARENT_ATTRIBUTABLE",
        "attributable_net_profit_cny": {
            "value": "50",
            "unit": "CNY",
            "data_class": "ANALYST_ASSUMPTION",
            "basis": "Normalized attributable profit from explicit driver build-up",
            "evidence_refs": ["E3"],
            "support_assessment": {
                "support_type": "BUSINESS_MECHANISM",
                "support_summary": "Orders convert to shipment volume; shipment volume drives utilization and product mix; utilization and mix drive normalized segment margin.",
                "support_evidence_refs": ["E3"],
                "mechanism_chain": [
                    "Order backlog converts into shipped units",
                    "Shipped units raise utilization and improve product mix",
                    "Utilization and mix translate into segment contribution margin",
                ],
                "key_operating_indicators": ["Order-to-shipment conversion", "Utilization", "Gross margin"],
                "derivation_steps": [],
                "counter_evidence_refs": [],
                "reversal_signals": ["Order conversion weakens and utilization fails to improve."],
            },
        },
        "pe_multiple_x": {
            "value": "18",
            "unit": "x",
            "data_class": "ANALYST_ASSUMPTION",
            "basis": "Terminal P/E assumption reflecting growth and cyclicality",
            "evidence_refs": ["E4"],
            "support_assessment": {
                "support_type": "PURE_MULTIPLE_ASSUMPTION",
                "support_summary": "Selected terminal multiple is a separate analyst assumption.",
                "support_evidence_refs": ["E4"],
                "comparable_observations": [],
            },
        },
    }

    sotp = {
        "status": "CALCULATED",
        "selected_for_primary_model": True,
        "forecast_period": "2026FY",
        "scenarios": {
            name: {"segments": [deepcopy(segment_a), deepcopy(segment_b)]}
            for name in ("bear", "base", "bull")
        },
    }
    b63 = {
        "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
        "scenarios": {
            name: {
                "status": "CONDITIONAL_ATTRIBUTION_CALCULATED",
                "earnings_effect_by_segment": [
                    {"segment_id": "seg_a"},
                    {"segment_id": "seg_b"},
                ],
            }
            for name in ("bear", "base", "bull")
        },
    }
    return sotp, [e1, e2, e3, e4, e5], b63


def test_b64_distinguishes_disclosure_linked_profit_and_multiple_assumption():
    sotp, evidence, b63 = _fixtures()
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    assert result["status"] == "ASSESSED_DIAGNOSTIC_ONLY"
    base = result["scenarios"]["base"]
    segments = {row["segment_id"]: row for row in base["segments"]}
    assert segments["seg_a"]["profit_evidence_assessment"]["grade"] == "G1_DISCLOSURE_LINKED_TO_PROFIT"
    assert segments["seg_a"]["multiple_evidence_assessment"]["grade"] == "G4_MULTIPLE_ASSUMPTION_ONLY"
    assert segments["seg_a"]["multiple_evidence_assessment"]["comparable_set_status"] == "COMPARABLE_SET_CAPTURED_NOT_INDEPENDENTLY_VERIFIED"
    multiple = segments["seg_a"]["multiple_evidence_assessment"]
    assert multiple["target_comparability_profile"]["business_model"] == "Industrial valve design and manufacture"
    peer_a = next(row for row in multiple["comparable_observations"] if row["entity"] == "Peer A")
    assert peer_a["peer_comparability_profile"]["business_model"] == "Industrial valve manufacturing"
    assert peer_a["dimension_assessments"]["business_model"]["comparison"] == "DIFFERENT"
    assert peer_a["date_alignment_rationale"] == "Historical reference date is retained for structural pass-through coverage."
    assert result["sotp_input_modified"] is False
    assert result["valuation_values_modified"] is False
    assert result["external_mie_modified"] is False
    assert result["decision_authority"] is False


def test_b64_grades_traceable_business_mechanism_as_g2():
    sotp, evidence, b63 = _fixtures()
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    base = {row["segment_id"]: row for row in result["scenarios"]["base"]["segments"]}
    assessment = base["seg_b"]["profit_evidence_assessment"]
    assert assessment["grade"] == "G2_BUSINESS_MECHANISM_AND_EVIDENCE_LINKED"
    assert len(assessment["mechanism_chain"]) >= 2
    assert assessment["reversal_signals"]


def test_b64_keeps_explicit_analyst_profit_input_at_g3():
    sotp, evidence, b63 = _fixtures()
    profit = sotp["scenarios"]["base"]["segments"][1]["attributable_net_profit_cny"]
    profit["support_assessment"] = None
    for name in ("bear", "bull"):
        sotp["scenarios"][name]["segments"][1]["attributable_net_profit_cny"]["support_assessment"] = None
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    base = {row["segment_id"]: row for row in result["scenarios"]["base"]["segments"]}
    assert base["seg_b"]["profit_evidence_assessment"]["grade"] == "G3_ANALYST_ASSUMPTION_ONLY"


def test_b64_keeps_issuer_forecast_with_no_support_linkage_at_g5():
    sotp, evidence, b63 = _fixtures()
    for name in ("bear", "base", "bull"):
        measure = sotp["scenarios"][name]["segments"][0]["attributable_net_profit_cny"]
        measure["support_assessment"] = None
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    base = {row["segment_id"]: row for row in result["scenarios"]["base"]["segments"]}
    assert base["seg_a"]["profit_evidence_assessment"]["grade"] == "G5_UNKNOWN"
    assert result["status"] == "PARTIAL"


def test_b64_rejects_support_reference_not_attached_to_profit_measure():
    sotp, evidence, b63 = _fixtures()
    for name in ("bear", "base", "bull"):
        support = sotp["scenarios"][name]["segments"][0]["attributable_net_profit_cny"]["support_assessment"]
        support["support_evidence_refs"] = ["E2"]
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    base = {row["segment_id"]: row for row in result["scenarios"]["base"]["segments"]}
    assert base["seg_a"]["profit_evidence_assessment"]["grade"] == "G5_UNKNOWN"
    assert "SUPPORT_REFERENCE_NOT_ATTACHED_TO_MEASURE:E2" in base["seg_a"]["profit_evidence_assessment"]["issues"]


def test_b64_requires_two_distinct_time_compatible_comparables_for_candidate_set():
    sotp, evidence, b63 = _fixtures()
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    base = {row["segment_id"]: row for row in result["scenarios"]["base"]["segments"]}
    multiple = base["seg_a"]["multiple_evidence_assessment"]
    assert multiple["grade"] == "G4_MULTIPLE_ASSUMPTION_ONLY"
    assert multiple["comparable_set_status"] == "COMPARABLE_SET_CAPTURED_NOT_INDEPENDENTLY_VERIFIED"
    assert len(multiple["comparable_observations"]) == 2


def test_b64_blocks_scenario_when_b63_reconciliation_did_not_pass():
    sotp, evidence, b63 = _fixtures()
    b63["scenarios"]["base"]["status"] = "RECONCILIATION_MISMATCH"
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    assert result["scenarios"]["base"]["status"] == "BLOCKED_BY_B63_SCENARIO"
    assert result["scenarios"]["bear"]["status"] == "ASSESSED_DIAGNOSTIC_ONLY"


def test_b64_does_not_apply_when_sotp_is_not_the_selected_primary_model():
    sotp, evidence, b63 = _fixtures()
    sotp["selected_for_primary_model"] = False
    result = build_sotp_evidence_grade_assessment(
        sotp_valuation=sotp,
        evidence_register=evidence,
        valuation_gap_attribution=b63,
    )
    assert result["status"] == "NOT_APPLICABLE_OR_SOTP_NOT_CALCULATED"
    assert result["scenarios"] == {}


def test_sotp_adapter_preserves_b64_annotations_without_changing_value_arithmetic():
    evidence = [
        {
            "source_id": "E1",
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
            "source_class": "EXCHANGE_PRIMARY",
        },
        {
            "source_id": "E2",
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
            "source_class": "REPRODUCIBLE_PUBLIC_DATA",
        },
    ]
    raw = {
        "schema_version": SOTP_VALUATION_SCHEMA,
        "calculation_method": SOTP_METHOD,
        "summary": "Segment attributable profit multiplied by selected segment P/E.",
        "forecast_period": "2026FY",
        "valuation_terminal_date": "2026-12-31",
        "scenarios": {},
    }
    for name in ("bear", "base", "bull"):
        raw["scenarios"][name] = {
            "rationale": f"{name} operating scenario",
            "segments": [
                {
                    "segment_id": "seg_a",
                    "segment_name": "Industrial valves",
                    "earnings_basis": "NORMALIZED_PARENT_ATTRIBUTABLE",
                    "attributable_net_profit_cny": {
                        "value": "100",
                        "unit": "CNY",
                        "data_class": "ISSUER_FORECAST",
                        "basis": "Forecast attributable normalized net profit",
                        "evidence_refs": ["E1"],
                        "support_assessment": {
                            "support_type": "ISSUER_GUIDANCE",
                            "support_summary": "Filed issuer guidance linked to the forecast profit.",
                            "support_evidence_refs": ["E1"],
                            "mechanism_chain": [],
                            "key_operating_indicators": ["Sales volume"],
                            "derivation_steps": [],
                            "counter_evidence_refs": [],
                            "reversal_signals": ["Guidance withdrawn."],
                        },
                    },
                    "pe_multiple_x": {
                        "value": "10",
                        "unit": "x",
                        "data_class": "ANALYST_ASSUMPTION",
                        "basis": "Selected terminal multiple",
                        "evidence_refs": ["E2"],
                        "support_assessment": {
                            "support_type": "PURE_MULTIPLE_ASSUMPTION",
                            "support_summary": "Analyst-selected terminal multiple.",
                            "support_evidence_refs": ["E2"],
                            "comparable_observations": [],
                        },
                    },
                }
            ],
            "parent_level_adjustments": {
                "central_cost_after_tax_cny": {
                    "value": "0", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                    "basis": "No central cost in this isolated adapter test", "evidence_refs": [],
                },
                "central_cost_multiple_x": {
                    "value": "0", "unit": "x", "data_class": "ANALYST_ASSUMPTION",
                    "basis": "No central cost in this isolated adapter test", "evidence_refs": [],
                },
                "net_cash_debt_cny": {
                    "value": "0", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                    "basis": "Neutral test balance", "evidence_refs": [],
                },
                "other_adjustments_cny": {
                    "value": "0", "unit": "CNY", "data_class": "ANALYST_ASSUMPTION",
                    "basis": "Neutral test adjustment", "evidence_refs": [],
                },
            },
            "diluted_shares": {
                "value": "100", "unit": "shares", "data_class": "ANALYST_ASSUMPTION",
                "basis": "Isolated test share count", "evidence_refs": [],
            },
        }

    normalized = evaluate_sotp_valuation(
        raw,
        selected_model_family="SOTP",
        expected_forecast_period="2026FY",
        expected_terminal_date="2026-12-31",
        evidence_register=evidence,
        expected_currency="CNY",
    )
    assert normalized["status"] == "CALCULATED"
    base_segment = normalized["scenarios"]["base"]["segments"][0]
    assert base_segment["segment_equity_value_cny"] == "1000"
    assert base_segment["attributable_net_profit_cny"]["support_assessment"]["support_type"] == "ISSUER_GUIDANCE"
    assert base_segment["pe_multiple_x"]["support_assessment"]["support_type"] == "PURE_MULTIPLE_ASSUMPTION"
