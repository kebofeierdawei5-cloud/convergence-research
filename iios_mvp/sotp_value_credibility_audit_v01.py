from __future__ import annotations

"""B67 read-only SOTP value-source and current-price requirement audit."""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

B67_SCHEMA = "IIOS-SOTP-VALUE-CREDIBILITY-PRICE-AUDIT-0.1"
_SCENARIOS = ("bear", "base", "bull")
_TOL = Decimal("0.01")


def _txt(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _num(value: Any) -> Decimal | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _eq(left: Decimal | None, right: Decimal | None) -> bool:
    return left is not None and right is not None and abs(left - right) <= _TOL


def _index(rows: Any, label: str, issues: list[str]) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    if not isinstance(rows, list):
        issues.append(f"{label}_ROWS_NOT_LIST")
        return indexed
    for n, raw in enumerate(rows, 1):
        if not isinstance(raw, Mapping):
            issues.append(f"{label}_ROW_NOT_OBJECT:{n}")
            continue
        key = _txt(raw.get("segment_id"))
        if not key or key in indexed:
            issues.append(f"{label}_SEGMENT_ID_MISSING_OR_DUPLICATE:{key or n}")
            continue
        indexed[key] = raw
    return indexed


def _grade(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    source = _map(row.get(key))
    grade = _txt(source.get("grade")).upper()
    if grade not in {"G1_DISCLOSURE_LINKED_TO_PROFIT", "G2_BUSINESS_MECHANISM_AND_EVIDENCE_LINKED",
                     "G3_ANALYST_ASSUMPTION_ONLY", "G4_MULTIPLE_ASSUMPTION_ONLY", "G5_UNKNOWN"}:
        grade = "G5_UNKNOWN"
    return {
        "grade": grade,
        "status": _txt(source.get("status")) or "UNKNOWN",
        "reason": _txt(source.get("grade_reason")) or "UNKNOWN",
        "data_class": _txt(source.get("data_class")) or "UNKNOWN",
        "basis": _txt(source.get("basis")) or "UNKNOWN",
        "evidence_refs": list(source.get("measure_evidence_refs") or []),
        "support_evidence_refs": list(source.get("support_evidence_refs") or []),
        "issues": list(source.get("issues") or []),
    }


def _multiple_bridge(
    row: Mapping[str, Any], *, profit: Decimal, selected_pe: Decimal
) -> dict[str, Any]:
    bridge = _map(row.get("explicit_selected_multiple_bridge"))
    method = _txt(bridge.get("reference_method")).upper() or "UNKNOWN"
    if _txt(bridge.get("status")).upper() != "MULTIPLE_BRIDGE_RECONCILED":
        return {
            "status": "NO_RECONCILED_REFERENCE_BRIDGE",
            "reference_method": method,
            "reference_multiple_x": _fmt(_num(bridge.get("reference_multiple_x"))),
            "explicit_adjustment_sum_x": _fmt(_num(bridge.get("explicit_adjustment_sum_x"))),
            "reference_value_at_selected_profit_cny": None,
            "multiple_adjustment_value_cny": None,
            "issues": list(bridge.get("issues") or []) + ["B66_REFERENCE_BRIDGE_NOT_RECONCILED"],
        }

    reference = _num(bridge.get("reference_multiple_x"))
    adjustment = _num(bridge.get("explicit_adjustment_sum_x"))
    calculated = _num(bridge.get("calculated_selected_pe_x"))
    operator_selected = _num(bridge.get("operator_selected_pe_x"))
    allowed = {"PEER_MEDIAN", "HISTORICAL_SELF_RANGE", "OTHER_EXPLICIT_REFERENCE"}
    problems = []
    if method not in allowed:
        problems.append("B66_REFERENCE_METHOD_NOT_IDENTIFIABLE")
    if reference is None or reference <= 0:
        problems.append("B66_REFERENCE_MULTIPLE_MISSING_OR_NONPOSITIVE")
    if adjustment is None:
        problems.append("B66_EXPLICIT_ADJUSTMENT_SUM_MISSING")
    if not _eq(calculated, selected_pe):
        problems.append("B66_CALCULATED_SELECTED_PE_VS_SOTP_MISMATCH")
    if not _eq(operator_selected, selected_pe):
        problems.append("B66_OPERATOR_SELECTED_PE_VS_SOTP_MISMATCH")
    if reference is not None and adjustment is not None and not _eq(reference + adjustment, selected_pe):
        problems.append("B66_REFERENCE_PLUS_ADJUSTMENTS_DO_NOT_RECONCILE")
    if problems:
        return {
            "status": "RECONCILIATION_MISMATCH",
            "reference_method": method,
            "reference_multiple_x": _fmt(reference),
            "explicit_adjustment_sum_x": _fmt(adjustment),
            "reference_value_at_selected_profit_cny": None,
            "multiple_adjustment_value_cny": None,
            "issues": sorted(set(problems)),
        }

    reference_value = profit * reference
    adjustment_value = profit * adjustment
    selected_value = profit * selected_pe
    if not _eq(reference_value + adjustment_value, selected_value):
        return {
            "status": "RECONCILIATION_MISMATCH",
            "reference_method": method,
            "reference_multiple_x": _fmt(reference),
            "explicit_adjustment_sum_x": _fmt(adjustment),
            "reference_value_at_selected_profit_cny": _fmt(reference_value),
            "multiple_adjustment_value_cny": _fmt(adjustment_value),
            "issues": ["B67_REFERENCE_VALUE_PLUS_MULTIPLE_EFFECT_DOES_NOT_EQUAL_SELECTED_SEGMENT_VALUE"],
        }
    return {
        "status": "REFERENCE_PLUS_EXPLICIT_MULTIPLE_EFFECT_RECONCILED",
        "reference_method": method,
        "reference_description": _txt(bridge.get("reference_description")) or "UNKNOWN",
        "reference_multiple_x": _fmt(reference),
        "explicit_adjustment_sum_x": _fmt(adjustment),
        "selected_pe_x": _fmt(selected_pe),
        "reference_value_at_selected_profit_cny": _fmt(reference_value),
        "multiple_adjustment_value_cny": _fmt(adjustment_value),
        "selected_segment_value_cny": _fmt(selected_value),
        "reconciliation_residual_cny": _fmt(reference_value + adjustment_value - selected_value),
        "interpretation": "REFERENCE_ANCHOR_VALUE_PLUS_EXPLICIT_ANALYST_MULTIPLE_ADJUSTMENT; NOT_FAIR_VALUE_PROOF",
        "issues": [],
    }


def _audit_scenario(name: str, sotp: Mapping[str, Any], b63: Mapping[str, Any],
                    b64: Mapping[str, Any], b66: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario": name, "status": "NOT_IDENTIFIABLE", "issues": [], "segments": [],
        "selected_value_bridge": {"status": "NOT_IDENTIFIABLE"},
        "independent_earnings_bridge": {"status": "NOT_IDENTIFIABLE"},
        "multiple_reference_bridge": {"status": "NOT_IDENTIFIABLE"},
        "parent_adjustment_bridge": {"status": "NOT_IDENTIFIABLE"},
        "dilution_bridge": {"status": "NOT_IDENTIFIABLE"},
        "current_price_required_return": {"status": "NOT_IDENTIFIABLE"},
        "evidence_grade_counts": {
            "profit_grade": {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0},
            "multiple_grade": {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0},
        },
    }
    if _txt(b63.get("status")).upper() != "CONDITIONAL_ATTRIBUTION_CALCULATED":
        out["status"] = "BLOCKED_BY_B63_SCENARIO"
        out["issues"].append(f"B63_SCENARIO_NOT_FULLY_RECONCILED:{_txt(b63.get('status')) or 'UNKNOWN'}")
        return out

    sotp_rows = _index(sotp.get("segments"), "SOTP", out["issues"])
    b63_rows = _index(b63.get("earnings_effect_by_segment"), "B63_EARNINGS", out["issues"])
    b64_rows = _index(b64.get("segments"), "B64", out["issues"])
    b66_rows = _index(b66.get("segments"), "B66", out["issues"])
    if not sotp_rows:
        out["status"] = "NOT_IDENTIFIABLE"
        out["issues"].append("SOTP_SEGMENT_UNIVERSE_EMPTY")
        return out
    if set(sotp_rows) != set(b63_rows):
        out["status"] = "RECONCILIATION_MISMATCH"
        out["issues"].append("SOTP_VS_B63_EARNINGS_SEGMENT_UNIVERSE_MISMATCH")
        return out

    selected_values: dict[str, Decimal] = {}
    profit_effects: dict[str, Decimal] = {}
    b4_segment_values: dict[str, Decimal] = {}
    reference_values: dict[str, Decimal] = {}
    adjustment_values: dict[str, Decimal] = {}
    segment_out = []
    hard_mismatch = False

    for segment_id, segment in sotp_rows.items():
        profit = _num(segment.get("attributable_net_profit_cny"))
        selected_pe = _num(segment.get("pe_multiple_x"))
        if profit is None or profit < 0 or selected_pe is None or selected_pe <= 0:
            out["issues"].append(f"SOTP_PROFIT_OR_SELECTED_PE_NOT_IDENTIFIABLE:{segment_id}")
            hard_mismatch = True
            continue
        if _txt(segment.get("earnings_basis")).upper() != "NORMALIZED_PARENT_ATTRIBUTABLE":
            out["issues"].append(f"SOTP_EARNINGS_BASIS_NOT_NORMALIZED_PARENT_ATTRIBUTABLE:{segment_id}")
            hard_mismatch = True
            continue

        b63_segment = b63_rows[segment_id]
        b63_pe = _num(b63_segment.get("selected_sotp_pe_x"))
        b63_value = _num(b63_segment.get("selected_sotp_segment_value_cny"))
        earnings_effect = _num(b63_segment.get("earnings_effect_at_selected_pe_cny"))
        b4_value = _num(b63_segment.get("b4_forecast_segment_value_at_selected_pe_cny"))
        profit_change = _num(b63_segment.get("normalized_profit_change_cny"))
        selected_value = profit * selected_pe
        if (not _eq(b63_pe, selected_pe) or not _eq(b63_value, selected_value)
                or earnings_effect is None or profit_change is None or b4_value is None
                or not _eq(earnings_effect, profit_change * selected_pe)
                or not _eq(b4_value, selected_value + earnings_effect)):
            out["issues"].append(f"B63_SEGMENT_VALUE_OR_EARNINGS_EFFECT_MISMATCH:{segment_id}")
            hard_mismatch = True
            continue

        b64_segment = b64_rows.get(segment_id, {})
        profit_grade = _grade(b64_segment, "profit_evidence_assessment")
        multiple_grade = _grade(b64_segment, "multiple_evidence_assessment")
        if not b64_segment:
            out["issues"].append(f"B64_EVIDENCE_GRADE_MISSING:{segment_id}")
        b64_profit = _num(b64_segment.get("sotp_selected_attributable_profit_cny")) if b64_segment else None
        b64_pe = _num(b64_segment.get("selected_terminal_pe_x")) if b64_segment else None
        if (b64_profit is not None and not _eq(b64_profit, profit)) or (b64_pe is not None and not _eq(b64_pe, selected_pe)):
            out["issues"].append(f"B64_SELECTED_MEASURE_VS_SOTP_MISMATCH:{segment_id}")
            hard_mismatch = True
        if profit_grade["grade"] == "G5_UNKNOWN" or multiple_grade["grade"] == "G5_UNKNOWN":
            out["issues"].append(f"B64_EVIDENCE_GRADE_UNKNOWN:{segment_id}")
        for group, grade in (("profit_grade", profit_grade["grade"]), ("multiple_grade", multiple_grade["grade"])):
            key = grade[:2] if grade[:2] in {"G1", "G2", "G3", "G4", "G5"} else "G5"
            out["evidence_grade_counts"][group][key] += 1

        b66_segment = b66_rows.get(segment_id, {})
        if not b66_segment:
            out["issues"].append(f"B66_MULTIPLE_CALIBRATION_MISSING:{segment_id}")
        b66_profit = _num(b66_segment.get("normalized_parent_attributable_profit_cny")) if b66_segment else None
        b66_pe = _num(b66_segment.get("selected_terminal_pe_x")) if b66_segment else None
        if b66_segment and (not _eq(b66_profit, profit) or not _eq(b66_pe, selected_pe)):
            out["issues"].append(f"B66_SELECTED_SEGMENT_INPUT_MISMATCH:{segment_id}")
            hard_mismatch = True
        bridge = _multiple_bridge(b66_segment, profit=profit, selected_pe=selected_pe) if b66_segment else {
            "status": "NO_RECONCILED_REFERENCE_BRIDGE", "issues": ["B66_SEGMENT_NOT_AVAILABLE"]
        }
        if bridge.get("status") == "RECONCILIATION_MISMATCH":
            out["issues"].extend(bridge.get("issues") or [])
            hard_mismatch = True
        elif bridge.get("status") == "REFERENCE_PLUS_EXPLICIT_MULTIPLE_EFFECT_RECONCILED":
            reference_values[segment_id] = _num(bridge.get("reference_value_at_selected_profit_cny")) or Decimal("0")
            adjustment_values[segment_id] = _num(bridge.get("multiple_adjustment_value_cny")) or Decimal("0")

        selected_values[segment_id] = selected_value
        profit_effects[segment_id] = earnings_effect
        b4_segment_values[segment_id] = b4_value
        segment_out.append({
            "segment_id": segment_id,
            "segment_name": _txt(segment.get("segment_name")) or "UNKNOWN",
            "normalized_parent_attributable_profit_cny": _fmt(profit),
            "selected_terminal_pe_x": _fmt(selected_pe),
            "selected_segment_equity_value_cny": _fmt(selected_value),
            "b4_forecast_normalized_profit_change_cny": _fmt(profit_change),
            "b4_forecast_value_effect_at_selected_pe_cny": _fmt(earnings_effect),
            "b4_forecast_segment_value_at_selected_pe_cny": _fmt(b4_value),
            "profit_evidence": profit_grade,
            "multiple_evidence": multiple_grade,
            "multiple_reference_bridge": bridge,
        })

    out["segments"] = segment_out
    if hard_mismatch:
        out["status"] = "RECONCILIATION_MISMATCH"
        out["issues"] = sorted(set(out["issues"]))
        return out
    if set(selected_values) != set(sotp_rows):
        out["status"] = "PARTIAL"
        out["issues"] = sorted(set(out["issues"] + ["INCOMPLETE_SEGMENT_VALUE_COVERAGE"]))
        return out

    selected_pool = sum(selected_values.values(), Decimal("0"))
    earnings_total = sum(profit_effects.values(), Decimal("0"))
    b4_pool = sum(b4_segment_values.values(), Decimal("0"))
    waterfall = _map(b63.get("value_pool_waterfall"))
    step1 = _num(waterfall.get("step_1_selected_sotp_segment_pool_cny"))
    step2 = _num(waterfall.get("step_2_b4_earnings_effect_at_selected_pes_cny"))
    step3 = _num(waterfall.get("step_3_b4_forecast_pool_at_selected_pes_cny"))
    step4 = _num(waterfall.get("step_4_common_pe_scale_effect_to_required_pool_cny"))
    step5 = _num(waterfall.get("step_5_required_segment_pool_cny"))
    waterfall_ok = all(_eq(a, b) for a, b in (
        (selected_pool, step1), (earnings_total, step2), (b4_pool, step3),
        (selected_pool + earnings_total, step3), (step3 + step4, step5),
    ))
    if not waterfall_ok:
        out["issues"].append("B67_SELECTED_EARNINGS_AND_REQUIRED_POOL_WATERFALL_MISMATCH")
    out["selected_value_bridge"] = {
        "status": "RECONCILED" if waterfall_ok else "RECONCILIATION_MISMATCH",
        "selected_segment_pool_recalculated_cny": _fmt(selected_pool),
        "selected_segment_pool_from_b63_cny": _fmt(step1),
        "formula": "SUM(NORMALIZED_PARENT_ATTRIBUTABLE_PROFIT × SELECTED_TERMINAL_PE)",
    }
    out["independent_earnings_bridge"] = {
        "status": "RECONCILED" if waterfall_ok else "RECONCILIATION_MISMATCH",
        "selected_sotp_segment_pool_cny": _fmt(selected_pool),
        "b4_earnings_effect_at_unchanged_selected_pes_cny": _fmt(earnings_total),
        "b4_forecast_segment_pool_at_selected_pes_cny": _fmt(b4_pool),
        "formula": "SELECTED_SOTP_POOL + SUM((B4_NORMALIZED_PROFIT − SELECTED_SOTP_PROFIT) × SELECTED_PE)",
        "segment_effects": [
            {"segment_id": s["segment_id"], "normalized_profit_change_cny": s["b4_forecast_normalized_profit_change_cny"],
             "value_effect_at_selected_pe_cny": s["b4_forecast_value_effect_at_selected_pe_cny"]}
            for s in segment_out
        ],
    }

    if len(reference_values) == len(segment_out) and segment_out:
        ref_pool = sum(reference_values.values(), Decimal("0"))
        adj_pool = sum(adjustment_values.values(), Decimal("0"))
        residual = ref_pool + adj_pool - selected_pool
        out["multiple_reference_bridge"] = {
            "status": "FULL_REFERENCE_AND_ADJUSTMENT_WATERFALL_RECONCILED" if abs(residual) <= _TOL else "RECONCILIATION_MISMATCH",
            "reference_segment_pool_cny": _fmt(ref_pool),
            "explicit_multiple_adjustment_value_cny": _fmt(adj_pool),
            "selected_segment_pool_cny": _fmt(selected_pool),
            "reconciliation_residual_cny": _fmt(residual),
            "reference_coverage": f"{len(reference_values)}/{len(segment_out)}",
            "interpretation": "REFERENCE_ANCHOR_VALUE_PLUS_EXPLICIT_ANALYST_MULTIPLE_ADJUSTMENTS; NOT FAIR_VALUE_PROOF",
        }
        if abs(residual) > _TOL:
            out["issues"].append("B67_AGGREGATE_REFERENCE_PLUS_MULTIPLE_VALUE_DOES_NOT_RECONCILE")
    else:
        out["multiple_reference_bridge"] = {
            "status": "PARTIAL_REFERENCE_COVERAGE",
            "identified_reference_segment_count": len(reference_values),
            "total_segment_count": len(segment_out),
            "identified_reference_value_subtotal_cny": _fmt(sum(reference_values.values(), Decimal("0"))),
            "identified_multiple_adjustment_value_subtotal_cny": _fmt(sum(adjustment_values.values(), Decimal("0"))),
            "full_sotp_reference_pool": None,
            "limitations": ["缺少至少一个分部的已复算参考锚；缺失值不作为零，也不外推全公司参考价值池。"],
        }

    parent = _map(b63.get("parent_adjustment_attribution"))
    central = _num(parent.get("capitalized_central_cost_load_on_required_segment_pool_cny"))
    net_cash = _num(parent.get("net_cash_debt_offset_to_required_segment_pool_cny"))
    other = _num(parent.get("other_adjustments_offset_to_required_segment_pool_cny"))
    parent_load = _num(parent.get("net_parent_adjustment_load_cny"))
    dilution = _map(b63.get("dilution_attribution"))
    required_equity = _num(dilution.get("required_total_equity_value_cny"))
    if all(v is not None for v in (central, net_cash, other, parent_load, required_equity)):
        parent_ok = _eq(central + net_cash + other, parent_load) and _eq(step5, required_equity + parent_load)
        out["parent_adjustment_bridge"] = {
            "status": "RECONCILED" if parent_ok else "RECONCILIATION_MISMATCH",
            "capitalized_central_cost_load_cny": _fmt(central),
            "net_cash_debt_offset_cny": _fmt(net_cash),
            "other_adjustments_offset_cny": _fmt(other),
            "net_parent_adjustment_load_cny": _fmt(parent_load),
            "required_segment_pool_cny": _fmt(step5),
            "future_parent_adjustment_change": "NOT_IDENTIFIABLE_WITHOUT_INDEPENDENT_FORWARD_FORECASTS",
        }
        if not parent_ok:
            out["issues"].append("B67_PARENT_ADJUSTMENT_IDENTITY_MISMATCH")
    else:
        out["parent_adjustment_bridge"] = {"status": "NOT_IDENTIFIABLE", "issues": ["B63_PARENT_ADJUSTMENT_COMPONENT_MISSING"]}

    shares = _num(dilution.get("selected_diluted_shares"))
    required_ps = _num(dilution.get("required_terminal_value_per_share_cny"))
    b4_equity = _num(dilution.get("b4_forecast_total_equity_value_cny"))
    equity_gap = _num(dilution.get("total_equity_gap_cny"))
    ps_gap = _num(dilution.get("per_share_gap_cny"))
    if all(v is not None for v in (shares, required_ps, required_equity, b4_equity, equity_gap, ps_gap)) and shares > 0:
        dilution_ok = _eq(required_ps * shares, required_equity) and _eq(required_equity - b4_equity, equity_gap) and _eq(ps_gap * shares, equity_gap)
        out["dilution_bridge"] = {
            "status": "RECONCILED" if dilution_ok else "RECONCILIATION_MISMATCH",
            "selected_diluted_shares": _fmt(shares),
            "required_terminal_value_per_share_cny": _fmt(required_ps),
            "required_total_equity_value_cny": _fmt(required_equity),
            "b4_forecast_total_equity_value_cny": _fmt(b4_equity),
            "equity_gap_cny": _fmt(equity_gap),
            "per_share_gap_cny": _fmt(ps_gap),
            "b4_forecast_implied_value_per_share_cny": _fmt(b4_equity / shares),
        }
        if not dilution_ok:
            out["issues"].append("B67_DILUTION_IDENTITY_MISMATCH")
    else:
        out["dilution_bridge"] = {"status": "NOT_IDENTIFIABLE", "issues": ["B63_DILUTION_INPUT_MISSING_OR_INVALID"]}

    multiple = _map(b63.get("multiple_attribution"))
    factor = _num(multiple.get("common_pe_scale_factor_required"))
    required_rows = _index(multiple.get("required_common_pe_by_segment"), "B63_REQUIRED_PE", out["issues"])
    requirement_ok = (
        step3 is not None and step5 is not None and step3 > 0 and step5 > 0
        and factor is not None and _eq(factor, step5 / step3)
        and set(required_rows) == set(sotp_rows)
    )
    out["current_price_required_return"] = {
        "status": "CONDITIONAL_REQUIREMENT_IDENTIFIED" if requirement_ok else "RECONCILIATION_MISMATCH",
        "basis": "B61_REQUIRED_RETURN_WITHOUT_DISTRIBUTIONS_AS_CARRIED_BY_B63",
        "b4_forecast_segment_pool_at_selected_pes_cny": _fmt(step3),
        "required_segment_pool_for_return_hurdle_cny": _fmt(step5),
        "remaining_value_pool_requirement_after_b4_earnings_cny": _fmt(step5 - step3) if step3 is not None and step5 is not None else None,
        "required_common_pe_scale_factor": _fmt(factor),
        "required_common_pe_by_segment": list(required_rows.values()),
        "b4_forecast_pool_meets_or_exceeds_required_pool": step3 >= step5 if step3 is not None and step5 is not None else None,
        "qualification": "CONDITIONAL_PRICE_IMPLIED_RETURN_HURDLE_NOT_EXTERNAL_MIE_OR_MARKET_CONSENSUS",
    }
    if not requirement_ok:
        out["issues"].append("B67_REQUIRED_COMMON_PE_SCALE_OR_SEGMENT_LINKAGE_MISMATCH")

    b64_status = _txt(b64.get("status")).upper()
    b66_status = _txt(b66.get("status")).upper()
    if b64_status not in {"ASSESSED_DIAGNOSTIC_ONLY", "PARTIAL"}:
        out["issues"].append(f"B64_SCENARIO_NOT_ASSESSABLE:{b64_status or 'UNKNOWN'}")
    if b66_status not in {"CALIBRATION_AND_RANGE_RECONCILED", "PARTIAL"}:
        out["issues"].append(f"B66_SCENARIO_NOT_ASSESSABLE:{b66_status or 'UNKNOWN'}")

    mismatch = any("MISMATCH" in x or "DOES_NOT_RECONCILE" in x for x in out["issues"]) or any(
        _txt(_map(out.get(key)).get("status")).upper() == "RECONCILIATION_MISMATCH"
        for key in ("selected_value_bridge", "independent_earnings_bridge", "multiple_reference_bridge",
                    "parent_adjustment_bridge", "dilution_bridge", "current_price_required_return")
    )
    partial = bool(out["issues"]) or b64_status != "ASSESSED_DIAGNOSTIC_ONLY" or b66_status != "CALIBRATION_AND_RANGE_RECONCILED" or out["multiple_reference_bridge"].get("status") != "FULL_REFERENCE_AND_ADJUSTMENT_WATERFALL_RECONCILED"
    out["status"] = "RECONCILIATION_MISMATCH" if mismatch else (
        "VALUE_SOURCE_AUDIT_RECONCILED_DIAGNOSTIC_ONLY" if not partial else "PARTIAL"
    )
    out["issues"] = sorted(set(out["issues"]))
    out["summary"] = "分开展示分部盈利价值、B4 盈利变化、参考倍数与显式倍数调整、母公司调整、稀释股数及 B61 Required Return 现价要求；不生成综合可信度分数。"
    return out


def build_sotp_value_credibility_price_audit(
    *,
    sotp_valuation: Mapping[str, Any],
    valuation_gap_attribution: Mapping[str, Any],
    evidence_grade_assessment: Mapping[str, Any],
    multiple_calibration_assessment: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a diagnostic view; never change valuation values or decision authority."""
    result: dict[str, Any] = {
        "schema_version": B67_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "READ_ONLY_VALUE_SOURCE_AND_PRICE_REQUIREMENT_AUDIT",
        "scenarios": {},
        "value_arithmetic_modified": False,
        "sotp_inputs_modified": False,
        "b61_b63_inputs_modified": False,
        "b64_evidence_grades_modified": False,
        "b66_multiple_assumptions_modified": False,
        "external_mie_modified": False,
        "expectation_gap_modified": False,
        "required_return_or_target_entry_modified": False,
        "portfolio_constraints_modified": False,
        "decision_authority": False,
        "limitations": [
            "B67 只复算现有 SOTP/B63 算术与结构化来源关联，不验证原始披露内容的真实性、完整性或语义支持关系。",
            "B64 盈利等级与倍数等级分别呈现；不合并为综合分数、概率、置信度或价值折扣系数。",
            "B66 参考倍数和显式调整的价值金额是相对所声明参考锚的算术拆解，不证明参考锚公允或调整合理。",
            "B63 的 B4 盈利效应和 Required Return 倍数缩放是条件敏感性，不等同市场共识，也不是某分部独立公平 P/E。",
            "母公司调整沿用当前选定假设；没有独立前瞻预测时不归因其未来变化。稀释股数仅用于权益价值到每股价值的换算。",
            "现价要求来自 B61 Required Return（未计分红）及 B63 传导，不是外部 MIE、市场一致预期或自动 BUY/SELL 结论。",
            "B67 不改变 15% 年化回报要求、目标买入价、组合约束、Decision、正式证据准入或执行权限。",
        ],
    }
    if _txt(sotp_valuation.get("status")).upper() != "CALCULATED" or sotp_valuation.get("selected_for_primary_model") is not True:
        result["status"] = "NOT_APPLICABLE_SOTP_NOT_SELECTED_OR_CALCULATED"
        return result
    b63_status = _txt(valuation_gap_attribution.get("status")).upper()
    if b63_status != "CONDITIONAL_ATTRIBUTION_CALCULATED":
        result["status"] = "BLOCKED_BY_B63"
        result["b63_status"] = b63_status or "UNKNOWN"
        return result

    s_scenarios = _map(sotp_valuation.get("scenarios"))
    b63_scenarios = _map(valuation_gap_attribution.get("scenarios"))
    b64_scenarios = _map(evidence_grade_assessment.get("scenarios"))
    b66_scenarios = _map(multiple_calibration_assessment.get("scenarios"))
    statuses = []
    for name in _SCENARIOS:
        row = _audit_scenario(
            name, _map(s_scenarios.get(name)), _map(b63_scenarios.get(name)),
            _map(b64_scenarios.get(name)), _map(b66_scenarios.get(name))
        )
        result["scenarios"][name] = row
        statuses.append(row["status"])
    if statuses and all(x == "VALUE_SOURCE_AUDIT_RECONCILED_DIAGNOSTIC_ONLY" for x in statuses):
        result["status"] = "VALUE_SOURCE_AUDIT_RECONCILED_DIAGNOSTIC_ONLY"
    elif any(x == "RECONCILIATION_MISMATCH" for x in statuses):
        result["status"] = "RECONCILIATION_MISMATCH"
    elif any(x in {"VALUE_SOURCE_AUDIT_RECONCILED_DIAGNOSTIC_ONLY", "PARTIAL"} for x in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    result["summary"] = (
        "B67 将 SOTP 分部价值、B4 盈利变化、B66 参考倍数/显式调整、母公司调整、稀释传导与 "
        "B61 Required Return 要求放入同一审计视图；证据等级分别呈现，不形成综合分数或自动投资结论。"
    )
    return result
