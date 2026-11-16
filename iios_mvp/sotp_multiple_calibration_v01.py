from __future__ import annotations

"""B66 explicit terminal P/E calibration and scenario sensitivity.

Peer anchors are descriptive references only. All target-specific P/E adjustments
must be explicit analyst inputs that reconcile arithmetically to the selected
multiple. Nothing in this module modifies the SOTP valuation or decision.
"""

from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Any, Mapping

B66_SCHEMA = "IIOS-B66-SOTP-TERMINAL-MULTIPLE-CALIBRATION-0.1"
_ACCEPTED_B63 = {"CONDITIONAL_ATTRIBUTION_CALCULATED", "PARTIAL"}
_ACCEPTED_B65 = {
    "COMPARABILITY_REVIEW_COMPLETE_NOT_VALUATION_APPROVED",
    "PARTIAL",
}
_REQUIRED_BASIS_DIMENSIONS = (
    "accounting_basis",
    "earnings_reference_period",
    "pe_measurement_basis",
)
_ALLOWED_REFERENCE_METHODS = {
    "PEER_MEDIAN",
    "HISTORICAL_SELF_RANGE",
    "OTHER_EXPLICIT_REFERENCE",
    "NO_COMPARABLE_REFERENCE",
}
_ALLOWED_DIRECTIONS = {"TARGET_PREMIUM", "TARGET_DISCOUNT", "NEUTRAL"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _identifiable(value: Any) -> bool:
    candidate = _text(value)
    return bool(candidate) and candidate.upper() not in {
        "UNKNOWN", "N/A", "NA", "NONE", "NULL", "TBD",
        "NOT_IDENTIFIABLE", "UNSPECIFIED", "NOT_PROVIDED",
        "未知", "不详", "待补充", "待确认",
    }


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _close(a: Decimal, b: Decimal, tolerance: Decimal = Decimal("0.01")) -> bool:
    return abs(a - b) <= tolerance


def _list(value: Any) -> tuple[list[str], bool]:
    if value is None:
        return [], True
    if not isinstance(value, list):
        return [], False
    return list(dict.fromkeys(_text(item) for item in value if _text(item))), True


def _audit_refs(
    refs: list[str],
    *,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    measure_refs: set[str],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    issues: list[str] = []
    for ref in refs:
        if ref not in measure_refs:
            issues.append(f"REFERENCE_NOT_ATTACHED_TO_SELECTED_PE_MEASURE:{ref}")
            continue
        source = evidence_by_id.get(ref)
        if source is None:
            issues.append(f"REFERENCE_UNRESOLVED:{ref}")
            continue
        timing = str(source.get("time_status") or "UNKNOWN").upper()
        if timing != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED":
            issues.append(f"REFERENCE_NOT_CUTOFF_COMPATIBLE:{ref}:{timing}")
            continue
        sources.append({
            "source_id": ref,
            "title": source.get("title") or "UNKNOWN",
            "source_class": source.get("source_class") or "UNKNOWN",
            "known_at": source.get("known_at") or "UNKNOWN",
            "time_status": timing,
        })
    return {
        "status": "RESOLVED_TIME_COMPATIBLE_ONLY_NOT_ADMITTED" if refs and not issues else (
            "NO_REFERENCES" if not refs else "UNRESOLVED_OR_NOT_CUTOFF_COMPATIBLE"
        ),
        "sources": sources,
        "issues": sorted(set(issues)),
    }


def _peer_reference_band(
    b65_segment: Mapping[str, Any],
    *,
    target_profile: Mapping[str, Any],
) -> dict[str, Any]:
    peers = b65_segment.get("peers") if isinstance(b65_segment.get("peers"), list) else []
    eligible: list[dict[str, Any]] = []
    excluded_from_numeric_anchor: list[dict[str, Any]] = []
    for peer in peers:
        if not isinstance(peer, Mapping):
            continue
        if peer.get("status") != "PEER_COMPARABILITY_COMPLETE" or peer.get("eligible_for_candidate_peer_set") is not True:
            continue
        dimensions = peer.get("dimension_review") if isinstance(peer.get("dimension_review"), list) else []
        by_dimension = {
            str(item.get("dimension")): item
            for item in dimensions if isinstance(item, Mapping)
        }
        basis_reasons: list[str] = []
        for dimension in _REQUIRED_BASIS_DIMENSIONS:
            target = _text(target_profile.get(dimension))
            row = by_dimension.get(dimension)
            peer_value = _text(row.get("peer_value")) if isinstance(row, Mapping) else ""
            comparison = str(row.get("comparison") or "UNKNOWN").upper() if isinstance(row, Mapping) else "UNKNOWN"
            if not _identifiable(target) or not _identifiable(peer_value):
                basis_reasons.append(f"{dimension}:BASIS_VALUE_UNKNOWN")
            elif comparison != "SIMILAR" or peer_value != target:
                basis_reasons.append(f"{dimension}:BASIS_NOT_COMPARABLE:{comparison}")
        multiple = _decimal(peer.get("observed_pe_x"))
        if multiple is None or multiple <= 0:
            basis_reasons.append("PEER_MULTIPLE_NOT_POSITIVE_NUMERIC")
        if basis_reasons:
            excluded_from_numeric_anchor.append({
                "entity": peer.get("entity") or "UNKNOWN",
                "observed_pe_x": peer.get("observed_pe_x"),
                "reasons": basis_reasons,
            })
            continue
        eligible.append({
            "entity": peer.get("entity") or "UNKNOWN",
            "observed_pe_x": multiple,
            "as_of_date": peer.get("as_of_date") or "UNKNOWN",
            "evidence_ref": peer.get("evidence_ref") or "UNKNOWN",
        })

    eligible.sort(key=lambda row: row["observed_pe_x"])
    values = [row["observed_pe_x"] for row in eligible]
    if len(values) >= 2:
        median_value = Decimal(str(median(values)))
        return {
            "status": "SAME_BASIS_PEER_ANCHOR_IDENTIFIED",
            "peer_count": len(values),
            "peer_observations": [
                {
                    "entity": row["entity"],
                    "observed_pe_x": _fmt(row["observed_pe_x"]),
                    "as_of_date": row["as_of_date"],
                    "evidence_ref": row.get("evidence_ref") or "UNKNOWN",
                }
                for row in eligible
            ],
            "peer_reference_evidence_refs": sorted({
                str(row.get("evidence_ref"))
                for row in eligible
                if row.get("evidence_ref") and row.get("evidence_ref") != "UNKNOWN"
            }),
            "minimum_pe_x": _fmt(min(values)),
            "median_pe_x": _fmt(median_value),
            "maximum_pe_x": _fmt(max(values)),
            "basis_dimensions_required_to_match": list(_REQUIRED_BASIS_DIMENSIONS),
            "excluded_from_numeric_anchor": excluded_from_numeric_anchor,
            "limitations": [
                "仅使用 B65 完整可比且会计口径、盈利期间、P/E 口径均与目标分部一致的同行观察。",
                "中位数/区间只是同口径样本的描述统计，不证明同行选择代表性、目标公司合理倍数或公允价值。",
            ],
        }
    return {
        "status": "SAME_BASIS_PEER_ANCHOR_NOT_IDENTIFIABLE",
        "peer_count": len(values),
        "peer_observations": [
            {
                "entity": row["entity"],
                "observed_pe_x": _fmt(row["observed_pe_x"]),
                "as_of_date": row["as_of_date"],
            }
            for row in eligible
        ],
        "minimum_pe_x": _fmt(min(values)) if values else None,
        "median_pe_x": None,
        "maximum_pe_x": _fmt(max(values)) if values else None,
        "basis_dimensions_required_to_match": list(_REQUIRED_BASIS_DIMENSIONS),
        "excluded_from_numeric_anchor": excluded_from_numeric_anchor,
        "limitations": [
            "同口径、完整可比同行少于两家；不计算 peer median 或可用于选倍数的样本区间。",
        ],
    }


def _audit_bridge(
    raw_bridge: Any,
    *,
    selected_pe: Decimal,
    multiple_data_class: str,
    measure_refs: set[str],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    peer_anchor: Mapping[str, Any],
    b65_segment: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw_bridge, Mapping):
        return {
            "status": "NOT_IDENTIFIABLE",
            "reference_method": "UNKNOWN",
            "reference_multiple_x": None,
            "adjustments": [],
            "issues": ["SELECTED_MULTIPLE_BRIDGE_MISSING"],
            "limitations": ["没有显式终值 P/E 论证桥；不从 P/E 数值或公司标签反推理由。"],
        }

    method = str(raw_bridge.get("reference_method") or "UNKNOWN").strip().upper()
    description = _text(raw_bridge.get("reference_description"))
    explanation = _text(raw_bridge.get("selected_multiple_explanation"))
    issues: list[str] = []
    if multiple_data_class != "ANALYST_ASSUMPTION":
        issues.append(f"SELECTED_TERMINAL_PE_MUST_BE_ANALYST_ASSUMPTION:{multiple_data_class}")
    if method not in _ALLOWED_REFERENCE_METHODS:
        issues.append(f"REFERENCE_METHOD_INVALID:{method}")
    if not _identifiable(explanation):
        issues.append("SELECTED_MULTIPLE_EXPLANATION_MISSING")

    if method == "NO_COMPARABLE_REFERENCE" and peer_anchor.get("status") == "SAME_BASIS_PEER_ANCHOR_IDENTIFIED":
        issues.append("NO_COMPARABLE_REFERENCE_CONFLICTS_WITH_IDENTIFIED_SAME_BASIS_PEERS")

    if method == "PEER_MEDIAN":
        reference = _decimal((peer_anchor or {}).get("median_pe_x"))
        if reference is None:
            issues.append("SAME_BASIS_PEER_MEDIAN_NOT_IDENTIFIABLE")
        if raw_bridge.get("reference_multiple_x") not in (None, ""):
            declared = _decimal(raw_bridge.get("reference_multiple_x"))
            if declared is None or reference is None or not _close(declared, reference):
                issues.append("DECLARED_PEER_MEDIAN_DIFFERS_FROM_LOCAL_RECALCULATION")
    elif method in {"HISTORICAL_SELF_RANGE", "OTHER_EXPLICIT_REFERENCE"}:
        reference = _decimal(raw_bridge.get("reference_multiple_x"))
        if reference is None or reference <= 0:
            issues.append("EXPLICIT_REFERENCE_MULTIPLE_NOT_POSITIVE_NUMERIC")
        if not _identifiable(description):
            issues.append("EXPLICIT_REFERENCE_DESCRIPTION_MISSING")
    else:
        reference = None
        if method == "NO_COMPARABLE_REFERENCE" and not _identifiable(description):
            issues.append("NO_COMPARABLE_REFERENCE_EXPLANATION_MISSING")

    reference_refs, refs_ok = _list(raw_bridge.get("reference_evidence_refs"))
    if not refs_ok:
        issues.append("REFERENCE_EVIDENCE_REFS_MUST_BE_LIST")
    if method in {"HISTORICAL_SELF_RANGE", "OTHER_EXPLICIT_REFERENCE"} and not reference_refs:
        issues.append("EXPLICIT_REFERENCE_EVIDENCE_REFS_REQUIRED")
    ref_audit = _audit_refs(
        reference_refs,
        evidence_by_id=evidence_by_id,
        measure_refs=measure_refs,
    )
    issues.extend(ref_audit["issues"])

    adjustments_raw = raw_bridge.get("adjustments")
    adjustments: list[dict[str, Any]] = []
    seen_dimensions: set[str] = set()
    valid_adjustment_sum = Decimal("0")
    if not isinstance(adjustments_raw, list):
        issues.append("MULTIPLE_ADJUSTMENTS_MUST_BE_LIST")
        adjustments_raw = []
    if method == "NO_COMPARABLE_REFERENCE" and adjustments_raw:
        issues.append("ADJUSTMENTS_WITHOUT_NUMERIC_REFERENCE_NOT_RECONCILABLE")

    b65_peer_directions: dict[str, set[str]] = {}
    b65_peer_dimension_refs: dict[tuple[str, str], set[str]] = {}
    anchor_entities = {
        str(item.get("entity"))
        for item in (peer_anchor.get("peer_observations") or [])
        if isinstance(item, Mapping) and item.get("entity")
    }
    for peer in b65_segment.get("peers") or []:
        if not isinstance(peer, Mapping) or peer.get("status") != "PEER_COMPARABILITY_COMPLETE":
            continue
        if peer_anchor.get("status") == "SAME_BASIS_PEER_ANCHOR_IDENTIFIED" and str(peer.get("entity")) not in anchor_entities:
            continue
        for dimension in peer.get("dimension_review") or []:
            if not isinstance(dimension, Mapping):
                continue
            key = str(dimension.get("dimension") or "")
            direction = str(dimension.get("target_multiple_implication") or "UNKNOWN").upper()
            if key and direction in _ALLOWED_DIRECTIONS:
                b65_peer_directions.setdefault(key, set()).add(direction)
                dimension_refs, refs_shape_ok = _list(dimension.get("evidence_refs"))
                if refs_shape_ok:
                    b65_peer_dimension_refs.setdefault((key, direction), set()).update(dimension_refs)

    for index, raw in enumerate(adjustments_raw, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"ADJUSTMENT_ROW_NOT_OBJECT:{index}")
            continue
        dimension = _text(raw.get("dimension"))
        direction = str(raw.get("direction") or "UNKNOWN").strip().upper()
        amount = _decimal(raw.get("adjustment_x"))
        rationale = _text(raw.get("rationale"))
        refs, refs_shape_ok = _list(raw.get("evidence_refs"))
        if not _identifiable(dimension):
            issues.append(f"ADJUSTMENT_DIMENSION_MISSING:{index}")
        if dimension in seen_dimensions:
            issues.append(f"DUPLICATE_ADJUSTMENT_DIMENSION:{dimension}")
        seen_dimensions.add(dimension)
        if direction not in _ALLOWED_DIRECTIONS:
            issues.append(f"ADJUSTMENT_DIRECTION_INVALID:{dimension or index}")
        if amount is None:
            issues.append(f"ADJUSTMENT_AMOUNT_NOT_NUMERIC:{dimension or index}")
        elif direction == "TARGET_PREMIUM" and amount <= 0:
            issues.append(f"PREMIUM_ADJUSTMENT_MUST_BE_POSITIVE:{dimension}")
        elif direction == "TARGET_DISCOUNT" and amount >= 0:
            issues.append(f"DISCOUNT_ADJUSTMENT_MUST_BE_NEGATIVE:{dimension}")
        elif direction == "NEUTRAL" and amount != 0:
            issues.append(f"NEUTRAL_ADJUSTMENT_MUST_BE_ZERO:{dimension}")
        supported_directions = b65_peer_directions.get(dimension, set())
        if {"TARGET_PREMIUM", "TARGET_DISCOUNT"}.issubset(supported_directions):
            issues.append(f"B65_DIMENSION_DIRECTION_CONFLICT:{dimension}")
        if direction in _ALLOWED_DIRECTIONS and dimension and direction not in supported_directions:
            issues.append(f"ADJUSTMENT_DIRECTION_NOT_SUPPORTED_BY_B65:{dimension}:{direction}")
        if not _identifiable(rationale):
            issues.append(f"ADJUSTMENT_RATIONALE_MISSING:{dimension or index}")
        if not refs_shape_ok:
            issues.append(f"ADJUSTMENT_EVIDENCE_REFS_MUST_BE_LIST:{dimension or index}")
        if not refs:
            issues.append(f"ADJUSTMENT_EVIDENCE_REFS_REQUIRED:{dimension or index}")
        ref_check = _audit_refs(refs, evidence_by_id=evidence_by_id, measure_refs=measure_refs)
        issues.extend(ref_check["issues"])
        dimension_support_refs = b65_peer_dimension_refs.get((dimension, direction), set())
        if refs and not (set(refs) & dimension_support_refs):
            issues.append(f"ADJUSTMENT_EVIDENCE_NOT_TIED_TO_B65_DIMENSION:{dimension}:{direction}")
        if amount is not None:
            valid_adjustment_sum += amount
        adjustments.append({
            "dimension": dimension or "UNKNOWN",
            "direction": direction,
            "adjustment_x": _fmt(amount),
            "rationale": rationale or "UNKNOWN",
            "evidence_refs": refs,
            "evidence_audit": ref_check,
        })

    calculated_selected = reference + valid_adjustment_sum if reference is not None else None
    residual = selected_pe - calculated_selected if calculated_selected is not None else None
    if calculated_selected is not None and not _close(calculated_selected, selected_pe):
        issues.append("REFERENCE_PLUS_EXPLICIT_ADJUSTMENTS_DO_NOT_RECONCILE_TO_SELECTED_PE")

    bridge_complete = (
        not issues
        and calculated_selected is not None
        and method in {"PEER_MEDIAN", "HISTORICAL_SELF_RANGE", "OTHER_EXPLICIT_REFERENCE"}
    )
    status = (
        "MULTIPLE_BRIDGE_RECONCILED"
        if bridge_complete else
        "NO_COMPARABLE_REFERENCE_ASSUMPTION_ONLY"
        if method == "NO_COMPARABLE_REFERENCE" and not issues else
        "PARTIAL"
    )
    return {
        "status": status,
        "reference_method": method,
        "reference_description": description or "UNKNOWN",
        "reference_multiple_x": _fmt(reference),
        "reference_evidence_refs": reference_refs,
        "reference_evidence_audit": ref_audit,
        "adjustments": adjustments,
        "explicit_adjustment_sum_x": _fmt(valid_adjustment_sum),
        "calculated_selected_pe_x": _fmt(calculated_selected),
        "operator_selected_pe_x": _fmt(selected_pe),
        "reconciliation_residual_x": _fmt(residual),
        "selected_multiple_explanation": explanation or "UNKNOWN",
        "issues": sorted(set(issues)),
        "limitations": [
            "所有调整倍数均为分析师显式输入；B66 不从 ROIC、成长率、周期、风险或质量标签自动推导数值。",
            "定性溢价/折价方向不能替代调整幅度依据；每项调整必须独立解释并引用截止时点兼容来源。",
            "算术闭合只证明输入桥接到选定 P/E，不证明选定倍数合理或公允。",
        ],
    }


def _audit_range(
    raw_range: Any,
    *,
    selected_pe: Decimal,
    measure_refs: set[str],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(raw_range, Mapping):
        return {
            "status": "NOT_IDENTIFIABLE",
            "lower_bound_pe_x": None,
            "upper_bound_pe_x": None,
            "issues": ["SELECTED_MULTIPLE_RANGE_MISSING"],
        }
    data_class = str(raw_range.get("data_class") or "UNKNOWN").strip().upper()
    lower = _decimal(raw_range.get("lower_bound_pe_x"))
    upper = _decimal(raw_range.get("upper_bound_pe_x"))
    basis = _text(raw_range.get("basis"))
    downside = _text(raw_range.get("downside_rationale"))
    upside = _text(raw_range.get("upside_rationale"))
    refs, refs_ok = _list(raw_range.get("evidence_refs"))
    ref_audit = _audit_refs(refs, evidence_by_id=evidence_by_id, measure_refs=measure_refs)
    issues = list(ref_audit["issues"])
    if data_class != "ANALYST_ASSUMPTION":
        issues.append("MULTIPLE_RANGE_MUST_BE_ANALYST_ASSUMPTION")
    if lower is None or upper is None or lower <= 0 or upper <= 0:
        issues.append("MULTIPLE_RANGE_BOUNDS_MUST_BE_POSITIVE_NUMERIC")
    elif lower > upper:
        issues.append("MULTIPLE_RANGE_LOWER_EXCEEDS_UPPER")
    elif not (lower <= selected_pe <= upper):
        issues.append("SELECTED_PE_OUTSIDE_ANALYST_RANGE")
    if not _identifiable(basis):
        issues.append("MULTIPLE_RANGE_BASIS_MISSING")
    if not _identifiable(downside):
        issues.append("MULTIPLE_RANGE_DOWNSIDE_RATIONALE_MISSING")
    if not _identifiable(upside):
        issues.append("MULTIPLE_RANGE_UPSIDE_RATIONALE_MISSING")
    if not refs_ok:
        issues.append("MULTIPLE_RANGE_EVIDENCE_REFS_MUST_BE_LIST")
    if not refs:
        issues.append("MULTIPLE_RANGE_EVIDENCE_REFS_REQUIRED")

    return {
        "status": "RANGE_INPUT_COMPLETE_NOT_PROBABILITY_INTERVAL" if not issues else "PARTIAL",
        "data_class": data_class,
        "lower_bound_pe_x": _fmt(lower),
        "selected_pe_x": _fmt(selected_pe),
        "upper_bound_pe_x": _fmt(upper),
        "basis": basis or "UNKNOWN",
        "downside_rationale": downside or "UNKNOWN",
        "upside_rationale": upside or "UNKNOWN",
        "evidence_refs": refs,
        "evidence_audit": ref_audit,
        "issues": sorted(set(issues)),
        "limitations": [
            "该区间是分析师输入的估值敏感性边界，不是统计置信区间、目标价承诺或概率分布。",
        ],
    }


def build_sotp_multiple_calibration_assessment(
    *,
    sotp_valuation: Mapping[str, Any],
    evidence_register: list[dict[str, Any]],
    valuation_gap_attribution: Mapping[str, Any],
    comparable_company_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Build explicit per-segment terminal P/E bridge and valuation sensitivity."""
    result: dict[str, Any] = {
        "schema_version": B66_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "EXPLICIT_ANALYST_MULTIPLE_CALIBRATION_AND_SENSITIVITY_ONLY",
        "scenarios": {},
        "selected_pes_modified": False,
        "sotp_values_modified": False,
        "b63_modified": False,
        "b64_modified": False,
        "b65_modified": False,
        "external_mie_modified": False,
        "decision_authority": False,
        "limitations": [
            "同行估值锚只从 B65 完整可比且会计口径、盈利期间、P/E 测量口径与目标一致的同行中计算描述性统计。",
            "选定 P/E 的差异调整必须由分析师逐项填写数值、方向、理由及证据；系统不从经营指标自动换算 P/E。",
            "Required Return 的 Required P/E 来自 B63 全分部 B4 盈利向量与统一倍数缩放假设，是组合敏感性，不是单个分部的公允倍数。",
            "低/选定/高 P/E 区间是分析师敏感性假设，不是概率置信区间。",
            "估值敏感性不修改 SOTP、B63、MIE、expectation_gap、15% 年化回报门槛、目标入场价、组合约束或 Decision。",
        ],
    }

    if (
        str(sotp_valuation.get("status") or "").upper() != "CALCULATED"
        or sotp_valuation.get("selected_for_primary_model") is not True
    ):
        result["status"] = "NOT_APPLICABLE_SOTP_NOT_SELECTED"
        return result

    b63_status = str(valuation_gap_attribution.get("status") or "UNKNOWN").upper()
    b65_status = str(comparable_company_audit.get("status") or "UNKNOWN").upper()
    if b63_status not in _ACCEPTED_B63:
        result["status"] = "BLOCKED_BY_B63"
        result["b63_status"] = b63_status
        return result
    if b65_status not in _ACCEPTED_B65:
        result["status"] = "BLOCKED_BY_B65"
        result["b65_status"] = b65_status
        return result

    evidence_by_id = {
        str(row.get("source_id")): row
        for row in evidence_register
        if isinstance(row, Mapping) and row.get("source_id")
    }
    sotp_scenarios = sotp_valuation.get("scenarios") if isinstance(sotp_valuation.get("scenarios"), Mapping) else {}
    b63_scenarios = valuation_gap_attribution.get("scenarios") if isinstance(valuation_gap_attribution.get("scenarios"), Mapping) else {}
    b65_scenarios = comparable_company_audit.get("scenarios") if isinstance(comparable_company_audit.get("scenarios"), Mapping) else {}
    scenario_statuses: list[str] = []

    for scenario_name in ("bear", "base", "bull"):
        sotp_row = sotp_scenarios.get(scenario_name) if isinstance(sotp_scenarios.get(scenario_name), Mapping) else {}
        b63_row = b63_scenarios.get(scenario_name) if isinstance(b63_scenarios.get(scenario_name), Mapping) else {}
        b65_row = b65_scenarios.get(scenario_name) if isinstance(b65_scenarios.get(scenario_name), Mapping) else {}
        row: dict[str, Any] = {
            "scenario": scenario_name,
            "status": "NOT_IDENTIFIABLE",
            "segments": [],
            "issues": [],
            "aggregate_sensitivity": {"status": "NOT_IDENTIFIABLE"},
        }
        if str(b63_row.get("status") or "UNKNOWN").upper() not in _ACCEPTED_B63:
            row["status"] = "BLOCKED_BY_B63_SCENARIO"
            row["issues"].append("B63_SCENARIO_NOT_RECONCILED")
            result["scenarios"][scenario_name] = row
            scenario_statuses.append(row["status"])
            continue
        if str(b65_row.get("status") or "UNKNOWN").upper() not in _ACCEPTED_B65:
            row["status"] = "BLOCKED_BY_B65_SCENARIO"
            row["issues"].append("B65_SCENARIO_NOT_ASSESSABLE")
            result["scenarios"][scenario_name] = row
            scenario_statuses.append(row["status"])
            continue

        sotp_segments = sotp_row.get("segments") if isinstance(sotp_row.get("segments"), list) else []
        b65_segments = b65_row.get("segments") if isinstance(b65_row.get("segments"), list) else []
        b63_multiple = b63_row.get("multiple_attribution") if isinstance(b63_row.get("multiple_attribution"), Mapping) else {}
        b63_required_rows = b63_multiple.get("required_common_pe_by_segment") if isinstance(b63_multiple.get("required_common_pe_by_segment"), list) else []
        required_pe_by_id = {
            str(item.get("segment_id")): item
            for item in b63_required_rows if isinstance(item, Mapping)
        }
        b65_by_id = {
            str(item.get("segment_id")): item
            for item in b65_segments if isinstance(item, Mapping)
        }
        segment_ids = {
            str(item.get("segment_id"))
            for item in sotp_segments if isinstance(item, Mapping)
        }
        if not segment_ids or segment_ids != set(b65_by_id):
            row["issues"].append("SOTP_VS_B65_SEGMENT_UNIVERSE_MISMATCH")
        if b63_required_rows and set(required_pe_by_id) != segment_ids:
            row["issues"].append("SOTP_VS_B63_REQUIRED_PE_SEGMENT_UNIVERSE_MISMATCH")

        aggregate_low_pool = Decimal("0")
        aggregate_selected_pool = Decimal("0")
        aggregate_high_pool = Decimal("0")
        all_ranges_complete = bool(segment_ids) and not row["issues"]
        segment_rows: list[dict[str, Any]] = []

        for segment in sotp_segments:
            if not isinstance(segment, Mapping):
                continue
            segment_id = str(segment.get("segment_id") or "")
            profit_measure = segment.get("attributable_net_profit_cny") if isinstance(segment.get("attributable_net_profit_cny"), Mapping) else {}
            multiple_measure = segment.get("pe_multiple_x") if isinstance(segment.get("pe_multiple_x"), Mapping) else {}
            profit = _decimal(profit_measure)
            selected_pe = _decimal(multiple_measure)
            measure_refs, refs_ok = _list(multiple_measure.get("evidence_refs"))
            support = multiple_measure.get("support_assessment") if isinstance(multiple_measure.get("support_assessment"), Mapping) else {}
            if not refs_ok:
                measure_refs = []
                row["issues"].append(f"PE_EVIDENCE_REFS_INVALID:{segment_id}")
            if profit is None or profit < 0 or selected_pe is None or selected_pe <= 0:
                row["issues"].append(f"SEGMENT_PROFIT_OR_PE_NOT_IDENTIFIABLE:{segment_id}")
                all_ranges_complete = False
                continue

            b65_segment = b65_by_id.get(segment_id) if isinstance(b65_by_id.get(segment_id), Mapping) else {}
            target_profile = b65_segment.get("target_comparability_profile") if isinstance(b65_segment.get("target_comparability_profile"), Mapping) else {}
            b65_selected_pe = _decimal(b65_segment.get("selected_terminal_pe_x"))
            if b65_selected_pe is None or not _close(b65_selected_pe, selected_pe):
                row["issues"].append(f"B65_SELECTED_PE_VS_SOTP_INPUT_MISMATCH:{segment_id}")
            peer_anchor = _peer_reference_band(
                b65_segment,
                target_profile=target_profile,
            )
            bridge = _audit_bridge(
                support.get("selected_multiple_bridge"),
                selected_pe=selected_pe,
                multiple_data_class=str(multiple_measure.get("data_class") or "UNKNOWN").strip().upper(),
                measure_refs=set(measure_refs),
                evidence_by_id=evidence_by_id,
                peer_anchor=peer_anchor,
                b65_segment=b65_segment,
            )
            multiple_range = _audit_range(
                support.get("selected_multiple_range"),
                selected_pe=selected_pe,
                measure_refs=set(measure_refs),
                evidence_by_id=evidence_by_id,
            )

            required_row = required_pe_by_id.get(segment_id) if isinstance(required_pe_by_id.get(segment_id), Mapping) else {}
            required_pe = _decimal(required_row.get("required_pe_under_common_scale_x"))
            b63_selected_pe = _decimal(required_row.get("selected_sotp_pe_x"))
            if required_row and (b63_selected_pe is None or not _close(b63_selected_pe, selected_pe)):
                row["issues"].append(f"B63_SELECTED_PE_VS_SOTP_INPUT_MISMATCH:{segment_id}")
            hurdle_gap = required_pe - selected_pe if required_pe is not None else None
            hurdle_gap_pct = (required_pe / selected_pe - Decimal("1")) * Decimal("100") if required_pe is not None else None

            low_pe = _decimal(multiple_range.get("lower_bound_pe_x"))
            high_pe = _decimal(multiple_range.get("upper_bound_pe_x"))
            range_valid = multiple_range.get("status") == "RANGE_INPUT_COMPLETE_NOT_PROBABILITY_INTERVAL"
            if range_valid and low_pe is not None and high_pe is not None:
                low_segment_value = profit * low_pe
                selected_segment_value = profit * selected_pe
                high_segment_value = profit * high_pe
                aggregate_low_pool += low_segment_value
                aggregate_selected_pool += selected_segment_value
                aggregate_high_pool += high_segment_value
            else:
                all_ranges_complete = False
                low_segment_value = selected_segment_value = high_segment_value = None

            anchor_median = _decimal(peer_anchor.get("median_pe_x"))
            premium_discount_pct = (
                (selected_pe / anchor_median - Decimal("1")) * Decimal("100")
                if anchor_median is not None and anchor_median > 0 else None
            )
            segment_rows.append({
                "segment_id": segment_id,
                "segment_name": segment.get("segment_name") or "UNKNOWN",
                "normalized_parent_attributable_profit_cny": _fmt(profit),
                "selected_terminal_pe_x": _fmt(selected_pe),
                "selected_pe_basis": multiple_measure.get("basis") or "UNKNOWN",
                "selected_pe_data_class": multiple_measure.get("data_class") or "UNKNOWN",
                "selected_pe_evidence_refs": measure_refs,
                "same_basis_peer_reference": peer_anchor,
                "selected_pe_vs_peer_median": {
                    "difference_x": _fmt(selected_pe - anchor_median) if anchor_median is not None else None,
                    "premium_discount_pct": _fmt(premium_discount_pct),
                    "interpretation": "DESCRIPTIVE_SELECTED_PE_VS_SAME_BASIS_PEER_MEDIAN_NOT_FAIR_VALUE",
                },
                "explicit_selected_multiple_bridge": bridge,
                "analyst_multiple_range": multiple_range,
                "b63_required_common_pe_sensitivity": {
                    "required_common_pe_x": _fmt(required_pe),
                    "selected_pe_x": _fmt(selected_pe),
                    "selected_minus_required_pe_x": _fmt(selected_pe - required_pe) if required_pe is not None else None,
                    "additional_pe_required_x": _fmt(hurdle_gap) if hurdle_gap is not None else None,
                    "additional_pe_required_pct_of_selected": _fmt(hurdle_gap_pct) if hurdle_gap_pct is not None else None,
                    "interpretation": (
                        "B63_PARALLEL_COMMON_SCALE_SENSITIVITY_BASED_ON_FULL_B4_EARNINGS_VECTOR; "
                        "NOT_STANDALONE_FAIR_PE_FOR_THIS_SEGMENT"
                    ),
                },
                "segment_equity_value_sensitivity_cny": {
                    "lower_range": _fmt(low_segment_value),
                    "selected": _fmt(selected_segment_value),
                    "upper_range": _fmt(high_segment_value),
                    "status": "CALCULATED" if range_valid else "NOT_IDENTIFIABLE",
                },
                "issues": sorted(set(
                    bridge.get("issues", []) + multiple_range.get("issues", [])
                )),
            })

        row["segments"] = segment_rows
        for b65_id in set(b65_by_id) - segment_ids:
            row["issues"].append(f"UNEXPECTED_B65_SEGMENT:{b65_id}")

        if all_ranges_complete and len(segment_rows) == len(segment_ids):
            parent = sotp_row.get("parent_level_adjustments") if isinstance(sotp_row.get("parent_level_adjustments"), Mapping) else {}
            central_cost = _decimal(parent.get("capitalized_central_cost_value_cny"))
            net_cash = _decimal(parent.get("net_cash_debt_cny"))
            other = _decimal(parent.get("other_adjustments_cny"))
            shares = _decimal(sotp_row.get("diluted_shares"))
            selected_equity = _decimal(sotp_row.get("total_equity_value_cny"))
            selected_segment_pool_declared = _decimal(sotp_row.get("segment_equity_value_cny"))
            selected_per_share = _decimal(sotp_row.get("terminal_value_per_share"))
            if any(value is None for value in (central_cost, net_cash, other, shares, selected_equity, selected_segment_pool_declared, selected_per_share)) or shares <= 0:
                row["aggregate_sensitivity"] = {
                    "status": "NOT_IDENTIFIABLE",
                    "issues": ["SOTP_PARENT_ADJUSTMENT_OR_SHARE_INPUT_MISSING"],
                }
            else:
                recalculated_selected_equity = aggregate_selected_pool - central_cost + net_cash + other
                selected_pool_mismatch = not _close(aggregate_selected_pool, selected_segment_pool_declared)
                if selected_pool_mismatch or not _close(recalculated_selected_equity, selected_equity) or not _close(recalculated_selected_equity / shares, selected_per_share):
                    aggregate_issues = []
                    if selected_pool_mismatch:
                        aggregate_issues.append("SELECTED_SOTP_SEGMENT_POOL_DOES_NOT_RECONCILE")
                        row["issues"].append("SELECTED_SOTP_SEGMENT_POOL_DOES_NOT_RECONCILE")
                    if not _close(recalculated_selected_equity, selected_equity) or not _close(recalculated_selected_equity / shares, selected_per_share):
                        aggregate_issues.append("SELECTED_SOTP_EQUITY_OR_PER_SHARE_DOES_NOT_RECONCILE")
                        row["issues"].append("SELECTED_SOTP_EQUITY_OR_PER_SHARE_DOES_NOT_RECONCILE")
                    row["aggregate_sensitivity"] = {
                        "status": "RECONCILIATION_MISMATCH",
                        "issues": aggregate_issues,
                    }
                else:
                    lower_equity = aggregate_low_pool - central_cost + net_cash + other
                    upper_equity = aggregate_high_pool - central_cost + net_cash + other
                    row["aggregate_sensitivity"] = {
                        "status": "CONDITIONAL_ALL_SEGMENT_MULTIPLE_RANGE_SENSITIVITY",
                        "all_segment_multiple_ranges_applied_together": True,
                        "lower_segment_pool_cny": _fmt(aggregate_low_pool),
                        "selected_segment_pool_cny": _fmt(aggregate_selected_pool),
                        "upper_segment_pool_cny": _fmt(aggregate_high_pool),
                        "lower_total_equity_value_cny": _fmt(lower_equity),
                        "selected_total_equity_value_cny": _fmt(selected_equity),
                        "upper_total_equity_value_cny": _fmt(upper_equity),
                        "lower_terminal_value_per_share_cny": _fmt(lower_equity / shares),
                        "selected_terminal_value_per_share_cny": _fmt(selected_per_share),
                        "upper_terminal_value_per_share_cny": _fmt(upper_equity / shares),
                        "diluted_shares_unchanged": _fmt(shares),
                        "parent_adjustments_unchanged": True,
                        "interpretation": "ALL_SEGMENT_ANALYST_PE_RANGES_APPLIED_SIMULTANEOUSLY; CONDITIONAL SENSITIVITY NOT CONFIDENCE INTERVAL",
                    }
        else:
            row["aggregate_sensitivity"] = {
                "status": "NOT_IDENTIFIABLE",
                "issues": ["AT_LEAST_ONE_SEGMENT_MULTIPLE_RANGE_NOT_IDENTIFIABLE"],
            }

        bridge_partial = sum(
            segment["explicit_selected_multiple_bridge"]["status"] != "MULTIPLE_BRIDGE_RECONCILED"
            for segment in segment_rows
        )
        range_partial = sum(segment["analyst_multiple_range"]["status"] != "RANGE_INPUT_COMPLETE_NOT_PROBABILITY_INTERVAL" for segment in segment_rows)
        row["status"] = (
            "CALIBRATION_AND_RANGE_RECONCILED"
            if segment_rows and not bridge_partial and not range_partial and not row["issues"]
            else "PARTIAL"
        )
        if bridge_partial:
            row["issues"].append(f"MULTIPLE_BRIDGE_INCOMPLETE_SEGMENT_COUNT:{bridge_partial}")
        if range_partial:
            row["issues"].append(f"MULTIPLE_RANGE_INCOMPLETE_SEGMENT_COUNT:{range_partial}")
        row["b63_common_pe_scale_factor_required"] = b63_multiple.get("common_pe_scale_factor_required")
        row["summary"] = (
            "分部终值 P/E 与同口径同行锚、显式调整桥、分析师敏感性区间和 B63 Required Return 倍数要求分开展示。"
            "所有数值调整均由分析师提供并接受算术复核；B66 不自动选择或修改 P/E。"
        )
        result["scenarios"][scenario_name] = row
        scenario_statuses.append(row["status"])

    if scenario_statuses and all(status == "CALIBRATION_AND_RANGE_RECONCILED" for status in scenario_statuses):
        result["status"] = "CALIBRATION_AND_RANGE_RECONCILED"
    elif any(status == "CALIBRATION_AND_RANGE_RECONCILED" for status in scenario_statuses):
        result["status"] = "PARTIAL"
    elif scenario_statuses:
        result["status"] = "PARTIAL"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    result["summary"] = (
        "B66 对每个分部解释所选 P/E 从何而来、如何由显式调整到达所选值、分析师估值区间及其价值敏感性，"
        "并与 B63 的 Required Return 统一倍数敏感性并列；不生成自动公平倍数。"
    )
    return result
