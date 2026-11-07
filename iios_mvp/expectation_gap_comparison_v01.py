from __future__ import annotations

"""B76 read-only comparison of independent B4 forecasts and price-conditioned requirements.

This adapter compares already-computed EPS_MULTIPLE/B60 and SOTP/B61/B63
requirements with the independent B4 forecast. It does not identify external MIE, calibrate win rates,
or modify any upstream forecast, valuation, return gate, or decision.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

B76_SCHEMA = "IIOS-B76-PRICE-CONDITIONED-EXPECTATION-COMPARISON-0.1"
_SCENARIOS = ("bear", "base", "bull")
_TOL = Decimal("0.01")


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dec(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _difference(left: Any, right: Any) -> dict[str, Any]:
    a, b = _dec(left), _dec(right)
    if a is None or b is None:
        return {"status": "NOT_IDENTIFIABLE", "difference": None, "unit": "CNY"}
    return {"status": "CALCULATED", "difference": _fmt(a - b), "unit": "CNY"}


def _driver_row(product: Mapping[str, Any]) -> dict[str, Any]:
    current = _map(product.get("current_forward_assumptions"))
    alternatives = _map(product.get("single_driver_alternatives"))
    volume = _map(alternatives.get("sales_volume_only"))
    asp = _map(alternatives.get("net_asp_only"))
    cost = _map(alternatives.get("unit_variable_cost_only"))
    return {
        "product_id": product.get("product_id"),
        "product_name": product.get("product_name"),
        "current_independent_forecast": {
            "sales_volume_tonnes": current.get("sales_volume_tonnes"),
            "net_asp_cny_per_tonne": current.get("net_asp_cny_per_tonne"),
            "variable_cost_cny_per_tonne": current.get("variable_cost_cny_per_tonne"),
        },
        "production_inventory_context": _map(product.get("production_inventory_context")),
        "driver_measure_lineage": _map(product.get("driver_measure_lineage")),
        "price_conditioned_single_driver_alternatives": {
            "sales_volume_only": {
                "status": volume.get("status", "UNKNOWN"),
                "required_sales_volume_tonnes": volume.get("required_sales_volume_tonnes"),
                "change_pct": volume.get("change_pct"),
                "unit_contribution_margin_cny_per_tonne_held_fixed": volume.get("unit_contribution_margin_cny_per_tonne_held_fixed"),
                "production_inventory_feasibility": volume.get("production_and_inventory_feasibility", "UNKNOWN"),
            },
            "net_asp_only": {
                "status": asp.get("status", "UNKNOWN"),
                "required_net_asp_cny_per_tonne": asp.get("required_net_asp_cny_per_tonne"),
                "change_pct": asp.get("change_pct"),
                "sales_volume_tonnes_held_fixed": asp.get("sales_volume_tonnes_held_fixed"),
            },
            "unit_variable_cost_only": {
                "status": cost.get("status", "UNKNOWN"),
                "required_variable_cost_cny_per_tonne": cost.get("required_variable_cost_cny_per_tonne"),
                "change_pct": cost.get("change_pct"),
                "sales_volume_tonnes_held_fixed": cost.get("sales_volume_tonnes_held_fixed"),
            },
        },
        "interpretation": "ALTERNATIVE_ONE_VARIABLE_SENSITIVITIES_NOT_SIMULTANEOUS_FORECAST_TARGETS",
    }


def _scenario_comparison(
    name: str,
    *,
    b61_scenario: Mapping[str, Any],
    b62_scenario: Mapping[str, Any],
    b63_scenario: Mapping[str, Any],
    b68_scenario: Mapping[str, Any],
) -> dict[str, Any]:
    waterfall = _map(b63_scenario.get("value_pool_waterfall"))
    b61_requirements = _map(b61_scenario.get("requirements"))
    required_return_requirement = _map(b61_requirements.get("required_return"))
    fundamental_target_requirement = _map(b61_requirements.get("fundamental_target_annualized_return"))
    b4_pool = _dec(waterfall.get("step_3_b4_forecast_pool_at_selected_pes_cny"))
    required_pool = _dec(waterfall.get("step_5_required_segment_pool_cny"))
    pool_gap = b4_pool - required_pool if b4_pool is not None and required_pool is not None else None
    pool_gap_pct = (
        (b4_pool / required_pool - Decimal("1")) * Decimal("100")
        if b4_pool is not None and required_pool is not None and required_pool > 0
        else None
    )
    b4_per_share = _dec(b62_scenario.get("b4_forecast_implied_terminal_value_per_share_cny"))
    required_per_share = _dec(b62_scenario.get("required_terminal_value_per_share_for_required_return_cny"))
    per_share_gap = (
        b4_per_share - required_per_share
        if b4_per_share is not None and required_per_share is not None else None
    )

    # Independent B76 second-pass audit of B63's full-vector two-step waterfall
    # and B62/B61 parent-adjustment and per-share transmission.
    b63_checks: dict[str, str] = {}
    b63_issues: list[str] = []
    b63_mismatches: list[str] = []
    b63_tol = Decimal("0.01")
    step1 = _dec(waterfall.get("step_1_selected_sotp_segment_pool_cny"))
    step2 = _dec(waterfall.get("step_2_b4_earnings_effect_at_selected_pes_cny"))
    step3 = _dec(waterfall.get("step_3_b4_forecast_pool_at_selected_pes_cny"))
    step4 = _dec(waterfall.get("step_4_common_pe_scale_effect_to_required_pool_cny"))
    step5 = _dec(waterfall.get("step_5_required_segment_pool_cny"))
    waterfall_residual = _dec(waterfall.get("waterfall_reconciliation_residual_cny"))
    b62_b4_pool = _dec(b62_scenario.get("b4_forecast_segment_equity_value_pool_at_selected_sotp_pe_cny"))
    b62_required_pool = _dec(b62_scenario.get("required_segment_equity_value_pool_for_required_return_cny"))
    if any(v is None for v in (step1, step2, step3, step4, step5, waterfall_residual, b62_b4_pool, b62_required_pool)):
        b63_issues.append("B63_WATERFALL_OR_B62_VALUE_POOL_ARITHMETIC_INPUT_MISSING")
        for key in ("step_1_plus_step_2_equals_step_3", "step_3_plus_step_4_equals_step_5",
                    "declared_waterfall_residual", "step_3_matches_b62_b4_pool", "step_5_matches_b62_required_pool"):
            b63_checks[key] = "NOT_IDENTIFIABLE"
    else:
        pairs = {
            "step_1_plus_step_2_equals_step_3": (step1 + step2, step3),
            "step_3_plus_step_4_equals_step_5": (step3 + step4, step5),
            "declared_waterfall_residual": (step1 + step2 + step4 - step5, waterfall_residual),
            "step_3_matches_b62_b4_pool": (step3, b62_b4_pool),
            "step_5_matches_b62_required_pool": (step5, b62_required_pool),
        }
        for key, (left, right) in pairs.items():
            passed = _close(left, right, b63_tol)
            b63_checks[key] = "PASS" if passed else "MISMATCH"
            if not passed:
                b63_mismatches.append(key.upper())

    dilution = _map(b63_scenario.get("dilution_attribution"))
    parent_attr = _map(b63_scenario.get("parent_adjustment_attribution"))
    b62_parent = _map(b62_scenario.get("selected_parent_adjustments"))
    b62_shares = _dec(b62_scenario.get("selected_diluted_shares"))
    b62_b4_equity = _dec(b62_scenario.get("b4_forecast_implied_total_equity_value_with_selected_parent_adjustments_cny"))
    b62_required_equity = _dec(b62_scenario.get("required_terminal_equity_value_for_required_return_cny"))
    b62_selected_pool = _dec(b62_scenario.get("selected_sotp_segment_equity_value_pool_cny"))
    b62_b4_pool = _dec(b62_scenario.get("b4_forecast_segment_equity_value_pool_at_selected_sotp_pe_cny"))
    b62_central_cost = _dec(b62_parent.get("capitalized_central_cost_cny"))
    b62_net_cash = _dec(b62_parent.get("net_cash_debt_cny"))
    b62_other = _dec(b62_parent.get("other_adjustments_cny"))
    b63_b4_equity = _dec(dilution.get("b4_forecast_total_equity_value_cny"))
    b63_required_equity = _dec(dilution.get("required_total_equity_value_cny"))
    b63_shares = _dec(dilution.get("selected_diluted_shares"))
    b63_required_per_share = _dec(dilution.get("required_terminal_value_per_share_cny"))
    b63_per_share_gap = _dec(dilution.get("per_share_gap_cny"))
    b63_required_pool_parent_identity = (
        _dec(parent_attr.get("capitalized_central_cost_load_on_required_segment_pool_cny")),
        _dec(parent_attr.get("net_cash_debt_offset_to_required_segment_pool_cny")),
        _dec(parent_attr.get("other_adjustments_offset_to_required_segment_pool_cny")),
    )
    b61_required_without = _map(required_return_requirement.get("without_distributions"))
    b61_required_pool = _dec(b61_required_without.get("required_segment_equity_value_pool_cny"))
    b61_required_equity = _dec(b61_required_without.get("required_terminal_equity_value_cny"))
    b61_shares = _dec(b61_scenario.get("selected_diluted_shares"))
    b61_central_cost = _dec(b61_scenario.get("selected_capitalized_central_cost_cny"))
    b61_net_cash = _dec(b61_scenario.get("selected_net_cash_debt_cny"))
    b61_other = _dec(b61_scenario.get("selected_other_adjustments_cny"))
    critical_b63_equity_inputs = (
        b62_shares, b62_b4_equity, b62_required_equity, b62_selected_pool, b62_b4_pool,
        b62_central_cost, b62_net_cash, b62_other, b4_per_share, required_per_share,
        b63_b4_equity, b63_required_equity, b63_shares, b63_required_per_share, b63_per_share_gap,
        b61_required_pool, b61_required_equity, b61_shares, b61_central_cost, b61_net_cash, b61_other,
        *b63_required_pool_parent_identity,
    )
    equity_pairs: dict[str, tuple[Decimal | None, Decimal | None]] = {
        "step_1_selected_pool_matches_b62": (step1, b62_selected_pool),
        "step_5_required_pool_matches_b61": (step5, b61_required_pool),
        "b61_required_pool_matches_b62": (b61_required_pool, b62_required_pool),
        "b61_required_equity_matches_b62": (b61_required_equity, b62_required_equity),
        "b61_b62_share_counts_match": (b61_shares, b62_shares),
        "b61_b62_capitalized_central_cost_matches": (b61_central_cost, b62_central_cost),
        "b61_b62_net_cash_debt_matches": (b61_net_cash, b62_net_cash),
        "b61_b62_other_adjustments_match": (b61_other, b62_other),
        "b62_b4_equity_divided_by_shares_equals_b4_per_share": (
            b62_b4_equity / b62_shares if b62_shares else None, b4_per_share
        ),
        "b62_required_equity_divided_by_shares_equals_required_per_share": (
            b62_required_equity / b62_shares if b62_shares else None, required_per_share
        ),
        "b63_vs_b62_diluted_shares": (b63_shares, b62_shares),
        "b63_b4_equity_matches_b62": (b63_b4_equity, b62_b4_equity),
        "b63_required_equity_matches_b62": (b63_required_equity, b62_required_equity),
        "b63_required_per_share_matches_b61": (b63_required_per_share, required_per_share),
        "b63_per_share_gap_sign_and_amount": (
            b63_per_share_gap, -per_share_gap if per_share_gap is not None else None
        ),
        "b63_parent_central_cost_matches_b62": (b63_required_pool_parent_identity[0], b62_central_cost),
        "b63_parent_net_cash_offset_matches_b62": (
            b63_required_pool_parent_identity[1], -b62_net_cash if b62_net_cash is not None else None
        ),
        "b63_parent_other_adjustment_offset_matches_b62": (
            b63_required_pool_parent_identity[2], -b62_other if b62_other is not None else None
        ),
        "required_pool_parent_adjustment_identity": (
            b63_required_equity
            + b63_required_pool_parent_identity[0]
            + b63_required_pool_parent_identity[1]
            + b63_required_pool_parent_identity[2],
            step5,
        ),
        "b4_equity_parent_adjustment_identity": (
            b62_b4_pool - b62_central_cost + b62_net_cash + b62_other
            if all(v is not None for v in (b62_b4_pool, b62_central_cost, b62_net_cash, b62_other)) else None,
            b62_b4_equity,
        ),
    }
    if any(v is None for v in critical_b63_equity_inputs):
        b63_issues.append("B63_PARENT_ADJUSTMENT_OR_PER_SHARE_ARITHMETIC_INPUT_MISSING")
    for key, (left, right) in equity_pairs.items():
        if left is None or right is None:
            b63_checks[key] = "NOT_IDENTIFIABLE"
            if "B63_PARENT_ADJUSTMENT_OR_PER_SHARE_ARITHMETIC_INPUT_MISSING" not in b63_issues:
                b63_issues.append(f"{key.upper()}_ARITHMETIC_INPUT_MISSING")
            continue
        passed = _close(left, right, b63_tol)
        b63_checks[key] = "PASS" if passed else "MISMATCH"
        if not passed:
            b63_mismatches.append(key.upper())

    # Independently sum the B68 carried B4 full-vector segment profits at the
    # same selected SOTP P/Es. This must reproduce B63 step 3, not a single-segment
    # alternative from B61/B63.
    b68_segments = b68_scenario.get("segments") if isinstance(b68_scenario.get("segments"), list) else []
    b68_full_vector_pool = Decimal("0")
    b68_vector_complete = bool(b68_segments)
    for segment in b68_segments:
        if not isinstance(segment, Mapping):
            b68_vector_complete = False
            break
        profit = _dec(segment.get("b4_forecast_normalized_parent_attributable_profit_cny"))
        pe = _dec(segment.get("selected_sotp_pe_x"))
        if profit is None or pe is None or pe <= 0:
            b68_vector_complete = False
            break
        b68_full_vector_pool += profit * pe
    if b68_vector_complete and step3 is not None:
        b68_vector_ok = _close(b68_full_vector_pool, step3, b63_tol)
        b63_checks["b68_full_vector_recomputed_pool_matches_b63_step_3"] = "PASS" if b68_vector_ok else "MISMATCH"
        if not b68_vector_ok:
            b63_mismatches.append("B68_FULL_VECTOR_POOL_DOES_NOT_MATCH_B63_STEP_3")
    else:
        b63_checks["b68_full_vector_recomputed_pool_matches_b63_step_3"] = "NOT_IDENTIFIABLE"
        b63_issues.append("B68_FULL_VECTOR_RECOMPUTATION_INPUT_MISSING")

    b63_checks["status"] = (
        "MISMATCH" if b63_mismatches else "NOT_IDENTIFIABLE" if b63_issues else "PASS"
    )
    b63_issues.extend(b63_mismatches)
    reconciliation_failed = bool(b63_mismatches)
    reconciliation_not_identifiable = bool(b63_issues) and not reconciliation_failed

    required_pe_rows = _map(b63_scenario.get("multiple_attribution")).get("required_common_pe_by_segment")
    if isinstance(required_pe_rows, list):
        required_pe_by_id = {
            str(row.get("segment_id")): row for row in required_pe_rows if isinstance(row, Mapping)
        }
    else:
        required_pe_by_id = {}
    segment_rows: list[dict[str, Any]] = []
    for segment in b68_scenario.get("segments") or []:
        if not isinstance(segment, Mapping):
            continue
        segment_id = str(segment.get("segment_id") or "")
        b4_profit = segment.get("b4_forecast_normalized_parent_attributable_profit_cny")
        b61_lens = _map(segment.get("b61_required_profit_lens"))
        b63_lens = _map(segment.get("b63_full_b4_vector_lens"))
        b61_reverse = _map(b61_lens.get("reverse_engineering"))
        b63_reverse = _map(b63_lens.get("reverse_engineering"))
        b61_required = b61_lens.get("required_parent_attributable_profit_cny")
        b63_required = b63_lens.get("required_parent_attributable_profit_cny")
        b4_minus_b61 = _difference(b4_profit, b61_required)
        b4_minus_b63 = _difference(b4_profit, b63_required)
        required_pe = _map(required_pe_by_id.get(segment_id))
        selected_pe = _dec(segment.get("selected_sotp_pe_x"))
        required_common_pe = _dec(required_pe.get("required_pe_under_common_scale_x"))
        segment_rows.append({
            "segment_id": segment_id,
            "segment_name": segment.get("segment_name"),
            "forecast_period": b62_scenario.get("forecast_period", "UNKNOWN"),
            "b4_independent_forecast_parent_attributable_profit_cny": b4_profit,
            "b61_one_segment_at_a_time_required_profit_cny": b61_required,
            "b4_forecast_minus_b61_requirement_cny": b4_minus_b61,
            "b61_lens_status": b61_reverse.get("status", "UNKNOWN"),
            "b63_full_b4_vector_one_segment_sensitivity_required_profit_cny": b63_required,
            "b4_forecast_minus_b63_segment_sensitivity_cny": b4_minus_b63,
            "b63_lens_status": b63_reverse.get("status", "UNKNOWN"),
            "selected_sotp_pe_x": _fmt(selected_pe),
            "b63_required_common_pe_x": _fmt(required_common_pe),
            "selected_minus_required_common_pe_x": (
                _fmt(selected_pe - required_common_pe)
                if selected_pe is not None and required_common_pe is not None else None
            ),
            "b61_driver_alternatives": [
                _driver_row(row) for row in (b61_reverse.get("product_driver_alternatives") or [])
                if isinstance(row, Mapping)
            ],
            "b63_driver_alternatives": [
                _driver_row(row) for row in (b63_reverse.get("product_driver_alternatives") or [])
                if isinstance(row, Mapping)
            ],
            "non_additive_warning": "B61/B63 单分部利润阈值及产品销量/售价/成本单变量解均为替代敏感性，不可相加。",
        })

    issues: list[str] = []
    if b61_scenario.get("status") != "CALCULATED_CONDITIONAL":
        issues.append("B61_SCENARIO_NOT_FULLY_CALCULATED")
    if b62_scenario.get("status") != "CALCULATED_CONDITIONAL":
        issues.append("B62_SCENARIO_NOT_FULLY_RECONCILED")
    if b63_scenario.get("status") == "PARTIAL":
        b63_partial_issues = b63_scenario.get("issues") if isinstance(b63_scenario.get("issues"), list) else []
        if b63_partial_issues and set(str(item) for item in b63_partial_issues) <= {
            "COMMON_PE_SCALE_NOT_IDENTIFIABLE_NONPOSITIVE_VALUE_POOL"
        }:
            issues.append("B63_COMMON_PE_SCALE_ONLY_NOT_IDENTIFIABLE")
        else:
            issues.append("B63_PARTIAL_NOT_LIMITED_TO_COMMON_PE_SCALE")
    elif b63_scenario.get("status") != "CONDITIONAL_ATTRIBUTION_CALCULATED":
        issues.append("B63_SCENARIO_NOT_FULLY_RECONCILED")
    if b63_issues:
        issues.extend(b63_issues)
    if b68_scenario.get("status") == "PARTIAL":
        issues.append("B68_SCENARIO_PARTIAL")
    elif b68_scenario.get("status") != "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED":
        issues.append("B68_SCENARIO_NOT_FULLY_REVERSE_ENGINEERED")
    if b4_pool is None or required_pool is None:
        issues.append("B63_FULL_VECTOR_POOL_VALUES_MISSING")
    if b4_per_share is None or required_per_share is None:
        issues.append("B62_PER_SHARE_COMPARISON_VALUES_MISSING")
    row_status = (
        "RECONCILIATION_MISMATCH" if reconciliation_failed
        else "NOT_IDENTIFIABLE" if reconciliation_not_identifiable
        else "PARTIAL" if issues
        else "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    )
    gap_allowed = row_status in {"PARTIAL", "CONDITIONAL_PRICE_COMPARISON_CALCULATED"}
    return {
        "scenario": name,
        "forecast_period": b62_scenario.get("forecast_period", "UNKNOWN"),
        "valuation_terminal_date": b62_scenario.get("valuation_terminal_date", "UNKNOWN"),
        "status": row_status,
        "issues": issues,
        "arithmetic_reconciliation": {
            "status": b63_checks.get("status", "NOT_IDENTIFIABLE"),
            "checks": b63_checks,
            "limitations": [
                "B63 全向量 step 3 与 step 5 分别对照 B62 B4 forecast pool 与 B61 required pool。",
                "稀释股数、母公司调整与每股终值/缺口由 B76 独立复核；共同 P/E 缩放不识别不等于价值池算术失败。",
            ],
        },
        "upstream_statuses": {
            "b61": b61_scenario.get("status", "UNKNOWN"),
            "b62": b62_scenario.get("status", "UNKNOWN"),
            "b63": b63_scenario.get("status", "UNKNOWN"),
            "b68": b68_scenario.get("status", "UNKNOWN"),
        },
        "forecast_period": b62_scenario.get("forecast_period", "UNKNOWN"),
        "earnings_gap": {
            "required_return_annualized_rate": required_return_requirement.get("annualized_return_rate"),
            "fundamental_target_annualized_rate": fundamental_target_requirement.get("annualized_return_rate"),
            "comparison_basis": "B4_FULL_FORECAST_SEGMENT_PROFIT_VECTOR_AT_SELECTED_SOTP_PES_VS_B61_REQUIRED_RETURN_POOL",
            "b4_independent_forecast_segment_value_pool_cny": _fmt(b4_pool) if gap_allowed else None,
            "required_segment_value_pool_for_required_return_cny": _fmt(required_pool) if gap_allowed else None,
            "b4_forecast_pool_minus_required_pool_cny": _fmt(pool_gap) if gap_allowed else None,
            "headroom_vs_required_pool_pct": _fmt(pool_gap_pct) if gap_allowed else None,
            "direction": (
                "FORECAST_POOL_ABOVE_REQUIRED_POOL" if gap_allowed and pool_gap is not None and pool_gap > _TOL
                else "FORECAST_POOL_BELOW_REQUIRED_POOL" if gap_allowed and pool_gap is not None and pool_gap < -_TOL
                else "AT_OR_WITHIN_TOLERANCE" if gap_allowed and pool_gap is not None
                else "UNKNOWN"
            ),
            "b4_forecast_implied_terminal_value_per_share_cny": _fmt(b4_per_share) if gap_allowed else None,
            "required_terminal_value_per_share_for_required_return_cny": _fmt(required_per_share) if gap_allowed else None,
            "per_share_terminal_value_headroom_cny": _fmt(per_share_gap) if gap_allowed else None,
            "parent_adjustments_and_diluted_shares": "HELD_AT_B61_SELECTED_VALUES",
            "meaning": "仅表示独立 B4 预测在当前 SOTP 假设下相对 Required Return 条件要求的数学余量；不是外部 MIE，也不是独立概率判断。",
        },
        "operating_gap": {
            "status": "CONDITIONAL_PRICE_CONDITIONED_OPERATING_ALTERNATIVES" if segment_rows else "NOT_IDENTIFIABLE",
            "comparison_basis": "B68_PRODUCT_SALES_VOLUME_NET_ASP_UNIT_VARIABLE_COST_SINGLE_DRIVER_ALTERNATIVES",
            "segments": [
                {
                    "segment_id": row.get("segment_id"),
                    "b61_one_segment_at_a_time_alternatives": row.get("b61_driver_alternatives") or [],
                    "b63_full_b4_vector_alternatives": row.get("b63_driver_alternatives") or [],
                }
                for row in segment_rows
            ],
            "limitation": "销量、净售价、单位成本是不同的替代敏感性，不是同时要实现的经营目标；销售量反推不自动证明产能/库存可行。",
        },
        "segment_comparisons": segment_rows,
        "valuation_gap": {
            "basis": "B63_PARALLEL_COMMON_PE_SCALE_REQUIRED_IF_FULL_B4_EARNINGS_ARE_ACHIEVED",
            "status": (
                _map(b63_scenario.get("multiple_attribution")).get("status", "UNKNOWN")
                if b63_scenario.get("status") != "PARTIAL" else "NOT_IDENTIFIABLE_OR_PARTIAL"
            ),
            "required_common_pe_by_segment": list(required_pe_by_id.values()),
            "interpretation": "条件倍数敏感性，不是单一分部公平 P/E，也不是市场交易倍数或外部 MIE。",
        },
        "event_timing_gap": {
            "status": "NOT_IDENTIFIABLE",
            "reason": "B61/B63/B68 的 Required Return 反推按估值终点和预测期间计算，没有独立的逐事件市场定价时间要求可供比较。",
        },
    }



def _eps_requirement_pair(
    forecast_eps: Any,
    required_eps: Any,
    *,
    basis: str,
) -> dict[str, Any]:
    forecast = _dec(forecast_eps)
    required = _dec(required_eps)
    if forecast is None or required is None or required <= 0:
        return {
            "status": "NOT_IDENTIFIABLE",
            "basis": basis,
            "forecast_eps_cny_per_share": _fmt(forecast),
            "required_eps_cny_per_share": _fmt(required),
            "forecast_minus_required_cny_per_share": None,
            "headroom_vs_required_pct": None,
            "direction": "UNKNOWN",
            "unit": "CNY/share",
        }
    gap = forecast - required
    return {
        "status": "CALCULATED",
        "basis": basis,
        "forecast_eps_cny_per_share": _fmt(forecast),
        "required_eps_cny_per_share": _fmt(required),
        "forecast_minus_required_cny_per_share": _fmt(gap),
        "headroom_vs_required_pct": _fmt((forecast / required - Decimal("1")) * Decimal("100")),
        "direction": (
            "B4_FORECAST_ABOVE_REQUIREMENT" if gap > 0
            else "B4_FORECAST_BELOW_REQUIREMENT" if gap < 0
            else "B4_FORECAST_EQUALS_REQUIREMENT"
        ),
        "unit": "CNY/share",
    }


def _close(left: Decimal | None, right: Decimal | None, tolerance: Decimal) -> bool:
    return left is not None and right is not None and abs(left - right) <= tolerance


def _eps_multiple_comparison(
    local_eps_multiple_recalculation: Mapping[str, Any] | None,
    *,
    selected_model_family: str,
    expected_current_price: Any,
) -> dict[str, Any]:
    """Independently reconcile B60 arithmetic and compare B57 EPS with the price hurdle."""
    b60 = _map(local_eps_multiple_recalculation)
    family = str(selected_model_family or "UNKNOWN").strip().upper()
    current_price = _dec(expected_current_price)
    b60_price = _dec(b60.get("reference_price"))
    years = _dec(b60.get("annualization_year_fraction"))
    hurdle = _dec(b60.get("required_return_annualized_rate"))
    target = _dec(b60.get("fundamental_target_annualized_rate"))
    result: dict[str, Any] = {
        "status": "NOT_IDENTIFIABLE",
        "classification": "B4_B57_CONDITIONAL_FORWARD_EPS_VS_B60_PRICE_CONDITIONED_REQUIRED_EPS_NOT_EXTERNAL_MIE",
        "selected_model_family": family,
        "currency": str(b60.get("currency") or "UNKNOWN").upper(),
        "unit": "CNY/share",
        "comparison_basis": "B4_B57_COMPANY_WIDE_FORWARD_ALL_ITEMS_DILUTED_EPS_PROXY_VS_B60_REQUIRED_TERMINAL_EPS_WITH_EXPLICIT_SOURCE_CLASS",
        "forecast_period": b60.get("forecast_period") or "UNKNOWN",
        "valuation_terminal_date": b60.get("valuation_terminal_date") or "UNKNOWN",
        "annualization_year_fraction": _fmt(years),
        "required_return_annualized_rate": _fmt(hurdle),
        "fundamental_target_annualized_rate": _fmt(target),
        "structured_current_price": _fmt(current_price),
        "b60_reference_price": _fmt(b60_price),
        "price_reference_status": "UNKNOWN",
        "price_assurance": b60.get("price_assurance") or "UNKNOWN",
        "price_pit_status": b60.get("price_pit_status") or "UNKNOWN",
        "b60_status": b60.get("status") or "UNKNOWN",
        "external_mie_status_unchanged": b60.get("external_mie_status_unchanged") or "UNKNOWN",
        "external_mie_modified": False,
        "expectation_gap_modified": False,
        "b4_forecast_modified": False,
        "b60_calculation_modified": False,
        "valuation_modified": False,
        "formal_evidence_pit_admission_created": False,
        "formal_forecast_admission_created": False,
        "decision_grade_forecast_eligible": False,
        "decision_grade_status": "NOT_ADMITTED_CONDITIONAL_ARITHMETIC_ONLY",
        "decision_authority": False,
        "period_alignment_contract": (
            "仅接受 B60 场景的 b58_forecast_period_match=True；B58 已核对 B4 forecast_period、B57 forward period、"
            "primary EPS bridge period 与 EPS_MULTIPLE forecast_period。valuation_terminal_date 单独展示，不作为盈利期间。"
        ),
        "earnings_basis": (
            "只使用 B60 携带的 B57 all-items parent-attributable EPS proxy；不使用 B57 normalized EPS，"
            "不把 EPS_MULTIPLE 主适配器自报 EPS 当成独立 B4 预测；每个情景必须保留 B57 与主 EPS 的来源分类。"
        ),
        "b58_confirmation_semantics": "B58 MATCH means arithmetic period/share/accounting reconciliation only; it is not independent source confirmation or formal admission.",
        "source_trust_semantics": "B57 source class and PIT-compatible prechecks are provenance metadata only; B76 does not create signed Evidence/PIT admission or formal Forecast Admission. Arithmetic PASS remains conditional, not decision-grade.",
        "required_return_rate_source": "B60 receives decision_parameters.required_return_annualized; B76 rechecks the supplied rate and never substitutes the Fundamental Target.",
        "fundamental_target_rate_source": "B60 receives the separately configured decision_parameters.fundamental_target_annualized_return.",
        "target_entry_price_source": "EXISTING_RETURN_SOLVER_ONLY",
        "distribution_treatment": (
            "不含分红的 Required Return EPS 为主比较；只有 B60 标记为已验证的定时现金分配时，"
            "才单独展示分红调整比较。"
        ),
        "arithmetic_tolerance": "0.000001 CNY/share",
        "scenarios": {},
        "limitations": [
            "这是当前结构化价格、B60 终端 P/E、持有期和回报门槛下的条件性 EPS 要求，不是外部 MIE。",
            "B4/B57 EPS 是公司整体 all-items EPS proxy；它不等于已审计实际 EPS，也不证明预测质量。",
            "Required Return 与 Fundamental Target 分开呈现；二者不能互相替代，也不能把 15%目标 EPS 当作 Required Return EPS。",
            "只有 B57 已完成公司整体利润归属/稀释股数桥且 B58 期间匹配为 true，才进行数值比较。",
            "B76 对 B60 的复核只验证输入之间的算术一致性，不验证终端 P/E 是否公允或可实现。",
        ],
    }
    if family != "EPS_MULTIPLE":
        result["status"] = "NOT_APPLICABLE_NOT_EPS_MULTIPLE"
        return result
    if not b60:
        result["status"] = "BLOCKED_BY_B60_RESULT_MISSING"
        return result
    if str(b60.get("selected_model_family") or "").strip().upper() != "EPS_MULTIPLE":
        result["status"] = "BLOCKED_BY_B60_MODEL_FAMILY_MISMATCH"
        return result
    if result["currency"] != "CNY":
        result["status"] = "NOT_COMPARABLE_CURRENCY"
        return result
    if result["b60_status"] not in {"CONDITIONAL_SENSITIVITY_CALCULATED", "PARTIAL"}:
        result["status"] = "BLOCKED_BY_B60"
        return result
    if current_price is None or current_price <= 0 or b60_price is None:
        result["status"] = "PRICE_REFERENCE_NOT_IDENTIFIABLE"
        return result
    if current_price != b60_price:
        result["price_reference_status"] = "MISMATCH"
        result["status"] = "PRICE_REFERENCE_MISMATCH"
        return result
    result["price_reference_status"] = "MATCH"
    if years is None or years <= 0 or hurdle is None or target is None or hurdle <= -1 or target <= -1:
        result["status"] = "RETURN_HURDLE_OR_HORIZON_NOT_IDENTIFIABLE"
        return result

    raw_scenarios = _map(b60.get("scenarios"))
    statuses: list[str] = []
    validated_distribution_statuses = {
        "VALIDATED_DATED_CASH_FLOWS",
        "VALIDATED_NO_FUTURE_DISTRIBUTIONS",
    }
    tolerance = Decimal("0.000001")
    required_factor = (Decimal("1") + hurdle) ** years
    target_factor = (Decimal("1") + target) ** years
    for name in _SCENARIOS:
        raw = _map(raw_scenarios.get(name))
        b57_status = str(raw.get("b57_status") or "UNKNOWN")
        period_match = raw.get("b58_forecast_period_match") is True
        b4_eps = _dec(raw.get("b57_all_items_eps_proxy"))
        b57_profit = _dec(raw.get("b57_all_items_parent_attributable_net_profit_proxy_cny"))
        b57_shares = _dec(raw.get("b57_diluted_weighted_average_shares"))
        terminal_pe = _dec(raw.get("selected_terminal_pe"))
        primary_eps = _dec(raw.get("primary_eps_actually_used"))
        primary_terminal = _dec(raw.get("primary_terminal_value_using_selected_pe"))
        row: dict[str, Any] = {
            "scenario": name,
            "status": "NOT_IDENTIFIABLE",
            "b60_scenario_status": raw.get("status") or "UNKNOWN",
            "b57_status": b57_status,
            "b58_status": raw.get("b58_status") or "UNKNOWN",
            "b58_forecast_period_match": period_match,
            "b4_forecast_period": raw.get("b57_forward_period") or ("UNKNOWN" if not period_match else result["forecast_period"]),
            "b60_eps_forecast_period": result["forecast_period"],
            "valuation_terminal_date": result["valuation_terminal_date"],
            "b4_all_items_parent_attributable_profit_cny": _fmt(b57_profit),
            "b4_diluted_weighted_average_shares": _fmt(b57_shares),
            "b4_independent_all_items_eps_proxy_cny_per_share": _fmt(b4_eps),
            "primary_adapter_eps_cny_per_share": _fmt(primary_eps),
            "b57_forward_data_class": str(raw.get("b57_forward_data_class") or "SOURCE_CLASS_NOT_IDENTIFIABLE"),
            "b57_source_data_classes": list(raw.get("b57_source_data_classes") or []) if isinstance(raw.get("b57_source_data_classes"), list) else [],
            "b57_source_lineage_assessment": dict(raw.get("b57_source_lineage_assessment") or {}) if isinstance(raw.get("b57_source_lineage_assessment"), Mapping) else {},
            "formal_evidence_pit_admission_created": False,
            "formal_forecast_admission_created": False,
            "decision_grade_forecast_eligible": False,
            "primary_eps_data_class": str(raw.get("primary_eps_data_class") or "SOURCE_CLASS_NOT_IDENTIFIABLE"),
            "primary_eps_evidence_refs": list(raw.get("primary_eps_evidence_refs") or []) if isinstance(raw.get("primary_eps_evidence_refs"), list) else [],
            "independent_confirmation_status": "NOT_ESTABLISHED_BY_B58_NUMERICAL_RECONCILIATION",
            "selected_terminal_pe_x": _fmt(terminal_pe),
            "primary_adapter_terminal_value_cny_per_share": _fmt(primary_terminal),
            "arithmetic_reconciliation": {
                "status": "NOT_IDENTIFIABLE",
                "b57_profit_divided_by_shares": "NOT_IDENTIFIABLE",
                "primary_eps_times_pe": "NOT_IDENTIFIABLE",
                "required_return_eps": "NOT_IDENTIFIABLE",
                "fundamental_target_eps": "NOT_IDENTIFIABLE",
                "distribution_adjusted_required_return_eps": "NOT_IDENTIFIABLE",
                "distribution_adjusted_fundamental_target_eps": "NOT_IDENTIFIABLE",
                "issues": [],
            },
            "required_return": {},
            "fundamental_target": {},
            "issues": [],
        }
        arithmetic_issues: list[str] = []
        if raw.get("status") != "CALCULATED_CONDITIONAL":
            row["issues"].append("B60_SCENARIO_NOT_CALCULATED")
        if b57_status not in {
            "CALCULATED_AND_RECONCILED",
            "FORWARD_ALL_ITEMS_EPS_CALCULATED_HISTORICAL_NORMALIZATION_NOT_IDENTIFIABLE",
        }:
            row["issues"].append("B57_COMPANY_WIDE_FORWARD_ALL_ITEMS_EPS_BRIDGE_NOT_RECONCILED")
        if not period_match:
            row["issues"].append("B4_B57_B58_B60_FORECAST_PERIOD_NOT_CONFIRMED_MATCH")
        if row["b58_status"] != "MATCH":
            row["issues"].append("B58_PRIMARY_EPS_ACCOUNTING_AND_DILUTED_SHARE_BASIS_NOT_RECONCILED")
        allowed_b57_source_classes = {
            "OBSERVED_ACTUAL",
            "ISSUER_FORECAST",
            "ANALYST_ASSUMPTION",
            "MIXED_OBSERVED_ACTUAL_AND_ANALYST_ASSUMPTION",
            "MIXED_OBSERVED_ACTUAL_AND_ISSUER_FORECAST",
            "MIXED_ISSUER_FORECAST_AND_ANALYST_ASSUMPTION",
            "MIXED_OBSERVED_ACTUAL_ISSUER_FORECAST_AND_ANALYST_ASSUMPTION",
        }
        if row["b57_forward_data_class"] not in allowed_b57_source_classes:
            row["issues"].append("B57_FORWARD_DATA_CLASS_NOT_IDENTIFIABLE")
        if row["primary_eps_data_class"] not in {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}:
            row["issues"].append("PRIMARY_EPS_DATA_CLASS_NOT_IDENTIFIABLE")
        if str(raw.get("b57_forward_period") or "").strip().upper() != str(b60.get("forecast_period") or "").strip().upper():
            row["issues"].append("B57_FORWARD_PERIOD_DIFFERS_FROM_B60_EARNINGS_PERIOD")
        if str(b60.get("forecast_period") or "").strip().upper() in {"", "UNKNOWN"}:
            row["issues"].append("B60_EPS_FORECAST_PERIOD_UNKNOWN")
        if b57_profit is None or b57_shares is None or b57_shares <= 0 or b4_eps is None:
            row["issues"].append("B57_ALL_ITEMS_PROFIT_SHARE_DENOMINATOR_OR_EPS_MISSING")
        if terminal_pe is None or terminal_pe <= 0 or primary_eps is None or primary_eps <= 0 or primary_terminal is None:
            row["issues"].append("B60_SELECTED_PE_PRIMARY_EPS_OR_TERMINAL_VALUE_MISSING")
        if row["issues"]:
            row["status"] = "NOT_IDENTIFIABLE"
            row["arithmetic_reconciliation"]["issues"] = list(row["issues"])
            result["scenarios"][name] = row
            statuses.append(row["status"])
            continue

        # Recalculate the B57 all-items EPS using the explicit parent-attributable
        # profit numerator and the same-period weighted-average diluted-share denominator.
        b57_eps_recalculated = b57_profit / b57_shares
        b57_eps_ok = _close(b57_eps_recalculated, b4_eps, tolerance)
        row["arithmetic_reconciliation"]["b57_profit_divided_by_shares"] = (
            "PASS" if b57_eps_ok else "MISMATCH"
        )
        if not b57_eps_ok:
            arithmetic_issues.append("B57_ALL_ITEMS_EPS_DOES_NOT_EQUAL_PARENT_PROFIT_DIVIDED_BY_DILUTED_SHARES")

        # Reconcile the actual EPS_MULTIPLE adapter's EPS × P/E to its saved terminal value.
        primary_terminal_recalculated = primary_eps * terminal_pe
        primary_terminal_ok = _close(primary_terminal_recalculated, primary_terminal, tolerance)
        row["arithmetic_reconciliation"]["primary_eps_times_pe"] = (
            "PASS" if primary_terminal_ok else "MISMATCH"
        )
        if not primary_terminal_ok:
            arithmetic_issues.append("PRIMARY_EPS_TIMES_PE_DOES_NOT_EQUAL_ADAPTER_TERMINAL_VALUE")

        hurdle_required_eps = current_price * required_factor / terminal_pe
        target_required_eps = current_price * target_factor / terminal_pe
        b60_hurdle_eps = _dec(raw.get("required_return_eps_without_distributions"))
        b60_target_eps = _dec(raw.get("fundamental_target_eps_without_distributions"))
        hurdle_ok = _close(hurdle_required_eps, b60_hurdle_eps, tolerance)
        target_ok = _close(target_required_eps, b60_target_eps, tolerance)
        row["arithmetic_reconciliation"]["required_return_eps"] = "PASS" if hurdle_ok else "MISMATCH"
        row["arithmetic_reconciliation"]["fundamental_target_eps"] = "PASS" if target_ok else "MISMATCH"
        if not hurdle_ok:
            arithmetic_issues.append("B60_REQUIRED_RETURN_EPS_FORMULA_MISMATCH")
        if not target_ok:
            arithmetic_issues.append("B60_FUNDAMENTAL_TARGET_EPS_FORMULA_MISMATCH")

        distribution_status = str(raw.get("distribution_status") or "UNKNOWN").upper()
        pv_hurdle = _dec(raw.get("present_value_of_validated_cash_distributions_at_hurdle"))
        pv_target = _dec(raw.get("present_value_of_validated_cash_distributions_at_fundamental_target"))
        if distribution_status in validated_distribution_statuses:
            adjusted_hurdle = _dec(raw.get("required_return_eps_with_validated_distributions"))
            adjusted_target = _dec(raw.get("fundamental_target_eps_with_validated_distributions"))
            if pv_hurdle is None or pv_target is None or adjusted_hurdle is None or adjusted_target is None:
                arithmetic_issues.append("VALIDATED_DISTRIBUTION_ADJUSTED_EPS_OR_PRESENT_VALUE_MISSING")
                row["arithmetic_reconciliation"]["distribution_adjusted_required_return_eps"] = "NOT_IDENTIFIABLE"
                row["arithmetic_reconciliation"]["distribution_adjusted_fundamental_target_eps"] = "NOT_IDENTIFIABLE"
            else:
                hurdle_adjusted_expected = max(Decimal("0"), (current_price - pv_hurdle) * required_factor) / terminal_pe
                target_adjusted_expected = max(Decimal("0"), (current_price - pv_target) * target_factor) / terminal_pe
                hurdle_adjusted_ok = _close(hurdle_adjusted_expected, adjusted_hurdle, tolerance)
                target_adjusted_ok = _close(target_adjusted_expected, adjusted_target, tolerance)
                row["arithmetic_reconciliation"]["distribution_adjusted_required_return_eps"] = "PASS" if hurdle_adjusted_ok else "MISMATCH"
                row["arithmetic_reconciliation"]["distribution_adjusted_fundamental_target_eps"] = "PASS" if target_adjusted_ok else "MISMATCH"
                if not hurdle_adjusted_ok:
                    arithmetic_issues.append("B60_DISTRIBUTION_ADJUSTED_REQUIRED_RETURN_EPS_FORMULA_MISMATCH")
                if not target_adjusted_ok:
                    arithmetic_issues.append("B60_DISTRIBUTION_ADJUSTED_FUNDAMENTAL_TARGET_EPS_FORMULA_MISMATCH")
        else:
            row["arithmetic_reconciliation"]["distribution_adjusted_required_return_eps"] = "UNKNOWN_UNVALIDATED_DISTRIBUTIONS"
            row["arithmetic_reconciliation"]["distribution_adjusted_fundamental_target_eps"] = "UNKNOWN_UNVALIDATED_DISTRIBUTIONS"

        if arithmetic_issues:
            mismatch_issues = [
                issue for issue in arithmetic_issues
                if "MISMATCH" in issue or "DOES_NOT_EQUAL" in issue or "DOES_NOT_RECONCILE" in issue
            ]
            row["arithmetic_reconciliation"]["status"] = (
                "MISMATCH" if mismatch_issues else "NOT_IDENTIFIABLE"
            )
            row["status"] = "ARITHMETIC_RECONCILIATION_MISMATCH" if mismatch_issues else "NOT_IDENTIFIABLE"
            row["issues"] = arithmetic_issues
            row["arithmetic_reconciliation"]["issues"] = arithmetic_issues
            # Keep source operands visible for audit, but never expose a numeric
            # forecast-to-requirement headroom from an internally inconsistent chain.
            result["scenarios"][name] = row
            statuses.append(row["status"])
            continue

        row["arithmetic_reconciliation"]["issues"] = []
        row["arithmetic_reconciliation"]["status"] = (
            "PASS" if distribution_status in validated_distribution_statuses
            else "PASS_CORE_DISTRIBUTION_ADJUSTMENT_NOT_VALIDATED"
        )
        row["required_return"] = {
            "without_distributions": _eps_requirement_pair(
                b4_eps, hurdle_required_eps,
                basis="B4_B57_ALL_ITEMS_EPS_VS_B60_REQUIRED_RETURN_EPS_WITHOUT_DISTRIBUTIONS",
            )
        }
        if distribution_status in validated_distribution_statuses:
            row["required_return"]["with_validated_distributions"] = _eps_requirement_pair(
                b4_eps, raw.get("required_return_eps_with_validated_distributions"),
                basis="B4_B57_ALL_ITEMS_EPS_VS_B60_REQUIRED_RETURN_EPS_WITH_VALIDATED_DISTRIBUTIONS",
            )
        else:
            row["required_return"]["with_validated_distributions"] = {
                "status": "NOT_IDENTIFIABLE",
                "basis": "VALIDATED_DISTRIBUTION_CASH_FLOWS_REQUIRED",
                "distribution_status": distribution_status,
                "forecast_eps_cny_per_share": _fmt(b4_eps),
                "required_eps_cny_per_share": None,
                "forecast_minus_required_cny_per_share": None,
                "headroom_vs_required_pct": None,
                "direction": "UNKNOWN",
                "unit": "CNY/share",
            }
        row["fundamental_target"] = {
            "without_distributions": _eps_requirement_pair(
                b4_eps, target_required_eps,
                basis="B4_B57_ALL_ITEMS_EPS_VS_B60_FUNDAMENTAL_TARGET_EPS_WITHOUT_DISTRIBUTIONS",
            )
        }
        if distribution_status in validated_distribution_statuses:
            row["fundamental_target"]["with_validated_distributions"] = _eps_requirement_pair(
                b4_eps, raw.get("fundamental_target_eps_with_validated_distributions"),
                basis="B4_B57_ALL_ITEMS_EPS_VS_B60_FUNDAMENTAL_TARGET_EPS_WITH_VALIDATED_DISTRIBUTIONS",
            )
        else:
            row["fundamental_target"]["with_validated_distributions"] = {
                "status": "NOT_IDENTIFIABLE",
                "basis": "VALIDATED_DISTRIBUTION_CASH_FLOWS_REQUIRED",
                "distribution_status": distribution_status,
                "forecast_eps_cny_per_share": _fmt(b4_eps),
                "required_eps_cny_per_share": None,
                "forecast_minus_required_cny_per_share": None,
                "headroom_vs_required_pct": None,
                "direction": "UNKNOWN",
                "unit": "CNY/share",
            }
        row["status"] = "CALCULATED"
        result["scenarios"][name] = row
        statuses.append(row["status"])

    if statuses and all(status == "CALCULATED" for status in statuses):
        result["status"] = "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    elif any(status == "CALCULATED" for status in statuses):
        result["status"] = "PARTIAL"
    elif any(status == "ARITHMETIC_RECONCILIATION_MISMATCH" for status in statuses):
        result["status"] = "ARITHMETIC_RECONCILIATION_MISMATCH"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    return result


def _populate_win_odds(
    result: dict[str, Any],
    *,
    return_metrics: Mapping[str, Any] | None,
    price_input: Mapping[str, Any],
    forecast_valuation: Mapping[str, Any],
    thesis_break_stress_review: Mapping[str, Any] | None,
) -> None:
    """Populate shared payoff, failure-cost and time-cost diagnostics for every model family."""
    metrics = _map(return_metrics)
    entry = _dec(_map(price_input).get("price"))
    wealth = _map(metrics.get("scenario_terminal_wealth"))
    scenario_returns: dict[str, Decimal] = {}
    if entry is not None and entry > 0:
        for name in _SCENARIOS:
            terminal_wealth = _dec(wealth.get(name))
            if terminal_wealth is not None:
                scenario_returns[name] = terminal_wealth / entry - Decimal("1")
    bear = scenario_returns.get("bear")
    base = scenario_returns.get("base")
    bull = scenario_returns.get("bull")
    odds = result["win_odds"]
    odds["payoff_asymmetry"] = {
        "holding_period_total_return_by_scenario": {
            name: _fmt(value * Decimal("100")) for name, value in scenario_returns.items()
        },
        "base_upside_to_bear_downside_ratio": (
            _fmt(base / abs(bear))
            if base is not None and bear is not None and base > 0 and bear < 0 else None
        ),
        "bull_upside_to_bear_downside_ratio": (
            _fmt(bull / abs(bear))
            if bull is not None and bear is not None and bull > 0 and bear < 0 else None
        ),
        "ratio_basis": "同一输入价格、同一估值终点/持有期的情景总回报；不含概率含义。",
        "expected_annualized_return_under_submitted_weights": metrics.get("expected_annualized_return"),
    }
    stress = _map(thesis_break_stress_review)
    odds["thesis_break_stress"] = {
        "status": stress.get("status", "UNKNOWN"),
        "stress_total_return": _fmt(_dec(stress.get("stress_total_return"))),
        "stress_downside_pct": _fmt(_dec(stress.get("stress_downside_pct"))),
        "probability_weighted": False,
        "interpretation": "独立 thesis-break stress 是失败代价参照，不赋予概率，不并入 Bear/Base/Bull 权重。",
    }
    odds["probability_weighted_return"] = {
        "value": metrics.get("expected_annualized_return"),
        "method": metrics.get("expected_annualized_return_method"),
        "scenario_probabilities_calibrated": False,
        "model_declared_probabilities_calibrated": forecast_valuation.get("probabilities_calibrated"),
        "calibration_status": "NOT_INDEPENDENTLY_VERIFIED",
        "interpretation": "模型自报的概率校准标记不被本地视为已验证；现有计算器按输入情景权重得到的算术结果，不得解读为投资胜率。",
    }
    odds["time_cost"]["holding_period_year_fraction"] = _fmt(_dec(metrics.get("annualization_year_fraction")))
    odds["time_cost"]["horizon_years"] = _fmt(_dec(metrics.get("horizon_years")))

def build_expectation_gap_comparison(
    *,
    local_sotp_recalculation: Mapping[str, Any],
    return_metrics: Mapping[str, Any] | None,
    price_input: Mapping[str, Any],
    forecast_valuation: Mapping[str, Any],
    thesis_break_stress_review: Mapping[str, Any] | None,
    external_mie_status: str,
    local_eps_multiple_recalculation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare B4 independent forecasts with B61/B63/B60 requirements without changing MIE."""
    local = _map(local_sotp_recalculation)
    result: dict[str, Any] = {
        "schema_version": B76_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "price_conditioned_comparison_status": "NOT_IDENTIFIABLE",
        "coverage_status": "PARTIAL_WIN_PROBABILITY_AND_EVENT_TIMING_NOT_IDENTIFIABLE",
        "classification": "PRICE_CONDITIONED_REQUIREMENT_VS_INDEPENDENT_FORECAST_NOT_EXTERNAL_MIE",
        "external_mie_status_unchanged": external_mie_status or "UNKNOWN",
        "external_mie_modified": False,
        "expectation_gap_modified": False,
        "return_solver_target_entry_price": _fmt(_dec(_map(return_metrics).get("target_entry_price"))),
        "target_entry_price_modified": False,
        "target_entry_price_source": "EXISTING_RETURN_SOLVER_ONLY",
        "b4_forecast_modified": False,
        "b61_b63_b68_modified": False,
        "valuation_modified": False,
        "decision_authority": False,
        "win_odds": {
            "win_probability_status": "NOT_IDENTIFIABLE",
            "win_probability_range": None,
            "probability_basis": "现有 Bear/Base/Bull 权重及概率加权回报不等于经过校准的投资胜率；本批不生成胜率。",
            "probability_weighted_return_interpretation": "仅为既有回报计算器按提交权重得到的机械结果，不是胜率或概率校准证明。",
            "payoff_asymmetry": {},
            "thesis_break_stress": {},
            "time_cost": {
                "holding_period_year_fraction": _fmt(_dec(_map(return_metrics).get("annualization_year_fraction"))),
                "horizon_years": _fmt(_dec(_map(return_metrics).get("horizon_years"))),
                "opportunity_cost_quantification": "NOT_PROVIDED",
                "interpretation": "展示资金占用期限；没有独立替代投资回报基准时，不伪造机会成本金额。",
            },
        },
        "scenarios": {},
        "limitations": [
            "价格条件性比较不是外部市场隐含预期 MIE；MIE 与 expectation_gap 原状态不变。",
            "B61/B63 单分部阈值及 B68 产品销量/售价/成本解是单变量替代敏感性，不可相加。",
            "B63 full-vector pool 对比使用完整 B4 分部利润向量与既定 SOTP P/E；母公司调整和稀释股数固定。",
            "B68 反推结果不是独立预测，不得把反推值当作公司将实现的经营结果。",
            "15% Fundamental Target 与 Required Return 保持原有独立口径；本模块只展示 B63 的 Required Return 价值池要求。",
        ],
    }
    eps_comparison = _eps_multiple_comparison(
        local_eps_multiple_recalculation,
        selected_model_family=str(local.get("selected_model_family") or "UNKNOWN"),
        expected_current_price=_map(price_input).get("price"),
    )
    result["eps_multiple_comparison"] = eps_comparison
    result["eps_multiple_comparison_status"] = eps_comparison.get("status", "UNKNOWN")
    _populate_win_odds(
        result,
        return_metrics=return_metrics,
        price_input=price_input,
        forecast_valuation=forecast_valuation,
        thesis_break_stress_review=thesis_break_stress_review,
    )
    if str(local.get("selected_model_family") or "").upper() != "SOTP":
        # EPS_MULTIPLE is a first-class B76 comparison path; other model families
        # remain not applicable until they have a comparable local inversion contract.
        if str(local.get("selected_model_family") or "").upper() == "EPS_MULTIPLE":
            result["status"] = eps_comparison.get("status", "NOT_IDENTIFIABLE")
            result["price_conditioned_comparison_status"] = result["status"]
        else:
            result["status"] = "NOT_APPLICABLE_NON_SOTP"
        return result
    structured_price = _dec(_map(price_input).get("price"))
    b61_reference_price = _dec(local.get("reference_price"))
    result["structured_current_price"] = _fmt(structured_price)
    result["b61_reference_price"] = _fmt(b61_reference_price)
    result["price_reference_status"] = (
        "MATCH" if structured_price is not None and structured_price > 0
        and b61_reference_price is not None and structured_price == b61_reference_price
        else "MISMATCH" if structured_price is not None and b61_reference_price is not None
        else "NOT_IDENTIFIABLE"
    )
    if result["price_reference_status"] != "MATCH":
        result["status"] = (
            "PRICE_REFERENCE_MISMATCH" if result["price_reference_status"] == "MISMATCH"
            else "PRICE_REFERENCE_NOT_IDENTIFIABLE"
        )
        result["price_conditioned_comparison_status"] = result["status"]
        return result
    if str(local.get("currency") or "").upper() != "CNY":
        result["status"] = "NOT_COMPARABLE_CURRENCY"
        result["price_conditioned_comparison_status"] = result["status"]
        return result

    b63 = _map(local.get("valuation_gap_attribution"))
    b62 = _map(local.get("segment_earnings_reconciliation"))
    b68 = _map(local.get("operating_requirement_reverse_engineering"))
    result["forecast_period"] = b62.get("forecast_period") or local.get("forecast_period") or "UNKNOWN"
    result["valuation_terminal_date"] = (
        b62.get("valuation_terminal_date") or local.get("valuation_terminal_date") or "UNKNOWN"
    )
    result["currency"] = str(local.get("currency") or "UNKNOWN").upper()
    if b63.get("status") not in {"CONDITIONAL_ATTRIBUTION_CALCULATED", "PARTIAL"}:
        result["status"] = "BLOCKED_BY_B63"
        return result
    if b62.get("status") not in {"CONDITIONAL_RECONCILIATION_CALCULATED", "PARTIAL"}:
        result["status"] = "BLOCKED_BY_B62"
        return result
    if b68.get("status") not in {"CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED", "PARTIAL"}:
        result["status"] = "BLOCKED_BY_B68"
        return result

    b61_scenarios = _map(local.get("scenarios"))
    b62_scenarios = _map(b62.get("scenarios"))
    b63_scenarios = _map(b63.get("scenarios"))
    b68_scenarios = _map(b68.get("scenarios"))
    statuses = []
    for name in _SCENARIOS:
        row = _scenario_comparison(
            name,
            b61_scenario=_map(b61_scenarios.get(name)),
            b62_scenario=_map(b62_scenarios.get(name)),
            b63_scenario=_map(b63_scenarios.get(name)),
            b68_scenario=_map(b68_scenarios.get(name)),
        )
        result["scenarios"][name] = row
        statuses.append(row["status"])
    if statuses and all(status == "CONDITIONAL_PRICE_COMPARISON_CALCULATED" for status in statuses):
        result["status"] = "CONDITIONAL_PRICE_COMPARISON_CALCULATED"
    elif any(status in {"CONDITIONAL_PRICE_COMPARISON_CALCULATED", "PARTIAL"} for status in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    result["price_conditioned_comparison_status"] = result["status"]

    return result
