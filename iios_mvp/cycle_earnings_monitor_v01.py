from __future__ import annotations

"""B44 non-canonical industry-cycle, normalized-earnings and review-chain monitor.

This layer is deliberately diagnostic: it does not overwrite B4 scenario earnings,
change a valuation, admit a forecast, or authorize a portfolio action.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .operating_driver_forecast_v01 import _is_identifiable_basis

CYCLE_EARNINGS_MONITOR_SCHEMA = "IIOS-CYCLE-EARNINGS-MONITOR-0.1"
NORMALIZED_FCF_METHOD = "B4_UNLEVERED_FCF_PROXY_EBIT_AFTER_TAX_PLUS_DA_MINUS_CASH_CAPEX_MINUS_EFFECTIVE_WC_V0.1"
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
        "cash_flow_path": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["CASH_FLOW_PATH_NOT_PROVIDED"], "normalized_fcf_comparison_available": False, "fcf_variance_reconciled": False},
        "normalized_fcf_bridge": {"status": "NOT_IDENTIFIABLE", "normalized_fcf": {"status": "NOT_IDENTIFIABLE", "scenarios": {}, "issues": ["NORMALIZED_FCF_NOT_PROVIDED"]}, "b4_comparison": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["B4_NORMALIZED_FCF_COMPARISON_NOT_IDENTIFIABLE"]}, "variance_attribution": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["FCF_VARIANCE_ATTRIBUTION_NOT_PROVIDED"]}, "issues": ["NORMALIZED_FCF_NOT_PROVIDED"], "normalized_fcf_comparison_available": False, "fcf_variance_reconciled": False, "cash_flow_amounts_aggregated": False, "valuation_input_eligible": False},
        "variance_transmission": {"status": "NOT_IDENTIFIABLE", "scenarios": {}, "issues": ["VARIANCE_TRANSMISSION_CONTEXT_NOT_PROVIDED"], "valuation_input_eligible": False},
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


def _build_variance_transmission_context(
    *,
    variance_attribution: Mapping[str, Any],
    eps_earnings_bridge: Mapping[str, Any] | None,
    eps_multiple_valuation: Mapping[str, Any] | None,
    per_share_value: Mapping[str, Any],
    normalized_earnings_period: str,
    b4_forecast_period: str,
) -> dict[str, Any]:
    """Translate reconciled net-profit differences into conditional EPS/P-E sensitivities only."""
    blocked_upstream = variance_attribution.get("status") != "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY"
    bridge = eps_earnings_bridge if isinstance(eps_earnings_bridge, Mapping) else {}
    adapter = eps_multiple_valuation if isinstance(eps_multiple_valuation, Mapping) else {}
    value_context = per_share_value if isinstance(per_share_value, Mapping) else {}
    period = _text(normalized_earnings_period).upper()
    b4_period = _text(b4_forecast_period).upper()
    bridge_period = _text(bridge.get("forecast_period")).upper()
    adapter_period = _text(adapter.get("forecast_period")).upper()
    adapter_date = _text(adapter.get("valuation_terminal_date"))
    bridge_date = _text(bridge.get("valuation_terminal_date"))
    issues: list[str] = []
    if blocked_upstream:
        issues.append("UPSTREAM_VARIANCE_ATTRIBUTION_NOT_RECONCILED")
    if bridge.get("primary_eps_price_calculation_eligible") is not True:
        issues.append("EPS_EARNINGS_BRIDGE_NOT_ELIGIBLE")
    if _text(bridge.get("currency")).upper() != "CNY":
        issues.append("EPS_BRIDGE_CURRENCY_MUST_BE_CNY_FOR_CNY_NET_PROFIT_DELTA")
    if not period or period != b4_period or bridge_period != period:
        issues.append("EPS_BRIDGE_AND_NORMALIZED_EARNINGS_PERIOD_MISMATCH")
    if adapter.get("status") != "CALCULATED" or adapter.get("selected_for_primary_model") is not True:
        issues.append("PRIMARY_EPS_MULTIPLE_ADAPTER_NOT_CALCULATED_AND_SELECTED")
    if _text(adapter.get("currency")).upper() != "CNY":
        issues.append("PRIMARY_EPS_MULTIPLE_CURRENCY_MUST_BE_CNY")
    if not period or adapter_period != period or not adapter_date or bridge_date != adapter_date:
        issues.append("EPS_BRIDGE_AND_PRIMARY_ADAPTER_PERIOD_OR_TERMINAL_DATE_MISMATCH")
    if _text(value_context.get("model_family")).upper() != "EPS_MULTIPLE":
        issues.append("CURRENT_PRIMARY_MODEL_IS_NOT_EPS_MULTIPLE")
    if value_context.get("status") != "IDENTIFIABLE_CURRENT_PRIMARY_VALUE_CONTEXT_NON_ADMITTED":
        issues.append("CURRENT_PRIMARY_PER_SHARE_VALUE_CONTEXT_NOT_IDENTIFIABLE")

    variance_scenarios = variance_attribution.get("scenarios")
    variance_scenarios = variance_scenarios if isinstance(variance_scenarios, Mapping) else {}
    bridge_scenarios = bridge.get("scenarios")
    bridge_scenarios = bridge_scenarios if isinstance(bridge_scenarios, Mapping) else {}
    adapter_scenarios = adapter.get("scenarios")
    adapter_scenarios = adapter_scenarios if isinstance(adapter_scenarios, Mapping) else {}
    value_scenarios = value_context.get("scenarios")
    value_scenarios = value_scenarios if isinstance(value_scenarios, Mapping) else {}
    results: dict[str, dict[str, Any]] = {}
    all_scenarios_calculated = not blocked_upstream
    for name in SCENARIOS:
        row_issues = list(issues)
        variance_row = variance_scenarios.get(name) if isinstance(variance_scenarios.get(name), Mapping) else {}
        bridge_row = bridge_scenarios.get(name) if isinstance(bridge_scenarios.get(name), Mapping) else {}
        adapter_row = adapter_scenarios.get(name) if isinstance(adapter_scenarios.get(name), Mapping) else {}
        value_row = value_scenarios.get(name) if isinstance(value_scenarios.get(name), Mapping) else {}
        if variance_row.get("status") != "RECONCILED_DIAGNOSTIC_ONLY":
            row_issues.append("SCENARIO_VARIANCE_NOT_RECONCILED")
        if bridge_row.get("status") != "CALCULATED" or bridge_row.get("eps_match") is not True:
            row_issues.append("SCENARIO_EPS_BRIDGE_NOT_CALCULATED_OR_NOT_MATCHED")
        shares_measure = bridge_row.get("diluted_shares")
        shares_measure = shares_measure if isinstance(shares_measure, Mapping) else {}
        try:
            if _text(shares_measure.get("unit")).lower() != "shares":
                raise ValueError("DILUTED_SHARES_UNIT_MUST_BE_SHARES")
            shares = _decimal(shares_measure.get("value"), f"{name}.diluted_shares")
            if shares <= 0:
                raise ValueError("DILUTED_SHARES_MUST_BE_POSITIVE")
        except ValueError as exc:
            shares = None
            row_issues.append(str(exc))
        pe_measure = adapter_row.get("pe_multiple_x")
        pe_measure = pe_measure if isinstance(pe_measure, Mapping) else {}
        try:
            if _text(pe_measure.get("unit")).lower() != "x":
                raise ValueError("PE_MULTIPLE_UNIT_MUST_BE_X")
            pe = _decimal(pe_measure.get("value"), f"{name}.pe_multiple_x")
            if pe <= 0:
                raise ValueError("PE_MULTIPLE_MUST_BE_POSITIVE")
        except ValueError as exc:
            pe = None
            row_issues.append(str(exc))
        try:
            terminal_value = _decimal(adapter_row.get("terminal_value_per_share"), f"{name}.adapter_terminal_value")
            current_value = _decimal(value_row.get("terminal_value_per_share"), f"{name}.primary_terminal_value")
            if terminal_value != current_value:
                row_issues.append("PRIMARY_VALUE_DOES_NOT_MATCH_SELECTED_EPS_MULTIPLE_ADAPTER")
        except ValueError:
            row_issues.append("PRIMARY_OR_ADAPTER_TERMINAL_VALUE_NOT_IDENTIFIABLE")
        try:
            difference = _decimal(
                variance_row.get("b4_minus_normalized_net_profit_cny"),
                f"{name}.b4_minus_normalized_net_profit_cny",
            )
        except ValueError:
            difference = None
            row_issues.append("NET_PROFIT_DIFFERENCE_NOT_IDENTIFIABLE")
        raw_items = variance_row.get("items") if isinstance(variance_row.get("items"), list) else []
        item_outputs: list[dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, Mapping):
                row_issues.append("VARIANCE_ATTRIBUTION_ITEM_INVALID")
                continue
            if item.get("issues"):
                row_issues.append(f"ATTRIBUTION_ITEM_NOT_USABLE:{_text(item.get('attribution_id')) or 'UNKNOWN'}")
                continue
            try:
                amount = _decimal(item.get("amount_cny"), "ATTRIBUTION_AMOUNT_CNY")
                if shares is None or pe is None:
                    raise ValueError("EPS_OR_PE_INPUT_NOT_IDENTIFIABLE")
                eps_sensitivity = amount / shares
                value_sensitivity = eps_sensitivity * pe
                item_outputs.append({
                    "attribution_id": _text(item.get("attribution_id")) or "UNKNOWN",
                    "driver_id": _text(item.get("driver_id")) or "UNKNOWN",
                    "review_trigger_id": _text(item.get("review_trigger_id")) or "UNKNOWN",
                    "amount_cny": _format(amount),
                    "implied_eps_sensitivity_per_share": _format(eps_sensitivity),
                    "constant_pe_value_sensitivity_per_share": _format(value_sensitivity),
                    "sensitivity_status": "CONDITIONAL_DIAGNOSTIC_ONLY",
                })
            except ValueError:
                row_issues.append(f"ATTRIBUTION_SENSITIVITY_NOT_IDENTIFIABLE:{_text(item.get('attribution_id')) or 'UNKNOWN'}")
        row_status = "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" if not row_issues and shares is not None and pe is not None and difference is not None else "NOT_IDENTIFIABLE"
        if row_status != "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY":
            all_scenarios_calculated = False
            # Fail closed: once any upstream, timing, unit, or item issue exists,
            # do not leave partial numeric sensitivities in the report.
            item_outputs = []
        results[name] = {
            "scenario": name,
            "status": row_status,
            "b4_minus_normalized_net_profit_cny": _format(difference) if row_status == "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" else None,
            "diluted_shares": _format(shares) if row_status == "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" else None,
            "pe_multiple_x": _format(pe) if row_status == "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" else None,
            "implied_eps_sensitivity_per_share": _format(difference / shares) if row_status == "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" and difference is not None and shares is not None and shares > 0 else None,
            "constant_pe_value_sensitivity_per_share": _format((difference / shares) * pe) if row_status == "CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" and difference is not None and shares is not None and shares > 0 and pe is not None and pe > 0 else None,
            "items": item_outputs,
            "issues": sorted(set(row_issues)),
        }
    status = "ALL_SCENARIOS_CONSTANT_PE_SENSITIVITY_DIAGNOSTIC_ONLY" if all_scenarios_calculated else (
        "BLOCKED_UPSTREAM_VARIANCE_ATTRIBUTION_NOT_RECONCILED" if blocked_upstream else "REVIEW_REQUIRED"
    )
    return {
        "status": status,
        "method": "NET_PROFIT_VARIANCE_CNY / DILUTED_SHARES × CURRENT_SCENARIO_PE",
        "currency": "CNY",
        "assumptions": [
            "仅在净利润口径、期间、CNY 货币、稀释股数和 EPS_MULTIPLE 主估值链均可核对时计算。",
            "假设非控股股东损益、其他税后归属调整、稀释股数和 P/E 倍数保持不变；该结果是条件敏感性，不是新的 EPS 预测或每股价值。",
            "该节点不改写 B4/B5/B6、主估值、目标入场价、回报率或决策；不适用于 SOTP，也不自动成为估值输入。",
        ],
        "scenarios": results,
        "issues": sorted(set(issues)),
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }


def _evaluate_cash_flow_path(
    *,
    raw_assessments: Any,
    variance_attribution: Mapping[str, Any],
    operating_driver_forecast: Mapping[str, Any],
    known_driver_ids: set[str],
    raw_review_triggers: list[Any],
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
) -> dict[str, Any]:
    """Keep cash/FCF attribution independent from net-profit attribution; never invent a normalized FCF bridge."""
    allowed_channels = {
        "OPERATING_CASH_CONVERSION", "WORKING_CAPITAL", "INVENTORY_MOVEMENT",
        "CAPEX", "NON_CASH_EARNINGS", "FINANCING_CASH_FLOW", "TAX_CASH_TIMING",
        "NO_DIRECT_CASH_EFFECT", "UNKNOWN",
    }
    allowed_directions = {
        "IMPROVES_FCF", "REDUCES_FCF", "MIXED_OR_TIMING_DEPENDENT",
        "NO_DIRECT_EFFECT", "UNKNOWN",
    }
    allowed_quantification = {"QUANTIFIED", "QUALITATIVE_ONLY", "NOT_APPLICABLE", "UNKNOWN"}
    channel_context_field = {
        "OPERATING_CASH_CONVERSION": "unlevered_fcf_proxy_cny",
        "WORKING_CAPITAL": "effective_change_working_capital_cny",
        "INVENTORY_MOVEMENT": "inventory_cash_impact_proxy_cny",
        "CAPEX": "cash_capex_cny",
        "NON_CASH_EARNINGS": "depreciation_amortization_cny",
        "FINANCING_CASH_FLOW": None,
        "TAX_CASH_TIMING": None,
    }
    triggers_by_id = {
        _text(row.get("trigger_id")): row for row in raw_review_triggers
        if isinstance(row, Mapping) and _text(row.get("trigger_id"))
    }
    expected_rows: dict[tuple[str, str], Mapping[str, Any]] = {}
    scenarios = variance_attribution.get("scenarios")
    scenarios = scenarios if isinstance(scenarios, Mapping) else {}
    for scenario in SCENARIOS:
        scenario_row = scenarios.get(scenario)
        scenario_row = scenario_row if isinstance(scenario_row, Mapping) else {}
        rows = scenario_row.get("items")
        comparable_items = rows if isinstance(rows, list) else []
        for item in comparable_items:
            if not isinstance(item, Mapping):
                continue
            key = (scenario, _text(item.get("attribution_id")))
            if key[1]:
                expected_rows[key] = item

    b4_scenarios = operating_driver_forecast.get("scenarios")
    b4_scenarios = b4_scenarios if isinstance(b4_scenarios, Mapping) else {}
    b4_cash_context: dict[str, dict[str, Any]] = {}
    cash_context_fields = (
        "cash_capex_cny", "change_working_capital_cny", "effective_change_working_capital_cny",
        "inventory_cash_impact_proxy_cny", "inventory_working_capital_treatment",
        "inventory_reconciliation_status", "depreciation_amortization_cny", "finance_cost_cny",
        "unlevered_fcf_proxy_cny",
    )
    for scenario in SCENARIOS:
        row = b4_scenarios.get(scenario)
        row = row if isinstance(row, Mapping) else {}
        usable = row.get("financial_outputs_decision_usable") is True
        fields = {
            key: (" ".join(str(row.get(key)).split()) if row.get(key) is not None else None) if usable else None
            for key in cash_context_fields
        }
        b4_cash_context[scenario] = {
            "status": "B4_CASH_CONTEXT_DECISION_USABLE" if usable else "B4_CASH_CONTEXT_NOT_DECISION_USABLE",
            "forecast_period": _text(operating_driver_forecast.get("forecast_period")) or "UNKNOWN",
            "financial_outputs_decision_usable": usable,
            "fields": fields,
            "issues": [] if usable else ["B4_CASH_CONTEXT_NOT_DECISION_USABLE"],
            "note": "仅复述 B4 自身现金流代理及相关输入；不构造正常化 FCF、不计算盈利差异对应的 FCF 差额。",
        }

    assessments = raw_assessments if isinstance(raw_assessments, list) else []
    global_issues: list[str] = []
    if not assessments and expected_rows:
        global_issues.append("CASH_FLOW_ASSESSMENTS_REQUIRED_FOR_EACH_PROFIT_ATTRIBUTION")
    if not expected_rows:
        global_issues.append("NO_IDENTIFIABLE_PROFIT_ATTRIBUTIONS_TO_LINK_CASH_FLOW_PATH")
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    by_scenario: dict[str, list[dict[str, Any]]] = {name: [] for name in SCENARIOS}

    for index, row in enumerate(assessments):
        if not isinstance(row, Mapping):
            global_issues.append(f"CASH_FLOW_ASSESSMENT_{index}_INVALID")
            continue
        scenario = _text(row.get("scenario")).lower()
        attribution_id = _text(row.get("attribution_id"))
        driver_id = _text(row.get("driver_id"))
        trigger_id = _text(row.get("review_trigger_id"))
        channel = _text(row.get("channel")).upper() or "UNKNOWN"
        direction = _text(row.get("direction")).upper() or "UNKNOWN"
        quant_status = _text(row.get("quantification_status")).upper() or "UNKNOWN"
        rationale = _text(row.get("rationale"))
        item_issues: list[str] = []
        key = (scenario, attribution_id)
        if scenario not in SCENARIOS:
            item_issues.append("CASH_FLOW_SCENARIO_INVALID")
        if not attribution_id:
            item_issues.append("CASH_FLOW_ATTRIBUTION_ID_REQUIRED")
        if key in seen:
            item_issues.append("DUPLICATE_CASH_FLOW_ASSESSMENT_FOR_ATTRIBUTION")
        seen.add(key)
        profit_item = expected_rows.get(key)
        if profit_item is None:
            item_issues.append("CASH_FLOW_ASSESSMENT_HAS_NO_MATCHING_PROFIT_ATTRIBUTION")
        else:
            if _text(profit_item.get("driver_id")) != driver_id:
                item_issues.append("CASH_FLOW_DRIVER_DOES_NOT_MATCH_PROFIT_ATTRIBUTION")
            if _text(profit_item.get("review_trigger_id")) != trigger_id:
                item_issues.append("CASH_FLOW_TRIGGER_DOES_NOT_MATCH_PROFIT_ATTRIBUTION")
        if driver_id not in known_driver_ids:
            item_issues.append("CASH_FLOW_DRIVER_LINK_UNRESOLVED")
        if channel not in allowed_channels or channel == "UNKNOWN":
            item_issues.append("CASH_FLOW_CHANNEL_NOT_IDENTIFIABLE")
        if direction not in allowed_directions or direction == "UNKNOWN":
            item_issues.append("CASH_FLOW_DIRECTION_NOT_IDENTIFIABLE")
        if quant_status not in allowed_quantification or quant_status == "UNKNOWN":
            item_issues.append("CASH_FLOW_QUANTIFICATION_STATUS_NOT_IDENTIFIABLE")
        if not _meaningful(rationale):
            item_issues.append("CASH_FLOW_RATIONALE_NOT_IDENTIFIABLE")
        trigger = triggers_by_id.get(trigger_id)
        if trigger is None:
            item_issues.append("CASH_FLOW_REVIEW_TRIGGER_UNRESOLVED")
        elif _text(trigger.get("driver_id")) != driver_id:
            item_issues.append("CASH_FLOW_DRIVER_DOES_NOT_MATCH_REVIEW_TRIGGER")
        refs, ref_issues = _resolve_refs(
            row.get("evidence_refs"),
            field=f"cash_flow_assessment.{scenario}.{attribution_id or index}",
            sources_by_id=sources_by_id,
            unresolved_refs=unresolved_refs,
            after_cutoff_refs=after_cutoff_refs,
            uncertain_refs=uncertain_refs,
            required=True,
        )
        item_issues.extend(ref_issues)
        raw_trigger_refs = trigger.get("evidence_refs") if isinstance(trigger, Mapping) and isinstance(trigger.get("evidence_refs"), list) else []
        trigger_refs = {_text(ref) for ref in raw_trigger_refs if _text(ref)}
        if not trigger_refs:
            item_issues.append("REVIEW_TRIGGER_EVIDENCE_REQUIRED_FOR_CASH_FLOW_LINK")
        elif not set(refs).intersection(trigger_refs):
            item_issues.append("CASH_FLOW_EVIDENCE_NOT_SHARED_WITH_REVIEW_TRIGGER")

        raw_effect = row.get("cash_flow_effect_cny")
        effect: Decimal | None = None
        effect_refs: list[str] = []
        effect_basis: str | None = None
        effect_data_class: str | None = None
        if quant_status == "QUANTIFIED":
            effect, effect_issues, effect_refs = _money(
                raw_effect,
                field=f"cash_flow_assessment.{scenario}.{attribution_id or index}.cash_flow_effect_cny",
                sources_by_id=sources_by_id,
                unresolved_refs=unresolved_refs,
                after_cutoff_refs=after_cutoff_refs,
                uncertain_refs=uncertain_refs,
                allow_negative=True,
            )
            if isinstance(raw_effect, Mapping):
                effect_basis = _text(raw_effect.get("basis")) or None
                effect_data_class = _text(raw_effect.get("data_class")).upper() or None
            item_issues.extend(effect_issues)
            if not effect_refs:
                item_issues.append("CASH_FLOW_QUANTIFIED_AMOUNT_EVIDENCE_REQUIRED")
            elif not trigger_refs or not set(effect_refs).intersection(trigger_refs):
                item_issues.append("CASH_FLOW_AMOUNT_EVIDENCE_NOT_SHARED_WITH_REVIEW_TRIGGER")
            if effect is not None:
                if effect > 0 and direction != "IMPROVES_FCF":
                    item_issues.append("POSITIVE_FCF_EFFECT_DIRECTION_MISMATCH")
                elif effect < 0 and direction != "REDUCES_FCF":
                    item_issues.append("NEGATIVE_FCF_EFFECT_DIRECTION_MISMATCH")
                elif effect == 0 and direction != "NO_DIRECT_EFFECT":
                    item_issues.append("ZERO_FCF_EFFECT_DIRECTION_MISMATCH")
            context_field = channel_context_field.get(channel)
            context = b4_cash_context.get(scenario, {})
            context_fields = context.get("fields") if isinstance(context.get("fields"), Mapping) else {}
            if context_field is None or context_fields.get(context_field) in (None, ""):
                item_issues.append(f"B4_CASH_CONTEXT_AMOUNT_UNAVAILABLE_FOR_QUANTIFIED_CHANNEL:{channel}")
            if context.get("financial_outputs_decision_usable") is not True:
                item_issues.append("B4_CASH_CONTEXT_NOT_DECISION_USABLE")
            if channel in {"WORKING_CAPITAL", "INVENTORY_MOVEMENT"}:
                reconciliation_status = _text(context_fields.get("inventory_reconciliation_status")).upper()
                valid_inventory_statuses = {
                    "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
                    "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL",
                    "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED",
                    "NOT_APPLICABLE_NO_TONNAGE_BASIS",
                }
                if reconciliation_status not in valid_inventory_statuses:
                    item_issues.append("B4_INVENTORY_WORKING_CAPITAL_RECONCILIATION_NOT_IDENTIFIABLE")
        elif raw_effect not in (None, ""):
            item_issues.append("UNQUANTIFIED_CASH_FLOW_ASSESSMENT_MUST_NOT_SUPPLY_AMOUNT")

        if quant_status == "NOT_APPLICABLE":
            if channel != "NO_DIRECT_CASH_EFFECT" or direction != "NO_DIRECT_EFFECT":
                item_issues.append("NOT_APPLICABLE_REQUIRES_EXPLICIT_NO_DIRECT_CASH_EFFECT")
            if raw_effect not in (None, ""):
                item_issues.append("NOT_APPLICABLE_CASH_FLOW_ASSESSMENT_MUST_NOT_SUPPLY_AMOUNT")
        elif channel == "NO_DIRECT_CASH_EFFECT" or direction == "NO_DIRECT_EFFECT":
            item_issues.append("NO_DIRECT_CASH_EFFECT_REQUIRES_NOT_APPLICABLE_STATUS")

        status = "CLASSIFIED_DIAGNOSTIC_ONLY" if not item_issues else "REVIEW_REQUIRED"
        item = {
            "scenario": scenario or "UNKNOWN",
            "attribution_id": attribution_id or "UNKNOWN",
            "driver_id": driver_id or "UNKNOWN",
            "review_trigger_id": trigger_id or "UNKNOWN",
            "channel": channel,
            "direction": direction,
            "quantification_status": quant_status,
            "cash_flow_effect_cny": _format(effect) if effect is not None and not item_issues else None,
            "cash_flow_effect_basis": effect_basis if effect is not None and not item_issues else None,
            "cash_flow_effect_data_class": effect_data_class if effect is not None and not item_issues else None,
            "cash_flow_effect_evidence_refs": effect_refs if effect is not None and not item_issues else [],
            "rationale": rationale or "UNKNOWN",
            "evidence_refs": refs,
            "status": status,
            "issues": sorted(set(item_issues)),
            "note": "本项按 FCF 方向解释：正数表示增加 FCF，负数表示减少 FCF；不得与营运资金余额变化符号混淆。",
        }
        normalized.append(item)
        global_issues.extend(f"{scenario.upper()}:{attribution_id or index}:{issue}" for issue in item_issues)
        if scenario in SCENARIOS:
            by_scenario[scenario].append(item)

    missing = sorted(set(expected_rows) - seen)
    for scenario, attribution_id in missing:
        issue = f"{scenario.upper()}:{attribution_id}:CASH_FLOW_ASSESSMENT_MISSING"
        global_issues.append(issue)
        by_scenario[scenario].append({
            "scenario": scenario,
            "attribution_id": attribution_id,
            "driver_id": _text(expected_rows[(scenario, attribution_id)].get("driver_id")) or "UNKNOWN",
            "review_trigger_id": _text(expected_rows[(scenario, attribution_id)].get("review_trigger_id")) or "UNKNOWN",
            "channel": "UNKNOWN",
            "direction": "UNKNOWN",
            "quantification_status": "UNKNOWN",
            "cash_flow_effect_cny": None,
            "rationale": "UNKNOWN",
            "evidence_refs": [],
            "status": "REVIEW_REQUIRED",
            "issues": ["CASH_FLOW_ASSESSMENT_MISSING"],
        })

    if variance_attribution.get("status") != "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY":
        global_issues.append("UPSTREAM_PROFIT_VARIANCE_NOT_RECONCILED")
    for scenario in SCENARIOS:
        by_scenario[scenario].sort(key=lambda item: item.get("attribution_id", ""))
    status = (
        "CASH_FLOW_PATH_LINKS_COMPLETE_DIAGNOSTIC_ONLY"
        if expected_rows and not global_issues and len(seen) == len(expected_rows)
        else "REVIEW_REQUIRED" if expected_rows else "NOT_COMPARABLE"
    )
    return {
        "status": status,
        "scenarios": by_scenario,
        "b4_cash_context": b4_cash_context,
        "issues": sorted(set(global_issues)),
        "cash_flow_amounts_aggregated": False,
        "normalized_fcf_comparison_available": False,
        "fcf_variance_reconciled": False,
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
        "formal_valuation_admission_created": False,
        "decision_authority": False,
        "note": "现金流路径与净利润归因分开登记；当前没有独立的正常化 FCF Bear/Base/Bull 基准，因此不把逐项金额合计成 FCF 差额，也不宣称 FCF 对账完成。",
    }


def _evaluate_normalized_fcf_bridge(
    *,
    raw_normalized_fcf: Any,
    raw_fcf_attributions: Any,
    operating_driver_forecast: Mapping[str, Any],
    known_driver_ids: set[str],
    raw_review_triggers: list[Any],
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
) -> dict[str, Any]:
    """Build B48 normalized-FCF and B49 measured component-level variance bridges."""
    empty = {
        "status": "NOT_IDENTIFIABLE",
        "normalized_fcf": {"status": "NOT_IDENTIFIABLE", "scenarios": {}, "issues": ["NORMALIZED_FCF_NOT_PROVIDED"]},
        "b4_comparison": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["B4_NORMALIZED_FCF_COMPARISON_NOT_IDENTIFIABLE"]},
        "component_variance_bridge": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["FCF_COMPONENT_VARIANCE_BRIDGE_NOT_IDENTIFIABLE"]},
        "variance_attribution": {"status": "NOT_COMPARABLE", "scenarios": {}, "issues": ["FCF_VARIANCE_ATTRIBUTION_NOT_PROVIDED"]},
        "issues": ["NORMALIZED_FCF_NOT_PROVIDED"],
        "sign_convention": "B4_UNLEVERED_FCF_PROXY_MINUS_NORMALIZED_FCF; positive means B4 FCF is higher",
        "tolerance_cny": "1",
        "normalized_fcf_comparison_available": False,
        "fcf_variance_reconciled": False,
        "cash_flow_amounts_aggregated": False,
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
        "formal_valuation_admission_created": False,
        "decision_authority": False,
    }
    if not isinstance(raw_normalized_fcf, Mapping):
        return empty

    allowed_scopes = {"COMPANY_WIDE", "PRODUCT_LINE", "PROJECT_INCREMENTAL"}
    allowed_categories = {
        "OPERATING_CASH_CONVERSION", "WORKING_CAPITAL", "INVENTORY_MOVEMENT",
        "CAPEX", "NON_CASH_EARNINGS", "TAX_CASH_TIMING", "OTHER",
    }
    variance_component_categories = {
        "OPERATING_CASH_CONVERSION", "NON_CASH_EARNINGS", "CAPEX",
        "WORKING_CAPITAL", "INVENTORY_MOVEMENT",
    }
    def _scenario_decimal(value: Any, label: str) -> Decimal:
        if isinstance(value, Mapping):
            value = value.get("value")
        return _decimal(value, label)

    monitor_issues: list[str] = []
    norm = raw_normalized_fcf
    metric = _text(norm.get("metric")).upper()
    method = _text(norm.get("method")).upper()
    scope = _text(norm.get("scope") or "UNKNOWN").upper()
    period = _text(norm.get("period"))
    reference_period = _text(norm.get("reference_period"))
    basis = _text(norm.get("normalization_basis"))
    b4_scope = _text(operating_driver_forecast.get("scope") or "UNKNOWN").upper()
    b4_period = _text(operating_driver_forecast.get("forecast_period") or "UNKNOWN")
    if not _meaningful(metric):
        monitor_issues.append("NORMALIZED_FCF_METRIC_REQUIRED")
        metric = "UNKNOWN"
    elif metric != "UNLEVERED_FCF_PROXY_CNY":
        monitor_issues.append("NORMALIZED_FCF_METRIC_UNSUPPORTED")
    if method != NORMALIZED_FCF_METHOD:
        monitor_issues.append("NORMALIZED_FCF_METHOD_MISMATCH_B4_PROXY_FORMULA")
    if scope not in allowed_scopes:
        monitor_issues.append("NORMALIZED_FCF_SCOPE_NOT_IDENTIFIABLE")
    if not _meaningful(period):
        monitor_issues.append("NORMALIZED_FCF_PERIOD_NOT_IDENTIFIABLE")
    if not _meaningful(reference_period):
        monitor_issues.append("NORMALIZED_FCF_REFERENCE_PERIOD_NOT_IDENTIFIABLE")
    if not _meaningful(basis):
        monitor_issues.append("NORMALIZED_FCF_NORMALIZATION_BASIS_NOT_IDENTIFIABLE")

    sources_normalized = norm.get("scenarios") if isinstance(norm.get("scenarios"), Mapping) else {}
    normalized_scenarios: dict[str, dict[str, Any]] = {}
    point_values: dict[str, Decimal] = {}
    normalized_complete = not monitor_issues
    for name in SCENARIOS:
        raw_scenario = sources_normalized.get(name) if isinstance(sources_normalized.get(name), Mapping) else {}
        item_issues: list[str] = []
        scenario_basis = _text(raw_scenario.get("scenario_basis"))
        if not _meaningful(scenario_basis):
            item_issues.append("SCENARIO_BASIS_NOT_IDENTIFIABLE")
        reference, ref_issues, ref_evidence = _money(
            raw_scenario.get("reference_fcf_cny"),
            field=f"normalized_fcf.{name}.reference_fcf_cny",
            sources_by_id=sources_by_id,
            unresolved_refs=unresolved_refs,
            after_cutoff_refs=after_cutoff_refs,
            uncertain_refs=uncertain_refs,
            allow_negative=True,
        )
        item_issues.extend(ref_issues)
        reference_measure = raw_scenario.get("reference_fcf_cny")
        if not ref_evidence:
            item_issues.append("NORMALIZED_FCF_REFERENCE_EVIDENCE_REQUIRED")

        raw_adjustments = raw_scenario.get("adjustments")
        raw_adjustments = raw_adjustments if isinstance(raw_adjustments, list) else []
        adjustments: list[dict[str, Any]] = []
        adjustment_ids: set[str] = set()
        adjustment_total = Decimal("0")
        adjustment_values_complete = True
        for index, row in enumerate(raw_adjustments):
            if not isinstance(row, Mapping):
                item_issues.append(f"ADJUSTMENT_{index}_INVALID")
                adjustment_values_complete = False
                continue
            adjustment_id = _text(row.get("adjustment_id"))
            driver_id = _text(row.get("driver_id"))
            trigger_id = _text(row.get("review_trigger_id"))
            category = _text(row.get("category")).upper()
            rationale = _text(row.get("rationale"))
            row_issues: list[str] = []
            if not adjustment_id:
                row_issues.append("ADJUSTMENT_ID_REQUIRED")
            elif adjustment_id in adjustment_ids:
                row_issues.append(f"DUPLICATE_ADJUSTMENT_ID:{adjustment_id}")
            adjustment_ids.add(adjustment_id)
            if driver_id not in known_driver_ids:
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_DRIVER_UNRESOLVED")
            if category not in allowed_categories:
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_CATEGORY_UNSUPPORTED")
            if not _meaningful(rationale):
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_RATIONALE_NOT_IDENTIFIABLE")
            trigger = next(
                (candidate for candidate in raw_review_triggers
                 if isinstance(candidate, Mapping) and _text(candidate.get("trigger_id")) == trigger_id),
                None,
            )
            if trigger is None:
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_REVIEW_TRIGGER_UNRESOLVED")
            elif _text(trigger.get("driver_id")) != driver_id:
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_TRIGGER_DRIVER_MISMATCH")
            amount, amount_issues, amount_refs = _money(
                row.get("amount_cny"),
                field=f"normalized_fcf.{name}.adjustment.{adjustment_id or index}.amount_cny",
                sources_by_id=sources_by_id,
                unresolved_refs=unresolved_refs,
                after_cutoff_refs=after_cutoff_refs,
                uncertain_refs=uncertain_refs,
                allow_negative=True,
            )
            row_issues.extend(amount_issues)
            if not amount_refs:
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_EVIDENCE_REQUIRED")
            trigger_refs_raw = trigger.get("evidence_refs") if isinstance(trigger, Mapping) and isinstance(trigger.get("evidence_refs"), list) else []
            trigger_refs = {_text(ref) for ref in trigger_refs_raw if _text(ref)}
            if not trigger_refs:
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_TRIGGER_EVIDENCE_REQUIRED")
            elif not set(amount_refs).intersection(trigger_refs):
                row_issues.append("NORMALIZED_FCF_ADJUSTMENT_EVIDENCE_NOT_SHARED_WITH_TRIGGER")
            if amount is not None and not row_issues:
                adjustment_total += amount
            else:
                adjustment_values_complete = False
            adjustments.append({
                "adjustment_id": adjustment_id or f"UNKNOWN_{index}",
                "driver_id": driver_id or "UNKNOWN",
                "review_trigger_id": trigger_id or "UNKNOWN",
                "category": category or "UNKNOWN",
                "rationale": rationale or "UNKNOWN",
                "amount_cny": _format(amount) if amount is not None and not row_issues else None,
                "evidence_refs": amount_refs,
                "issues": sorted(set(row_issues)),
            })
            item_issues.extend(f"ADJUSTMENT:{adjustment_id or index}:{issue}" for issue in row_issues)
        if not raw_adjustments:
            item_issues.append("NORMALIZED_FCF_ADJUSTMENTS_REQUIRED_EVEN_FOR_ZERO_BRIDGE")
        adjustment_categories = {
            _text(row.get("category")).upper()
            for row in raw_adjustments if isinstance(row, Mapping)
        }
        for required_category in ("CAPEX", "WORKING_CAPITAL", "INVENTORY_MOVEMENT"):
            if required_category not in adjustment_categories:
                item_issues.append(f"NORMALIZED_FCF_COMPONENT_COVERAGE_MISSING:{required_category}")

        numeric_fields: dict[str, Decimal | None] = {}
        for key in ("low_fcf_cny", "point_fcf_cny", "high_fcf_cny"):
            try:
                numeric_fields[key] = _decimal(raw_scenario.get(key), f"normalized_fcf.{name}.{key}")
            except ValueError:
                numeric_fields[key] = None
                item_issues.append(f"{key.upper()}_NOT_IDENTIFIABLE")
        low_value, point_value, high_value = (
            numeric_fields["low_fcf_cny"], numeric_fields["point_fcf_cny"], numeric_fields["high_fcf_cny"]
        )
        if low_value is not None and point_value is not None and high_value is not None and not (low_value <= point_value <= high_value):
            item_issues.append("NORMALIZED_FCF_LOW_POINT_HIGH_ORDER_INVALID")

        # Independently re-compute the normalized FCF point from the same B4 proxy
        # formula, and reconcile raw/effective working capital so inventory is not
        # silently double-counted or omitted.
        components_raw = raw_scenario.get("cash_components")
        components_raw = components_raw if isinstance(components_raw, Mapping) else {}
        component_values: dict[str, Decimal | None] = {}
        component_output: dict[str, Any] = {}
        component_issues: list[str] = []
        component_contract = (
            ("ebit_cny", True),
            ("depreciation_amortization_cny", False),
            ("cash_capex_cny", False),
            ("change_working_capital_cny", True),
            ("effective_change_working_capital_cny", True),
        )
        if not components_raw:
            component_issues.append("NORMALIZED_FCF_CASH_COMPONENTS_REQUIRED")
        for component_field, allow_negative in component_contract:
            value, value_issues, value_refs = _money(
                components_raw.get(component_field),
                field=f"normalized_fcf.{name}.cash_components.{component_field}",
                sources_by_id=sources_by_id,
                unresolved_refs=unresolved_refs,
                after_cutoff_refs=after_cutoff_refs,
                uncertain_refs=uncertain_refs,
                allow_negative=allow_negative,
            )
            if not value_refs:
                value_issues.append(f"NORMALIZED_FCF_CASH_COMPONENT_EVIDENCE_REQUIRED:{component_field}")
            component_values[component_field] = value if not value_issues else None
            component_output[component_field] = {
                "value": _format(value) if value is not None and not value_issues else None,
                "unit": "CNY",
                "evidence_refs": value_refs,
                "issues": sorted(set(value_issues)),
            }
            component_issues.extend(value_issues)

        raw_tax = components_raw.get("tax_rate")
        tax_value: Decimal | None = None
        tax_refs: list[str] = []
        tax_issues: list[str] = []
        if not isinstance(raw_tax, Mapping):
            tax_issues.append("NORMALIZED_FCF_TAX_RATE_TYPED_RATIO_REQUIRED")
        else:
            if _text(raw_tax.get("unit")).lower() != "ratio":
                tax_issues.append("NORMALIZED_FCF_TAX_RATE_UNIT_MUST_BE_RATIO")
            tax_class = _text(raw_tax.get("data_class")).upper()
            if tax_class not in {"OBSERVED_ACTUAL", "ISSUER_FORECAST", "ANALYST_ASSUMPTION"}:
                tax_issues.append("NORMALIZED_FCF_TAX_RATE_DATA_CLASS_NOT_IDENTIFIABLE")
            if not _meaningful(raw_tax.get("basis")):
                tax_issues.append("NORMALIZED_FCF_TAX_RATE_BASIS_NOT_IDENTIFIABLE")
            try:
                tax_value = _decimal(raw_tax.get("value"), "NORMALIZED_FCF_TAX_RATE")
                if tax_value < 0 or tax_value > 1:
                    tax_issues.append("NORMALIZED_FCF_TAX_RATE_OUTSIDE_ZERO_TO_ONE")
            except ValueError:
                tax_value = None
                tax_issues.append("NORMALIZED_FCF_TAX_RATE_NOT_IDENTIFIABLE")
            tax_refs, tax_ref_issues = _resolve_refs(
                raw_tax.get("evidence_refs"),
                field=f"normalized_fcf.{name}.cash_components.tax_rate",
                sources_by_id=sources_by_id,
                unresolved_refs=unresolved_refs,
                after_cutoff_refs=after_cutoff_refs,
                uncertain_refs=uncertain_refs,
                required=tax_class in {"OBSERVED_ACTUAL", "ISSUER_FORECAST"},
            )
            tax_issues.extend(tax_ref_issues)
            if not tax_refs:
                tax_issues.append("NORMALIZED_FCF_TAX_RATE_EVIDENCE_REQUIRED")
        component_output["tax_rate"] = {
            "value": _format(tax_value) if tax_value is not None and not tax_issues else None,
            "unit": "ratio",
            "evidence_refs": tax_refs,
            "issues": sorted(set(tax_issues)),
        }
        component_issues.extend(tax_issues)

        treatment = _text(components_raw.get("inventory_working_capital_treatment")).upper()
        inventory_status = _text(components_raw.get("inventory_reconciliation_status")).upper()
        if treatment not in {
            "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
            "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
            "NOT_APPLICABLE",
            "NOT_APPLICABLE_NO_TONNAGE_BASIS",
        }:
            component_issues.append("NORMALIZED_FCF_INVENTORY_TREATMENT_NOT_IDENTIFIABLE")
        if not _meaningful(inventory_status):
            component_issues.append("NORMALIZED_FCF_INVENTORY_RECONCILIATION_STATUS_NOT_IDENTIFIABLE")
        valid_inventory_statuses = {
            "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
            "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL",
            "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED",
            "NOT_APPLICABLE_NO_TONNAGE_BASIS",
        }
        if inventory_status not in valid_inventory_statuses:
            component_issues.append("NORMALIZED_FCF_INVENTORY_RECONCILIATION_NOT_PASS")
        inventory_proxy: Decimal | None = None
        raw_inventory_proxy = components_raw.get("inventory_cash_impact_proxy_cny")
        if raw_inventory_proxy not in (None, "") and not (
            isinstance(raw_inventory_proxy, Mapping)
            and raw_inventory_proxy.get("value") in (None, "")
            and treatment != "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL"
        ):
            inventory_proxy, proxy_issues, proxy_refs = _money(
                raw_inventory_proxy,
                field=f"normalized_fcf.{name}.cash_components.inventory_cash_impact_proxy_cny",
                sources_by_id=sources_by_id,
                unresolved_refs=unresolved_refs,
                after_cutoff_refs=after_cutoff_refs,
                uncertain_refs=uncertain_refs,
                allow_negative=True,
            )
            if not proxy_refs:
                proxy_issues.append("NORMALIZED_FCF_INVENTORY_PROXY_EVIDENCE_REQUIRED")
            component_issues.extend(proxy_issues)
            component_output["inventory_cash_impact_proxy_cny"] = {
                "value": _format(inventory_proxy) if inventory_proxy is not None and not proxy_issues else None,
                "unit": "CNY",
                "evidence_refs": proxy_refs,
                "issues": sorted(set(proxy_issues)),
            }
        elif treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL":
            component_issues.append("NORMALIZED_FCF_INVENTORY_PROXY_REQUIRED_WHEN_INVENTORY_EXCLUDED")
        component_output["inventory_working_capital_treatment"] = treatment or "UNKNOWN"
        component_output["inventory_reconciliation_status"] = inventory_status or "UNKNOWN"

        change_wc = component_values.get("change_working_capital_cny")
        effective_wc = component_values.get("effective_change_working_capital_cny")
        if change_wc is not None and effective_wc is not None:
            if treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL":
                if "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL" not in inventory_status:
                    component_issues.append("NORMALIZED_FCF_EXCLUDED_INVENTORY_RECONCILIATION_STATUS_MISMATCH")
                if inventory_proxy is None:
                    component_issues.append("NORMALIZED_FCF_INVENTORY_PROXY_NOT_IDENTIFIABLE")
                elif abs((change_wc + inventory_proxy) - effective_wc) > Decimal("1"):
                    component_issues.append("NORMALIZED_FCF_NONINVENTORY_WC_PLUS_INVENTORY_PROXY_MISMATCH")
            elif treatment == "INCLUDED_IN_CHANGE_WORKING_CAPITAL":
                if "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL" not in inventory_status:
                    component_issues.append("NORMALIZED_FCF_INCLUDED_INVENTORY_RECONCILIATION_STATUS_MISMATCH")
                if abs(change_wc - effective_wc) > Decimal("1"):
                    component_issues.append("NORMALIZED_FCF_INCLUDED_WC_EFFECTIVE_WC_MISMATCH")
            elif treatment in {"NOT_APPLICABLE", "NOT_APPLICABLE_NO_TONNAGE_BASIS"}:
                valid_zero_status = (
                    inventory_status == "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED"
                    or inventory_status == "NOT_APPLICABLE_NO_TONNAGE_BASIS"
                )
                if not valid_zero_status:
                    component_issues.append("NORMALIZED_FCF_NOT_APPLICABLE_INVENTORY_STATUS_MISMATCH")
                if abs(change_wc - effective_wc) > Decimal("1"):
                    component_issues.append("NORMALIZED_FCF_NOT_APPLICABLE_WC_EFFECTIVE_WC_MISMATCH")

        calculated_fcf: Decimal | None = None
        ebit = component_values.get("ebit_cny")
        da = component_values.get("depreciation_amortization_cny")
        capex = component_values.get("cash_capex_cny")
        if all(value is not None for value in (ebit, da, capex, effective_wc, tax_value)) and not component_issues:
            calculated_fcf = ebit - max(ebit, Decimal("0")) * tax_value + da - capex - effective_wc
            if point_value is not None and abs(calculated_fcf - point_value) > Decimal("1"):
                component_issues.append("NORMALIZED_FCF_CASH_COMPONENT_FORMULA_MISMATCH_WITHIN_CNY_1")
        else:
            component_issues.append("NORMALIZED_FCF_CASH_COMPONENT_FORMULA_NOT_IDENTIFIABLE")
        component_output["calculated_fcf_point_cny"] = _format(calculated_fcf) if calculated_fcf is not None else None
        component_output["issues"] = sorted(set(component_issues))
        item_issues.extend(f"CASH_COMPONENT:{issue}" for issue in component_issues)

        if reference is not None and point_value is not None and adjustment_values_complete:
            residual = reference + adjustment_total - point_value
            if abs(residual) > Decimal("1"):
                item_issues.append("NORMALIZED_FCF_REFERENCE_PLUS_ADJUSTMENTS_DO_NOT_RECONCILE_WITHIN_CNY_1")
        else:
            residual = None
            item_issues.append("NORMALIZED_FCF_BRIDGE_RESIDUAL_NOT_IDENTIFIABLE")
        if reference is not None and point_value is not None and high_value is not None and low_value is not None and not item_issues:
            point_values[name] = point_value
        elif point_value is not None and not item_issues:
            point_values[name] = point_value
        else:
            normalized_complete = False
        scenario_status = "NORMALIZED_FCF_BRIDGE_RECONCILED_DIAGNOSTIC_ONLY" if not item_issues else "REVIEW_REQUIRED"
        normalized_scenarios[name] = {
            "scenario": name,
            "status": scenario_status,
            "reference_fcf_cny": _format(reference) if reference is not None and not ref_issues else None,
            "reference_period": reference_period or "UNKNOWN",
            "period": period or "UNKNOWN",
            "adjustment_total_cny": _format(adjustment_total) if adjustment_values_complete else None,
            "low_fcf_cny": _format(low_value),
            "point_fcf_cny": _format(point_value),
            "high_fcf_cny": _format(high_value),
            "bridge_residual_cny": _format(residual),
            "cash_components": component_output,
            "adjustments": adjustments,
            "scenario_basis": scenario_basis or "UNKNOWN",
            "issues": sorted(set(item_issues)),
        }
        if item_issues:
            monitor_issues.extend(f"{name.upper()}:{issue}" for issue in item_issues)

    if set(point_values) == set(SCENARIOS) and not (point_values["bear"] <= point_values["base"] <= point_values["bull"]):
        normalized_complete = False
        monitor_issues.append("NORMALIZED_FCF_BEAR_BASE_BULL_POINT_ORDER_INVALID")
    normalized_status = "NORMALIZED_FCF_BRIDGE_RECONCILED_DIAGNOSTIC_ONLY" if normalized_complete and not monitor_issues else "REVIEW_REQUIRED"
    normalized_result = {
        "status": normalized_status,
        "metric": metric,
        "method": method or "UNKNOWN",
        "scope": scope,
        "reference_period": reference_period or "UNKNOWN",
        "period": period or "UNKNOWN",
        "normalization_basis": basis or "UNKNOWN",
        "scenarios": normalized_scenarios,
        "issues": sorted(set(monitor_issues)),
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
    }


    b4_rows = operating_driver_forecast.get("scenarios")
    b4_rows = b4_rows if isinstance(b4_rows, Mapping) else {}
    comparable = (
        normalized_status == "NORMALIZED_FCF_BRIDGE_RECONCILED_DIAGNOSTIC_ONLY"
        and scope == b4_scope and period == b4_period
    )
    comparisons: dict[str, dict[str, Any]] = {}
    comparison_issues: list[str] = []
    b4_component_values: dict[str, dict[str, Any]] = {}
    required_b4_fields = (
        "ebit_cny", "tax_rate", "depreciation_amortization_cny",
        "cash_capex_cny", "change_working_capital_cny",
        "effective_change_working_capital_cny",
    )
    valid_inventory_statuses = {
        "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
        "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL",
        "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED",
        "NOT_APPLICABLE_NO_TONNAGE_BASIS",
    }
    for name in SCENARIOS:
        b4_row = b4_rows.get(name) if isinstance(b4_rows.get(name), Mapping) else {}
        row_issues: list[str] = []
        if b4_row.get("financial_outputs_decision_usable") is not True:
            row_issues.append("B4_FCF_OUTPUT_NOT_DECISION_USABLE")
        values: dict[str, Decimal | None] = {}
        for component_field in required_b4_fields:
            try:
                values[component_field] = _scenario_decimal(
                    b4_row.get(component_field), f"b4.{name}.{component_field}"
                )
            except ValueError:
                values[component_field] = None
                row_issues.append("B4_FCF_COMPONENT_NOT_IDENTIFIABLE:" + component_field)
        tax_rate = values.get("tax_rate")
        if tax_rate is not None and not (Decimal("0") <= tax_rate <= Decimal("1")):
            row_issues.append("B4_FCF_TAX_RATE_OUTSIDE_ZERO_TO_ONE")

        inventory_treatment = _text(b4_row.get("inventory_working_capital_treatment")).upper()
        inventory_status = _text(b4_row.get("inventory_reconciliation_status")).upper()
        if inventory_treatment not in {
            "INCLUDED_IN_CHANGE_WORKING_CAPITAL", "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
            "NOT_APPLICABLE", "NOT_APPLICABLE_NO_TONNAGE_BASIS",
        }:
            row_issues.append("B4_INVENTORY_WORKING_CAPITAL_TREATMENT_NOT_IDENTIFIABLE")
        if inventory_status not in valid_inventory_statuses:
            row_issues.append("B4_INVENTORY_WORKING_CAPITAL_RECONCILIATION_NOT_IDENTIFIABLE")
        inventory_proxy: Decimal | None = None
        raw_inventory_proxy = b4_row.get("inventory_cash_impact_proxy_cny")
        if raw_inventory_proxy not in (None, "") and not (
            isinstance(raw_inventory_proxy, Mapping)
            and raw_inventory_proxy.get("value") in (None, "")
            and inventory_treatment != "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL"
        ):
            try:
                inventory_proxy = _scenario_decimal(
                    raw_inventory_proxy, f"b4.{name}.inventory_cash_impact_proxy_cny"
                )
            except ValueError:
                row_issues.append("B4_INVENTORY_CASH_IMPACT_PROXY_NOT_IDENTIFIABLE")

        change_wc = values.get("change_working_capital_cny")
        effective_wc = values.get("effective_change_working_capital_cny")
        if inventory_treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL":
            if inventory_status != "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL":
                row_issues.append("B4_EXCLUDED_INVENTORY_RECONCILIATION_STATUS_MISMATCH")
            if inventory_proxy is None:
                row_issues.append("B4_INVENTORY_CASH_IMPACT_PROXY_REQUIRED_WHEN_INVENTORY_EXCLUDED")
            elif change_wc is not None and effective_wc is not None and abs(change_wc + inventory_proxy - effective_wc) > Decimal("1"):
                row_issues.append("B4_NONINVENTORY_WC_PLUS_INVENTORY_PROXY_MISMATCH")
        elif inventory_treatment == "INCLUDED_IN_CHANGE_WORKING_CAPITAL":
            if inventory_status != "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL":
                row_issues.append("B4_INCLUDED_INVENTORY_RECONCILIATION_STATUS_MISMATCH")
            if change_wc is not None and effective_wc is not None and abs(change_wc - effective_wc) > Decimal("1"):
                row_issues.append("B4_INCLUDED_WC_EFFECTIVE_WC_MISMATCH")
        elif inventory_treatment in {"NOT_APPLICABLE", "NOT_APPLICABLE_NO_TONNAGE_BASIS"}:
            status_ok = (
                inventory_status == "NOT_APPLICABLE_NO_TONNAGE_BASIS"
                if inventory_treatment == "NOT_APPLICABLE_NO_TONNAGE_BASIS"
                else inventory_status in {
                    "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED",
                    "NOT_APPLICABLE_NO_TONNAGE_BASIS",
                }
            )
            if not status_ok:
                row_issues.append("B4_NOT_APPLICABLE_INVENTORY_STATUS_MISMATCH")
            if change_wc is not None and effective_wc is not None and abs(change_wc - effective_wc) > Decimal("1"):
                row_issues.append("B4_NOT_APPLICABLE_WC_EFFECTIVE_WC_MISMATCH")

        try:
            b4_fcf = _scenario_decimal(
                b4_row.get("unlevered_fcf_proxy_cny"), f"b4.{name}.unlevered_fcf_proxy_cny"
            )
        except ValueError:
            b4_fcf = None
            row_issues.append("B4_FCF_PROXY_NOT_IDENTIFIABLE")

        calculated_b4_fcf: Decimal | None = None
        ebit = values.get("ebit_cny")
        da = values.get("depreciation_amortization_cny")
        capex = values.get("cash_capex_cny")
        if all(value is not None for value in (ebit, tax_rate, da, capex, effective_wc)):
            calculated_b4_fcf = ebit - max(ebit, Decimal("0")) * tax_rate + da - capex - effective_wc
            if b4_fcf is not None and abs(calculated_b4_fcf - b4_fcf) > Decimal("1"):
                row_issues.append("B4_FCF_CASH_COMPONENT_FORMULA_MISMATCH_WITHIN_CNY_1")
        else:
            row_issues.append("B4_FCF_CASH_COMPONENT_FORMULA_NOT_IDENTIFIABLE")

        b4_component_values[name] = {
            "values": values,
            "inventory_treatment": inventory_treatment or "UNKNOWN",
            "inventory_status": inventory_status or "UNKNOWN",
            "inventory_proxy": inventory_proxy,
            "b4_fcf": b4_fcf,
            "calculated_fcf": calculated_b4_fcf,
            "issues": sorted(set(row_issues)),
        }
        norm_point = point_values.get(name)
        if norm_point is None:
            row_issues.append("NORMALIZED_FCF_POINT_NOT_IDENTIFIABLE")
        difference = b4_fcf - norm_point if b4_fcf is not None and norm_point is not None else None
        status = "COMPARABLE_DIAGNOSTIC_ONLY" if comparable and not row_issues else "NOT_COMPARABLE_OR_REVIEW_REQUIRED"
        comparisons[name] = {
            "b4_unlevered_fcf_proxy_cny": _format(b4_fcf) if b4_fcf is not None and not row_issues else None,
            "normalized_fcf_point_cny": _format(norm_point),
            "b4_minus_normalized_fcf_cny": _format(difference) if difference is not None and comparable and not row_issues else None,
            "status": status,
            "issues": sorted(set(row_issues)),
        }
        if row_issues:
            comparison_issues.extend(f"{name.upper()}:{issue}" for issue in row_issues)
    comparison_complete = comparable and all(row.get("status") == "COMPARABLE_DIAGNOSTIC_ONLY" for row in comparisons.values())
    comparison_result = {
        "status": "DIAGNOSTIC_ONLY_NOT_A_VALUATION_INPUT" if comparison_complete else "NOT_COMPARABLE",
        "scope": scope,
        "period": period,
        "method": method or "UNKNOWN",
        "scenarios": comparisons,
        "issues": sorted(set(comparison_issues)),
        "note": "B4 FCF 仅在自身财务输出可用于决策且范围/期间一致时比较；并须按同一 FCF 公式复算 B4 组件，不改变 B4 结果。",
    }

    # B49: measure each B4-minus-normalized component contribution independently.
    # Each contribution uses the sign convention B4 FCF minus normalized FCF.
    component_bridges: dict[str, dict[str, Any]] = {}
    component_bridge_issues: list[str] = []
    not_applicable_treatments = {"NOT_APPLICABLE", "NOT_APPLICABLE_NO_TONNAGE_BASIS"}
    for name in SCENARIOS:
        b4_components = b4_component_values.get(name, {})
        b4_values = b4_components.get("values") if isinstance(b4_components.get("values"), Mapping) else {}
        norm_row = normalized_scenarios.get(name, {})
        norm_components = norm_row.get("cash_components") if isinstance(norm_row.get("cash_components"), Mapping) else {}
        norm_values: dict[str, Decimal | None] = {}
        local_issues: list[str] = []
        component_fields = (
            "ebit_cny", "tax_rate", "depreciation_amortization_cny",
            "cash_capex_cny", "change_working_capital_cny",
            "effective_change_working_capital_cny",
        )
        for field in component_fields:
            component = norm_components.get(field) if isinstance(norm_components.get(field), Mapping) else {}
            try:
                norm_values[field] = _scenario_decimal(
                    component.get("value"), f"normalized_fcf.{name}.{field}"
                )
            except ValueError:
                norm_values[field] = None
                local_issues.append(f"NORMALIZED_FCF_COMPONENT_NOT_IDENTIFIABLE:{field}")

        norm_treatment = _text(norm_components.get("inventory_working_capital_treatment")).upper()
        norm_status = _text(norm_components.get("inventory_reconciliation_status")).upper()
        norm_inventory_proxy: Decimal | None = None
        norm_proxy_component = norm_components.get("inventory_cash_impact_proxy_cny")
        if isinstance(norm_proxy_component, Mapping) and norm_proxy_component.get("value") not in (None, ""):
            try:
                norm_inventory_proxy = _scenario_decimal(
                    norm_proxy_component.get("value"),
                    f"normalized_fcf.{name}.inventory_cash_impact_proxy_cny",
                )
            except ValueError:
                local_issues.append("NORMALIZED_FCF_INVENTORY_PROXY_NOT_IDENTIFIABLE")

        b4_treatment = _text(b4_components.get("inventory_treatment")).upper()
        b4_inventory_proxy = b4_components.get("inventory_proxy")
        if comparisons.get(name, {}).get("status") != "COMPARABLE_DIAGNOSTIC_ONLY":
            local_issues.append("B4_AND_NORMALIZED_FCF_COMPONENTS_NOT_COMPARABLE")
        if b4_treatment != norm_treatment:
            if not (b4_treatment in not_applicable_treatments and norm_treatment in not_applicable_treatments):
                local_issues.append("B4_NORMALIZED_INVENTORY_TREATMENT_MISMATCH")
        allowed_treatments = {
            "INCLUDED_IN_CHANGE_WORKING_CAPITAL", "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
            "NOT_APPLICABLE", "NOT_APPLICABLE_NO_TONNAGE_BASIS",
        }
        if b4_treatment not in allowed_treatments or norm_treatment not in allowed_treatments:
            local_issues.append("B4_NORMALIZED_INVENTORY_TREATMENT_NOT_IDENTIFIABLE")

        contributions: dict[str, Decimal] = {}
        required_component_values = (
            b4_values.get("ebit_cny"), b4_values.get("tax_rate"),
            b4_values.get("depreciation_amortization_cny"), b4_values.get("cash_capex_cny"),
            b4_values.get("change_working_capital_cny"), b4_values.get("effective_change_working_capital_cny"),
            norm_values.get("ebit_cny"), norm_values.get("tax_rate"),
            norm_values.get("depreciation_amortization_cny"), norm_values.get("cash_capex_cny"),
            norm_values.get("change_working_capital_cny"), norm_values.get("effective_change_working_capital_cny"),
        )
        b4_fcf = b4_components.get("b4_fcf")
        norm_point = point_values.get(name)
        if all(value is not None for value in required_component_values):
            b4_ebit = b4_values["ebit_cny"]
            b4_tax = b4_values["tax_rate"]
            norm_ebit = norm_values["ebit_cny"]
            norm_tax = norm_values["tax_rate"]
            contributions["OPERATING_CASH_CONVERSION"] = (
                b4_ebit - max(b4_ebit, Decimal("0")) * b4_tax
                - (norm_ebit - max(norm_ebit, Decimal("0")) * norm_tax)
            )
            contributions["NON_CASH_EARNINGS"] = (
                b4_values["depreciation_amortization_cny"]
                - norm_values["depreciation_amortization_cny"]
            )
            contributions["CAPEX"] = (
                norm_values["cash_capex_cny"] - b4_values["cash_capex_cny"]
            )
            if b4_treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL" and norm_treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL":
                if b4_inventory_proxy is None or norm_inventory_proxy is None:
                    local_issues.append("FCF_COMPONENT_INVENTORY_PROXY_NOT_IDENTIFIABLE")
                else:
                    contributions["WORKING_CAPITAL"] = (
                        norm_values["change_working_capital_cny"]
                        - b4_values["change_working_capital_cny"]
                    )
                    contributions["INVENTORY_MOVEMENT"] = norm_inventory_proxy - b4_inventory_proxy
                    effective_wc_delta = (
                        norm_values["effective_change_working_capital_cny"]
                        - b4_values["effective_change_working_capital_cny"]
                    )
                    if abs(
                        contributions["WORKING_CAPITAL"]
                        + contributions["INVENTORY_MOVEMENT"] - effective_wc_delta
                    ) > Decimal("1"):
                        local_issues.append("FCF_COMPONENT_WC_PLUS_INVENTORY_DOES_NOT_MATCH_EFFECTIVE_WC_DELTA")
            elif (
                b4_treatment == "INCLUDED_IN_CHANGE_WORKING_CAPITAL"
                and norm_treatment == "INCLUDED_IN_CHANGE_WORKING_CAPITAL"
            ) or (
                b4_treatment in not_applicable_treatments
                and norm_treatment in not_applicable_treatments
            ):
                contributions["WORKING_CAPITAL"] = (
                    norm_values["effective_change_working_capital_cny"]
                    - b4_values["effective_change_working_capital_cny"]
                )
                # Inventory is already embedded in effective working capital, or is not applicable:
                # a separate inventory contribution must be zero to prevent double counting.
                contributions["INVENTORY_MOVEMENT"] = Decimal("0")
            else:
                local_issues.append("FCF_COMPONENT_INVENTORY_TREATMENT_NOT_COMPARABLE")

        difference = b4_fcf - norm_point if b4_fcf is not None and norm_point is not None else None
        contribution_total = sum(contributions.values(), Decimal("0")) if len(contributions) == 5 else None
        residual = difference - contribution_total if difference is not None and contribution_total is not None else None
        if contribution_total is None:
            local_issues.append("FCF_COMPONENT_CONTRIBUTIONS_NOT_IDENTIFIABLE")
        elif residual is not None and abs(residual) > Decimal("1"):
            local_issues.append("FCF_COMPONENT_CONTRIBUTIONS_DO_NOT_RECONCILE_WITHIN_CNY_1")

        status = (
            "COMPONENTS_RECONCILED_DIAGNOSTIC_ONLY"
            if comparison_complete and len(contributions) == 5 and residual is not None
            and abs(residual) <= Decimal("1") and not local_issues
            else "REVIEW_REQUIRED" if comparison_complete else "NOT_COMPARABLE"
        )
        component_bridges[name] = {
            "scenario": name,
            "status": status,
            "b4_minus_normalized_fcf_cny": _format(difference),
            "measured_component_total_cny": _format(contribution_total),
            "component_residual_cny": _format(residual),
            "b4_cash_components": {
                **{field: _format(value) if value is not None else None for field, value in b4_values.items()},
                "inventory_cash_impact_proxy_cny": _format(b4_inventory_proxy) if b4_inventory_proxy is not None else None,
                "inventory_working_capital_treatment": b4_treatment or "UNKNOWN",
                "inventory_reconciliation_status": b4_components.get("inventory_status", "UNKNOWN"),
                "calculated_fcf_point_cny": _format(b4_components.get("calculated_fcf")) if b4_components.get("calculated_fcf") is not None else None,
            },
            "normalized_cash_components": {
                **{field: _format(value) if value is not None else None for field, value in norm_values.items()},
                "inventory_cash_impact_proxy_cny": _format(norm_inventory_proxy) if norm_inventory_proxy is not None else None,
                "inventory_working_capital_treatment": norm_treatment or "UNKNOWN",
                "inventory_reconciliation_status": norm_status or "UNKNOWN",
                "calculated_fcf_point_cny": norm_components.get("calculated_fcf_point_cny"),
            },
            "contributions_cny": {category: _format(amount) for category, amount in contributions.items()},
            "inventory_component_basis": (
                "原始营运资金不含库存：WORKING_CAPITAL 使用原始非库存营运资金差额，"
                "INVENTORY_MOVEMENT 使用库存现金影响代理差额；两项之和须匹配有效营运资金差额。"
                if b4_treatment == norm_treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL"
                else "库存已包含在有效营运资金，或库存不适用：WORKING_CAPITAL 使用有效营运资金差额，"
                "INVENTORY_MOVEMENT 固定为 0，避免重复计算。"
            ),
            "issues": sorted(set(local_issues)),
            "valuation_input_eligible": False,
        }
        if local_issues:
            component_bridge_issues.extend(f"{name.upper()}:{issue}" for issue in local_issues)

    component_bridge_complete = comparison_complete and all(
        row.get("status") == "COMPONENTS_RECONCILED_DIAGNOSTIC_ONLY"
        for row in component_bridges.values()
    )
    component_bridge_result = {
        "status": "ALL_SCENARIOS_COMPONENTS_RECONCILED_DIAGNOSTIC_ONLY"
        if component_bridge_complete else ("REVIEW_REQUIRED" if comparison_complete else "NOT_COMPARABLE"),
        "sign_convention": "B4_UNLEVERED_FCF_PROXY_MINUS_NORMALIZED_FCF; each measured component contribution uses the same sign convention",
        "tolerance_cny": "1",
        "scenarios": component_bridges,
        "issues": sorted(set(component_bridge_issues)),
        "cash_flow_amounts_aggregated": False,
        "valuation_input_eligible": False,
    }

    raw_attributions = raw_fcf_attributions if isinstance(raw_fcf_attributions, list) else []
    trigger_map = {
        _text(row.get("trigger_id")): row for row in raw_review_triggers
        if isinstance(row, Mapping) and _text(row.get("trigger_id"))
    }
    attribution_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in SCENARIOS}
    attribution_issues: list[str] = []
    attribution_ids: set[tuple[str, str]] = set()
    for index, row in enumerate(raw_attributions):
        if not isinstance(row, Mapping):
            attribution_issues.append(f"FCF_VARIANCE_ATTRIBUTION_{index}_INVALID")
            continue
        scenario = _text(row.get("scenario")).lower()
        if scenario not in SCENARIOS:
            attribution_issues.append(f"FCF_VARIANCE_ATTRIBUTION_{index}_SCENARIO_INVALID")
            continue
        attribution_id = _text(row.get("fcf_attribution_id"))
        driver_id = _text(row.get("driver_id"))
        trigger_id = _text(row.get("review_trigger_id"))
        category = _text(row.get("category")).upper()
        rationale = _text(row.get("rationale"))
        row_issues: list[str] = []
        key = (scenario, attribution_id)
        if not attribution_id:
            row_issues.append("FCF_ATTRIBUTION_ID_REQUIRED")
        if key in attribution_ids:
            row_issues.append("DUPLICATE_FCF_ATTRIBUTION_ID")
        attribution_ids.add(key)
        if driver_id not in known_driver_ids:
            row_issues.append("FCF_ATTRIBUTION_DRIVER_UNRESOLVED")
        if category not in variance_component_categories:
            row_issues.append("FCF_ATTRIBUTION_CATEGORY_NOT_COMPONENT_RECONCILABLE")
        if not _meaningful(rationale):
            row_issues.append("FCF_ATTRIBUTION_RATIONALE_NOT_IDENTIFIABLE")
        trigger = trigger_map.get(trigger_id)
        if trigger is None:
            row_issues.append("FCF_ATTRIBUTION_REVIEW_TRIGGER_UNRESOLVED")
        elif _text(trigger.get("driver_id")) != driver_id:
            row_issues.append("FCF_ATTRIBUTION_TRIGGER_DRIVER_MISMATCH")
        amount, amount_issues, amount_refs = _money(
            row.get("amount_cny"),
            field=f"fcf_variance_attribution.{scenario}.{attribution_id or index}.amount_cny",
            sources_by_id=sources_by_id,
            unresolved_refs=unresolved_refs,
            after_cutoff_refs=after_cutoff_refs,
            uncertain_refs=uncertain_refs,
            allow_negative=True,
        )
        row_issues.extend(amount_issues)
        if not amount_refs:
            row_issues.append("FCF_ATTRIBUTION_EVIDENCE_REQUIRED")
        trigger_refs_raw = trigger.get("evidence_refs") if isinstance(trigger, Mapping) and isinstance(trigger.get("evidence_refs"), list) else []
        trigger_refs = {_text(ref) for ref in trigger_refs_raw if _text(ref)}
        if not trigger_refs:
            row_issues.append("FCF_ATTRIBUTION_TRIGGER_EVIDENCE_REQUIRED")
        elif not set(amount_refs).intersection(trigger_refs):
            row_issues.append("FCF_ATTRIBUTION_EVIDENCE_NOT_SHARED_WITH_TRIGGER")
        attribution_rows[scenario].append({
            "scenario": scenario,
            "fcf_attribution_id": attribution_id or f"UNKNOWN_{index}",
            "driver_id": driver_id or "UNKNOWN",
            "review_trigger_id": trigger_id or "UNKNOWN",
            "category": category or "UNKNOWN",
            "rationale": rationale or "UNKNOWN",
            "amount_cny": _format(amount) if amount is not None and not row_issues else None,
            "evidence_refs": amount_refs,
            "issues": sorted(set(row_issues)),
        })
        attribution_issues.extend(f"{scenario.upper()}:{attribution_id or index}:{issue}" for issue in row_issues)

    variance_scenarios: dict[str, dict[str, Any]] = {}
    variance_complete = comparison_complete and component_bridge_complete
    required_variance_categories = (
        "OPERATING_CASH_CONVERSION", "NON_CASH_EARNINGS", "CAPEX",
        "WORKING_CAPITAL", "INVENTORY_MOVEMENT",
    )
    for name in SCENARIOS:
        compare_row = comparisons.get(name, {})
        try:
            difference = _decimal(compare_row.get("b4_minus_normalized_fcf_cny"), f"{name}.b4_minus_normalized_fcf_cny")
        except ValueError:
            difference = None
        rows = attribution_rows[name]
        scenario_issues: list[str] = []
        contributions: list[Decimal] = []
        attributed_by_category: dict[str, Decimal] = {}
        attribution_categories = {_text(item.get("category")).upper() for item in rows}
        for required_category in required_variance_categories:
            if required_category not in attribution_categories:
                scenario_issues.append(f"FCF_VARIANCE_COMPONENT_COVERAGE_MISSING:{required_category}")
        if comparison_complete and not rows:
            scenario_issues.append("FCF_ATTRIBUTIONS_REQUIRED_FOR_COMPARABLE_SCENARIO")
        for item in rows:
            if item.get("issues") or item.get("amount_cny") is None:
                scenario_issues.extend(
                    f"{item.get('fcf_attribution_id')}:{issue}"
                    for issue in (item.get("issues") or ["FCF_ATTRIBUTION_AMOUNT_NOT_IDENTIFIABLE"])
                )
                continue
            amount = _decimal(item["amount_cny"], "FCF_ATTRIBUTION_AMOUNT")
            contributions.append(amount)
            category = _text(item.get("category")).upper()
            attributed_by_category[category] = attributed_by_category.get(category, Decimal("0")) + amount

        component_bridge = component_bridges.get(name, {})
        measured_components = component_bridge.get("contributions_cny") if isinstance(component_bridge.get("contributions_cny"), Mapping) else {}
        category_reconciliation: dict[str, dict[str, Any]] = {}
        if component_bridge.get("status") != "COMPONENTS_RECONCILED_DIAGNOSTIC_ONLY":
            scenario_issues.append("FCF_COMPONENT_BRIDGE_NOT_RECONCILED")
            scenario_issues.extend(
                f"COMPONENT_BRIDGE:{issue}" for issue in (component_bridge.get("issues") or [])
            )
        for category in required_variance_categories:
            measured_raw = measured_components.get(category)
            try:
                measured = _decimal(measured_raw, f"{name}.measured_component.{category}")
            except ValueError:
                measured = None
            attributed = attributed_by_category.get(category)
            category_residual = measured - attributed if measured is not None and attributed is not None else None
            category_status = (
                "RECONCILED" if measured is not None and attributed is not None
                and abs(category_residual) <= Decimal("1")
                else "REVIEW_REQUIRED"
            )
            category_reconciliation[category] = {
                "measured_component_contribution_cny": _format(measured),
                "attributed_category_total_cny": _format(attributed),
                "residual_cny": _format(category_residual),
                "status": category_status,
            }
            if measured is None:
                scenario_issues.append(f"FCF_MEASURED_COMPONENT_NOT_IDENTIFIABLE:{category}")
            elif attributed is None:
                scenario_issues.append(f"FCF_ATTRIBUTED_COMPONENT_TOTAL_MISSING:{category}")
            elif abs(category_residual) > Decimal("1"):
                scenario_issues.append(f"FCF_VARIANCE_CATEGORY_CONTRIBUTION_MISMATCH:{category}")

        total = sum(contributions, Decimal("0")) if len(contributions) == len(rows) else None
        residual = difference - total if difference is not None and total is not None else None
        if difference is not None and total is not None and residual is not None and abs(residual) > Decimal("1"):
            scenario_issues.append("FCF_VARIANCE_ATTRIBUTIONS_DO_NOT_RECONCILE_WITHIN_CNY_1")
        scenario_status = (
            "RECONCILED_DIAGNOSTIC_ONLY"
            if comparison_complete and component_bridge.get("status") == "COMPONENTS_RECONCILED_DIAGNOSTIC_ONLY"
            and rows and total is not None and residual is not None and not scenario_issues
            else "REVIEW_REQUIRED" if comparison_complete else "NOT_COMPARABLE"
        )
        if scenario_status != "RECONCILED_DIAGNOSTIC_ONLY":
            variance_complete = False
        variance_scenarios[name] = {
            "scenario": name,
            "b4_minus_normalized_fcf_cny": _format(difference),
            "attributed_total_cny": _format(total),
            "unattributed_residual_cny": _format(residual),
            "items": rows,
            "component_attribution_reconciliation": category_reconciliation,
            "status": scenario_status,
            "issues": sorted(set(scenario_issues)),
        }
        attribution_issues.extend(f"{name.upper()}:{issue}" for issue in scenario_issues)
    variance_status = (
        "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY"
        if variance_complete and not attribution_issues
        else "REVIEW_REQUIRED" if comparison_complete
        else "NOT_COMPARABLE"
    )
    variance_result = {
        "status": variance_status,
        "sign_convention": "B4_UNLEVERED_FCF_PROXY_MINUS_NORMALIZED_FCF; positive means B4 FCF is higher, negative means B4 FCF is lower",
        "tolerance_cny": "1",
        "scenarios": variance_scenarios,
        "issues": sorted(set(attribution_issues)),
        "cash_flow_amounts_aggregated": False,
        "valuation_input_eligible": False,
    }
    all_issues = sorted(set(monitor_issues + comparison_issues + component_bridge_issues + attribution_issues))
    result_status = (
        "FCF_VARIANCE_RECONCILED_DIAGNOSTIC_ONLY"
        if normalized_status == "NORMALIZED_FCF_BRIDGE_RECONCILED_DIAGNOSTIC_ONLY"
        and comparison_complete and component_bridge_complete and variance_status == "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY"
        else "REVIEW_REQUIRED" if all_issues or normalized_status != "NORMALIZED_FCF_BRIDGE_RECONCILED_DIAGNOSTIC_ONLY"
        else "NOT_COMPARABLE"
    )
    return {
        "status": result_status,
        "normalized_fcf": normalized_result,
        "b4_comparison": comparison_result,
        "component_variance_bridge": component_bridge_result,
        "variance_attribution": variance_result,
        "issues": all_issues,
        "sign_convention": "B4_UNLEVERED_FCF_PROXY_MINUS_NORMALIZED_FCF; positive means B4 FCF is higher",
        "tolerance_cny": "1",
        "normalized_fcf_comparison_available": comparison_complete,
        "fcf_variance_reconciled": component_bridge_complete and variance_status == "ALL_SCENARIOS_RECONCILED_DIAGNOSTIC_ONLY",
        "cash_flow_amounts_aggregated": False,
        "valuation_input_eligible": False,
        "formal_forecast_admission_created": False,
        "formal_valuation_admission_created": False,
        "decision_authority": False,
        "note": "B48 先核对参考 FCF + 逐项调整 = 正常化 FCF 中枢；B49 再按经营现金转换、非现金收益、资本开支、营运资金、库存五类实测 B4−正常化组件差额并逐类核对归因。库存已包含在营运资金时单列库存贡献必须为零；任一组件、类别或总额不一致均不得宣称 FCF 已对账。",
    }


def evaluate_cycle_earnings_monitor(
    raw: Any,
    *,
    operating_driver_forecast: Mapping[str, Any],
    forecast_valuation: Mapping[str, Any] | None = None,
    valuation_model_consistency: Mapping[str, Any] | None = None,
    valuation_timing: Mapping[str, Any] | None = None,
    valuation_transmission: Mapping[str, Any] | None = None,
    eps_earnings_bridge: Mapping[str, Any] | None = None,
    eps_multiple_valuation: Mapping[str, Any] | None = None,
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
    variance_transmission = _build_variance_transmission_context(
        variance_attribution=variance_attribution,
        eps_earnings_bridge=eps_earnings_bridge,
        eps_multiple_valuation=eps_multiple_valuation,
        per_share_value=per_share_value,
        normalized_earnings_period=earnings_period,
        b4_forecast_period=b4_period,
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

    cash_flow_path = _evaluate_cash_flow_path(
        raw_assessments=raw.get("cash_flow_assessments"),
        variance_attribution=variance_attribution,
        operating_driver_forecast=operating_driver_forecast,
        known_driver_ids=known_driver_ids,
        raw_review_triggers=raw_triggers,
        sources_by_id=sources_by_id,
        unresolved_refs=unresolved,
        after_cutoff_refs=after_cutoff,
        uncertain_refs=uncertain,
    )
    normalized_fcf_bridge = _evaluate_normalized_fcf_bridge(
        raw_normalized_fcf=raw.get("normalized_fcf"),
        raw_fcf_attributions=raw.get("fcf_variance_attribution"),
        operating_driver_forecast=operating_driver_forecast,
        known_driver_ids=known_driver_ids,
        raw_review_triggers=raw_triggers,
        sources_by_id=sources_by_id,
        unresolved_refs=unresolved,
        after_cutoff_refs=after_cutoff,
        uncertain_refs=uncertain,
    )
    all_issues = sorted(set(
        cycle_issues + earnings_issues + comparison_issues + variance_issues + trigger_issues
        + all_issues_for_value + (cash_flow_path.get("issues") or [])
        + (normalized_fcf_bridge.get("issues") or [])
    ))
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
        "cash_flow_path": cash_flow_path,
        "normalized_fcf_bridge": normalized_fcf_bridge,
        "variance_transmission": variance_transmission,
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
        "### B44–B48：行业周期 → 盈利/现金流桥接 → 每股价值 → 持仓复核",
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
    cash_node = data.get("cash_flow_path") if isinstance(data.get("cash_flow_path"), Mapping) else {}
    lines.extend([
        "",
        "#### B47：独立现金流/营运资金路径（不与净利润归因混算）",
        f"- 现金流路径状态：{cash_node.get('status', 'NOT_IDENTIFIABLE')}；正常化 FCF 对照是否存在：{cash_node.get('normalized_fcf_comparison_available', False)}；FCF 差额是否完成对账：{cash_node.get('fcf_variance_reconciled', False)}",
        f"- 逐项金额是否合计：{cash_node.get('cash_flow_amounts_aggregated', False)}（无独立正常化 FCF 基准，不得将项目金额当作总 FCF 差额）",
    ])
    b4_cash_context = cash_node.get("b4_cash_context") if isinstance(cash_node.get("b4_cash_context"), Mapping) else {}
    for name in SCENARIOS:
        context = b4_cash_context.get(name) if isinstance(b4_cash_context.get(name), Mapping) else {}
        fields = context.get("fields") if isinstance(context.get("fields"), Mapping) else {}
        lines.append(
            f"- {name.upper()} B4 现金上下文：{context.get('status', 'UNKNOWN')}；"
            f"FCF 代理 {fields.get('unlevered_fcf_proxy_cny') or 'UNKNOWN'}；"
            f"资本开支 {fields.get('cash_capex_cny') or 'UNKNOWN'}；"
            f"有效营运资金变动 {fields.get('effective_change_working_capital_cny') or 'UNKNOWN'}；"
            f"库存现金影响代理 {fields.get('inventory_cash_impact_proxy_cny') or 'UNKNOWN'}；"
            f"库存处理 {fields.get('inventory_working_capital_treatment') or 'UNKNOWN'}；"
            f"库存对账 {fields.get('inventory_reconciliation_status') or 'UNKNOWN'}"
        )
    cash_scenarios = cash_node.get("scenarios") if isinstance(cash_node.get("scenarios"), Mapping) else {}
    for name in SCENARIOS:
        rows = cash_scenarios.get(name) if isinstance(cash_scenarios.get(name), list) else []
        if not rows:
            lines.append(f"- {name.upper()}：没有已链接的现金流路径项目。")
        for item in rows:
            lines.append(
                f"- {name.upper()} / {item.get('attribution_id', 'UNKNOWN')} / driver {item.get('driver_id', 'UNKNOWN')}："
                f"渠道 {item.get('channel', 'UNKNOWN')}；方向 {item.get('direction', 'UNKNOWN')}；"
                f"量化状态 {item.get('quantification_status', 'UNKNOWN')}；"
                f"独立现金流影响 {item.get('cash_flow_effect_cny') or 'UNKNOWN'} CNY；"
                f"依据 {item.get('cash_flow_effect_basis') or 'UNKNOWN'}；"
                f"数据类别 {item.get('cash_flow_effect_data_class') or 'UNKNOWN'}；"
                f"金额证据 { '、'.join(item.get('cash_flow_effect_evidence_refs') or []) or 'UNKNOWN' }；"
                f"复核触发器 {item.get('review_trigger_id', 'UNKNOWN')}；状态 {item.get('status', 'UNKNOWN')}"
            )
            for issue in item.get("issues") or []:
                lines.append(f"  - 未解决：{issue}")
    for issue in cash_node.get("issues") or []:
        lines.append(f"- 现金流路径未解决：{issue}")
    fcf_node = data.get("normalized_fcf_bridge") if isinstance(data.get("normalized_fcf_bridge"), Mapping) else {}
    normalized_fcf_node = fcf_node.get("normalized_fcf") if isinstance(fcf_node.get("normalized_fcf"), Mapping) else {}
    fcf_comparison = fcf_node.get("b4_comparison") if isinstance(fcf_node.get("b4_comparison"), Mapping) else {}
    fcf_variance = fcf_node.get("variance_attribution") if isinstance(fcf_node.get("variance_attribution"), Mapping) else {}
    fcf_component_bridge = fcf_node.get("component_variance_bridge") if isinstance(fcf_node.get("component_variance_bridge"), Mapping) else {}
    lines.extend([
        "",
        "#### B48–B49：独立正常化 FCF、组件差额与逐类归因桥",
        f"- 总状态：{fcf_node.get('status', 'NOT_IDENTIFIABLE')}；正常化 FCF 桥：{normalized_fcf_node.get('status', 'NOT_IDENTIFIABLE')}；B4 比较：{fcf_comparison.get('status', 'NOT_COMPARABLE')}；组件差额桥：{fcf_component_bridge.get('status', 'NOT_COMPARABLE')}；FCF 差异归因：{fcf_variance.get('status', 'NOT_COMPARABLE')}",
        f"- 口径 / 方法 / 参考期间 / 目标期间：{normalized_fcf_node.get('scope', 'UNKNOWN')} / {normalized_fcf_node.get('method', 'UNKNOWN')} / {normalized_fcf_node.get('reference_period', 'UNKNOWN')} / {normalized_fcf_node.get('period', 'UNKNOWN')}",
        f"- 符号约定：{fcf_node.get('sign_convention', 'UNKNOWN')}；归因容差 {fcf_node.get('tolerance_cny', 'UNKNOWN')} CNY；是否作为估值输入：{fcf_node.get('valuation_input_eligible', False)}",
    ])
    norm_fcf_scenarios = normalized_fcf_node.get("scenarios") if isinstance(normalized_fcf_node.get("scenarios"), Mapping) else {}
    comparison_fcf_scenarios = fcf_comparison.get("scenarios") if isinstance(fcf_comparison.get("scenarios"), Mapping) else {}
    component_fcf_scenarios = fcf_component_bridge.get("scenarios") if isinstance(fcf_component_bridge.get("scenarios"), Mapping) else {}
    attribution_fcf_scenarios = fcf_variance.get("scenarios") if isinstance(fcf_variance.get("scenarios"), Mapping) else {}
    for name in SCENARIOS:
        norm_row = norm_fcf_scenarios.get(name) if isinstance(norm_fcf_scenarios.get(name), Mapping) else {}
        comp_row = comparison_fcf_scenarios.get(name) if isinstance(comparison_fcf_scenarios.get(name), Mapping) else {}
        component_row = component_fcf_scenarios.get(name) if isinstance(component_fcf_scenarios.get(name), Mapping) else {}
        var_row = attribution_fcf_scenarios.get(name) if isinstance(attribution_fcf_scenarios.get(name), Mapping) else {}
        lines.append(
            f"- {name.upper()} 正常化 FCF 参考/调整合计/低-中-高："
            f"{norm_row.get('reference_fcf_cny') or 'UNKNOWN'} / {norm_row.get('adjustment_total_cny') or 'UNKNOWN'} / "
            f"{norm_row.get('low_fcf_cny') or 'UNKNOWN'}–{norm_row.get('point_fcf_cny') or 'UNKNOWN'}–{norm_row.get('high_fcf_cny') or 'UNKNOWN'} CNY；"
            f"内部桥残差 {norm_row.get('bridge_residual_cny') or 'UNKNOWN'}；状态 {norm_row.get('status', 'UNKNOWN')}"
        )
        components = norm_row.get("cash_components") if isinstance(norm_row.get("cash_components"), Mapping) else {}
        def _component_value(key: str) -> str:
            component = components.get(key) if isinstance(components.get(key), Mapping) else {}
            return component.get("value") if component.get("value") not in (None, "") else "UNKNOWN"
        lines.append(
            f"  - 正常化组件复算（EBIT / 税率 / 折旧摊销 / 现金资本开支 / 原始营运资金 / 有效营运资金）："
            f"{_component_value('ebit_cny')} / {_component_value('tax_rate')} / "
            f"{_component_value('depreciation_amortization_cny')} / {_component_value('cash_capex_cny')} / "
            f"{_component_value('change_working_capital_cny')} / {_component_value('effective_change_working_capital_cny')}；"
            f"库存处理 {components.get('inventory_working_capital_treatment', 'UNKNOWN')}；"
            f"库存状态 {components.get('inventory_reconciliation_status', 'UNKNOWN')}；"
            f"组件公式 FCF {components.get('calculated_fcf_point_cny') or 'UNKNOWN'}"
        )
        for adjustment in norm_row.get("adjustments") or []:
            lines.append(
                f"  - 正常化调整 {adjustment.get('adjustment_id', 'UNKNOWN')} / {adjustment.get('category', 'UNKNOWN')} / "
                f"driver {adjustment.get('driver_id', 'UNKNOWN')}：{adjustment.get('amount_cny') or 'UNKNOWN'} CNY；"
                f"触发器 {adjustment.get('review_trigger_id', 'UNKNOWN')}；{adjustment.get('rationale', 'UNKNOWN')}"
            )
        lines.append(
            f"  - B4 FCF / 正常化 FCF / B4−正常化：{comp_row.get('b4_unlevered_fcf_proxy_cny') or 'UNKNOWN'} / "
            f"{comp_row.get('normalized_fcf_point_cny') or 'UNKNOWN'} / {comp_row.get('b4_minus_normalized_fcf_cny') or 'UNKNOWN'} CNY；"
            f"{comp_row.get('status', 'NOT_COMPARABLE')}"
        )
        contributions = component_row.get("contributions_cny") if isinstance(component_row.get("contributions_cny"), Mapping) else {}
        b4_component_detail = component_row.get("b4_cash_components") if isinstance(component_row.get("b4_cash_components"), Mapping) else {}
        norm_component_detail = component_row.get("normalized_cash_components") if isinstance(component_row.get("normalized_cash_components"), Mapping) else {}
        def _bridge_component_value(row: Mapping[str, Any], key: str) -> str:
            value = row.get(key)
            return str(value) if value not in (None, "") else "UNKNOWN"
        lines.append(
            f"  - B49 B4 / 正常化组件值：EBIT {_bridge_component_value(b4_component_detail, 'ebit_cny')} / {_bridge_component_value(norm_component_detail, 'ebit_cny')}；"
            f"税率 {_bridge_component_value(b4_component_detail, 'tax_rate')} / {_bridge_component_value(norm_component_detail, 'tax_rate')}；"
            f"D&A {_bridge_component_value(b4_component_detail, 'depreciation_amortization_cny')} / {_bridge_component_value(norm_component_detail, 'depreciation_amortization_cny')}；"
            f"CapEx {_bridge_component_value(b4_component_detail, 'cash_capex_cny')} / {_bridge_component_value(norm_component_detail, 'cash_capex_cny')}；"
            f"原始 WC {_bridge_component_value(b4_component_detail, 'change_working_capital_cny')} / {_bridge_component_value(norm_component_detail, 'change_working_capital_cny')}；"
            f"有效 WC {_bridge_component_value(b4_component_detail, 'effective_change_working_capital_cny')} / {_bridge_component_value(norm_component_detail, 'effective_change_working_capital_cny')}；"
            f"库存代理 {_bridge_component_value(b4_component_detail, 'inventory_cash_impact_proxy_cny')} / {_bridge_component_value(norm_component_detail, 'inventory_cash_impact_proxy_cny')}"
        )
        lines.append(
            f"  - B49 组件差额贡献（经营现金转换 / 非现金收益 / 资本开支 / 营运资金 / 库存）："
            f"{contributions.get('OPERATING_CASH_CONVERSION', 'UNKNOWN')} / {contributions.get('NON_CASH_EARNINGS', 'UNKNOWN')} / "
            f"{contributions.get('CAPEX', 'UNKNOWN')} / {contributions.get('WORKING_CAPITAL', 'UNKNOWN')} / "
            f"{contributions.get('INVENTORY_MOVEMENT', 'UNKNOWN')} CNY；组件残差 {component_row.get('component_residual_cny') or 'UNKNOWN'}；"
            f"{component_row.get('status', 'NOT_COMPARABLE')}"
        )
        lines.append(f"    - 库存拆分规则：{component_row.get('inventory_component_basis', 'UNKNOWN')}")
        lines.append(
            f"  - FCF 差异归因合计 / 未解释残差：{var_row.get('attributed_total_cny') or 'UNKNOWN'} / "
            f"{var_row.get('unattributed_residual_cny') or 'UNKNOWN'} CNY；{var_row.get('status', 'NOT_COMPARABLE')}"
        )
        category_checks = var_row.get("component_attribution_reconciliation") if isinstance(var_row.get("component_attribution_reconciliation"), Mapping) else {}
        for category, category_row in category_checks.items():
            if isinstance(category_row, Mapping):
                lines.append(
                    f"    - 逐类核对 {category}：实测 {category_row.get('measured_component_contribution_cny') or 'UNKNOWN'} / "
                    f"归因 {category_row.get('attributed_category_total_cny') or 'UNKNOWN'} / "
                    f"残差 {category_row.get('residual_cny') or 'UNKNOWN'} CNY；{category_row.get('status', 'UNKNOWN')}"
                )
        for attribution in var_row.get("items") or []:
            lines.append(
                f"    - {attribution.get('fcf_attribution_id', 'UNKNOWN')} / {attribution.get('category', 'UNKNOWN')} / "
                f"driver {attribution.get('driver_id', 'UNKNOWN')}：{attribution.get('amount_cny') or 'UNKNOWN'} CNY；"
                f"触发器 {attribution.get('review_trigger_id', 'UNKNOWN')}；{attribution.get('rationale', 'UNKNOWN')}"
            )
        for issue in norm_row.get("issues") or []:
            lines.append(f"  - 正常化 FCF 桥未解决：{issue}")
        for issue in comp_row.get("issues") or []:
            lines.append(f"  - B4 FCF 比较未解决：{issue}")
        for issue in component_row.get("issues") or []:
            lines.append(f"  - B49 组件差额桥未解决：{issue}")
        for issue in var_row.get("issues") or []:
            lines.append(f"  - FCF 差异归因未解决：{issue}")
    for issue in fcf_component_bridge.get("issues") or []:
        lines.append(f"- B49 组件差额桥未解决：{issue}")
    for issue in fcf_node.get("issues") or []:
        lines.append(f"- B48/B49 FCF 路径未解决：{issue}")
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
    transmission = data.get("variance_transmission") if isinstance(data.get("variance_transmission"), Mapping) else {}
    lines.extend([
        "",
        "#### B46：盈利差异 → EPS / 固定 P/E 每股价值敏感性（非估值输入）",
        f"- 传导状态：{transmission.get('status', 'NOT_IDENTIFIABLE')}；方法：{transmission.get('method', 'UNKNOWN')}",
    ])
    for assumption in transmission.get("assumptions") or []:
        lines.append(f"- 假设边界：{assumption}")
    transmission_scenarios = transmission.get("scenarios") if isinstance(transmission.get("scenarios"), Mapping) else {}
    for name in SCENARIOS:
        tx = transmission_scenarios.get(name) if isinstance(transmission_scenarios.get(name), Mapping) else {}
        lines.append(
            f"- {name.upper()}：B4−正常化净利润 {tx.get('b4_minus_normalized_net_profit_cny') or 'UNKNOWN'} CNY；"
            f"稀释股数 {tx.get('diluted_shares') or 'UNKNOWN'}；P/E {tx.get('pe_multiple_x') or 'UNKNOWN'}x；"
            f"隐含 EPS 敏感性 {tx.get('implied_eps_sensitivity_per_share') or 'UNKNOWN'} CNY/股；"
            f"固定 P/E 价值敏感性 {tx.get('constant_pe_value_sensitivity_per_share') or 'UNKNOWN'} CNY/股；"
            f"状态 {tx.get('status', 'NOT_IDENTIFIABLE')}"
        )
        for item in tx.get("items") or []:
            lines.append(
                f"  - 归因 {item.get('attribution_id', 'UNKNOWN')} / driver {item.get('driver_id', 'UNKNOWN')}："
                f"利润差异贡献 {item.get('amount_cny') or 'UNKNOWN'} CNY；"
                f"EPS 敏感性 {item.get('implied_eps_sensitivity_per_share') or 'UNKNOWN'} CNY/股；"
                f"固定 P/E 价值敏感性 {item.get('constant_pe_value_sensitivity_per_share') or 'UNKNOWN'} CNY/股；"
                f"触发器 {item.get('review_trigger_id', 'UNKNOWN')}"
            )
        for issue in tx.get("issues") or []:
            lines.append(f"  - 未解决：{issue}")
    for issue in transmission.get("issues") or []:
        lines.append(f"- 传导诊断未解决：{issue}")
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
