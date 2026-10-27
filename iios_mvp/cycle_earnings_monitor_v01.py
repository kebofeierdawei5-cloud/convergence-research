from __future__ import annotations

"""B44 non-canonical industry-cycle, normalized-earnings and review-chain monitor.

This layer is deliberately diagnostic: it does not overwrite B4 scenario earnings,
change a valuation, admit a forecast, or authorize a portfolio action.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .operating_driver_forecast_v01 import _is_identifiable_basis

CYCLE_EARNINGS_MONITOR_SCHEMA = "IIOS-CYCLE-EARNINGS-MONITOR-0.1"
CYCLE_PHASES = {
    "TROUGH",
    "EARLY_RECOVERY",
    "RECOVERY",
    "MID_CYCLE",
    "LATE_CYCLE",
    "DOWNTURN",
    "STRUCTURAL_DECLINE",
    "UNKNOWN",
}
INDICATOR_DIRECTIONS = {"IMPROVING", "STABLE", "DETERIORATING", "MIXED", "UNKNOWN"}
REVIEW_ACTIONS = {
    "REASSESS_THESIS",
    "REESTIMATE_NORMALIZED_EARNINGS",
    "REBUILD_VALUATION",
    "REVIEW_POSITION",
}
CHAIN_NODES = (
    "INDUSTRY_CYCLE",
    "NORMALIZED_EARNINGS",
    "EPS_OR_FCF",
    "PER_SHARE_VALUE",
    "POSITION_REVIEW",
)
SCENARIOS = ("bear", "base", "bull")


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _decimal(value: Any, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field}_MUST_BE_NUMERIC") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field}_MUST_BE_FINITE")
    return parsed


def _format(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _unknown(reason: str = "未提供行业周期、正常化盈利和复核触发链。") -> dict[str, Any]:
    return {
        "schema_version": CYCLE_EARNINGS_MONITOR_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "industry_cycle": {"status": "UNKNOWN", "phase": "UNKNOWN", "issues": ["INDUSTRY_CYCLE_NOT_PROVIDED"]},
        "normalized_earnings": {"status": "NOT_IDENTIFIABLE", "metric": "NET_PROFIT_CNY", "reference_period": "UNKNOWN", "period": "UNKNOWN", "scenarios": {}, "issues": ["NORMALIZED_EARNINGS_NOT_PROVIDED"]},
        "review_triggers": {"status": "NOT_IDENTIFIABLE", "items": [], "issues": ["REVIEW_TRIGGERS_NOT_PROVIDED"]},
        "summary": reason,
        "b4_comparison": {"status": "NOT_COMPARABLE", "scenarios": {}, "note": "不修改或替代 B4 情景。"},
        "variance_attribution": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["B4_NORMALIZED_COMPARISON_NOT_IDENTIFIABLE"], "sign_convention": "B4_FORECAST_MINUS_NORMALIZED_EARNINGS"},
        "per_share_value": {"status": "NOT_IDENTIFIABLE", "model_family": "UNKNOWN", "scenarios": {}, "issues": ["PRIMARY_PER_SHARE_VALUE_CONTEXT_NOT_PROVIDED"], "formula_recomputed_from_normalized_earnings": False},
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }


def _resolve_refs(
    raw_refs: Any,
    *,
    field: str,
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
    required: bool = True,
) -> tuple[list[str], list[str]]:
    refs = sorted({_text(item) for item in raw_refs if _text(item)}) if isinstance(raw_refs, list) else []
    issues: list[str] = []
    if required and not refs:
        issues.append(f"{field}:EVIDENCE_REFERENCE_REQUIRED")
        return refs, issues
    for ref in refs:
        source = sources_by_id.get(ref)
        if source is None or ref in unresolved_refs:
            issues.append(f"{field}:EVIDENCE_REFERENCE_UNRESOLVED:{ref}")
        elif ref in after_cutoff_refs:
            issues.append(f"{field}:EVIDENCE_SOURCE_AFTER_CUTOFF:{ref}")
        elif ref in uncertain_refs or _text(source.get("time_status")).upper() != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED":
            issues.append(f"{field}:EVIDENCE_SOURCE_TIMING_UNCERTAIN:{ref}")
    return refs, issues


def _meaningful(value: Any) -> bool:
    return _is_identifiable_basis(_text(value))


def _money(raw: Any, *, field: str, sources_by_id: Mapping[str, Mapping[str, Any]],
           unresolved_refs: set[str], after_cutoff_refs: set[str], uncertain_refs: set[str],
           allow_negative: bool = True) -> tuple[Decimal | None, list[str], list[str]]:
    issues: list[str] = []
    if not isinstance(raw, Mapping):
        return None, [f"{field}:TYPED_MONEY_MEASURE_REQUIRED"], []
    if _text(raw.get("unit") or "CNY").upper() != "CNY":
        issues.append(f"{field}:UNIT_MUST_BE_CNY")
    data_class = _text(raw.get("data_class") or "UNKNOWN").upper()
    if data_class not in {"OBSERVED_ACTUAL", "ISSUER_FORECAST", "ANALYST_ASSUMPTION"}:
        issues.append(f"{field}:DATA_CLASS_NOT_IDENTIFIABLE")
    basis = _text(raw.get("basis"))
    if not _meaningful(basis):
        issues.append(f"{field}:BASIS_NOT_IDENTIFIABLE")
    try:
        value = _decimal(raw.get("value"), field)
    except ValueError:
        return None, issues + [f"{field}:VALUE_NOT_IDENTIFIABLE"], []
    if not allow_negative and value < 0:
        issues.append(f"{field}:NEGATIVE_VALUE_NOT_ALLOWED")
    refs, ref_issues = _resolve_refs(
        raw.get("evidence_refs"), field=field, sources_by_id=sources_by_id,
        unresolved_refs=unresolved_refs, after_cutoff_refs=after_cutoff_refs,
        uncertain_refs=uncertain_refs, required=data_class in {"OBSERVED_ACTUAL", "ISSUER_FORECAST"},
    )
    issues.extend(ref_issues)
    return (value if not issues else None), issues, refs


def _build_per_share_value_context(
    forecast_valuation: Mapping[str, Any] | None,
    valuation_model_consistency: Mapping[str, Any] | None,
    valuation_timing: Mapping[str, Any] | None,
    valuation_transmission: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read the existing selected primary-model results; do not recalculate value."""
    forecast = forecast_valuation if isinstance(forecast_valuation, Mapping) else {}
    consistency = valuation_model_consistency if isinstance(valuation_model_consistency, Mapping) else {}
    timing = valuation_timing if isinstance(valuation_timing, Mapping) else {}
    b5 = valuation_transmission if isinstance(valuation_transmission, Mapping) else {}
    issues: list[str] = []
    model_family = _text(forecast.get("model_family") or "UNKNOWN").upper()
    if model_family in {"", "UNKNOWN"}:
        issues.append("PRIMARY_VALUATION_MODEL_FAMILY_NOT_IDENTIFIABLE")
    if consistency.get("primary_model_price_calculation_eligible") is not True:
        issues.append("PRIMARY_MODEL_PRICE_CALCULATION_NOT_ELIGIBLE")
    if _text(timing.get("status")).upper() != "PASS":
        issues.append("VALUATION_TIMING_NOT_PASS")
    try:
        entry_anchor = _decimal(forecast.get("entry_value_reference_per_share"), "ENTRY_VALUE_REFERENCE_PER_SHARE")
        if entry_anchor <= 0:
            issues.append("ENTRY_VALUE_REFERENCE_NOT_POSITIVE")
    except ValueError:
        entry_anchor = None
        issues.append("ENTRY_VALUE_REFERENCE_NOT_IDENTIFIABLE")
    raw_scenarios = forecast.get("scenarios") if isinstance(forecast.get("scenarios"), Mapping) else {}
    scenarios: dict[str, dict[str, Any]] = {}
    values: dict[str, Decimal] = {}
    for name in SCENARIOS:
        row = raw_scenarios.get(name) if isinstance(raw_scenarios.get(name), Mapping) else {}
        raw_value = row.get("terminal_value_per_share")
        try:
            value = _decimal(raw_value, f"{name}.terminal_value_per_share")
            if value < 0:
                raise ValueError("TERMINAL_VALUE_PER_SHARE_NEGATIVE")
            values[name] = value
        except ValueError:
            value = None
            issues.append(f"PRIMARY_MODEL_{name.upper()}_PER_SHARE_VALUE_NOT_IDENTIFIABLE")
        source_path: list[str] = []
        if row.get("eps_multiple_calculation_applied") is True:
            source_path.append("EPS_MULTIPLE_ADAPTER")
        if row.get("sotp_calculation_applied") is True:
            source_path.append("SOTP_ADAPTER")
        if row.get("b5_transmission_applied") is True:
            source_path.append("B5_VALUE_ADJUSTMENT")
        scenarios[name] = {
            "scenario": name,
            "terminal_value_per_share": _format(value),
            "source_status": "READ_FROM_SELECTED_PRIMARY_MODEL_OUTPUT" if value is not None else "UNKNOWN",
            "calculation_path_markers": source_path or ["PRIMARY_VALUE_SOURCE_MARKER_NOT_PRESENT"],
        }
    if set(values) == set(SCENARIOS) and not (values["bear"] <= values["base"] <= values["bull"]):
        issues.append("PRIMARY_MODEL_PER_SHARE_SCENARIO_ORDER_INVALID")
    status = "IDENTIFIABLE_CURRENT_PRIMARY_VALUE_CONTEXT_NON_ADMITTED" if not issues else "NOT_IDENTIFIABLE"
    return {
        "status": status,
        "model_family": model_family,
        "model_name": _text(forecast.get("model")) or "UNKNOWN",
        "entry_value_reference_per_share": _format(entry_anchor),
        "valuation_timing_status": _text(timing.get("status")) or "UNKNOWN",
        "b5_transmission_status": _text(b5.get("status")) or "UNKNOWN",
        "scenarios": scenarios,
        "issues": sorted(set(issues)),
        "formula_recomputed_from_normalized_earnings": False,
        "note": "只读取现有主估值结果作为价值节点上下文；本监测器不把正常化盈利重新代入估值公式，也不替代主估值适配器。",
    }


