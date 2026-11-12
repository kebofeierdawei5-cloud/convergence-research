from __future__ import annotations

"""B68: reverse-engineer price-implied segment profit requirements into B4 drivers.

Read-only conditional sensitivities. It never writes back to B4 or SOTP inputs.
Each product's volume / ASP / unit-cost result is an alternative one-variable
solution with every other product and the other two drivers held fixed.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


B68_SCHEMA = "IIOS-SOTP-OPERATING-REQUIREMENT-REVERSE-ENGINEERING-0.1"
_SCENARIOS = ("bear", "base", "bull")
_TOL = Decimal("1")
_PRICE_POOL_TOL = Decimal("0.01")
_DRIVER_FIELDS = (
    "sales_volume_tonnes",
    "net_asp_cny_per_tonne",
    "variable_cost_cny_per_tonne",
)
_FINANCIAL_FIELDS = (
    "fixed_cash_opex_cny",
    "depreciation_amortization_cny",
    "finance_cost_cny",
    "tax_rate",
    "recurring_non_operating_pre_tax_cny",
    "normalized_minority_interest_net_profit_cny",
)


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
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() else None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _eq(a: Decimal | None, b: Decimal | None, tolerance: Decimal = _TOL) -> bool:
    return a is not None and b is not None and abs(a - b) <= tolerance


def _index(rows: Any, label: str, issues: list[str]) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    if not isinstance(rows, list):
        issues.append(f"{label}_ROWS_NOT_LIST")
        return output
    for n, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            issues.append(f"{label}_ROW_NOT_OBJECT:{n}")
            continue
        key = _txt(row.get("segment_id") or row.get("business_segment_id"))
        if not key or key in output:
            issues.append(f"{label}_ID_MISSING_OR_DUPLICATE:{key or n}")
            continue
        output[key] = row
    return output


def _lineage(row: Mapping[str, Any], field: str, accepted_classes: set[str]) -> dict[str, Any]:
    source = _map(_map(row.get("measure_lineage")).get(field))
    data_class = _txt(source.get("data_class")).upper() or "UNKNOWN"
    basis = _txt(source.get("basis")) or "UNKNOWN"
    refs = list(source.get("evidence_refs") or []) if isinstance(source.get("evidence_refs"), list) else []
    issues = list(source.get("issues") or []) if isinstance(source.get("issues"), list) else []
    status = (
        "TYPED_ASSUMPTION_OR_FORECAST_WITH_REFERENCE"
        if data_class in accepted_classes and basis != "UNKNOWN" and refs and not issues
        else "TYPED_ASSUMPTION_OR_FORECAST_WITHOUT_COMPLETE_REFERENCE"
        if data_class in accepted_classes and basis != "UNKNOWN" and not issues
        else "NOT_IDENTIFIABLE"
    )
    return {
        "data_class": data_class,
        "basis": basis,
        "evidence_refs": refs,
        "status": status,
        "issues": issues,
        "formal_evidence_admitted": False,
    }


def _financial_lineage(forward_segment: Mapping[str, Any]) -> dict[str, Any]:
    direct = {
        field: _lineage(forward_segment, field, {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"})
        for field in (
            "fixed_cash_opex_cny",
            "depreciation_amortization_cny",
            "finance_cost_cny",
            "tax_rate",
            "recurring_non_operating_pre_tax_cny",
        )
    }
    measure_lineage = _map(forward_segment.get("measure_lineage"))
    total_nci = _map(measure_lineage.get("minority_interest_net_profit_after_tax_cny"))
    nonrec_nci = _map(measure_lineage.get("minority_interest_nonrecurring_after_tax_cny"))
    nci_classes = {
        _txt(total_nci.get("data_class")).upper(),
        _txt(nonrec_nci.get("data_class")).upper(),
    }
    nci_refs = sorted({
        str(ref).strip()
        for item in (total_nci, nonrec_nci)
        for ref in (item.get("evidence_refs") if isinstance(item.get("evidence_refs"), list) else [])
        if str(ref).strip()
    })
    nci_issues = list(total_nci.get("issues") or []) + list(nonrec_nci.get("issues") or [])
    nci_ok = (
        _txt(total_nci.get("data_class")).upper() in {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}
        and _txt(nonrec_nci.get("data_class")).upper() in {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"}
        and bool(_txt(total_nci.get("basis")))
        and bool(_txt(nonrec_nci.get("basis")))
        and not nci_issues
    )
    direct["normalized_minority_interest_net_profit_cny"] = {
        "data_class": "DERIVED_FROM_TYPED_NCI_INPUTS" if nci_ok else "UNKNOWN",
        "basis": "TOTAL_NCI_AFTER_TAX_MINUS_NONRECURRING_NCI_AFTER_TAX",
        "evidence_refs": nci_refs,
        "status": (
            "DERIVED_FROM_TWO_TYPED_NCI_MEASURES"
            if nci_ok and nci_refs
            else "DERIVED_BUT_REFERENCE_COVERAGE_INCOMPLETE"
            if nci_ok
            else "NOT_IDENTIFIABLE"
        ),
        "source_data_classes": sorted(nci_classes),
        "issues": nci_issues,
        "formal_evidence_admitted": False,
    }
    return direct


def _invert_normalized_profit_to_contribution(
    required_parent_profit: Decimal,
    forward_segment: Mapping[str, Any],
) -> dict[str, Any]:
    values = {field: _num(forward_segment.get(field)) for field in _FINANCIAL_FIELDS}
    missing = [field for field, value in values.items() if value is None]
    if missing:
        return {
            "status": "NOT_IDENTIFIABLE",
            "missing_inputs": missing,
            "issues": ["B4_FORWARD_SEGMENT_FINANCIAL_INPUT_MISSING"],
        }
    fixed = values["fixed_cash_opex_cny"]
    da = values["depreciation_amortization_cny"]
    finance = values["finance_cost_cny"]
    tax = values["tax_rate"]
    recurring_nonop = values["recurring_non_operating_pre_tax_cny"]
    nci = values["normalized_minority_interest_net_profit_cny"]
    if tax < 0 or tax > 1:
        return {"status": "NOT_IDENTIFIABLE", "missing_inputs": [], "issues": ["B4_FORWARD_TAX_RATE_OUT_OF_RANGE"]}
    taxable_profit_after_nci = required_parent_profit + nci
    if taxable_profit_after_nci > 0:
        if tax >= 1:
            return {
                "status": "NOT_IDENTIFIABLE",
                "missing_inputs": [],
                "issues": ["FULL_TAX_RATE_PREVENTS_POSITIVE_PROFIT_INVERSION"],
            }
        required_normalized_pbt = taxable_profit_after_nci / (Decimal("1") - tax)
        tax_branch = "POSITIVE_TAXABLE_PROFIT"
    else:
        required_normalized_pbt = taxable_profit_after_nci
        tax_branch = "NONPOSITIVE_TAXABLE_PROFIT_NO_MODELED_CASH_TAX"
    required_contribution = required_normalized_pbt + fixed + da + finance - recurring_nonop
    current_contribution = _num(forward_segment.get("contribution_after_variable_cost_cny"))
    current_profit = _num(forward_segment.get("normalized_parent_attributable_net_profit_cny"))
    if current_contribution is None or current_profit is None:
        return {
            "status": "NOT_IDENTIFIABLE",
            "missing_inputs": ["contribution_after_variable_cost_cny", "normalized_parent_attributable_net_profit_cny"],
            "issues": ["B4_CURRENT_FORWARD_PROFIT_BRIDGE_MISSING"],
        }
    current_pbt = current_contribution - fixed - da - finance + recurring_nonop
    current_tax = max(current_pbt, Decimal("0")) * tax
    recalc_current = current_pbt - current_tax - nci
    if not _eq(recalc_current, current_profit, _PRICE_POOL_TOL):
        return {
            "status": "RECONCILIATION_MISMATCH",
            "missing_inputs": [],
            "current_profit_recalculated_cny": _fmt(recalc_current),
            "current_profit_from_b4_cny": _fmt(current_profit),
            "issues": ["B68_CURRENT_B4_NORMALIZED_PROFIT_RECALCULATION_MISMATCH"],
        }
    return {
        "status": "INVERTED_CONDITIONALLY",
        "required_parent_attributable_profit_cny": _fmt(required_parent_profit),
        "normalized_minority_interest_net_profit_cny_held_fixed": _fmt(nci),
        "required_normalized_profit_before_tax_cny": _fmt(required_normalized_pbt),
        "tax_rate_held_fixed": _fmt(tax),
        "tax_branch": tax_branch,
        "required_contribution_after_variable_cost_cny": _fmt(required_contribution),
        "current_contribution_after_variable_cost_cny": _fmt(current_contribution),
        "contribution_gap_cny": _fmt(required_contribution - current_contribution),
        "financial_assumptions_held_fixed": {
            "fixed_cash_opex_cny": _fmt(fixed),
            "depreciation_amortization_cny": _fmt(da),
            "finance_cost_cny": _fmt(finance),
            "tax_rate": _fmt(tax),
            "recurring_non_operating_pre_tax_cny": _fmt(recurring_nonop),
            "normalized_minority_interest_net_profit_cny": _fmt(nci),
        },
        "financial_measure_lineage": _financial_lineage(forward_segment),
        "formula": (
            "NORMALIZED_PARENT_PROFIT = NORMALIZED_PBT - MAX(NORMALIZED_PBT,0)*TAX_RATE - NORMALIZED_NCI; "
            "REQUIRED_CONTRIBUTION = REQUIRED_NORMALIZED_PBT + FIXED_OPEX + D&A + FINANCE_COST - RECURRING_NONOPERATING"
        ),
        "limitations": [
            "此反解固定 B4 已填的分部固定费用、折旧、融资、税率、经常性非经营项与正常化少数股东损益。",
            "税额沿用 B62 的 max(PBT,0) × tax_rate 简化规则；不模拟递延税、亏损结转、税收优惠或特殊税务安排。",
        ],
    }


def _driver_alternatives(
    *,
    product_row: Mapping[str, Any],
    required_segment_contribution: Decimal,
    current_segment_contribution: Decimal,
    segment_products: list[Mapping[str, Any]],
) -> dict[str, Any]:
    product_id = _txt(product_row.get("product_id"))
    forward = _map(product_row.get("forward_scenario"))
    q = _num(forward.get("sales_volume_tonnes"))
    asp = _num(forward.get("net_asp_cny_per_tonne"))
    unit_cost = _num(forward.get("variable_cost_cny_per_tonne"))
    missing = [
        field for field, value in (
            ("sales_volume_tonnes", q),
            ("net_asp_cny_per_tonne", asp),
            ("variable_cost_cny_per_tonne", unit_cost),
        ) if value is None
    ]
    if missing or _txt(product_row.get("status")).upper() != "CALCULATED_AND_RECONCILED":
        return {
            "product_id": product_id,
            "status": "NOT_IDENTIFIABLE",
            "missing_inputs": missing,
            "issues": ["B55_PRODUCT_LINE_NOT_RECONCILED_OR_DRIVER_MISSING"],
        }

    line_contribution = q * (asp - unit_cost)
    other_contribution = current_segment_contribution - line_contribution
    required_line_contribution = required_segment_contribution - other_contribution
    contribution_gap = required_line_contribution - line_contribution
    line_revenue = q * asp
    line_variable_cost = q * unit_cost
    other_revenue = sum(
        (_num(_map(other.get("forward_scenario")).get("sales_volume_tonnes")) or Decimal("0"))
        * (_num(_map(other.get("forward_scenario")).get("net_asp_cny_per_tonne")) or Decimal("0"))
        for other in segment_products if _txt(other.get("product_id")) != product_id
    )
    other_variable_cost = sum(
        (_num(_map(other.get("forward_scenario")).get("sales_volume_tonnes")) or Decimal("0"))
        * (_num(_map(other.get("forward_scenario")).get("variable_cost_cny_per_tonne")) or Decimal("0"))
        for other in segment_products if _txt(other.get("product_id")) != product_id
    )

    volume_status = "CALCULATED_CONDITIONAL"
    volume_required: Decimal | None = None
    unit_margin = asp - unit_cost
    if unit_margin <= 0:
        volume_status = "NOT_IDENTIFIABLE_NONPOSITIVE_UNIT_CONTRIBUTION"
    else:
        volume_required = required_line_contribution / unit_margin
        if volume_required < 0:
            volume_status = "NOT_FEASIBLE_NEGATIVE_REQUIRED_SALES_VOLUME"
    volume_revenue = volume_required * asp if volume_required is not None and volume_status == "CALCULATED_CONDITIONAL" else None
    volume_cost = volume_required * unit_cost if volume_required is not None and volume_status == "CALCULATED_CONDITIONAL" else None

    asp_status = "CALCULATED_CONDITIONAL"
    asp_required: Decimal | None = None
    if q <= 0:
        asp_status = "NOT_IDENTIFIABLE_NONPOSITIVE_SALES_VOLUME"
    else:
        asp_required = unit_cost + required_line_contribution / q
        if asp_required <= 0:
            asp_status = "NOT_FEASIBLE_NONPOSITIVE_REQUIRED_NET_ASP"
    asp_revenue = q * asp_required if asp_required is not None and asp_status == "CALCULATED_CONDITIONAL" else None

    cost_status = "CALCULATED_CONDITIONAL"
    cost_required: Decimal | None = None
    if q <= 0:
        cost_status = "NOT_IDENTIFIABLE_NONPOSITIVE_SALES_VOLUME"
    else:
        cost_required = asp - required_line_contribution / q
        if cost_required < 0:
            cost_status = "NOT_FEASIBLE_NEGATIVE_REQUIRED_UNIT_COST"
    cost_variable_cost = q * cost_required if cost_required is not None and cost_status == "CALCULATED_CONDITIONAL" else None

    product_lineage = {
        field: _lineage(forward, field, {"ISSUER_FORECAST", "ANALYST_ASSUMPTION"})
        for field in _DRIVER_FIELDS
    }
    production_context = _map(product_row.get("production_inventory_context"))
    return {
        "product_id": product_id,
        "product_name": _txt(product_row.get("product_name")) or product_id,
        "status": (
            "CALCULATED_CONDITIONAL"
            if any(status == "CALCULATED_CONDITIONAL" for status in (volume_status, asp_status, cost_status))
            else "NOT_IDENTIFIABLE"
        ),
        "current_forward_assumptions": {
            "sales_volume_tonnes": _fmt(q),
            "net_asp_cny_per_tonne": _fmt(asp),
            "variable_cost_cny_per_tonne": _fmt(unit_cost),
            "contribution_after_variable_cost_cny": _fmt(line_contribution),
            "revenue_cny": _fmt(line_revenue),
            "variable_cost_cny": _fmt(line_variable_cost),
        },
        "required_product_contribution_cny_under_this_alternative": _fmt(required_line_contribution),
        "required_product_contribution_change_cny": _fmt(contribution_gap),
        "single_driver_alternatives": {
            "sales_volume_only": {
                "status": volume_status,
                "required_sales_volume_tonnes": _fmt(volume_required) if volume_status == "CALCULATED_CONDITIONAL" else None,
                "change_tonnes": _fmt(volume_required - q) if volume_required is not None and volume_status == "CALCULATED_CONDITIONAL" else None,
                "change_pct": _fmt((volume_required / q - Decimal("1")) * Decimal("100")) if q > 0 and volume_required is not None and volume_status == "CALCULATED_CONDITIONAL" else None,
                "unit_contribution_margin_cny_per_tonne_held_fixed": _fmt(unit_margin),
                "required_product_revenue_cny": _fmt(volume_revenue),
                "required_segment_revenue_cny": _fmt(other_revenue + volume_revenue) if volume_revenue is not None else None,
                "required_segment_variable_cost_cny": _fmt(other_variable_cost + volume_cost) if volume_cost is not None else None,
                "production_and_inventory_feasibility": "NOT_IDENTIFIABLE_WITHOUT_EXPLICIT_PRODUCTION_INVENTORY_RELEASE_POLICY",
            },
            "net_asp_only": {
                "status": asp_status,
                "required_net_asp_cny_per_tonne": _fmt(asp_required) if asp_status == "CALCULATED_CONDITIONAL" else None,
                "change_cny_per_tonne": _fmt(asp_required - asp) if asp_required is not None and asp_status == "CALCULATED_CONDITIONAL" else None,
                "change_pct": _fmt((asp_required / asp - Decimal("1")) * Decimal("100")) if asp > 0 and asp_required is not None and asp_status == "CALCULATED_CONDITIONAL" else None,
                "sales_volume_tonnes_held_fixed": _fmt(q),
                "required_product_revenue_cny": _fmt(asp_revenue),
                "required_segment_revenue_cny": _fmt(other_revenue + asp_revenue) if asp_revenue is not None else None,
                "variable_cost_cny_per_tonne_held_fixed": _fmt(unit_cost),
            },
            "unit_variable_cost_only": {
                "status": cost_status,
                "required_variable_cost_cny_per_tonne": _fmt(cost_required) if cost_status == "CALCULATED_CONDITIONAL" else None,
                "change_cny_per_tonne": _fmt(cost_required - unit_cost) if cost_required is not None and cost_status == "CALCULATED_CONDITIONAL" else None,
                "change_pct": _fmt((cost_required / unit_cost - Decimal("1")) * Decimal("100")) if unit_cost > 0 and cost_required is not None and cost_status == "CALCULATED_CONDITIONAL" else None,
                "sales_volume_tonnes_held_fixed": _fmt(q),
                "net_asp_cny_per_tonne_held_fixed": _fmt(asp),
                "required_product_variable_cost_cny": _fmt(cost_variable_cost),
                "required_segment_variable_cost_cny": _fmt(other_variable_cost + cost_variable_cost) if cost_variable_cost is not None else None,
            },
        },
        "driver_measure_lineage": product_lineage,
        "production_inventory_context": {
            "forward_production_tonnes": production_context.get("forward_production_tonnes"),
            "historical_inventory_change_tonnes": production_context.get("historical_inventory_change_tonnes"),
            "forward_inventory_change_tonnes": production_context.get("forward_inventory_change_tonnes"),
            "nameplate_capacity_tonnes_per_year": _map(product_row.get("capacity_tonnes_per_year")).get("value"),
            "interpretation": "销售量、产量和库存变化不是同一变量；反推销售量不自动证明生产/库存可行。",
        },
        "holding_assumptions": [
            "仅改变本产品的一个驱动变量；本产品其余两个驱动变量不变。",
            "同一分部其他产品的销量、售价、单位成本全部保持当前 B4 前瞻假设。",
            "不考虑产品间替代、客户需求弹性、价格导致的销量变化、规模效应、产能/库存约束或固定费用二次变化。",
        ],
        "limitations": [
            "三个单变量结果是互相替代的数学解，不可相加，也不等于公司预测。",
            "产品层驱动值沿用 B55 已登记的前瞻来源分类和引用；来源结构完整不代表来源内容已独立核实。",
        ],
        "issues": [],
    }


def _build_target_lens(
    *,
    required_profit: Decimal | None,
    current_profit: Decimal,
    forward_segment: Mapping[str, Any],
    product_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if required_profit is None:
        return {"status": "NOT_IDENTIFIABLE", "issues": ["REQUIRED_PARENT_ATTRIBUTABLE_PROFIT_NOT_IDENTIFIABLE"]}
    inversion = _invert_normalized_profit_to_contribution(required_profit, forward_segment)
    if inversion.get("status") != "INVERTED_CONDITIONALLY":
        return {
            "status": inversion.get("status") or "NOT_IDENTIFIABLE",
            "required_parent_attributable_profit_cny": _fmt(required_profit),
            "current_parent_attributable_profit_cny": _fmt(current_profit),
            "profit_gap_cny": _fmt(required_profit - current_profit),
            "contribution_inversion": inversion,
            "product_driver_alternatives": [],
            "issues": list(inversion.get("issues") or []),
        }
    current_contribution = _num(forward_segment.get("contribution_after_variable_cost_cny"))
    required_contribution = _num(inversion.get("required_contribution_after_variable_cost_cny"))
    if current_contribution is None or required_contribution is None:
        return {
            "status": "NOT_IDENTIFIABLE",
            "required_parent_attributable_profit_cny": _fmt(required_profit),
            "contribution_inversion": inversion,
            "issues": ["CURRENT_OR_REQUIRED_SEGMENT_CONTRIBUTION_MISSING"],
        }
    driver_rows = [
        _driver_alternatives(
            product_row=row,
            required_segment_contribution=required_contribution,
            current_segment_contribution=current_contribution,
            segment_products=product_rows,
        )
        for row in product_rows
    ]
    calculated_drivers = sum(1 for row in driver_rows if row.get("status") == "CALCULATED_CONDITIONAL")
    lineage_partial = any(
        info.get("status") != "TYPED_ASSUMPTION_OR_FORECAST_WITH_REFERENCE"
        for product in driver_rows
        for info in _map(product.get("driver_measure_lineage")).values()
        if isinstance(info, Mapping)
    ) or any(
        info.get("status") not in {"TYPED_ASSUMPTION_OR_FORECAST_WITH_REFERENCE", "DERIVED_FROM_TWO_TYPED_NCI_MEASURES"}
        for info in _map(inversion.get("financial_measure_lineage")).values()
        if isinstance(info, Mapping)
    )
    return {
        "status": (
            "PARTIAL"
            if calculated_drivers == 0 or lineage_partial
            else "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED"
        ),
        "required_parent_attributable_profit_cny": _fmt(required_profit),
        "current_parent_attributable_profit_cny": _fmt(current_profit),
        "profit_gap_cny": _fmt(required_profit - current_profit),
        "contribution_inversion": inversion,
        "product_driver_alternatives": driver_rows,
        "calculated_product_count": calculated_drivers,
        "total_product_count": len(driver_rows),
        "interpretation": (
            "Each product-level driver is an alternative one-variable sensitivity; "
            "other products and remaining drivers are unchanged. Results are not additive."
        ),
        "issues": [],
    }


def _audit_scenario(
    name: str,
    *,
    operating_driver_forecast: Mapping[str, Any],
    segment_earnings_reconciliation: Mapping[str, Any],
    valuation_gap_attribution: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario": name,
        "status": "NOT_IDENTIFIABLE",
        "issues": [],
        "segments": [],
        "requirement_basis": {
            "b61_one_segment_at_a_time": "ALTERNATIVE_THRESHOLD_OTHER_SEGMENTS_AT_SELECTED_SOTP",
            "b63_full_b4_vector_at_selected_pes": "ALTERNATIVE_THRESHOLD_OTHER_SEGMENTS_AT_FULL_B4_FORECAST",
        },
    }
    if _txt(segment_earnings_reconciliation.get("status")).upper() not in {
        "CONDITIONAL_RECONCILIATION_CALCULATED", "PARTIAL"
    }:
        out["status"] = "BLOCKED_BY_B62"
        out["issues"] = [f"B62_STATUS:{_txt(segment_earnings_reconciliation.get('status')) or 'UNKNOWN'}"]
        return out

    baseline = _map(operating_driver_forecast.get("baseline_transition"))
    b4_bridge = _map(baseline.get("segment_normalized_earnings_bridge"))
    b55_scenario = _map(_map(baseline.get("scenarios")).get(name))
    b4_scenario = _map(_map(b4_bridge.get("scenarios")).get(name))
    b62_scenario = _map(_map(segment_earnings_reconciliation.get("scenarios")).get(name))
    b63_scenario = _map(_map(valuation_gap_attribution.get("scenarios")).get(name))

    if _txt(b62_scenario.get("status")).upper() != "CALCULATED_CONDITIONAL":
        out["status"] = "BLOCKED_BY_B62_SCENARIO"
        out["issues"] = [f"B62_SCENARIO_STATUS:{_txt(b62_scenario.get('status')) or 'UNKNOWN'}"]
        return out
    if _txt(b4_scenario.get("status")).upper() != "CALCULATED_AND_RECONCILED":
        out["status"] = "BLOCKED_BY_B4_SEGMENT_EARNINGS"
        out["issues"] = [f"B4_SEGMENT_EARNINGS_STATUS:{_txt(b4_scenario.get('status')) or 'UNKNOWN'}"]
        return out
    if _txt(b55_scenario.get("status")).upper() != "CALCULATED_AND_RECONCILED":
        out["status"] = "BLOCKED_BY_B55"
        out["issues"] = [f"B55_SCENARIO_STATUS:{_txt(b55_scenario.get('status')) or 'UNKNOWN'}"]
        return out
    if _txt(b63_scenario.get("status")).upper() != "CONDITIONAL_ATTRIBUTION_CALCULATED":
        out["status"] = "BLOCKED_BY_B63_SCENARIO"
        out["issues"] = [f"B63_SCENARIO_STATUS:{_txt(b63_scenario.get('status')) or 'UNKNOWN'}"]
        return out

    b4_segment_rows = _index(
        [{"segment_id": key, **dict(value)} for key, value in _map(b4_scenario.get("segments")).items()],
        "B4_SEGMENT",
        out["issues"],
    )
    b62_segment_rows = _index(b62_scenario.get("segment_comparisons"), "B62_SEGMENT", out["issues"])
    b63_segment_rows = _index(b63_scenario.get("earnings_effect_by_segment"), "B63_SEGMENT", out["issues"])
    if (
        not b4_segment_rows
        or set(b4_segment_rows) != set(b62_segment_rows)
        or set(b4_segment_rows) != set(b63_segment_rows)
    ):
        out["status"] = "RECONCILIATION_MISMATCH"
        out["issues"].append("B68_B4_B62_B63_SEGMENT_UNIVERSE_MISMATCH")
        return out

    products_by_segment: dict[str, list[Mapping[str, Any]]] = {}
    seen_products: set[str] = set()
    b4_product_rows = {
        _txt(row.get("product_id")): row
        for row in (operating_driver_forecast.get("product_lines") or [])
        if isinstance(row, Mapping) and _txt(row.get("product_id"))
    }
    b4_product_map = {
        product_id: _txt(row.get("business_segment_id"))
        for product_id, row in b4_product_rows.items()
    }
    for product in (b55_scenario.get("product_lines") or []):
        if not isinstance(product, Mapping):
            out["issues"].append("B55_PRODUCT_ROW_NOT_OBJECT")
            continue
        product_id = _txt(product.get("product_id"))
        segment_id = _txt(product.get("business_segment_id"))
        if not product_id or product_id in seen_products or not segment_id:
            out["issues"].append(f"B68_B55_PRODUCT_ID_OR_SEGMENT_MISSING_OR_DUPLICATE:{product_id or 'UNKNOWN'}")
            continue
        seen_products.add(product_id)
        if b4_product_map.get(product_id) != segment_id:
            out["issues"].append(f"B68_B4_B55_PRODUCT_SEGMENT_MAPPING_MISMATCH:{product_id}")
            continue
        enriched_product = dict(product)
        if not isinstance(enriched_product.get("capacity_tonnes_per_year"), Mapping):
            capacity_measure = _map(_map(b4_product_rows.get(product_id)).get("capacity_tonnes_per_year"))
            enriched_product["capacity_tonnes_per_year"] = dict(capacity_measure) if capacity_measure else None
        products_by_segment.setdefault(segment_id, []).append(enriched_product)

    if seen_products != set(b4_product_rows):
        out["issues"].append("B68_B4_B55_PRODUCT_UNIVERSE_MISMATCH")

    waterfall = _map(b63_scenario.get("value_pool_waterfall"))
    b4_pool = _num(waterfall.get("step_3_b4_forecast_pool_at_selected_pes_cny"))
    required_pool = _num(waterfall.get("step_5_required_segment_pool_cny"))
    if b4_pool is None or required_pool is None:
        out["status"] = "NOT_IDENTIFIABLE"
        out["issues"].append("B63_FULL_VECTOR_VALUE_POOL_REQUIREMENT_MISSING")
        return out
    b63_forecast_rows = list(b63_segment_rows.values())
    b4_pool_recalculated = sum(
        (_num(item.get("b4_forecast_segment_value_at_selected_pe_cny")) or Decimal("0"))
        for item in b63_forecast_rows
    )
    if not _eq(b4_pool_recalculated, b4_pool, _PRICE_POOL_TOL):
        out["status"] = "RECONCILIATION_MISMATCH"
        out["issues"].append("B68_B63_B4_FULL_VECTOR_POOL_RECALCULATION_MISMATCH")
        return out

    segment_rows = []
    for segment_id in sorted(b4_segment_rows):
        b4_segment = b4_segment_rows[segment_id]
        b62_segment = b62_segment_rows[segment_id]
        b63_segment = b63_segment_rows[segment_id]
        forward = _map(b4_segment.get("forward_scenario"))
        current_profit = _num(forward.get("normalized_parent_attributable_net_profit_cny"))
        b4_b62_profit = _num(b62_segment.get("b4_forecast_parent_attributable_normalized_profit_cny"))
        selected_sotp_profit = _num(b62_segment.get("sotp_selected_attributable_profit_cny"))
        b63_profit_change = _num(b63_segment.get("normalized_profit_change_cny"))
        b63_earnings_effect = _num(b63_segment.get("earnings_effect_at_selected_pe_cny"))
        b63_selected_value = _num(b63_segment.get("selected_sotp_segment_value_cny"))
        b63_b4_value = _num(b63_segment.get("b4_forecast_segment_value_at_selected_pe_cny"))
        selected_pe = _num(b63_segment.get("selected_sotp_pe_x"))
        b62_selected_pe = _num(b62_segment.get("sotp_selected_pe_multiple_x"))
        if (
            current_profit is None or b4_b62_profit is None or selected_sotp_profit is None
            or b63_profit_change is None or b63_earnings_effect is None
            or b63_selected_value is None or b63_b4_value is None
            or selected_pe is None or selected_pe <= 0 or b62_selected_pe is None
            or not _eq(selected_pe, b62_selected_pe, _PRICE_POOL_TOL)
            or not _eq(current_profit, b4_b62_profit, _PRICE_POOL_TOL)
            or not _eq(current_profit - selected_sotp_profit, b63_profit_change, _PRICE_POOL_TOL)
            or not _eq(b63_profit_change * selected_pe, b63_earnings_effect, _PRICE_POOL_TOL)
            or not _eq(selected_sotp_profit * selected_pe, b63_selected_value, _PRICE_POOL_TOL)
            or not _eq(current_profit * selected_pe, b63_b4_value, _PRICE_POOL_TOL)
        ):
            out["issues"].append(f"B68_B4_B62_B63_SEGMENT_PROFIT_VALUE_BRIDGE_MISMATCH:{segment_id}")
            continue

        products = products_by_segment.get(segment_id, [])
        current_contribution = _num(forward.get("contribution_after_variable_cost_cny"))
        product_contribution_sum = Decimal("0")
        product_revenue_sum = Decimal("0")
        product_cost_sum = Decimal("0")
        products_complete = bool(products)
        for product in products:
            pforward = _map(product.get("forward_scenario"))
            q = _num(pforward.get("sales_volume_tonnes"))
            asp = _num(pforward.get("net_asp_cny_per_tonne"))
            vc = _num(pforward.get("variable_cost_cny_per_tonne"))
            if _txt(product.get("status")).upper() != "CALCULATED_AND_RECONCILED" or any(x is None for x in (q, asp, vc)):
                products_complete = False
                continue
            product_contribution_sum += q * (asp - vc)
            product_revenue_sum += q * asp
            product_cost_sum += q * vc
        if (
            current_contribution is None
            or not products_complete
            or not _eq(product_contribution_sum, current_contribution)
        ):
            out["issues"].append(f"B68_B55_PRODUCT_TO_SEGMENT_CONTRIBUTION_MISMATCH:{segment_id}")
            products = []

        b61_required_profit = _num(b62_segment.get("b61_one_at_a_time_required_attributable_profit_cny_signed"))
        b63_required_profit = current_profit + (required_pool - b4_pool) / selected_pe
        if b63_required_profit is None:
            out["issues"].append(f"B68_B63_REQUIRED_SEGMENT_PROFIT_NOT_IDENTIFIABLE:{segment_id}")
        b61_lens = _build_target_lens(
            required_profit=b61_required_profit,
            current_profit=current_profit,
            forward_segment=forward,
            product_rows=products,
        ) if products else {"status": "NOT_IDENTIFIABLE", "issues": ["B68_NO_COMPLETE_B55_PRODUCT_MAPPING_FOR_SEGMENT"]}
        b63_lens = _build_target_lens(
            required_profit=b63_required_profit,
            current_profit=current_profit,
            forward_segment=forward,
            product_rows=products,
        ) if products else {"status": "NOT_IDENTIFIABLE", "issues": ["B68_NO_COMPLETE_B55_PRODUCT_MAPPING_FOR_SEGMENT"]}

        selected_sotp_profit = _num(b62_segment.get("sotp_selected_attributable_profit_cny"))
        segment_rows.append({
            "segment_id": segment_id,
            "segment_name": _txt(b62_segment.get("segment_name")) or segment_id,
            "selected_sotp_profit_cny": _fmt(selected_sotp_profit),
            "b4_forecast_normalized_parent_attributable_profit_cny": _fmt(current_profit),
            "selected_sotp_pe_x": _fmt(selected_pe),
            "b4_forecast_contribution_after_variable_cost_cny": _fmt(current_contribution),
            "b4_forecast_revenue_cny": _fmt(product_revenue_sum) if products_complete else None,
            "b4_forecast_variable_cost_cny": _fmt(product_cost_sum) if products_complete else None,
            "b61_required_profit_lens": {
                "status": "IDENTIFIED" if b61_required_profit is not None else "NOT_IDENTIFIABLE",
                "required_parent_attributable_profit_cny": _fmt(b61_required_profit),
                "interpretation": "B61_SINGLE_SEGMENT_PROFIT_THRESHOLD; ALL_OTHER_SEGMENTS_HELD_AT_SELECTED_SOTP_PROFIT; NON_ADDITIVE",
                "reverse_engineering": b61_lens,
            },
            "b63_full_b4_vector_lens": {
                "status": "IDENTIFIED",
                "required_parent_attributable_profit_cny": _fmt(b63_required_profit),
                "b4_full_vector_required_segment_pool_cny": _fmt(required_pool),
                "b4_full_vector_current_segment_pool_cny": _fmt(b4_pool),
                "remaining_pool_gap_before_this_segment_change_cny": _fmt(required_pool - b4_pool),
                "interpretation": "OTHER_SEGMENTS_HELD_AT_FULL_B4_FORECAST; THIS SEGMENT ALONE CHANGES AT SELECTED PE; NON_ADDITIVE",
                "reverse_engineering": b63_lens,
            },
            "issues": [],
        })

    if out["issues"]:
        out["status"] = "PARTIAL"
    elif segment_rows and all(
        row["b63_full_b4_vector_lens"]["reverse_engineering"].get("status") == "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED"
        and row["b61_required_profit_lens"]["reverse_engineering"].get("status") == "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED"
        for row in segment_rows
    ):
        out["status"] = "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED"
    elif segment_rows:
        out["status"] = "PARTIAL"
    else:
        out["status"] = "NOT_IDENTIFIABLE"
    out["segments"] = segment_rows
    return out


def build_sotp_operating_requirement_reverse_engineering(
    *,
    operating_driver_forecast: Mapping[str, Any],
    segment_earnings_reconciliation: Mapping[str, Any],
    valuation_gap_attribution: Mapping[str, Any],
) -> dict[str, Any]:
    """Translate B61/B63 profit thresholds into B4 product operating-driver sensitivities."""
    result: dict[str, Any] = {
        "schema_version": B68_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "CONDITIONAL_PRICE_IMPLIED_OPERATING_SENSITIVITY_NOT_FORECAST",
        "forecast_period": _txt(operating_driver_forecast.get("forecast_period")) or "UNKNOWN",
        "scenarios": {},
        "b4_inputs_modified": False,
        "sotp_inputs_modified": False,
        "b61_b63_inputs_modified": False,
        "external_mie_modified": False,
        "expectation_gap_modified": False,
        "required_return_or_target_entry_modified": False,
        "portfolio_constraints_modified": False,
        "decision_authority": False,
        "formal_forecast_admission_created": False,
        "limitations": [
            "仅在 B4/B55/B62 的同范围、同期间、同分部映射和算术闭合条件满足时反推；缺失字段不填零。",
            "归母利润到分部贡献的反推固定 B4 已声明的固定费用、折旧、融资成本、税率、经常性非经营项和正常化少数股东损益。",
            "每个产品的销量、净售价、单位成本结果是单变量替代敏感性；其他产品和本产品剩余驱动变量不变，不能相加。",
            "销售量不能与产量或库存释放混为一谈；销量反推的生产、产能、库存与营运资金可行性仍须独立审查。",
            "这不是独立盈利预测、市场共识、外部 MIE 或 BUY/SELL 结论；不修改 B4、SOTP、15% 年化回报门槛、目标入场价或 Decision。",
        ],
    }
    if _txt(operating_driver_forecast.get("scope")).upper() != "COMPANY_WIDE":
        result["status"] = "NOT_COMPARABLE_SCOPE"
        return result
    if _txt(segment_earnings_reconciliation.get("status")).upper() not in {
        "CONDITIONAL_RECONCILIATION_CALCULATED", "PARTIAL"
    }:
        result["status"] = "BLOCKED_BY_B62"
        result["b62_status"] = _txt(segment_earnings_reconciliation.get("status")) or "UNKNOWN"
        return result
    baseline = _map(operating_driver_forecast.get("baseline_transition"))
    b4_period = _txt(baseline.get("forecast_period"))
    b62_period = _txt(segment_earnings_reconciliation.get("forecast_period"))
    if not b4_period or b4_period.upper() == "UNKNOWN" or b4_period.upper() != b62_period.upper():
        result["status"] = "FORECAST_PERIOD_NOT_COMPARABLE"
        return result
    if _txt(valuation_gap_attribution.get("status")).upper() != "CONDITIONAL_ATTRIBUTION_CALCULATED":
        result["status"] = "BLOCKED_BY_B63"
        result["b63_status"] = _txt(valuation_gap_attribution.get("status")) or "UNKNOWN"
        return result

    statuses = []
    for name in _SCENARIOS:
        row = _audit_scenario(
            name,
            operating_driver_forecast=operating_driver_forecast,
            segment_earnings_reconciliation=segment_earnings_reconciliation,
            valuation_gap_attribution=valuation_gap_attribution,
        )
        result["scenarios"][name] = row
        statuses.append(row["status"])
    if statuses and all(status == "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED" for status in statuses):
        result["status"] = "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED"
    elif any(status in {"PARTIAL", "CONDITIONAL_OPERATING_REQUIREMENT_REVERSE_ENGINEERED"} for status in statuses):
        result["status"] = "PARTIAL"
    elif any(status.startswith("BLOCKED") for status in statuses):
        result["status"] = "BLOCKED_BY_UPSTREAM_RECONCILIATION"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    result["summary"] = (
        "B68 将 B61/B63 的条件归母利润要求反解为 B4 分部贡献，再映射为产品销量、净售价或单位变动成本的单变量敏感性。"
        "每项驱动结果均是互相替代的条件解，不是预测，也不可相加。"
    )
    return result
