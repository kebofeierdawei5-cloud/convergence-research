from __future__ import annotations

"""B65 SOTP comparable-company comparability audit.

The module audits declared target/peer profiles and the evidence references
behind them. It never calculates a multiple premium/discount, peer average,
fair value, or a replacement terminal P/E.
"""

from datetime import date
from typing import Any, Mapping

B65_SCHEMA = "IIOS-B65-SOTP-COMPARABILITY-AUDIT-0.1"

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

_ALLOWED_COMPARISONS = {"SIMILAR", "DIFFERENT", "NOT_COMPARABLE", "UNKNOWN"}
_ALLOWED_IMPLICATIONS = {"TARGET_PREMIUM", "TARGET_DISCOUNT", "NEUTRAL", "UNKNOWN"}
_ALLOWED_TREATMENTS = {
    "SELECTED_PE_ADJUSTED",
    "NO_NUMERIC_ADJUSTMENT",
    "PEER_EXCLUDED",
    "UNKNOWN",
}
_GOOD_B64_STATUSES = {"ASSESSED_DIAGNOSTIC_ONLY", "PARTIAL"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _valid_date(value: Any) -> date | None:
    raw = _text(value)
    try:
        if len(raw) != 10:
            return None
        parsed = date.fromisoformat(raw)
        return parsed if parsed.isoformat() == raw else None
    except ValueError:
        return None


def _string_list(value: Any) -> tuple[list[str], bool]:
    if value is None:
        return [], True
    if not isinstance(value, list):
        return [], False
    return list(dict.fromkeys(_text(item) for item in value if _text(item))), True


def _audit_references(
    refs: list[str],
    *,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    measure_refs: set[str],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    issues: list[str] = []
    for ref in refs:
        if ref not in measure_refs:
            issues.append(f"COMPARABILITY_EVIDENCE_NOT_ATTACHED_TO_PE_MEASURE:{ref}")
            continue
        source = evidence_by_id.get(ref)
        if source is None:
            issues.append(f"COMPARABILITY_EVIDENCE_UNRESOLVED:{ref}")
            continue
        timing = str(source.get("time_status") or "UNKNOWN").upper()
        if timing != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED":
            issues.append(f"COMPARABILITY_EVIDENCE_NOT_CUTOFF_COMPATIBLE:{ref}:{timing}")
            continue
        sources.append({
            "source_id": ref,
            "title": source.get("title") or "UNKNOWN",
            "source_class": source.get("source_class") or "UNKNOWN",
            "known_at": source.get("known_at") or "UNKNOWN",
            "time_status": timing,
            "source_domain_class_status": source.get("source_domain_class_status") or "UNKNOWN",
        })
    return {
        "status": "RESOLVED_TIME_COMPATIBLE_ONLY_NOT_ADMITTED" if refs and not issues else (
            "NO_REFERENCES" if not refs else "UNRESOLVED_OR_NOT_CUTOFF_COMPATIBLE"
        ),
        "sources": sources,
        "issues": sorted(set(issues)),
    }


def _audit_one_dimension(
    dimension: str,
    *,
    target_profile: Mapping[str, Any],
    peer_profile: Mapping[str, Any],
    raw_assessment: Any,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    measure_refs: set[str],
) -> dict[str, Any]:
    assessment = raw_assessment if isinstance(raw_assessment, Mapping) else {}
    comparison = str(assessment.get("comparison") or "UNKNOWN").strip().upper()
    implication = str(assessment.get("target_multiple_implication") or "UNKNOWN").strip().upper()
    treatment = str(assessment.get("multiple_adjustment_treatment") or "UNKNOWN").strip().upper()
    target_value = _text(target_profile.get(dimension))
    peer_value = _text(peer_profile.get(dimension))
    declared_target = _text(assessment.get("target_value"))
    declared_peer = _text(assessment.get("peer_value"))
    rationale = _text(assessment.get("rationale"))
    adjustment_rationale = _text(assessment.get("adjustment_rationale"))
    refs, refs_shape_ok = _string_list(assessment.get("evidence_refs"))
    reference_audit = _audit_references(
        refs,
        evidence_by_id=evidence_by_id,
        measure_refs=measure_refs,
    )
    issues: list[str] = []
    if comparison not in _ALLOWED_COMPARISONS:
        issues.append(f"COMPARISON_STATUS_INVALID:{comparison}")
    if implication not in _ALLOWED_IMPLICATIONS:
        issues.append(f"TARGET_MULTIPLE_IMPLICATION_INVALID:{implication}")
    if treatment not in _ALLOWED_TREATMENTS:
        issues.append(f"MULTIPLE_ADJUSTMENT_TREATMENT_INVALID:{treatment}")
    if not refs_shape_ok:
        issues.append("DIMENSION_EVIDENCE_REFS_MUST_BE_LIST")
    if not target_value or not peer_value:
        issues.append("TARGET_OR_PEER_PROFILE_VALUE_MISSING")
    if declared_target != target_value or declared_peer != peer_value:
        issues.append("DIMENSION_ASSESSMENT_PROFILE_VALUE_MISMATCH")
    if not rationale:
        issues.append("DIMENSION_COMPARABILITY_RATIONALE_MISSING")
    if not refs:
        issues.append("DIMENSION_EVIDENCE_REFERENCES_MISSING")
    issues.extend(reference_audit["issues"])

    if comparison == "SIMILAR":
        if implication != "NEUTRAL":
            issues.append("SIMILAR_DIMENSION_MUST_HAVE_NEUTRAL_MULTIPLE_IMPLICATION")
        if treatment != "NO_NUMERIC_ADJUSTMENT":
            issues.append("SIMILAR_DIMENSION_MUST_NOT_CLAIM_NUMERIC_MULTIPLE_ADJUSTMENT")
    elif comparison == "DIFFERENT":
        if implication not in {"TARGET_PREMIUM", "TARGET_DISCOUNT", "NEUTRAL"}:
            issues.append("DIFFERENCE_DIRECTION_NOT_IDENTIFIABLE")
        if treatment not in {"SELECTED_PE_ADJUSTED", "NO_NUMERIC_ADJUSTMENT"}:
            issues.append("DIFFERENCE_ADJUSTMENT_TREATMENT_NOT_IDENTIFIABLE")
        if not adjustment_rationale:
            issues.append("DIFFERENCE_ADJUSTMENT_RATIONALE_MISSING")
    elif comparison == "NOT_COMPARABLE":
        if treatment != "PEER_EXCLUDED":
            issues.append("NOT_COMPARABLE_DIMENSION_REQUIRES_PEER_EXCLUSION")
        if implication not in {"UNKNOWN", "NEUTRAL"}:
            issues.append("EXCLUDED_PEER_MUST_NOT_CLAIM_TARGET_PREMIUM_OR_DISCOUNT")
        if not adjustment_rationale:
            issues.append("PEER_EXCLUSION_RATIONALE_MISSING")
    else:
        issues.append("DIMENSION_COMPARABILITY_UNKNOWN")

    complete = not issues and comparison in {"SIMILAR", "DIFFERENT"}
    excluded = comparison == "NOT_COMPARABLE" and not issues
    return {
        "dimension": dimension,
        "status": (
            "COMPARABILITY_REVIEW_COMPLETE" if complete else
            "PEER_EXCLUDED_FOR_DIMENSION" if excluded else
            "UNKNOWN_OR_INCOMPLETE"
        ),
        "comparison": comparison,
        "target_value": target_value or "UNKNOWN",
        "peer_value": peer_value or "UNKNOWN",
        "target_multiple_implication": implication,
        "multiple_adjustment_treatment": treatment,
        "rationale": rationale or "UNKNOWN",
        "adjustment_rationale": adjustment_rationale or "UNKNOWN",
        "evidence_refs": refs,
        "evidence_audit": reference_audit,
        "issues": sorted(set(issues)),
    }


def _audit_peer(
    peer: Mapping[str, Any],
    *,
    valuation_as_of_date: date,
    target_profile: Mapping[str, Any],
    measure_refs: set[str],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    entity = _text(peer.get("entity")) or "UNKNOWN"
    peer_as_of = _valid_date(peer.get("as_of_date"))
    peer_date_text = _text(peer.get("as_of_date")) or "UNKNOWN"
    issues: list[str] = []
    if peer_as_of is None:
        issues.append("COMPARABLE_VALUATION_DATE_INVALID")
        day_lag = None
        date_status = "UNKNOWN"
    elif peer_as_of > valuation_as_of_date:
        issues.append("COMPARABLE_VALUATION_DATE_AFTER_CASE_CUTOFF")
        day_lag = (valuation_as_of_date - peer_as_of).days
        date_status = "FUTURE_DATE_BLOCKED"
    else:
        day_lag = (valuation_as_of_date - peer_as_of).days
        date_status = "SAME_CUTOFF_DATE" if day_lag == 0 else "EARLIER_DATE_REQUIRES_EXPLICIT_REBASE"

    date_rationale = _text(peer.get("date_alignment_rationale"))
    if peer_as_of is not None and peer_as_of < valuation_as_of_date and not date_rationale:
        issues.append("EARLIER_COMPARABLE_DATE_REQUIRES_REBASE_RATIONALE")

    peer_profile = peer.get("peer_comparability_profile")
    if not isinstance(peer_profile, Mapping):
        peer_profile = {}
        issues.append("PEER_COMPARABILITY_PROFILE_MISSING")
    raw_dimensions = peer.get("dimension_assessments")
    if not isinstance(raw_dimensions, Mapping):
        raw_dimensions = {}
        issues.append("DIMENSION_ASSESSMENTS_MISSING")

    dimensions: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        item = _audit_one_dimension(
            dimension,
            target_profile=target_profile,
            peer_profile=peer_profile,
            raw_assessment=raw_dimensions.get(dimension),
            evidence_by_id=evidence_by_id,
            measure_refs=measure_refs,
        )
        dimensions.append(item)
        issues.extend(f"{dimension}:{issue}" for issue in item["issues"])

    extra_dimension_keys = sorted(set(raw_dimensions) - set(DIMENSIONS))
    if extra_dimension_keys:
        issues.append("UNRECOGNIZED_COMPARABILITY_DIMENSIONS:" + ",".join(extra_dimension_keys))

    complete_dimensions = sum(
        item["status"] == "COMPARABILITY_REVIEW_COMPLETE" for item in dimensions
    )
    excluded_dimensions = [
        item["dimension"] for item in dimensions
        if item["status"] == "PEER_EXCLUDED_FOR_DIMENSION"
    ]
    unknown_dimensions = [
        item["dimension"] for item in dimensions
        if item["status"] == "UNKNOWN_OR_INCOMPLETE"
    ]
    target_premium = [
        item["dimension"] for item in dimensions
        if item["target_multiple_implication"] == "TARGET_PREMIUM"
    ]
    target_discount = [
        item["dimension"] for item in dimensions
        if item["target_multiple_implication"] == "TARGET_DISCOUNT"
    ]
    neutral = [
        item["dimension"] for item in dimensions
        if item["target_multiple_implication"] == "NEUTRAL"
    ]

    all_dimensions_complete = complete_dimensions == len(DIMENSIONS)
    no_exclusion = not excluded_dimensions
    peer_eligible = (
        all_dimensions_complete
        and no_exclusion
        and not issues
        and peer_as_of is not None
        and peer_as_of <= valuation_as_of_date
    )
    peer_excluded = bool(excluded_dimensions)
    status = (
        "PEER_COMPARABILITY_COMPLETE" if peer_eligible else
        "PEER_EXCLUDED_NOT_COMPARABLE" if peer_excluded else
        "PEER_COMPARABILITY_PARTIAL"
    )
    return {
        "entity": entity,
        "as_of_date": peer_date_text,
        "days_before_case_cutoff": day_lag,
        "date_alignment_status": date_status,
        "date_alignment_rationale": date_rationale or "UNKNOWN",
        "status": status,
        "eligible_for_candidate_peer_set": peer_eligible,
        "observed_pe_x": peer.get("observed_pe_x"),
        "evidence_ref": peer.get("evidence_ref") or "UNKNOWN",
        "comparability_adjustment_summary": peer.get("comparability_adjustment") or "UNKNOWN",
        "dimension_review": dimensions,
        "dimension_counts": {
            "complete": complete_dimensions,
            "required": len(DIMENSIONS),
            "excluded": len(excluded_dimensions),
            "unknown_or_incomplete": len(unknown_dimensions),
        },
        "directional_dimension_summary": {
            "target_premium_dimensions": target_premium,
            "target_discount_dimensions": target_discount,
            "neutral_dimensions": neutral,
        },
        "excluded_dimensions": excluded_dimensions,
        "unknown_dimensions": unknown_dimensions,
        "issues": sorted(set(issues)),
    }


def build_sotp_comparability_audit(
    *,
    evidence_grade_assessment: Mapping[str, Any],
    evidence_register: list[dict[str, Any]],
    valuation_as_of_date: Any,
) -> dict[str, Any]:
    """Audit peer comparability profiles after B64; do not set or adjust P/Es."""
    cutoff = _valid_date(valuation_as_of_date)
    result: dict[str, Any] = {
        "schema_version": B65_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "COMPARABILITY_AUDIT_ONLY_NO_AUTOMATIC_MULTIPLE_ADJUSTMENT",
        "valuation_as_of_date": cutoff.isoformat() if cutoff else "UNKNOWN",
        "required_dimensions": list(DIMENSIONS),
        "scenarios": {},
        "summary": "不对可比公司或终值倍数做自动选择、加权、溢价/折价计算或公平价值结论。",
        "selected_pe_modified": False,
        "sotp_input_modified": False,
        "valuation_values_modified": False,
        "b64_grade_modified": False,
        "external_mie_modified": False,
        "decision_authority": False,
        "limitations": [
            "可比性审计依赖结构化目标公司/分部画像、同行画像与维度判断；它不自动读取或验证原始披露内容。",
            "TARGET_PREMIUM / TARGET_DISCOUNT 是研究者对差异方向的定性判断，不是数值倍数调整或回报预测。",
            "即使同业样本全部通过结构化比较，也不代表同行样本选择正确、估值口径完全一致或所选 P/E 公允。",
            "不同差异不做加总，不生成可比性分数，不对多个差异进行机械平均或加权。",
            "估值日期早于案例截止日时，必须提供明确的时点重估说明；晚于截止日的同行观察直接阻断。",
            "没有资料、没有引用或口径不一致时保持 UNKNOWN / PARTIAL，不推测目标或同行的 ROIC、杠杆、现金流或会计口径。",
        ],
    }

    if cutoff is None:
        result["status"] = "VALUATION_AS_OF_DATE_NOT_IDENTIFIABLE"
        result["issues"] = ["VALUATION_AS_OF_DATE_MUST_BE_ISO_DATE"]
        return result

    b64_status = str(evidence_grade_assessment.get("status") or "UNKNOWN").upper()
    if b64_status == "NOT_APPLICABLE_OR_SOTP_NOT_CALCULATED":
        result["status"] = "NOT_APPLICABLE_SOTP_NOT_SELECTED"
        return result
    if b64_status not in _GOOD_B64_STATUSES:
        result["status"] = "BLOCKED_BY_B64"
        result["b64_status"] = b64_status
        return result

    evidence_by_id = {
        str(row.get("source_id")): row
        for row in evidence_register
        if isinstance(row, Mapping) and row.get("source_id")
    }
    b64_scenarios = (
        evidence_grade_assessment.get("scenarios")
        if isinstance(evidence_grade_assessment.get("scenarios"), Mapping) else {}
    )
    scenario_statuses: list[str] = []

    for scenario_name in ("bear", "base", "bull"):
        b64_row = b64_scenarios.get(scenario_name) if isinstance(b64_scenarios.get(scenario_name), Mapping) else {}
        row: dict[str, Any] = {
            "scenario": scenario_name,
            "status": "NOT_IDENTIFIABLE",
            "segments": [],
            "issues": [],
        }
        b64_scenario_status = str(b64_row.get("status") or "UNKNOWN").upper()
        if b64_scenario_status not in _GOOD_B64_STATUSES:
            row["status"] = "BLOCKED_BY_B64_SCENARIO"
            row["issues"] = [f"B64_SCENARIO_NOT_ASSESSABLE:{b64_scenario_status}"]
            result["scenarios"][scenario_name] = row
            scenario_statuses.append(row["status"])
            continue

        for segment in b64_row.get("segments") or []:
            if not isinstance(segment, Mapping):
                continue
            multiple = segment.get("multiple_evidence_assessment")
            multiple = multiple if isinstance(multiple, Mapping) else {}
            segment_id = _text(segment.get("segment_id")) or "UNKNOWN"
            measure_refs, refs_ok = _string_list(multiple.get("measure_evidence_refs"))
            support_refs, support_refs_ok = _string_list(multiple.get("support_evidence_refs"))
            target_profile = multiple.get("target_comparability_profile")
            profile_issues: list[str] = []
            if not refs_ok or not support_refs_ok:
                profile_issues.append("P_EVIDENCE_REFERENCE_LIST_INVALID")
            if not isinstance(target_profile, Mapping):
                target_profile = {}
                profile_issues.append("TARGET_COMPARABILITY_PROFILE_MISSING")
            missing_target_dimensions = [
                dimension for dimension in DIMENSIONS
                if not _text(target_profile.get(dimension))
            ]
            if missing_target_dimensions:
                profile_issues.append("TARGET_PROFILE_DIMENSIONS_MISSING:" + ",".join(missing_target_dimensions))

            observations = multiple.get("comparable_observations")
            if not isinstance(observations, list):
                observations = []
                profile_issues.append("COMPARABLE_OBSERVATIONS_NOT_A_LIST")

            peers: list[dict[str, Any]] = []
            seen_entities: set[str] = set()
            duplicate_entities: set[str] = set()
            for peer in observations:
                if not isinstance(peer, Mapping):
                    profile_issues.append("COMPARABLE_OBSERVATION_NOT_AN_OBJECT")
                    continue
                entity = _text(peer.get("entity"))
                if not entity or entity in seen_entities:
                    duplicate_entities.add(entity or "UNKNOWN")
                    continue
                seen_entities.add(entity)
                peer_result = _audit_peer(
                    peer,
                    valuation_as_of_date=cutoff,
                    target_profile=target_profile,
                    measure_refs=set(measure_refs),
                    evidence_by_id=evidence_by_id,
                )
                peers.append(peer_result)
            if duplicate_entities:
                profile_issues.append("DUPLICATE_OR_UNKNOWN_PEER_ENTITY:" + ",".join(sorted(duplicate_entities)))

            eligible_count = sum(peer["eligible_for_candidate_peer_set"] for peer in peers)
            excluded_count = sum(peer["status"] == "PEER_EXCLUDED_NOT_COMPARABLE" for peer in peers)
            partial_count = sum(peer["status"] == "PEER_COMPARABILITY_PARTIAL" for peer in peers)
            if len(peers) < 2:
                profile_issues.append("FEWER_THAN_TWO_DISTINCT_PEER_OBSERVATIONS")
            if eligible_count < 2:
                profile_issues.append("FEWER_THAN_TWO_COMPARABILITY_COMPLETE_PEERS")
            support_ref_set = set(support_refs)
            if not support_ref_set.issubset(set(measure_refs)):
                profile_issues.append("B64_SUPPORT_REFERENCE_NOT_ATTACHED_TO_PE_MEASURE")

            segment_status = (
                "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
                if eligible_count >= 2 and partial_count == 0 and not profile_issues
                else "PEER_SET_INSUFFICIENTLY_COMPARABLE"
                if eligible_count < 2 and not partial_count
                else "PARTIAL"
            )
            row["segments"].append({
                "segment_id": segment_id,
                "segment_name": segment.get("segment_name") or "UNKNOWN",
                "selected_terminal_pe_x": segment.get("selected_terminal_pe_x"),
                "selected_pe_grade": multiple.get("grade") or "G5_UNKNOWN",
                "target_comparability_profile": {
                    key: _text(target_profile.get(key)) or "UNKNOWN"
                    for key in DIMENSIONS
                },
                "candidate_peer_count": len(peers),
                "eligible_peer_count": eligible_count,
                "excluded_peer_count": excluded_count,
                "partial_peer_count": partial_count,
                "peer_set_status": segment_status,
                "peers": peers,
                "issues": sorted(set(profile_issues)),
                "valuation_effect": "NONE; SELECTED_TERMINAL_PE_UNCHANGED",
            })
            row["issues"].extend(f"{segment_id}:{issue}" for issue in profile_issues)

        if not row["segments"]:
            row["issues"].append("NO_SEGMENT_MULTIPLE_ASSESSMENTS")
        partial_segments = sum(
            segment["peer_set_status"] != "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
            for segment in row["segments"]
        )
        row["status"] = "PARTIAL" if partial_segments or row["issues"] else "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
        row["summary"] = (
            "逐同行、逐维度展示可比性差异及其定性倍数含义；不计算数值溢价/折价，也不自动调整所选终值 P/E。"
        )
        result["scenarios"][scenario_name] = row
        scenario_statuses.append(row["status"])

    if scenario_statuses and all(
        status == "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
        for status in scenario_statuses
    ):
        result["status"] = "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED"
    elif any(status == "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED" for status in scenario_statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "PARTIAL" if scenario_statuses else "NOT_IDENTIFIABLE"

    result["peer_set_summary"] = {
        "scenarios_assessed": len(scenario_statuses),
        "scenario_count": 3,
        "status": result["status"],
        "selection_or_adjustment_authority": False,
    }
    return result