def evaluate_cycle_earnings_monitor(
    raw: Any,
    *,
    operating_driver_forecast: Mapping[str, Any],
    forecast_valuation: Mapping[str, Any] | None = None,
    valuation_model_consistency: Mapping[str, Any] | None = None,
    valuation_timing: Mapping[str, Any] | None = None,
    valuation_transmission: Mapping[str, Any] | None = None,
    assessment: Mapping[str, Any] | None = None,
    evidence_register: list[Mapping[str, Any]] | None = None,
    unresolved_evidence_ids: list[str] | None = None,
    after_cutoff_evidence_ids: list[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Validate a cycle → normalized-earnings → value → holding-review chain."""
    if not isinstance(raw, Mapping):
        return _unknown()
    if raw.get("schema_version") != CYCLE_EARNINGS_MONITOR_SCHEMA:
        result = _unknown("行业周期/正常化盈利节点的 schema 缺失或版本不兼容。")
        result["status"] = "INVALID_SCHEMA"
        result["industry_cycle"]["issues"] = ["CYCLE_EARNINGS_MONITOR_SCHEMA_MISMATCH"]
        return result

    sources_by_id = {
        _text(row.get("source_id")): row for row in (evidence_register or [])
        if isinstance(row, Mapping) and _text(row.get("source_id"))
    }
    unresolved = set(unresolved_evidence_ids or [])
    after_cutoff = set(after_cutoff_evidence_ids or [])
    uncertain = set(uncertain_timing_evidence_ids or [])
    all_issues: list[str] = []

    # 1) Industry-cycle assessment: state the phase, why, the opposing evidence,
    # leading indicators, and signals that would reverse the phase call.
    cycle_raw = raw.get("industry_cycle") if isinstance(raw.get("industry_cycle"), Mapping) else {}
    cycle_issues: list[str] = []
    cycle_id = _text(cycle_raw.get("cycle_id"))
    phase = _text(cycle_raw.get("phase") or "UNKNOWN").upper()
    if phase not in CYCLE_PHASES:
        cycle_issues.append("INDUSTRY_CYCLE_PHASE_UNSUPPORTED")
        phase = "UNKNOWN"
    if phase == "UNKNOWN":
        cycle_issues.append("INDUSTRY_CYCLE_PHASE_UNKNOWN")
    if not cycle_id or not _meaningful(cycle_id):
        cycle_issues.append("INDUSTRY_CYCLE_ID_REQUIRED")
    phase_basis = _text(cycle_raw.get("phase_basis"))
    if not _meaningful(phase_basis):
        cycle_issues.append("INDUSTRY_CYCLE_PHASE_BASIS_NOT_IDENTIFIABLE")

    cycle_evidence, refs_issues = _resolve_refs(
        cycle_raw.get("evidence_refs"), field="industry_cycle",
        sources_by_id=sources_by_id, unresolved_refs=unresolved,
        after_cutoff_refs=after_cutoff, uncertain_refs=uncertain,
    )
    cycle_issues.extend(refs_issues)
    counter_evidence, refs_issues = _resolve_refs(
        cycle_raw.get("counter_evidence_refs"), field="industry_cycle_counter_evidence",
        sources_by_id=sources_by_id, unresolved_refs=unresolved,
        after_cutoff_refs=after_cutoff, uncertain_refs=uncertain,
    )
    cycle_issues.extend(refs_issues)

    raw_indicators = cycle_raw.get("leading_indicators")
    raw_indicators = raw_indicators if isinstance(raw_indicators, list) else []
    indicators: list[dict[str, Any]] = []
    indicator_ids: set[str] = set()
    for index, row in enumerate(raw_indicators):
        if not isinstance(row, Mapping):
            cycle_issues.append(f"LEADING_INDICATOR_{index}_INVALID")
            continue
        indicator_id = _text(row.get("indicator_id"))
        direction = _text(row.get("direction") or "UNKNOWN").upper()
        item_issues: list[str] = []
        if not indicator_id:
            item_issues.append("INDICATOR_ID_REQUIRED")
        elif indicator_id in indicator_ids:
            item_issues.append(f"DUPLICATE_INDICATOR_ID:{indicator_id}")
        indicator_ids.add(indicator_id)
        if direction not in INDICATOR_DIRECTIONS:
            item_issues.append("INDICATOR_DIRECTION_UNSUPPORTED")
        for key in ("name", "observation", "threshold_or_reversal", "review_by"):
            if not _meaningful(row.get(key)):
                item_issues.append(f"{key.upper()}_NOT_IDENTIFIABLE")
        refs, ri = _resolve_refs(
            row.get("evidence_refs"), field=f"leading_indicator:{indicator_id}",
            sources_by_id=sources_by_id, unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff, uncertain_refs=uncertain,
        )
        item_issues.extend(ri)
        counter_refs, ri = _resolve_refs(
            row.get("counter_evidence_refs"), field=f"leading_indicator_counter:{indicator_id}",
            sources_by_id=sources_by_id, unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff, uncertain_refs=uncertain, required=False,
        )
        item_issues.extend(ri)
        indicators.append({
            "indicator_id": indicator_id,
            "name": _text(row.get("name")),
            "direction": direction,
            "observation": _text(row.get("observation")) or "UNKNOWN",
            "threshold_or_reversal": _text(row.get("threshold_or_reversal")) or "UNKNOWN",
            "review_by": _text(row.get("review_by")) or "UNKNOWN",
            "evidence_refs": refs,
            "counter_evidence_refs": counter_refs,
            "issues": sorted(set(item_issues)),
        })
        cycle_issues.extend(f"INDICATOR:{indicator_id}:{issue}" for issue in item_issues)
    if not indicators:
        cycle_issues.append("LEADING_INDICATORS_REQUIRED")

    raw_reversals = cycle_raw.get("reversal_signals")
    raw_reversals = raw_reversals if isinstance(raw_reversals, list) else []
    reversals: list[dict[str, Any]] = []
    reversal_ids: set[str] = set()
    for index, row in enumerate(raw_reversals):
        if not isinstance(row, Mapping):
            cycle_issues.append(f"REVERSAL_SIGNAL_{index}_INVALID")
            continue
        signal_id = _text(row.get("signal_id"))
        related_id = _text(row.get("related_indicator_id"))
        item_issues: list[str] = []
        if not signal_id:
            item_issues.append("REVERSAL_SIGNAL_ID_REQUIRED")
        elif signal_id in reversal_ids:
            item_issues.append(f"DUPLICATE_REVERSAL_SIGNAL_ID:{signal_id}")
        reversal_ids.add(signal_id)
        if related_id not in indicator_ids:
            item_issues.append("REVERSAL_SIGNAL_INDICATOR_LINK_UNRESOLVED")
        for key in ("condition", "threshold", "review_by", "operating_impact", "valuation_impact"):
            if not _meaningful(row.get(key)):
                item_issues.append(f"{key.upper()}_NOT_IDENTIFIABLE")
        refs, ri = _resolve_refs(
            row.get("evidence_refs"), field=f"reversal_signal:{signal_id}",
            sources_by_id=sources_by_id, unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff, uncertain_refs=uncertain, required=False,
        )
        item_issues.extend(ri)
        reversals.append({
            "signal_id": signal_id,
            "related_indicator_id": related_id,
            "condition": _text(row.get("condition")) or "UNKNOWN",
            "threshold": _text(row.get("threshold")) or "UNKNOWN",
            "review_by": _text(row.get("review_by")) or "UNKNOWN",
            "operating_impact": _text(row.get("operating_impact")) or "UNKNOWN",
            "valuation_impact": _text(row.get("valuation_impact")) or "UNKNOWN",
            "evidence_refs": refs,
            "issues": sorted(set(item_issues)),
        })
        cycle_issues.extend(f"REVERSAL:{signal_id}:{issue}" for issue in item_issues)
    if not reversals:
        cycle_issues.append("CYCLE_REVERSAL_SIGNALS_REQUIRED")

    cycle_status = "IDENTIFIABLE" if not cycle_issues else "REVIEW_REQUIRED"
    cycle_result = {
        "status": cycle_status,
        "cycle_id": cycle_id or "UNKNOWN",
        "phase": phase,
        "phase_basis": phase_basis or "UNKNOWN",
        "evidence_refs": cycle_evidence,
        "counter_evidence_refs": counter_evidence,
        "leading_indicators": indicators,
        "reversal_signals": reversals,
        "issues": sorted(set(cycle_issues)),
        "formal_forecast_admission_created": False,
    }

    # Driver identity map is used to prove that the normalized-earnings and
    # review nodes refer to the same underlying drivers rather than parallel prose.
    assessment_map = assessment if isinstance(assessment, Mapping) else {}
    value_driver_rows = assessment_map.get("value_drivers")
    value_driver_rows = value_driver_rows if isinstance(value_driver_rows, list) else []
    value_driver_ids = {
        _text(row.get("driver_id") or row.get("value_driver_id") or row.get("id"))
        for row in value_driver_rows if isinstance(row, Mapping)
    }
    value_driver_ids.discard("")
    known_driver_ids = set(indicator_ids) | value_driver_ids
    if cycle_id:
        known_driver_ids.add(cycle_id)
    known_driver_ids.update(reversal_ids)

    # 2) Normalized earnings: an explicit reported/reference base plus signed,
    # evidence-linked adjustments must reconcile exactly to each scenario's point.
    earnings_raw = raw.get("normalized_earnings") if isinstance(raw.get("normalized_earnings"), Mapping) else {}
    earnings_issues: list[str] = []
    metric = _text(earnings_raw.get("metric") or "NET_PROFIT_CNY").upper()
    if metric != "NET_PROFIT_CNY":
        earnings_issues.append("NORMALIZED_EARNINGS_METRIC_UNSUPPORTED_V01_NET_PROFIT_CNY_ONLY")
    earnings_scope = _text(earnings_raw.get("scope") or "UNKNOWN").upper()
    if earnings_scope not in {"COMPANY_WIDE", "PRODUCT_LINE", "PROJECT_INCREMENTAL"}:
        earnings_issues.append("NORMALIZED_EARNINGS_SCOPE_NOT_IDENTIFIABLE")
    earnings_period = _text(earnings_raw.get("period"))
    reference_period = _text(earnings_raw.get("reference_period"))
    if not _meaningful(reference_period):
        earnings_issues.append("NORMALIZED_EARNINGS_REFERENCE_PERIOD_NOT_IDENTIFIABLE")
    b4_scope = _text(operating_driver_forecast.get("scope") or "UNKNOWN").upper()
    b4_period = _text(operating_driver_forecast.get("forecast_period") or "UNKNOWN")
    if not earnings_period or earnings_period == "UNKNOWN":
        earnings_issues.append("NORMALIZED_EARNINGS_PERIOD_NOT_IDENTIFIABLE")
    elif b4_period != "UNKNOWN" and earnings_period != b4_period:
        earnings_issues.append("NORMALIZED_EARNINGS_PERIOD_MISMATCH_B4")
    if b4_scope != "UNKNOWN" and earnings_scope != b4_scope:
        earnings_issues.append("NORMALIZED_EARNINGS_SCOPE_MISMATCH_B4")
    overall_basis = _text(earnings_raw.get("normalization_basis"))
    if not _meaningful(overall_basis):
        earnings_issues.append("NORMALIZATION_BASIS_NOT_IDENTIFIABLE")

    raw_earnings_scenarios = earnings_raw.get("scenarios")
    raw_earnings_scenarios = raw_earnings_scenarios if isinstance(raw_earnings_scenarios, Mapping) else {}
    earnings_scenarios: dict[str, dict[str, Any]] = {}
    point_values: dict[str, Decimal] = {}
    for name in SCENARIOS:
        row = raw_earnings_scenarios.get(name) if isinstance(raw_earnings_scenarios.get(name), Mapping) else {}
        row_issues: list[str] = []
        reference, reference_issues, _ = _money(
            row.get("reference_net_profit_cny"), field=f"normalized_earnings.{name}.reference_net_profit_cny",
            sources_by_id=sources_by_id, unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff, uncertain_refs=uncertain, allow_negative=True,
        )
        row_issues.extend(reference_issues)
        adjustments = row.get("adjustments")
        adjustments = adjustments if isinstance(adjustments, list) else []
        adjustment_ids: set[str] = set()
        adjustment_total = Decimal("0")
        normalized_adjustments: list[dict[str, Any]] = []
        if not adjustments:
            row_issues.append("NORMALIZATION_ADJUSTMENTS_REQUIRED")
        for index, adj in enumerate(adjustments):
            if not isinstance(adj, Mapping):
                row_issues.append(f"ADJUSTMENT_{index}_INVALID")
                continue
            adj_id = _text(adj.get("adjustment_id"))
            driver_id = _text(adj.get("driver_id"))
            if not adj_id:
                row_issues.append(f"ADJUSTMENT_{index}_ID_REQUIRED")
            elif adj_id in adjustment_ids:
                row_issues.append(f"DUPLICATE_ADJUSTMENT_ID:{adj_id}")
            adjustment_ids.add(adj_id)
            if driver_id not in known_driver_ids:
                row_issues.append(f"ADJUSTMENT_DRIVER_LINK_UNRESOLVED:{driver_id or 'UNKNOWN'}")
            if not _meaningful(adj.get("rationale")):
                row_issues.append(f"ADJUSTMENT_RATIONALE_NOT_IDENTIFIABLE:{adj_id or index}")
            amount, amount_issues, _ = _money(
                adj.get("amount_cny"), field=f"normalized_earnings.{name}.adjustment:{adj_id or index}",
                sources_by_id=sources_by_id, unresolved_refs=unresolved,
                after_cutoff_refs=after_cutoff, uncertain_refs=uncertain, allow_negative=True,
            )
            row_issues.extend(amount_issues)
            if amount is not None:
                adjustment_total += amount
            normalized_adjustments.append({
                "adjustment_id": adj_id or f"UNKNOWN_{index}",
                "driver_id": driver_id or "UNKNOWN",
                "rationale": _text(adj.get("rationale")) or "UNKNOWN",
                "amount_cny": _format(amount),
                "issues": sorted(set(amount_issues)),
            })
        try:
            low = _decimal(row.get("low_cny"), f"{name}.low_cny")
            point = _decimal(row.get("point_cny"), f"{name}.point_cny")
            high = _decimal(row.get("high_cny"), f"{name}.high_cny")
            if low > point or point > high:
                row_issues.append("NORMALIZED_EARNINGS_RANGE_ORDER_INVALID")
        except ValueError:
            low = point = high = None
            row_issues.append("NORMALIZED_EARNINGS_RANGE_NOT_IDENTIFIABLE")
        if reference is not None and low is not None and point is not None and high is not None:
            reconciled_point = reference + adjustment_total
            if abs(reconciled_point - point) > Decimal("1"):
                row_issues.append("NORMALIZED_POINT_DOES_NOT_RECONCILE_TO_REFERENCE_PLUS_ADJUSTMENTS")
            else:
                point_values[name] = point
        if not _meaningful(row.get("scenario_basis")):
            row_issues.append("SCENARIO_NORMALIZATION_BASIS_NOT_IDENTIFIABLE")
        normalized_earnings_scenario = {
            "scenario": name,
            "reference_net_profit_cny": _format(reference),
            "adjustments": normalized_adjustments,
            "adjustment_total_cny": _format(adjustment_total if reference is not None else None),
            "low_cny": _format(low),
            "point_cny": _format(point),
            "high_cny": _format(high),
            "scenario_basis": _text(row.get("scenario_basis")) or "UNKNOWN",
            "issues": sorted(set(row_issues)),
        }
        earnings_scenarios[name] = normalized_earnings_scenario
        earnings_issues.extend(f"{name.upper()}:{issue}" for issue in row_issues)
    if set(point_values) == set(SCENARIOS) and not (
        point_values["bear"] <= point_values["base"] <= point_values["bull"]
    ):
        earnings_issues.append("NORMALIZED_EARNINGS_BEAR_BASE_BULL_POINT_ORDER_INVALID")
    if len(earnings_scenarios) != 3:
        earnings_issues.append("NORMALIZED_EARNINGS_BEAR_BASE_BULL_SCENARIOS_REQUIRED")

    earnings_status = "REVIEW_REQUIRED" if earnings_issues else "RANGE_AND_ADJUSTMENT_RECONCILIATION_PASS_NOT_ADMITTED"
    earnings_result = {
        "status": earnings_status,
        "metric": metric,
        "scope": earnings_scope,
        "period": earnings_period or "UNKNOWN",
        "reference_period": reference_period or "UNKNOWN",
        "normalization_basis": overall_basis or "UNKNOWN",
        "scenarios": earnings_scenarios,
        "issues": sorted(set(earnings_issues)),
        "formal_forecast_admission_created": False,
        "valuation_input_eligible": False,
    }

    # 3) Compare against B4 only when period, metric and scope are aligned.
    b4_rows = operating_driver_forecast.get("scenarios")
    b4_rows = b4_rows if isinstance(b4_rows, Mapping) else {}
    comparisons: dict[str, dict[str, Any]] = {}
    comparison_complete = (
        not earnings_issues and earnings_scope == b4_scope and earnings_period == b4_period
    )
    for name in SCENARIOS:
        norm_point = point_values.get(name)
        b4_row = b4_rows.get(name) if isinstance(b4_rows.get(name), Mapping) else {}
        b4_raw = b4_row.get("net_profit_cny")
        b4_value: Decimal | None = None
        if b4_raw not in (None, ""):
            try:
                b4_value = _decimal(b4_raw, f"b4.{name}.net_profit_cny")
            except ValueError:
                b4_value = None
        difference = (b4_value - norm_point) if b4_value is not None and norm_point is not None else None
        ratio = abs(difference) / max(abs(norm_point), Decimal("1")) if difference is not None and norm_point is not None else None
        comparisons[name] = {
            "normalized_point_net_profit_cny": _format(norm_point),
            "b4_forecast_net_profit_cny": _format(b4_value),
            "b4_minus_normalized_cny": _format(difference),
            "absolute_difference_ratio_of_normalized_point": _format(ratio),
            "status": (
                "DIAGNOSTIC_COMPARISON_ONLY" if difference is not None and comparison_complete
                else "NOT_COMPARABLE_PERIOD_SCOPE_OR_INPUT_UNKNOWN"
            ),
        }
    comparison_rows_complete = (
        comparison_complete
        and all(row.get("status") == "DIAGNOSTIC_COMPARISON_ONLY" for row in comparisons.values())
    )
    comparison_status = (
        "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT" if comparison_rows_complete
        else "NOT_COMPARABLE_PERIOD_SCOPE_OR_NORMALIZED_EARNINGS_INCOMPLETE"
    )

    # B45: every B4-minus-normalized earnings delta must reconcile to named,
    # driver-linked contributions. Positive means B4 is higher than normalized
    # earnings; negative means B4 is lower. This is explanation only, not a
    # new profit forecast or a valuation input.
    raw_variances = raw.get("variance_attribution")
    raw_variances = raw_variances if isinstance(raw_variances, list) else []
    raw_review_triggers = raw.get("review_triggers")
    raw_review_triggers = raw_review_triggers if isinstance(raw_review_triggers, list) else []
    triggers_by_id = {
        _text(row.get("trigger_id")): row for row in raw_review_triggers
        if isinstance(row, Mapping) and _text(row.get("trigger_id"))
    }
    variance_rows_by_scenario: dict[str, list[Mapping[str, Any]]] = {name: [] for name in SCENARIOS}
    variance_issues: list[str] = []
    normalized_variance_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in SCENARIOS}
    variance_ids: set[tuple[str, str]] = set()
    allowed_variance_categories = {
        "INDUSTRY_CYCLE", "PRICE_VOLUME_MIX", "UNIT_PRICE", "UNIT_COST_MARGIN",
        "CAPACITY_UTILIZATION", "FIXED_COST_OPERATING_LEVERAGE", "FINANCE_TAX",
        "NON_RECURRING", "ACCOUNTING_SCOPE", "PRODUCT_MIX_OR_PERIMETER", "OTHER",
    }
    for index, row in enumerate(raw_variances):
        if not isinstance(row, Mapping):
            variance_issues.append(f"VARIANCE_ATTRIBUTION_{index}_INVALID")
            continue
        scenario = _text(row.get("scenario")).lower()
        attribution_id = _text(row.get("attribution_id"))
        driver_id = _text(row.get("driver_id"))
        trigger_id = _text(row.get("review_trigger_id"))
        category = _text(row.get("category")).upper()
        item_issues: list[str] = []
        if scenario not in SCENARIOS:
            variance_issues.append(f"VARIANCE_ATTRIBUTION_{index}_SCENARIO_INVALID")
            continue
        if not attribution_id:
            item_issues.append("ATTRIBUTION_ID_REQUIRED")
        key = (scenario, attribution_id)
        if key in variance_ids:
            item_issues.append(f"DUPLICATE_ATTRIBUTION_ID:{attribution_id}")
        variance_ids.add(key)
        if driver_id not in known_driver_ids:
            item_issues.append("ATTRIBUTION_DRIVER_LINK_UNRESOLVED")
        if category not in allowed_variance_categories:
            item_issues.append("ATTRIBUTION_CATEGORY_UNSUPPORTED")
        if not _meaningful(row.get("rationale")):
            item_issues.append("ATTRIBUTION_RATIONALE_NOT_IDENTIFIABLE")
        trigger = triggers_by_id.get(trigger_id)
        if trigger is None:
            item_issues.append("ATTRIBUTION_REVIEW_TRIGGER_UNRESOLVED")
        elif _text(trigger.get("driver_id")) != driver_id:
            item_issues.append("ATTRIBUTION_DRIVER_DOES_NOT_MATCH_REVIEW_TRIGGER")
        amount, amount_issues, refs = _money(
            row.get("amount_cny"), field=f"variance_attribution.{scenario}.{attribution_id or index}",
            sources_by_id=sources_by_id, unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff, uncertain_refs=uncertain, allow_negative=True,
        )
        item_issues.extend(amount_issues)
        normalized_row = {
            "scenario": scenario,
            "attribution_id": attribution_id or f"UNKNOWN_{index}",
            "driver_id": driver_id or "UNKNOWN",
            "review_trigger_id": trigger_id or "UNKNOWN",
            "category": category or "UNKNOWN",
            "rationale": _text(row.get("rationale")) or "UNKNOWN",
            "amount_cny": _format(amount),
            "evidence_refs": refs,
            "issues": sorted(set(item_issues)),
        }
        normalized_variance_rows[scenario].append(normalized_row)
        variance_rows_by_scenario[scenario].append(row)
        variance_issues.extend(f"{scenario.upper()}:{attribution_id or index}:{issue}" for issue in item_issues)

    variance_scenarios: dict[str, dict[str, Any]] = {}
    variance_scenarios_complete = comparison_rows_complete
    for name in SCENARIOS:
        comparison_row = comparisons.get(name, {})
        difference_raw = comparison_row.get("b4_minus_normalized_cny")
        try:
            difference = _decimal(difference_raw, f"{name}.b4_minus_normalized_cny")
        except ValueError:
            difference = None
        rows = normalized_variance_rows[name]
        scenario_issues: list[str] = []
        amount_values: list[Decimal] = []
        for item in rows:
            if not item["issues"] and item["amount_cny"] is not None:
                amount_values.append(_decimal(item["amount_cny"], "ATTRIBUTION_AMOUNT"))
        if comparison_rows_complete and not rows:
            scenario_issues.append("VARIANCE_ATTRIBUTIONS_REQUIRED_FOR_COMPARABLE_SCENARIO")
        if comparison_rows_complete and len(amount_values) != len(rows):
            scenario_issues.append("VARIANCE_ATTRIBUTION_CONTAINS_UNUSABLE_COMPONENTS")
        total = sum(amount_values, Decimal("0")) if len(amount_values) == len(rows) and rows else None
        residual = difference - total if difference is not None and total is not None else None
        if comparison_rows_complete and total is not None and residual is not None and abs(residual) > Decimal("1"):
            scenario_issues.append("VARIANCE_ATTRIBUTION_DOES_NOT_RECONCILE_TO_B4_MINUS_NORMALIZED")
        scenario_status = (
            "RECONCILED_DIAGNOSTIC_ONLY"
            if comparison_rows_complete and total is not None and residual is not None and not scenario_issues
            else "REVIEW_REQUIRED" if comparison_rows_complete
            else "NOT_COMPARABLE"
        )
        if scenario_status != "RECONCILED_DIAGNOSTIC_ONLY":
            variance_scenarios_complete = False
        variance_issues.extend(f"{name.upper()}:{issue}" for issue in scenario_issues)
        variance_scenarios[name] = {
            "scenario": name,
            "b4_minus_normalized_net_profit_cny": _format(difference),
            "attributed_total_cny": _format(total),
            "unattributed_residual_cny": _format(residual),
            "items": rows,
            "status": scenario_status,
            "issues": sorted(set(scenario_issues)),
        }
    if not comparison_rows_complete:
        variance_status = "NOT_COMPARABLE"
    elif variance_scenarios_complete and not variance_issues:
        variance_status = "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY"
    else:
        variance_status = "REVIEW_REQUIRED"
    variance_attribution = {
        "status": variance_status,
        "sign_convention": "B4_FORECAST_MINUS_NORMALIZED_EARNINGS; positive means B4 higher, negative means B4 lower",
        "tolerance_cny": "1",
        "scenarios": variance_scenarios,
        "issues": sorted(set(variance_issues)),
        "valuation_input_eligible": False,
        "note": "仅解释 B4 与正常化盈利差异；不修改任一净利润、EPS、FCF、每股估值或决策。",
    }

    per_share_value = _build_per_share_value_context(
        forecast_valuation, valuation_model_consistency, valuation_timing, valuation_transmission
    )
    comparison_issues = (
        [] if comparison_status == "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT"
        else ["B4_NORMALIZED_EARNINGS_COMPARISON_NOT_IDENTIFIABLE"]
    )
    if per_share_value.get("status") != "IDENTIFIABLE_CURRENT_PRIMARY_VALUE_CONTEXT_NON_ADMITTED":
        all_issues_for_value = list(per_share_value.get("issues") or [])
        if not all_issues_for_value:
            all_issues_for_value = ["PRIMARY_PER_SHARE_VALUE_CONTEXT_NOT_IDENTIFIABLE"]
    else:
        all_issues_for_value = []

    # 4) Review triggers must name a known driver and explicitly span the
    # cycle -> earnings -> EPS/FCF -> per-share-value -> position-review chain.
    raw_triggers = raw.get("review_triggers")
    raw_triggers = raw_triggers if isinstance(raw_triggers, list) else []
    trigger_issues: list[str] = []
    trigger_rows: list[dict[str, Any]] = []
    trigger_ids: set[str] = set()
    for index, row in enumerate(raw_triggers):
        if not isinstance(row, Mapping):
            trigger_issues.append(f"REVIEW_TRIGGER_{index}_INVALID")
            continue
        trigger_id = _text(row.get("trigger_id"))
        driver_id = _text(row.get("driver_id"))
        action = _text(row.get("review_action")).upper()
        item_issues: list[str] = []
        if not trigger_id:
            item_issues.append("TRIGGER_ID_REQUIRED")
        elif trigger_id in trigger_ids:
            item_issues.append(f"DUPLICATE_TRIGGER_ID:{trigger_id}")
        trigger_ids.add(trigger_id)
        if driver_id not in known_driver_ids:
            item_issues.append("REVIEW_TRIGGER_DRIVER_LINK_UNRESOLVED")
        for key in ("condition", "threshold", "review_by", "expected_operating_impact", "valuation_path"):
            if not _meaningful(row.get(key)):
                item_issues.append(f"{key.upper()}_NOT_IDENTIFIABLE")
        if action not in REVIEW_ACTIONS:
            item_issues.append("REVIEW_ACTION_UNSUPPORTED_OR_UNKNOWN")
        path = [_text(v).upper() for v in row.get("causal_path", [])] if isinstance(row.get("causal_path"), list) else []
        positions = [path.index(node) if node in path else -1 for node in CHAIN_NODES]
        if any(i < 0 for i in positions) or positions != sorted(positions) or len(set(positions)) != len(positions):
            item_issues.append("CAUSAL_PATH_MUST_CONNECT_CYCLE_TO_EARNINGS_TO_PER_SHARE_VALUE_TO_POSITION_REVIEW")
        refs, ri = _resolve_refs(
            row.get("evidence_refs"), field=f"review_trigger:{trigger_id}",
            sources_by_id=sources_by_id, unresolved_refs=unresolved,
            after_cutoff_refs=after_cutoff, uncertain_refs=uncertain, required=False,
        )
        item_issues.extend(ri)
        trigger_rows.append({
            "trigger_id": trigger_id or f"UNKNOWN_{index}",
            "driver_id": driver_id or "UNKNOWN",
            "condition": _text(row.get("condition")) or "UNKNOWN",
            "threshold": _text(row.get("threshold")) or "UNKNOWN",
            "review_by": _text(row.get("review_by")) or "UNKNOWN",
            "expected_operating_impact": _text(row.get("expected_operating_impact")) or "UNKNOWN",
            "valuation_path": _text(row.get("valuation_path")) or "UNKNOWN",
            "review_action": action or "UNKNOWN",
            "causal_path": path,
            "evidence_refs": refs,
            "issues": sorted(set(item_issues)),
        })
        trigger_issues.extend(f"TRIGGER:{trigger_id}:{issue}" for issue in item_issues)
    if not trigger_rows:
        trigger_issues.append("REVIEW_TRIGGERS_REQUIRED")
    trigger_status = "IDENTIFIABLE" if not trigger_issues else "REVIEW_REQUIRED"
    trigger_result = {"status": trigger_status, "items": trigger_rows, "issues": sorted(set(trigger_issues))}

    all_issues = sorted(set(cycle_issues + earnings_issues + comparison_issues + variance_issues + trigger_issues + all_issues_for_value))
    complete = not all_issues
    result_status = "CHAIN_IDENTIFIABLE_NON_ADMITTED" if complete else "REVIEW_REQUIRED"
    summary = (
        "行业周期、正常化盈利、B4 比较和持仓复核触发链结构完整；仅用于交叉检查，不自动修改 B4/B5/B6 或产生投资动作。"
        if complete else
        "行业周期—正常化盈利—每股价值—持仓复核链存在缺口；保留原 B4/B5/B6 数值，按下方 issues 人工复核。"
    )
    return {
        "schema_version": CYCLE_EARNINGS_MONITOR_SCHEMA,
        "status": result_status,
        "industry_cycle": cycle_result,
        "normalized_earnings": earnings_result,
        "review_triggers": trigger_result,
        "b4_comparison": {"status": comparison_status, "scenarios": comparisons, "issues": comparison_issues, "note": "比较结果仅作诊断，不替代 B4 经营预测。"},
        "variance_attribution": variance_attribution,
        "per_share_value": per_share_value,
        "issues": all_issues,
        "summary": summary,
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }


def render_cycle_earnings_monitor_section(monitor: Mapping[str, Any] | None) -> list[str]:
    """Render the non-authoritative causal chain for operator review."""
    data = monitor if isinstance(monitor, Mapping) else _unknown()
    cycle = data.get("industry_cycle") if isinstance(data.get("industry_cycle"), Mapping) else {}
    earnings = data.get("normalized_earnings") if isinstance(data.get("normalized_earnings"), Mapping) else {}
    triggers = data.get("review_triggers") if isinstance(data.get("review_triggers"), Mapping) else {}
    comparison = data.get("b4_comparison") if isinstance(data.get("b4_comparison"), Mapping) else {}
    value_node = data.get("per_share_value") if isinstance(data.get("per_share_value"), Mapping) else {}
    variance_node = data.get("variance_attribution") if isinstance(data.get("variance_attribution"), Mapping) else {}
    lines = [
        "",
        "### B44：行业周期 → 正常化盈利 → 每股价值 → 持仓复核",
        "",
        f"- 因果链状态：**{data.get('status', 'NOT_IDENTIFIABLE')}**",
        f"- 研究摘要：{data.get('summary', '未提供。')}",
        f"- 行业周期：{cycle.get('phase', 'UNKNOWN')}；判断依据：{cycle.get('phase_basis', 'UNKNOWN')}",
        f"- 支持证据引用：{'、'.join(cycle.get('evidence_refs') or []) or 'UNKNOWN'}；反证引用：{'、'.join(cycle.get('counter_evidence_refs') or []) or 'UNKNOWN'}",
        "",
        "#### 领先指标与周期反转信号",
    ]
    indicators = cycle.get("leading_indicators") if isinstance(cycle.get("leading_indicators"), list) else []
    if not indicators:
        lines.append("- 未提供可审计领先指标。")
    for row in indicators:
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"- {row.get('indicator_id', 'UNKNOWN')}｜{row.get('name', 'UNKNOWN')}｜方向 {row.get('direction', 'UNKNOWN')}｜"
            f"观测 {row.get('observation', 'UNKNOWN')}｜阈值/反转条件 {row.get('threshold_or_reversal', 'UNKNOWN')}｜"
            f"复核时点 {row.get('review_by', 'UNKNOWN')}"
        )
        for issue in row.get("issues") or []:
            lines.append(f"  - 待复核：{issue}")
    reversals = cycle.get("reversal_signals") if isinstance(cycle.get("reversal_signals"), list) else []
    if not reversals:
        lines.append("- 未提供周期反转信号。")
    for row in reversals:
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"- 反转 {row.get('signal_id', 'UNKNOWN')}（关联 {row.get('related_indicator_id', 'UNKNOWN')}）："
            f"{row.get('condition', 'UNKNOWN')}；阈值 {row.get('threshold', 'UNKNOWN')}；"
            f"经营影响 {row.get('operating_impact', 'UNKNOWN')}；估值影响 {row.get('valuation_impact', 'UNKNOWN')}；"
            f"复核 {row.get('review_by', 'UNKNOWN')}"
        )
    lines.extend([
        "",
        "#### 正常化盈利区间（人民币净利润；非自动估值输入）",
        f"- 范围/基准期间/正常化目标期间/依据：{earnings.get('scope', 'UNKNOWN')} / {earnings.get('reference_period', 'UNKNOWN')} / {earnings.get('period', 'UNKNOWN')} / {earnings.get('normalization_basis', 'UNKNOWN')}",
    ])
    scenarios = earnings.get("scenarios") if isinstance(earnings.get("scenarios"), Mapping) else {}
    for name in SCENARIOS:
        row = scenarios.get(name) if isinstance(scenarios.get(name), Mapping) else {}
        lines.append(
            f"- {name.upper()}：参考净利润 {row.get('reference_net_profit_cny') or 'UNKNOWN'}；"
            f"调整净额 {row.get('adjustment_total_cny') or 'UNKNOWN'}；区间低/中/高 "
            f"{row.get('low_cny') or 'UNKNOWN'} / {row.get('point_cny') or 'UNKNOWN'} / {row.get('high_cny') or 'UNKNOWN'}；"
            f"状态 {'PASS' if not row.get('issues') else 'REVIEW_REQUIRED'}"
        )
        for adjustment in row.get("adjustments") or []:
            lines.append(
                f"  - 调整 {adjustment.get('adjustment_id', 'UNKNOWN')} / driver {adjustment.get('driver_id', 'UNKNOWN')}："
                f"{adjustment.get('amount_cny') or 'UNKNOWN'}；{adjustment.get('rationale', 'UNKNOWN')}"
            )
        for issue in row.get("issues") or []:
            lines.append(f"  - 待复核：{issue}")
        compare = comparison.get("scenarios", {}).get(name, {}) if isinstance(comparison.get("scenarios"), Mapping) else {}
        lines.append(
            f"  - 与 B4 净利润对比（只诊断）：B4 {compare.get('b4_forecast_net_profit_cny') or 'UNKNOWN'}；"
            f"差额 {compare.get('b4_minus_normalized_cny') or 'UNKNOWN'}；"
            f"差额/正常化中枢绝对值 {compare.get('absolute_difference_ratio_of_normalized_point') or 'UNKNOWN'}；"
            f"{compare.get('status', 'NOT_COMPARABLE')}"
        )
    lines.extend([
        "",
        "#### B4 与正常化盈利差异归因（B45；正数表示 B4 高于正常化盈利）",
        f"- 归因状态：{variance_node.get('status', 'NOT_COMPARABLE')}；规则：{variance_node.get('sign_convention', 'UNKNOWN')}；对账容差 {variance_node.get('tolerance_cny', 'UNKNOWN')} CNY。",
    ])
    variance_scenarios = variance_node.get("scenarios") if isinstance(variance_node.get("scenarios"), Mapping) else {}
    for name in SCENARIOS:
        variance_row = variance_scenarios.get(name) if isinstance(variance_scenarios.get(name), Mapping) else {}
        lines.append(
            f"- {name.upper()}：B4−正常化 {variance_row.get('b4_minus_normalized_net_profit_cny') or 'UNKNOWN'}；"
            f"归因合计 {variance_row.get('attributed_total_cny') or 'UNKNOWN'}；"
            f"未解释残差 {variance_row.get('unattributed_residual_cny') or 'UNKNOWN'}；"
            f"状态 {variance_row.get('status', 'NOT_COMPARABLE')}"
        )
        for item in variance_row.get("items") or []:
            lines.append(
                f"  - {item.get('attribution_id', 'UNKNOWN')} / {item.get('driver_id', 'UNKNOWN')} / "
                f"{item.get('category', 'UNKNOWN')}：贡献 {item.get('amount_cny') or 'UNKNOWN'}；"
                f"复核触发器 {item.get('review_trigger_id', 'UNKNOWN')}；{item.get('rationale', 'UNKNOWN')}"
            )
            for issue in item.get("issues") or []:
                lines.append(f"    - 待复核：{issue}")
        for issue in variance_row.get("issues") or []:
            lines.append(f"  - 待复核：{issue}")
    for issue in variance_node.get("issues") or []:
        lines.append(f"- 差异归因未解决：{issue}")
    lines.extend([
        "",
        "#### 当前主估值每股价值节点（只读上下文，不重新计算）",
        f"- 价值节点状态：{value_node.get('status', 'NOT_IDENTIFIABLE')}；主模型：{value_node.get('model_family', 'UNKNOWN')} / {value_node.get('model_name', 'UNKNOWN')}；估值时点状态：{value_node.get('valuation_timing_status', 'UNKNOWN')}；B5 传导状态：{value_node.get('b5_transmission_status', 'UNKNOWN')}",
        f"- 入场估值锚：{value_node.get('entry_value_reference_per_share') or 'UNKNOWN'}；是否由本节点用正常化盈利重算：{value_node.get('formula_recomputed_from_normalized_earnings', False)}",
    ])
    value_scenarios = value_node.get("scenarios") if isinstance(value_node.get("scenarios"), Mapping) else {}
    for name in SCENARIOS:
        value_row = value_scenarios.get(name) if isinstance(value_scenarios.get(name), Mapping) else {}
        compare_row = comparison.get("scenarios", {}).get(name, {}) if isinstance(comparison.get("scenarios"), Mapping) else {}
        lines.append(
            f"- {name.upper()} 每股终值：{value_row.get('terminal_value_per_share') or 'UNKNOWN'}；"
            f"计算链标记：{' + '.join(value_row.get('calculation_path_markers') or []) or 'UNKNOWN'}；"
            f"正常化净利润中枢：{compare_row.get('normalized_point_net_profit_cny') or 'UNKNOWN'}；"
            f"B4 净利润：{compare_row.get('b4_forecast_net_profit_cny') or 'UNKNOWN'}；"
            f"差额：{compare_row.get('b4_minus_normalized_cny') or 'UNKNOWN'}"
        )
    for issue in value_node.get("issues") or []:
        lines.append(f"- 价值节点待复核：{issue}")
    lines.extend(["", "#### 持仓复核触发器（不是自动交易指令）"])
    trigger_items = triggers.get("items") if isinstance(triggers.get("items"), list) else []
    if not trigger_items:
        lines.append("- 尚无可执行的复核触发器定义。")
    for row in trigger_items:
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"- {row.get('trigger_id', 'UNKNOWN')} / {row.get('driver_id', 'UNKNOWN')}："
            f"{row.get('condition', 'UNKNOWN')}；阈值 {row.get('threshold', 'UNKNOWN')}；"
            f"复核时点 {row.get('review_by', 'UNKNOWN')}；动作 {row.get('review_action', 'UNKNOWN')}；"
            f"经营影响 {row.get('expected_operating_impact', 'UNKNOWN')}；估值路径 {row.get('valuation_path', 'UNKNOWN')}；"
            f"因果路径 {' → '.join(row.get('causal_path') or []) or 'UNKNOWN'}"
        )
        for issue in row.get("issues") or []:
            lines.append(f"  - 待复核：{issue}")
    for issue in data.get("issues") or []:
        lines.append(f"- 全链路未解决：{issue}")
    lines.extend([
        "",
        "- 权限边界：本节点不覆盖 B4/B5/B6，不创建 Forecast/Valuation 准入，不改变 15% 年化回报门槛、目标入场价或 BUY/ADD/HOLD/REDUCE/EXIT，也不下单。",
        "",
    ])
    return lines
