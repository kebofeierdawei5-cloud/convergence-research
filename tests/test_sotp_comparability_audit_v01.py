from __future__ import annotations

from copy import deepcopy

from iios_mvp.sotp_comparability_audit_v01 import DIMENSIONS, build_sotp_comparability_audit


def _fixtures():
    target_profile = {
        "business_model": "Design, manufacture and service of industrial valves",
        "revenue_mix": "70% project sales / 30% recurring service",
        "end_market_customer": "Oil and gas, chemicals, power generation",
        "growth_stage": "Mid-growth with service mix expansion",
        "cycle_phase": "Early recovery",
        "profit_quality": "Normalized recurring parent-attributable earnings",
        "roic": "15%-18% normalized ROIC",
        "capital_intensity": "Moderate; maintenance and selective expansion capex",
        "leverage": "Net cash",
        "cash_flow_conversion": "FCF / normalized net profit around 0.8-1.0",
        "accounting_basis": "PRC GAAP consolidated, parent-attributable",
        "earnings_reference_period": "FY2026 normalized forecast",
        "pe_measurement_basis": "NTM normalized parent-attributable P/E",
    }
    evidence = [
        {
            "source_id": "E1",
            "title": "Target segment operating and financial disclosure",
            "source_class": "EXCHANGE_PRIMARY",
            "source_domain_class_status": "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED",
            "known_at": "2026-10-30",
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        },
        {
            "source_id": "P_A",
            "title": "Peer A valuation and financial observations",
            "source_class": "REPRODUCIBLE_PUBLIC_DATA",
            "source_domain_class_status": "SOURCE_CLASS_NOT_PRIMARY",
            "known_at": "2026-10-31",
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        },
        {
            "source_id": "P_B",
            "title": "Peer B valuation and financial observations",
            "source_class": "REPRODUCIBLE_PUBLIC_DATA",
            "source_domain_class_status": "SOURCE_CLASS_NOT_PRIMARY",
            "known_at": "2026-10-30",
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        },
    ]

    peer_a_profile = deepcopy(target_profile)
    peer_b_profile = deepcopy(target_profile)
    peer_b_profile["growth_stage"] = "Mature with low single-digit organic growth"
    peer_b_profile["cycle_phase"] = "Late-cycle stable utilization"
    peer_b_profile["roic"] = "10%-12% normalized ROIC"

    def dimension_rows(peer_profile, changed_dims=()):
        result = {}
        for dimension in DIMENSIONS:
            changed = dimension in changed_dims
            result[dimension] = {
                "target_value": target_profile[dimension],
                "peer_value": peer_profile[dimension],
                "comparison": "DIFFERENT" if changed else "SIMILAR",
                "target_multiple_implication": "TARGET_PREMIUM" if changed else "NEUTRAL",
                "multiple_adjustment_treatment": "SELECTED_PE_ADJUSTED" if changed else "NO_NUMERIC_ADJUSTMENT",
                "rationale": (
                    f"Target is economically stronger on {dimension}."
                    if changed else f"Target and peer are sufficiently similar on {dimension}."
                ),
                "adjustment_rationale": (
                    f"The selected target P/E already reflects the {dimension} difference."
                    if changed else "No numeric multiple adjustment is warranted for this similar dimension."
                ),
                "evidence_refs": ["E1", "P_A" if peer_profile is peer_a_profile else "P_B"],
            }
        return result

    peer_a = {
        "entity": "Peer A",
        "as_of_date": "2026-10-31",
        "observed_pe_x": "14.2",
        "evidence_ref": "P_A",
        "comparability_adjustment": "Broadly similar industrial valve and service mix.",
        "date_alignment_rationale": "",
        "peer_comparability_profile": peer_a_profile,
        "dimension_assessments": dimension_rows(peer_a_profile),
    }
    peer_b = {
        "entity": "Peer B",
        "as_of_date": "2026-10-30",
        "observed_pe_x": "11.8",
        "evidence_ref": "P_B",
        "comparability_adjustment": "Lower growth, later cycle and lower normalized ROIC.",
        "date_alignment_rationale": "One day before cutoff; the cited trading and financial snapshot is still the latest available at the case cutoff.",
        "peer_comparability_profile": peer_b_profile,
        "dimension_assessments": dimension_rows(
            peer_b_profile, {"growth_stage", "cycle_phase", "roic"}
        ),
    }
    target = {
        "segment_id": "seg_a",
        "segment_name": "Industrial valves",
        "selected_terminal_pe_x": "13",
        "selected_pe_grade": "G4_MULTIPLE_ASSUMPTION_ONLY",
        "multiple_evidence_assessment": {
            "grade": "G4_MULTIPLE_ASSUMPTION_ONLY",
            "measure_evidence_refs": ["E1", "P_A", "P_B"],
            "support_evidence_refs": ["E1"],
            "target_comparability_profile": target_profile,
            "comparable_observations": [peer_a, peer_b],
        },
    }
    b64 = {
        "status": "ASSESSED_DIAGNOSTIC_ONLY",
        "scenarios": {
            name: {
                "status": "ASSESSED_DIAGNOSTIC_ONLY",
                "segments": [deepcopy(target)],
            }
            for name in ("bear", "base", "bull")
        },
    }
    return b64, evidence, target_profile


