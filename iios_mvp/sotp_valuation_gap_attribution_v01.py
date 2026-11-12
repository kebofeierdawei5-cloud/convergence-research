from __future__ import annotations

"""B63 SOTP valuation-gap attribution.

This module is diagnostic-only. It reconciles B4 normalized segment earnings,
the selected SOTP assumptions, B61's current-price return hurdle, parent-level
adjustments and diluted-share mechanics without changing the primary model.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

B63_SCHEMA = "IIOS-B63-SOTP-VALUATION-GAP-ATTRIBUTION-0.1"
_TOLERANCE = Decimal("0.01")
_SCENARIOS = ("bear", "base", "bull")


def _dec(value: Any) -> Decimal | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _close(left: Decimal | None, right: Decimal | None) -> bool:
    return left is not None and right is not None and abs(left - right) <= _TOLERANCE


def build_sotp_valuation_gap_attribution(
    *,
    local_sotp_inversion: Mapping[str, Any],
    sotp_valuation: Mapping[str, Any],
    segment_earnings_reconciliation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a fail-closed earnings/multiple/parent-adjustment/share-count bridge."""
    result: dict[str, Any] = {
        "schema_version": B63_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "CONDITIONAL_DIAGNOSTIC_ONLY",
        "currency": "CNY",
        "forecast_period": "UNKNOWN",
        "method": (
            "SELECTED_SOTP_POOL_PLUS_B4_EARNINGS_EFFECT_PLUS_COMMON_PE_SCALE_EFFECT"
            "_TO_B61_REQUIRED_POOL; PARENT_ADJUSTMENTS_AND_DILUTION_SHOWN_SEPARATELY"
        ),
        "scenario_basis": (
            "B61_REQUIRED_RETURN_WITHOUT_DISTRIBUTIONS; B4_FULL_SEGMENT_VECTOR; "
            "SELECTED_SOTP_PARENT_ADJUSTMENTS_AND_DILUTED_SHARES_HELD_FIXED"
        ),
        "scenarios": {},
        "limitations": [
            "所选 SOTP P/E 是模型假设，不是市场实际交易倍数或外部共识；统一 P/E 缩放是满足 Required Return 价值池的数学敏感性，不证明估值公允或市场低估。",
            "盈利影响按选定 SOTP P/E 计算；倍数影响使用所有分部 P/E 同比例缩放的单一情景，避免将多个分部单变量 P/E/盈利阈值相加。",
            "中心成本、净现金/净负债及其他调整使用当前 SOTP 情景值；没有独立未来母公司调整预测时，不把其变化归因到未来价值缺口。",
            "稀释股数影响按 B61 每股终值要求计算；未提供独立未来股数情景时，只展示每股要求、盈亏平衡股数及股数敏感性。",
            "B63 只解释模型内价值池与回报门槛的条件算术，不验证盈利预测真实性、分部 P/E 公允性、外部 MIE 或市场预期。",
            "不修改 B4/B5/B6、SOTP 主估值、B61、外部 MIE、expectation_gap、15% 年化目标、Required Return、目标入场价、组合约束、Decision 或执行权限。",
        ],
        "external_mie_modified": False,
        "sotp_input_modified": False,
        "valuation_input_modified": False,
        "b61_input_modified": False,
        "formal_mie_admission_created": False,
        "formal_forecast_admission_created": False,
        "decision_authority": False,
    }

    if str(local_sotp_inversion.get("selected_model_family") or "").strip().upper() != "SOTP":
        result["status"] = "NOT_APPLICABLE_NOT_SOTP"
        return result
    if str(local_sotp_inversion.get("currency") or "").strip().upper() != "CNY":
        result["status"] = "NOT_COMPARABLE_CURRENCY"
        return result
    if sotp_valuation.get("status") != "CALCULATED" or sotp_valuation.get("selected_for_primary_model") is not True:
        result["status"] = "PRIMARY_SOTP_NOT_CALCULATED"
        return result
    if str(local_sotp_inversion.get("status") or "").upper() not in {
        "CONDITIONAL_SENSITIVITY_CALCULATED", "PARTIAL"
    }:
        result["status"] = "BLOCKED_BY_B61"
        return result
    if str(segment_earnings_reconciliation.get("status") or "").upper() not in {
        "CONDITIONAL_RECONCILIATION_CALCULATED", "PARTIAL"
    }:
        result["status"] = "BLOCKED_BY_B62"
        result["b62_status"] = segment_earnings_reconciliation.get("status") or "UNKNOWN"
        return result

    period = str(segment_earnings_reconciliation.get("forecast_period") or "UNKNOWN").strip()
    result["forecast_period"] = period
    if period.upper() in {"", "UNKNOWN"}:
        result["status"] = "FORECAST_PERIOD_NOT_IDENTIFIABLE"
        return result
    if period.upper() != str(sotp_valuation.get("forecast_period") or "").strip().upper():
        result["status"] = "FORECAST_PERIOD_MISMATCH"
        return result
    if period.upper() != str(local_sotp_inversion.get("forecast_period") or "").strip().upper():
        result["status"] = "B61_FORECAST_PERIOD_MISMATCH"
        return result

    sotp_scenarios = sotp_valuation.get("scenarios") if isinstance(sotp_valuation.get("scenarios"), Mapping) else {}
    b61_scenarios = local_sotp_inversion.get("scenarios") if isinstance(local_sotp_inversion.get("scenarios"), Mapping) else {}
    b62_scenarios = segment_earnings_reconciliation.get("scenarios") if isinstance(segment_earnings_reconciliation.get("scenarios"), Mapping) else {}
    statuses: list[str] = []

    for scenario_name in _SCENARIOS:
        sotp = sotp_scenarios.get(scenario_name) if isinstance(sotp_scenarios.get(scenario_name), Mapping) else {}
        b61 = b61_scenarios.get(scenario_name) if isinstance(b61_scenarios.get(scenario_name), Mapping) else {}
        b62 = b62_scenarios.get(scenario_name) if isinstance(b62_scenarios.get(scenario_name), Mapping) else {}
        row: dict[str, Any] = {
            "scenario": scenario_name,
            "status": "NOT_IDENTIFIABLE",
            "forecast_period": period,
            "issues": [],
            "earnings_effect_by_segment": [],
            "required_common_pe_by_segment": [],
        }
        if str(b62.get("status") or "").upper() != "CALCULATED_CONDITIONAL":
            row["issues"].append(f"B62_SCENARIO_NOT_CALCULATED:{b62.get('status') or 'UNKNOWN'}")
        if str(b61.get("status") or "").upper() != "CALCULATED_CONDITIONAL":
            row["issues"].append(f"B61_SCENARIO_NOT_CALCULATED:{b61.get('status') or 'UNKNOWN'}")
        raw_sotp_segments = sotp.get("segments")
        if not isinstance(raw_sotp_segments, list) or not raw_sotp_segments:
            row["issues"].append("SOTP_SEGMENTS_MISSING")
        if row["issues"]:
            row["status"] = "BLOCKED_BY_UPSTREAM_SCENARIO"
            row["issues"] = sorted(set(row["issues"]))
            result["scenarios"][scenario_name] = row
            statuses.append(row["status"])
            continue

        # Current selected SOTP segment pool and parent adjustments.
        parent = sotp.get("parent_level_adjustments") if isinstance(sotp.get("parent_level_adjustments"), Mapping) else {}
        central_cost = _dec(parent.get("capitalized_central_cost_value_cny"))
        central_cost_after_tax = _dec(parent.get("central_cost_after_tax_cny"))
        central_cost_multiple = _dec(parent.get("central_cost_multiple_x"))
        net_cash = _dec(parent.get("net_cash_debt_cny"))
        other = _dec(parent.get("other_adjustments_cny"))
        diluted_shares = _dec(sotp.get("diluted_shares"))
        selected_segment_pool = _dec(sotp.get("segment_equity_value_cny"))
        selected_total_equity = _dec(sotp.get("total_equity_value_cny"))
        selected_terminal_per_share = _dec(sotp.get("terminal_value_per_share"))

        b61_required = b61.get("requirements") if isinstance(b61.get("requirements"), Mapping) else {}
        required_return = b61_required.get("required_return") if isinstance(b61_required.get("required_return"), Mapping) else {}
        required_without = required_return.get("without_distributions") if isinstance(required_return.get("without_distributions"), Mapping) else {}
        required_per_share = _dec(required_return.get("required_terminal_value_per_share_without_distributions"))
        required_total_equity = _dec(required_without.get("required_terminal_equity_value_cny"))
        required_segment_pool = _dec(required_without.get("required_segment_equity_value_pool_cny"))
        selected_pool_from_b61 = _dec(required_without.get("selected_segment_equity_value_pool_cny"))

        b61_central_cost = _dec(b61.get("selected_capitalized_central_cost_cny"))
        b61_net_cash = _dec(b61.get("selected_net_cash_debt_cny"))
        b61_other = _dec(b61.get("selected_other_adjustments_cny"))
        b61_shares = _dec(b61.get("selected_diluted_shares"))
        b61_selected_equity = _dec(b61.get("selected_total_equity_value_cny"))
        b61_selected_per_share = _dec(b61.get("selected_sotp_terminal_value_per_share"))

        b4_pool = _dec(b62.get("b4_forecast_segment_equity_value_pool_at_selected_sotp_pe_cny"))
        b62_selected_pool = _dec(b62.get("selected_sotp_segment_equity_value_pool_cny"))
        b62_required_pool = _dec(b62.get("required_segment_equity_value_pool_for_required_return_cny"))
        b62_forecast_equity = _dec(b62.get("b4_forecast_implied_total_equity_value_with_selected_parent_adjustments_cny"))
        b62_forecast_per_share = _dec(b62.get("b4_forecast_implied_terminal_value_per_share_cny"))
        b62_required_total_equity = _dec(b62.get("required_terminal_equity_value_for_required_return_cny"))
        b62_required_per_share = _dec(b62.get("required_terminal_value_per_share_for_required_return_cny"))

        required_fields = (
            central_cost, central_cost_after_tax, central_cost_multiple,
            net_cash, other, diluted_shares, selected_segment_pool,
            selected_total_equity, selected_terminal_per_share, required_per_share,
            required_total_equity, required_segment_pool, selected_pool_from_b61,
            b61_central_cost, b61_net_cash, b61_other, b61_shares,
            b4_pool, b62_selected_pool, b62_required_pool, b62_forecast_equity,
            b62_forecast_per_share, b62_required_total_equity, b62_required_per_share,
        )
        if any(value is None for value in required_fields) or diluted_shares <= 0 or b61_shares <= 0:
            row["status"] = "NOT_IDENTIFIABLE"
            row["issues"] = ["REQUIRED_SOTP_B61_OR_B62_ARITHMETIC_INPUT_MISSING"]
            result["scenarios"][scenario_name] = row
            statuses.append(row["status"])
            continue

        # Reconcile adapter parent adjustments and share count with B61's frozen copy.
        checks = {
            "B61_CENTRAL_COST_VS_SOTP": (b61_central_cost, central_cost),
            "B61_NET_CASH_VS_SOTP": (b61_net_cash, net_cash),
            "B61_OTHER_ADJUSTMENTS_VS_SOTP": (b61_other, other),
            "B61_SHARES_VS_SOTP": (b61_shares, diluted_shares),
            "B61_SELECTED_EQUITY_VS_SOTP": (b61_selected_equity, selected_total_equity),
            "B61_SELECTED_PER_SHARE_VS_SOTP": (b61_selected_per_share, selected_terminal_per_share),
            "B61_SELECTED_POOL_VS_SOTP": (selected_pool_from_b61, selected_segment_pool),
            "B62_SELECTED_POOL_VS_SOTP": (b62_selected_pool, selected_segment_pool),
            "B62_REQUIRED_POOL_VS_B61": (b62_required_pool, required_segment_pool),
            "B62_REQUIRED_EQUITY_VS_B61": (b62_required_total_equity, required_total_equity),
            "B62_REQUIRED_PER_SHARE_VS_B61": (b62_required_per_share, required_per_share),
        }
        for label, (left, right) in checks.items():
            if not _close(left, right):
                row["issues"].append(f"{label}_MISMATCH")
        if not _close(required_total_equity, required_per_share * b61_shares):
            row["issues"].append("REQUIRED_EQUITY_DOES_NOT_EQUAL_REQUIRED_PER_SHARE_TIMES_SHARES")
        if not _close(
            required_segment_pool,
            required_total_equity + central_cost - net_cash - other,
        ):
            row["issues"].append("REQUIRED_SEGMENT_POOL_PARENT_ADJUSTMENT_IDENTITY_MISMATCH")
        if not _close(
            selected_total_equity,
            selected_segment_pool - central_cost + net_cash + other,
        ):
            row["issues"].append("SELECTED_SOTP_TOTAL_EQUITY_IDENTITY_MISMATCH")
        if not _close(
            selected_terminal_per_share,
            selected_total_equity / diluted_shares,
        ):
            row["issues"].append("SELECTED_SOTP_PER_SHARE_IDENTITY_MISMATCH")
        if central_cost_after_tax is not None and central_cost_multiple is not None:
            if not _close(central_cost_after_tax * central_cost_multiple, central_cost):
                row["issues"].append("CAPITALIZED_CENTRAL_COST_IDENTITY_MISMATCH")

        segment_rows = b62.get("segment_comparisons") if isinstance(b62.get("segment_comparisons"), list) else []
        segment_profit_effect_sum = Decimal("0")
        selected_pool_recalculated = Decimal("0")
        b4_pool_recalculated = Decimal("0")
        segment_ids: set[str] = set()
        sotp_segment_by_id: dict[str, Mapping[str, Any]] = {}
        for raw_segment in raw_sotp_segments if isinstance(raw_sotp_segments, list) else []:
            if not isinstance(raw_segment, Mapping):
                row["issues"].append("SOTP_SEGMENT_ROW_INVALID")
                continue
            raw_segment_id = str(raw_segment.get("segment_id") or "").strip()
            if not raw_segment_id or raw_segment_id in sotp_segment_by_id:
                row["issues"].append(f"SOTP_SEGMENT_ID_MISSING_OR_DUPLICATE:{raw_segment_id or 'UNKNOWN'}")
                continue
            sotp_segment_by_id[raw_segment_id] = raw_segment
        for segment in segment_rows:
            if not isinstance(segment, Mapping):
                row["issues"].append("B62_SEGMENT_COMPARISON_ROW_INVALID")
                continue
            segment_id = str(segment.get("segment_id") or "").strip()
            if not segment_id or segment_id in segment_ids:
                row["issues"].append(f"B62_SEGMENT_ID_MISSING_OR_DUPLICATE:{segment_id or 'UNKNOWN'}")
                continue
            segment_ids.add(segment_id)
            source_sotp_segment = sotp_segment_by_id.get(segment_id)
            if not isinstance(source_sotp_segment, Mapping):
                row["issues"].append(f"SOTP_SEGMENT_MISSING_FOR_B62_COMPARISON:{segment_id}")
                continue
            if str(source_sotp_segment.get("earnings_basis") or "UNKNOWN").strip().upper() != "NORMALIZED_PARENT_ATTRIBUTABLE":
                row["issues"].append(f"SOTP_EARNINGS_BASIS_NOT_NORMALIZED_PARENT_ATTRIBUTABLE:{segment_id}")
                continue
            b4_profit = _dec(segment.get("b4_forecast_parent_attributable_normalized_profit_cny"))
            sotp_profit = _dec(segment.get("sotp_selected_attributable_profit_cny"))
            pe = _dec(segment.get("sotp_selected_pe_multiple_x"))
            declared_profit_effect = _dec(segment.get("profit_change_value_effect_at_selected_sotp_pe_cny"))
            if any(value is None for value in (b4_profit, sotp_profit, pe, declared_profit_effect)) or pe <= 0:
                row["issues"].append(f"SEGMENT_EARNINGS_OR_PE_NOT_NUMERIC:{segment_id}")
                continue
            selected_value = sotp_profit * pe
            b4_value = b4_profit * pe
            profit_effect = (b4_profit - sotp_profit) * pe
            if not _close(declared_profit_effect, profit_effect):
                row["issues"].append(f"SEGMENT_EARNINGS_VALUE_EFFECT_MISMATCH:{segment_id}")
            selected_pool_recalculated += selected_value
            b4_pool_recalculated += b4_value
            segment_profit_effect_sum += profit_effect
            source_pe = source_sotp_segment.get("pe_multiple_x") if isinstance(source_sotp_segment.get("pe_multiple_x"), Mapping) else {}
            source_profit = source_sotp_segment.get("attributable_net_profit_cny") if isinstance(source_sotp_segment.get("attributable_net_profit_cny"), Mapping) else {}
            if not _close(_dec(source_pe), pe) or not _close(_dec(source_profit), sotp_profit):
                row["issues"].append(f"SOTP_SEGMENT_MEASURE_VS_B62_MISMATCH:{segment_id}")
            row["earnings_effect_by_segment"].append({
                "segment_id": segment_id,
                "normalized_profit_change_cny": _fmt(b4_profit - sotp_profit),
                "selected_sotp_pe_x": _fmt(pe),
                "selected_pe_basis": source_pe.get("basis") or "UNKNOWN",
                "selected_pe_data_class": source_pe.get("data_class") or "UNKNOWN",
                "selected_pe_evidence_refs": list(source_pe.get("evidence_refs") or []),
                "selected_profit_basis": source_profit.get("basis") or "UNKNOWN",
                "selected_profit_data_class": source_profit.get("data_class") or "UNKNOWN",
                "selected_profit_evidence_refs": list(source_profit.get("evidence_refs") or []),
                "earnings_effect_at_selected_pe_cny": _fmt(profit_effect),
                "selected_sotp_segment_value_cny": _fmt(selected_value),
                "b4_forecast_segment_value_at_selected_pe_cny": _fmt(b4_value),
                "interpretation": "B4_MINUS_SELECTED_SOTP_PROFIT_TIMES_UNCHANGED_SELECTED_PE",
            })

        if not segment_ids:
            row["issues"].append("B62_SEGMENT_COMPARISON_UNIVERSE_EMPTY")
        if segment_ids != set(sotp_segment_by_id):
            row["issues"].append("B62_VS_SOTP_SEGMENT_UNIVERSE_MISMATCH")
        if not _close(selected_pool_recalculated, selected_segment_pool):
            row["issues"].append("SELECTED_SEGMENT_POOL_RECALCULATION_MISMATCH")
        if not _close(b4_pool_recalculated, b4_pool):
            row["issues"].append("B4_FORECAST_SEGMENT_POOL_RECALCULATION_MISMATCH")
        if not _close(segment_profit_effect_sum, b4_pool - selected_segment_pool):
            row["issues"].append("SEGMENT_EARNINGS_EFFECT_DOES_NOT_RECONCILE_TO_POOL_CHANGE")

        if row["issues"]:
            row["status"] = "RECONCILIATION_MISMATCH"
            row["issues"] = sorted(set(row["issues"]))
            result["scenarios"][scenario_name] = row
            statuses.append(row["status"])
            continue

        # A two-step pool bridge: first earnings at selected P/Es, then a common
        # proportional P/E scaling across all segments. This is a sensitivity,
        # not a claim that all segment multiples should move by the same amount.
        earnings_effect = b4_pool - selected_segment_pool
        residual_multiple_effect = required_segment_pool - b4_pool
        common_pe_scale: Decimal | None = None
        required_common_pe_rows: list[dict[str, Any]] = []
        if b4_pool > 0 and required_segment_pool > 0:
            common_pe_scale = required_segment_pool / b4_pool
            for segment in row["earnings_effect_by_segment"]:
                selected_pe = _dec(segment.get("selected_sotp_pe_x"))
                required_common_pe_rows.append({
                    "segment_id": segment["segment_id"],
                    "selected_sotp_pe_x": _fmt(selected_pe),
                    "selected_pe_basis": segment.get("selected_pe_basis"),
                    "selected_pe_data_class": segment.get("selected_pe_data_class"),
                    "selected_pe_evidence_refs": segment.get("selected_pe_evidence_refs") or [],
                    "required_pe_under_common_scale_x": _fmt(selected_pe * common_pe_scale),
                    "common_scale_factor": _fmt(common_pe_scale),
                    "interpretation": "ALL_SELECTED_SEGMENT_PES_SCALED_BY_THE_SAME_FACTOR;CONDITIONAL_ONLY",
                })
        else:
            row["issues"].append("COMMON_PE_SCALE_NOT_IDENTIFIABLE_NONPOSITIVE_VALUE_POOL")

        # Exact equity bridge from B4's full forecast vector to B61's required
        # equity, keeping current parent adjustments and diluted shares fixed.
        b4_equity_recalculated = b4_pool - central_cost + net_cash + other
        equity_gap = required_total_equity - b4_equity_recalculated
        pool_gap = required_segment_pool - b4_pool
        per_share_gap = required_per_share - b62_forecast_per_share
        if not _close(b4_equity_recalculated, b62_forecast_equity):
            row["issues"].append("B4_EQUITY_RECALCULATION_MISMATCH")
        if not _close(b4_equity_recalculated, required_total_equity - equity_gap):
            row["issues"].append("TOTAL_EQUITY_GAP_IDENTITY_MISMATCH")
        if not _close(equity_gap, pool_gap):
            row["issues"].append("POOL_GAP_VS_EQUITY_GAP_IDENTITY_MISMATCH")
        if not _close(per_share_gap * diluted_shares, equity_gap):
            row["issues"].append("PER_SHARE_GAP_VS_EQUITY_GAP_IDENTITY_MISMATCH")

        # Required-pool decomposition: required equity plus the selected parent
        # cost burden, less net cash and other adjustments.
        parent_load = central_cost - net_cash - other
        if not _close(required_total_equity + parent_load, required_segment_pool):
            row["issues"].append("PARENT_ADJUSTMENT_LOAD_DOES_NOT_RECONCILE")

        break_even_shares = (
            b4_equity_recalculated / required_per_share
            if required_per_share > 0 else None
        )
        share_headroom = break_even_shares - diluted_shares if break_even_shares is not None else None
        share_burden_one_percent = required_per_share * diluted_shares * Decimal("0.01")

        arithmetic_issue = any(
            "MISMATCH" in str(issue)
            or "DOES_NOT_EQUAL" in str(issue)
            or "DOES_NOT_RECONCILE" in str(issue)
            or "IDENTITY" in str(issue)
            for issue in row["issues"]
        )
        row.update({
            "status": (
                "RECONCILIATION_MISMATCH" if arithmetic_issue
                else "PARTIAL" if row["issues"]
                else "CONDITIONAL_ATTRIBUTION_CALCULATED"
            ),
            "selected_sotp_segment_pool_cny": _fmt(selected_segment_pool),
            "b4_forecast_segment_pool_at_selected_pes_cny": _fmt(b4_pool),
            "required_segment_pool_for_b61_required_return_cny": _fmt(required_segment_pool),
            "value_pool_waterfall": {
                "step_1_selected_sotp_segment_pool_cny": _fmt(selected_segment_pool),
                "step_2_b4_earnings_effect_at_selected_pes_cny": _fmt(earnings_effect),
                "step_3_b4_forecast_pool_at_selected_pes_cny": _fmt(b4_pool),
                "step_4_common_pe_scale_effect_to_required_pool_cny": _fmt(residual_multiple_effect),
                "step_5_required_segment_pool_cny": _fmt(required_segment_pool),
                "waterfall_reconciliation_residual_cny": _fmt(
                    selected_segment_pool + earnings_effect + residual_multiple_effect - required_segment_pool
                ),
                "sign_convention": "POSITIVE_EFFECT_INCREASES_SEGMENT_EQUITY_VALUE_POOL",
            },
            "earnings_attribution": {
                "b4_minus_selected_sotp_profit_value_effect_cny": _fmt(earnings_effect),
                "segment_effects": row["earnings_effect_by_segment"],
                "reconciliation_status": "RECONCILED_WITHIN_CNY_0_01",
            },
            "multiple_attribution": {
                "status": "CONDITIONAL_SENSITIVITY_CALCULATED" if common_pe_scale is not None else "NOT_IDENTIFIABLE",
                "residual_segment_pool_requirement_after_b4_earnings_cny": _fmt(residual_multiple_effect),
                "common_pe_scale_factor_required": _fmt(common_pe_scale),
                "required_common_pe_by_segment": required_common_pe_rows,
                "interpretation": (
                    "REQUIRED_PARALLEL_P_E_MULTIPLIER_IF_B4_EARNINGS_ARE_ACHIEVED; "
                    "NOT_FAIR_VALUE_NOT_MARKET_CONSENSUS_NOT_A_SEGMENT_BY_SEGMENT_ADDITIVE_TARGET"
                ),
            },
            "parent_adjustment_attribution": {
                "capitalized_central_cost_load_on_required_segment_pool_cny": _fmt(central_cost),
                "net_cash_debt_offset_to_required_segment_pool_cny": _fmt(-net_cash),
                "other_adjustments_offset_to_required_segment_pool_cny": _fmt(-other),
                "net_parent_adjustment_load_cny": _fmt(parent_load),
                "required_pool_identity": (
                    "REQUIRED_TOTAL_EQUITY + CAPITALIZED_CENTRAL_COST "
                    "- NET_CASH_DEBT - OTHER_ADJUSTMENTS"
                ),
                "one_cny_sensitivity": {
                    "capitalized_central_cost_plus_one_cny_required_pool_effect": "+1 CNY",
                    "net_cash_debt_plus_one_cny_required_pool_effect": "-1 CNY",
                    "other_adjustments_plus_one_cny_required_pool_effect": "-1 CNY",
                },
                "future_parent_adjustment_change_attribution": "NOT_IDENTIFIABLE_WITHOUT_EXPLICIT_FORWARD_PARENT_ADJUSTMENT_FORECASTS",
                "reconciliation_status": "RECONCILED_WITHIN_CNY_0_01",
            },
            "dilution_attribution": {
                "selected_diluted_shares": _fmt(diluted_shares),
                "required_terminal_value_per_share_cny": _fmt(required_per_share),
                "required_total_equity_value_cny": _fmt(required_total_equity),
                "b4_forecast_total_equity_value_cny": _fmt(b4_equity_recalculated),
                "total_equity_gap_cny": _fmt(equity_gap),
                "per_share_gap_cny": _fmt(per_share_gap),
                "break_even_diluted_shares_at_b4_forecast_equity": _fmt(break_even_shares),
                "diluted_share_headroom_vs_break_even": _fmt(share_headroom),
                "additional_required_equity_per_plus_one_share_cny": _fmt(required_per_share),
                "additional_required_equity_for_plus_one_percent_shares_cny": _fmt(share_burden_one_percent),
                "interpretation": "REQUIRED_EQUITY_EQUALS_REQUIRED_TERMINAL_PER_SHARE_TIMES_DILUTED_SHARES; SHARE_COUNT_IS_NOT_AN_OPERATING_EARNINGS_EFFECT",
            },
            "total_gap_bridge": {
                "b4_forecast_equity_cny": _fmt(b4_equity_recalculated),
                "required_equity_for_b61_return_hurdle_cny": _fmt(required_total_equity),
                "required_equity_minus_b4_equity_cny": _fmt(equity_gap),
                "required_per_share_minus_b4_per_share_cny": _fmt(per_share_gap),
                "equity_gap_reconciliation_residual_cny": _fmt(equity_gap - pool_gap),
                "status": "RECONCILED_WITHIN_CNY_0_01",
            },
            "issues": sorted(set(row["issues"])),
        })
        result["scenarios"][scenario_name] = row
        statuses.append(row["status"])

    if statuses and all(status == "CONDITIONAL_ATTRIBUTION_CALCULATED" for status in statuses):
        result["status"] = "CONDITIONAL_ATTRIBUTION_CALCULATED"
    elif any(status == "RECONCILIATION_MISMATCH" for status in statuses):
        result["status"] = "RECONCILIATION_MISMATCH"
    elif any(status in {"CONDITIONAL_ATTRIBUTION_CALCULATED", "PARTIAL"} for status in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    result["summary"] = (
        "先将 B4 分部正常化盈利变化按已选 SOTP P/E 计价，再以统一 P/E 缩放敏感性解释剩余价值池要求；"
        "母公司调整和稀释股数单独列示，不将缺少前瞻依据的变化伪装为经营归因。"
    )
    return result
