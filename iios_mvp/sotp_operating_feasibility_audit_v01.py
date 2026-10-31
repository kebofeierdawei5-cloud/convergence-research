from __future__ import annotations

"""B69: audit operational feasibility of B68 price-implied driver requirements.

This is a read-only, conditional constraint check. It never upgrades B68
sensitivities into forecasts and never changes B4, valuation or decision inputs.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

B69_SCHEMA = "IIOS-SOTP-OPERATING-FEASIBILITY-AUDIT-0.1"
_SCENARIOS = ("bear", "base", "bull")
_LENSES = (
    ("b61_required_profit_lens", "B61_SINGLE_SEGMENT_THRESHOLD"),
    ("b63_full_b4_vector_lens", "B63_FULL_B4_VECTOR_THRESHOLD"),
)
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
        out = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    return out if out.is_finite() else None


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _full_year(period: Any) -> bool:
    label = "".join(str(period or "").upper().split())
    return bool(re.fullmatch(r"(?:\d{4}FY|FY\d{4}|\d{4}年度|\d{4}全年)", label))


def _lineage(measure: Any) -> dict[str, Any]:
    row = _map(measure)
    data_class = _txt(row.get("data_class")).upper() or "UNKNOWN"
    basis = _txt(row.get("basis")) or "UNKNOWN"
    refs = [
        str(item).strip()
        for item in (row.get("evidence_refs") if isinstance(row.get("evidence_refs"), list) else [])
        if str(item).strip()
    ]
    issues = list(row.get("issues") or []) if isinstance(row.get("issues"), list) else []
    return {
        "data_class": data_class,
        "basis": basis,
        "evidence_refs": refs,
        "status": (
            "TYPED_WITH_REFERENCE"
            if data_class != "UNKNOWN" and basis != "UNKNOWN" and refs and not issues
            else "TYPED_WITHOUT_COMPLETE_REFERENCE"
            if data_class != "UNKNOWN" and basis != "UNKNOWN" and not issues
            else "NOT_IDENTIFIABLE"
        ),
        "issues": issues,
        "formal_evidence_admitted": False,
    }


def _index(rows: Any, label: str, issues: list[str]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    if not isinstance(rows, list):
        issues.append(f"{label}_NOT_LIST")
        return out
    for index, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            issues.append(f"{label}_ROW_NOT_OBJECT:{index}")
            continue
        key = _txt(row.get("product_id"))
        if not key or key in out:
            issues.append(f"{label}_ID_MISSING_OR_DUPLICATE:{key or index}")
            continue
        out[key] = row
    return out


def _product_audit(
    *,
    product: Mapping[str, Any],
    b4_master: Mapping[str, Any],
    b4_scenario_product: Mapping[str, Any],
    forecast_period: str,
) -> dict[str, Any]:
    product_id = _txt(product.get("product_id")) or "UNKNOWN"
    current = _map(product.get("current_forward_assumptions"))
    alternatives = _map(product.get("single_driver_alternatives"))
    volume = _map(alternatives.get("sales_volume_only"))
    asp = _map(alternatives.get("net_asp_only"))
    cost = _map(alternatives.get("unit_variable_cost_only"))
    context = _map(product.get("production_inventory_context"))

    current_sales = _num(current.get("sales_volume_tonnes"))
    current_asp = _num(current.get("net_asp_cny_per_tonne"))
    current_unit_cost = _num(current.get("variable_cost_cny_per_tonne"))
    required_sales = _num(volume.get("required_sales_volume_tonnes"))
    required_asp = _num(asp.get("required_net_asp_cny_per_tonne"))
    required_unit_cost = _num(cost.get("required_variable_cost_cny_per_tonne"))

    b4_production = _num(b4_scenario_product.get("production_tonnes"))
    b4_sales = _num(b4_scenario_product.get("sales_volume_tonnes"))
    b4_inventory_change = _num(b4_scenario_product.get("inventory_change_tonnes"))
    context_production = _num(context.get("forward_production_tonnes"))
    context_inventory_change = _num(context.get("forward_inventory_change_tonnes"))

    production = b4_production if b4_production is not None else context_production
    inventory_change = b4_inventory_change if b4_inventory_change is not None else context_inventory_change
    issues: list[str] = []

    if production is not None and b4_sales is not None:
        recalculated_inventory_change = production - b4_sales
        if inventory_change is not None and abs(recalculated_inventory_change - inventory_change) > _TOL:
            issues.append("B69_B4_B68_PRODUCTION_SALES_BALANCE_MISMATCH")
            inventory_change = None
        else:
            inventory_change = recalculated_inventory_change
    elif inventory_change is None:
        issues.append("FORWARD_PRODUCTION_SALES_INVENTORY_DELTA_UNKNOWN")

    required_production = (
        required_sales + inventory_change
        if required_sales is not None and inventory_change is not None
        else None
    )
    capacity_measure = _map(b4_master.get("capacity_tonnes_per_year"))
    capacity = _num(capacity_measure)
    capacity_lineage = _lineage(capacity_measure)
    if capacity is None:
        capacity = _num(context.get("nameplate_capacity_tonnes_per_year"))
        if capacity is not None:
            capacity_lineage = {
                "data_class": "UNKNOWN",
                "basis": "B68_CARRIED_CAPACITY_VALUE_WITHOUT_B4_MEASURE_LINEAGE",
                "evidence_refs": [],
                "status": "NOT_IDENTIFIABLE",
                "issues": ["CAPACITY_MEASURE_LINEAGE_MISSING"],
                "formal_evidence_admitted": False,
            }

    capacity_status = "NOT_IDENTIFIABLE"
    required_utilization = None
    capacity_headroom = None
    if not _full_year(forecast_period):
        capacity_status = "NOT_IDENTIFIABLE_PERIOD_NOT_FULL_YEAR"
        issues.append("ANNUAL_NAMEPLATE_CAPACITY_REQUIRES_FULL_YEAR_FORECAST_PERIOD")
    elif required_sales is None or _txt(volume.get("status")).upper() != "CALCULATED_CONDITIONAL":
        capacity_status = "NOT_IDENTIFIABLE_REQUIRED_SALES_VOLUME"
        issues.append("B68_VOLUME_ONLY_REQUIREMENT_NOT_CALCULATED")
    elif inventory_change is None:
        capacity_status = "NOT_IDENTIFIABLE_INVENTORY_POLICY"
        issues.append("REQUIRED_PRODUCTION_CANNOT_BE_DERIVED_WITHOUT_FORWARD_INVENTORY_MOVEMENT")
    elif required_production is None or required_production < 0:
        capacity_status = "NOT_FEASIBLE_NEGATIVE_REQUIRED_PRODUCTION"
        issues.append("REQUIRED_PRODUCTION_IS_NEGATIVE")
    elif capacity is None or capacity <= 0:
        capacity_status = "NOT_IDENTIFIABLE_NAMEPLATE_CAPACITY"
        issues.append("POSITIVE_NAMEPLATE_CAPACITY_NOT_AVAILABLE")
    else:
        required_utilization = required_production / capacity
        capacity_headroom = capacity - required_production
        capacity_status = (
            "EXCEEDS_NAMEPLATE_CAPACITY"
            if required_production > capacity
            else "WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL"
        )

    capacity_assumption = (
        "FORWARD_INVENTORY_CHANGE_HELD_AT_B4_LEVEL"
        if inventory_change is not None
        else "UNKNOWN"
    )
    demand_status = "NOT_IDENTIFIABLE_NO_TYPED_ORDER_BOOK_OR_CUSTOMER_DEMAND_INPUT"
    pricing_status = "NOT_IDENTIFIABLE_PRICE_ELASTICITY_AND_COMPETITIVE_PRICE_EVIDENCE"
    cost_status = "NOT_IDENTIFIABLE_COST_CURVE_AND_SAVINGS_PLAN_EVIDENCE"
    capex_wc_status = "NOT_IDENTIFIABLE_INCREMENTAL_EXPANSION_CAPEX_AND_WORKING_CAPITAL"

    asp_change_pct = None
    if current_asp is not None and current_asp != 0 and required_asp is not None:
        asp_change_pct = (required_asp / current_asp - Decimal("1")) * Decimal("100")
    unit_cost_change_pct = None
    if current_unit_cost is not None and current_unit_cost != 0 and required_unit_cost is not None:
        unit_cost_change_pct = (required_unit_cost / current_unit_cost - Decimal("1")) * Decimal("100")

    return {
        "product_id": product_id,
        "product_name": _txt(product.get("product_name")) or product_id,
        "volume_only_status": _txt(volume.get("status")) or "UNKNOWN",
        "current_forward_sales_volume_tonnes": _fmt(current_sales),
        "required_sales_volume_tonnes": _fmt(required_sales),
        "required_sales_volume_change_pct": volume.get("change_pct"),
        "forward_production_tonnes": _fmt(production),
        "forward_inventory_change_tonnes": _fmt(inventory_change),
        "required_production_tonnes_under_unchanged_inventory_movement": _fmt(required_production),
        "inventory_policy_assumption": capacity_assumption,
        "nameplate_capacity_tonnes_per_year": _fmt(capacity),
        "capacity_measure_lineage": capacity_lineage,
        "required_capacity_utilization": _fmt(required_utilization),
        "remaining_nameplate_capacity_tonnes": _fmt(capacity_headroom),
        "capacity_status": capacity_status,
        "current_b4_capacity_status": _txt(b4_scenario_product.get("capacity_feasibility_status"))
        or _txt(b4_scenario_product.get("production_sales_balance_status"))
        or "UNKNOWN",
        "required_net_asp_cny_per_tonne": _fmt(required_asp),
        "required_net_asp_change_pct": _fmt(asp_change_pct),
        "pricing_feasibility_status": pricing_status,
        "required_unit_variable_cost_cny_per_tonne": _fmt(required_unit_cost),
        "required_unit_variable_cost_change_pct": _fmt(unit_cost_change_pct),
        "unit_cost_feasibility_status": cost_status,
        "demand_feasibility_status": demand_status,
        "incremental_capex_and_working_capital_status": capex_wc_status,
        "issues": issues,
        "limitations": [
            "产能比较是假设 B4 前瞻产销库存差额保持不变；不代表已核实的期初可售库存或库存释放政策。",
            "年化名义产能不等于有效产能；未计入检修、良率、产品切换、爬坡、物流瓶颈及产线共享。",
            "没有订单/客户需求、价格弹性、成本曲线、扩建投产日期和项目级资金需求时，不认定经营要求可实现。",
        ],
    }


def _scenario_audit(
    scenario_name: str,
    b4: Mapping[str, Any],
    b68: Mapping[str, Any],
    forecast_period: str,
) -> dict[str, Any]:
    b4_scenario = _map(_map(b4.get("scenarios")).get(scenario_name))
    b68_scenario = _map(_map(b68.get("scenarios")).get(scenario_name))
    out: dict[str, Any] = {
        "scenario": scenario_name,
        "status": "NOT_IDENTIFIABLE",
        "b4_existing_financial_plan": {
            "inventory_reconciliation_status": _txt(b4_scenario.get("inventory_reconciliation_status")) or "UNKNOWN",
            "inventory_working_capital_treatment": _txt(b4_scenario.get("inventory_working_capital_treatment")) or "UNKNOWN",
            "effective_change_working_capital_cny": b4_scenario.get("effective_change_working_capital_cny"),
            "cash_capex_cny": b4_scenario.get("cash_capex_cny"),
            "unlevered_fcf_proxy_cny": b4_scenario.get("unlevered_fcf_proxy_cny"),
            "financial_outputs_decision_usable": b4_scenario.get("financial_outputs_decision_usable"),
            "interpretation": "原 B4 资本开支/有效营运资金/FCF 保持原值；B69 不叠加库存代理，也不补算扩产资金。",
        },
        "requirement_lenses": [],
        "issues": [],
    }
    if not b68_scenario:
        out["issues"].append("B68_SCENARIO_NOT_AVAILABLE")
        return out

    b4_products = _index(b4_scenario.get("product_lines"), "B4_PRODUCT", out["issues"])
    b4_master = _index(b4.get("product_lines"), "B4_MASTER_PRODUCT", out["issues"])
    segment_rows = b68_scenario.get("segments")
    if not isinstance(segment_rows, list):
        out["issues"].append("B68_SEGMENTS_NOT_LIST")
        return out

    for segment in segment_rows:
        if not isinstance(segment, Mapping):
            out["issues"].append("B68_SEGMENT_ROW_NOT_OBJECT")
            continue
        segment_id = _txt(segment.get("segment_id")) or "UNKNOWN"
        for lens_key, lens_name in _LENSES:
            lens = _map(segment.get(lens_key))
            reverse = _map(lens.get("reverse_engineering"))
            product_rows = reverse.get("product_driver_alternatives")
            if not isinstance(product_rows, list):
                product_rows = []
            products = []
            for product in product_rows:
                if not isinstance(product, Mapping):
                    continue
                product_id = _txt(product.get("product_id"))
                master = b4_master.get(product_id, {})
                b4_product = b4_products.get(product_id, {})
                products.append(_product_audit(
                    product=product,
                    b4_master=master,
                    b4_scenario_product=b4_product,
                    forecast_period=forecast_period,
                ))
            out["requirement_lenses"].append({
                "segment_id": segment_id,
                "lens": lens_name,
                "required_parent_attributable_profit_cny": lens.get("required_parent_attributable_profit_cny"),
                "reverse_engineering_status": _txt(reverse.get("status")) or "UNKNOWN",
                "products": products,
                "non_additive": True,
            })

    b4_inventory_status = _txt(b4_scenario.get("inventory_reconciliation_status")).upper()
    if b4_inventory_status in {
        "INVENTORY_WORKING_CAPITAL_TREATMENT_REQUIRED",
        "INVENTORY_BALANCE_NOT_IDENTIFIABLE_FOR_EXCLUDED_WORKING_CAPITAL",
        "INVENTORY_COST_PROXY_UNAVAILABLE_FOR_EXCLUDED_WORKING_CAPITAL",
        "NOT_APPLICABLE_CONTRADICTS_TONNAGE_INVENTORY_BASIS",
        "INVALID_INVENTORY_WORKING_CAPITAL_TREATMENT",
    }:
        out["issues"].append("B42_INVENTORY_WORKING_CAPITAL_RECONCILIATION_NOT_CLOSED")

    statuses = [
        product.get("capacity_status")
        for lens in out["requirement_lenses"]
        for product in lens.get("products", [])
    ]
    if any(status == "EXCEEDS_NAMEPLATE_CAPACITY" for status in statuses):
        out["status"] = "CAPACITY_CONSTRAINT_IDENTIFIED"
    elif statuses and all(status == "WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL" for status in statuses):
        out["status"] = "CAPACITY_ARITHMETIC_CONDITIONALLY_WITHIN_NAMEPLATE"
    elif statuses:
        out["status"] = "PARTIAL"
    else:
        out["status"] = "NOT_IDENTIFIABLE"
    if out["issues"] and out["status"] != "CAPACITY_CONSTRAINT_IDENTIFIED":
        out["status"] = "PARTIAL"
    return out


def build_sotp_operating_feasibility_audit(
    *,
    operating_driver_forecast: Mapping[str, Any],
    operating_requirement_reverse_engineering: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit B68 volume/ASP/cost alternatives against B4 operating constraints."""
    forecast_period = (
        _txt(operating_driver_forecast.get("forecast_period"))
        or _txt(_map(operating_driver_forecast.get("baseline_transition")).get("forecast_period"))
        or "UNKNOWN"
    )
    result: dict[str, Any] = {
        "schema_version": B69_SCHEMA,
        "status": "NOT_IDENTIFIABLE",
        "qualification": "CONDITIONAL_OPERATING_FEASIBILITY_AUDIT_NOT_FORECAST",
        "forecast_period": forecast_period,
        "scenarios": {},
        "b4_inputs_modified": False,
        "b68_inputs_modified": False,
        "sotp_inputs_modified": False,
        "external_mie_modified": False,
        "expectation_gap_modified": False,
        "required_return_or_target_entry_modified": False,
        "portfolio_constraints_modified": False,
        "decision_authority": False,
        "formal_forecast_admission_created": False,
        "summary": (
            "B69 只对 B68 的现价隐含经营要求进行条件约束检查；产能通过不等于需求、价格、成本或扩产可实现。"
            "B61 与 B63 门槛继续分开，不相加。"
        ),
        "limitations": [
            "产能只按 B4 年度名义产能与前瞻产销差额不变的条件检查；不代表有效产能、良率、爬坡或库存政策已核实。",
            "B4 当前没有可核对的订单覆盖/客户需求、价格弹性、产品成本曲线、扩建投产时间及项目级增量资金需求字段；这些约束保持 NOT_IDENTIFIABLE。",
            "B69 不调整 B4 的现金资本开支、有效营运资金或 FCF，不重复添加 B42 库存现金影响代理。",
            "所有 B68 单变量要求是替代数学解，不是同时发生的预测；来源结构存在不等于证据语义已经独立核实。",
        ],
    }
    if _txt(operating_requirement_reverse_engineering.get("schema_version")) != "IIOS-SOTP-OPERATING-REQUIREMENT-REVERSE-ENGINEERING-0.1":
        result["status"] = "BLOCKED_BY_B68_SCHEMA"
        return result

    for scenario_name in _SCENARIOS:
        result["scenarios"][scenario_name] = _scenario_audit(
            scenario_name,
            operating_driver_forecast,
            operating_requirement_reverse_engineering,
            forecast_period,
        )
    statuses = [row.get("status") for row in result["scenarios"].values()]
    if statuses and all(status == "CAPACITY_ARITHMETIC_CONDITIONALLY_WITHIN_NAMEPLATE" for status in statuses):
        result["status"] = "CAPACITY_ARITHMETIC_CONDITIONALLY_WITHIN_NAMEPLATE"
    elif any(status == "CAPACITY_CONSTRAINT_IDENTIFIED" for status in statuses):
        result["status"] = "CAPACITY_CONSTRAINT_IDENTIFIED"
    elif any(status == "PARTIAL" for status in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "NOT_IDENTIFIABLE"
    return result