def _run(b64, evidence):
    return build_sotp_comparability_audit(
        evidence_grade_assessment=b64,
        evidence_register=evidence,
        valuation_as_of_date="2026-10-31",
    )


def test_b65_completes_dimension_audit_but_never_changes_selected_pe():
    b64, evidence, _ = _fixtures()
    result = _run(b64, evidence)
    assert result["status"] == "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
    base = result["scenarios"]["base"]["segments"][0]
    assert base["selected_terminal_pe_x"] == "13"
    assert base["eligible_peer_count"] == 2
    assert base["peer_set_status"] == "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
    peer_b = next(peer for peer in base["peers"] if peer["entity"] == "Peer B")
    assert peer_b["directional_dimension_summary"]["target_premium_dimensions"] == [
        "growth_stage", "cycle_phase", "roic"
    ]
    assert result["selected_pe_modified"] is False
    assert result["valuation_values_modified"] is False
    assert result["decision_authority"] is False


def test_b65_requires_all_thirteen_dimensions():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][0]
        del peer["dimension_assessments"]["roic"]
    result = _run(b64, evidence)
    base = result["scenarios"]["base"]["segments"][0]
    assert base["peer_set_status"] == "PARTIAL"
    peer = next(peer for peer in base["peers"] if peer["entity"] == "Peer A")
    assert "roic" in peer["unknown_dimensions"]


def test_b65_blocks_profile_and_dimension_value_mismatch():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][0]
        peer["dimension_assessments"]["roic"]["target_value"] = "UNKNOWN"
    result = _run(b64, evidence)
    peer = next(peer for peer in result["scenarios"]["base"]["segments"][0]["peers"] if peer["entity"] == "Peer A")
    assert "roic" in peer["unknown_dimensions"]
    assert any("DIMENSION_ASSESSMENT_PROFILE_VALUE_MISMATCH" in item for item in peer["issues"])


def test_b65_requires_explained_direction_and_treatment_for_differences():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][1]
        peer["dimension_assessments"]["roic"]["target_multiple_implication"] = "UNKNOWN"
        peer["dimension_assessments"]["roic"]["multiple_adjustment_treatment"] = "UNKNOWN"
        peer["dimension_assessments"]["roic"]["adjustment_rationale"] = ""
    result = _run(b64, evidence)
    peer = next(peer for peer in result["scenarios"]["base"]["segments"][0]["peers"] if peer["entity"] == "Peer B")
    assert peer["status"] == "PEER_COMPARABILITY_PARTIAL"
    assert any("DIFFERENCE_DIRECTION_NOT_IDENTIFIABLE" in item for item in peer["issues"])


def test_b65_excludes_not_comparable_peer_instead_of_counting_it_in_peer_set():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][1]
        row = peer["dimension_assessments"]["business_model"]
        row["comparison"] = "NOT_COMPARABLE"
        row["target_multiple_implication"] = "UNKNOWN"
        row["multiple_adjustment_treatment"] = "PEER_EXCLUDED"
        row["adjustment_rationale"] = "This peer is primarily a software licensing platform and has a structurally different business model."
    result = _run(b64, evidence)
    segment = result["scenarios"]["base"]["segments"][0]
    peer = next(peer for peer in segment["peers"] if peer["entity"] == "Peer B")
    assert peer["status"] == "PEER_EXCLUDED_NOT_COMPARABLE"
    assert segment["eligible_peer_count"] == 1
    assert segment["peer_set_status"] == "PEER_SET_INSUFFICIENTLY_COMPARABLE"


def test_b65_blocks_peer_valuation_date_after_case_cutoff():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][1]
        peer["as_of_date"] = "2026-11-01"
    result = _run(b64, evidence)
    peer = next(peer for peer in result["scenarios"]["base"]["segments"][0]["peers"] if peer["entity"] == "Peer B")
    assert peer["date_alignment_status"] == "FUTURE_DATE_BLOCKED"
    assert peer["status"] == "PEER_COMPARABILITY_PARTIAL"


def test_b65_requires_rebase_rationale_for_earlier_peer_valuation_date():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][1]
        peer["date_alignment_rationale"] = ""
    result = _run(b64, evidence)
    peer = next(peer for peer in result["scenarios"]["base"]["segments"][0]["peers"] if peer["entity"] == "Peer B")
    assert peer["status"] == "PEER_COMPARABILITY_PARTIAL"
    assert "EARLIER_COMPARABLE_DATE_REQUIRES_REBASE_RATIONALE" in peer["issues"]


def test_b65_requires_each_dimension_reference_to_belong_to_pe_measure():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][0]
        peer["dimension_assessments"]["roic"]["evidence_refs"] = ["UNRESOLVED"]
    result = _run(b64, evidence)
    peer = next(peer for peer in result["scenarios"]["base"]["segments"][0]["peers"] if peer["entity"] == "Peer A")
    assert peer["status"] == "PEER_COMPARABILITY_PARTIAL"
    assert any("COMPARABILITY_EVIDENCE_NOT_ATTACHED_TO_PE_MEASURE:UNRESOLVED" in item for item in peer["issues"])


def test_b65_refuses_unavailable_valuation_cutoff_or_unassessed_b64():
    b64, evidence, _ = _fixtures()
    missing_date = build_sotp_comparability_audit(
        evidence_grade_assessment=b64,
        evidence_register=evidence,
        valuation_as_of_date="UNKNOWN",
    )
    assert missing_date["status"] == "VALUATION_AS_OF_DATE_NOT_IDENTIFIABLE"

    b64["status"] = "NOT_APPLICABLE_OR_SOTP_NOT_CALCULATED"
    not_applicable = _run(b64, evidence)
    assert not_applicable["status"] == "NOT_APPLICABLE_SOTP_NOT_SELECTED"
    assert not_applicable["scenarios"] == {}

    b64["status"] = "BLOCKED_BY_B63"
    blocked = _run(b64, evidence)
    assert blocked["status"] == "BLOCKED_BY_B64"
    assert blocked["scenarios"] == {}


def test_b65_keeps_different_accounting_or_pe_period_basis_visible_as_distinct_dimensions():
    b64, evidence, _ = _fixtures()
    for name in ("bear", "base", "bull"):
        peer = b64["scenarios"][name]["segments"][0]["multiple_evidence_assessment"]["comparable_observations"][0]
        peer["peer_comparability_profile"]["pe_measurement_basis"] = "TTM reported P/E"
        row = peer["dimension_assessments"]["pe_measurement_basis"]
        row["peer_value"] = "TTM reported P/E"
        row["comparison"] = "DIFFERENT"
        row["target_multiple_implication"] = "UNKNOWN"
        row["multiple_adjustment_treatment"] = "UNKNOWN"
        row["adjustment_rationale"] = ""
    result = _run(b64, evidence)
    peer = next(peer for peer in result["scenarios"]["base"]["segments"][0]["peers"] if peer["entity"] == "Peer A")
    assert peer["status"] == "PEER_COMPARABILITY_PARTIAL"
    assert "pe_measurement_basis" in peer["unknown_dimensions"]
