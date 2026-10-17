from __future__ import annotations

"""Non-canonical operating-driver forecast and reconciliation for the local IIOS pilot.

This module makes the assumptions visible and computes only from explicitly
typed, unit-compatible inputs. It never upgrades source claims to formal
evidence, treats issuer plans as realized results, creates EPS or authorizes a
capital action.
"""

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

OPERATING_DRIVER_SCHEMA = "IIOS-OPERATING-DRIVER-FORECAST-0.1"
SCENARIOS = ("bear", "base", "bull")
DATA_CLASSES = {"OBSERVED_ACTUAL", "ISSUER_FORECAST", "ANALYST_ASSUMPTION", "UNKNOWN"}
SCOPES = {"PROJECT_INCREMENTAL", "PRODUCT_LINE", "COMPANY_WIDE", "UNKNOWN"}

PRODUCT_MEASURES = {
    "capacity_tonnes_per_year": "tonnes/year",
    "production_tonnes": "tonnes",
    "sales_volume_tonnes": "tonnes",
    "net_asp_cny_per_tonne": "CNY/tonne",
    "variable_cost_cny_per_tonne": "CNY/tonne",
}
GLOBAL_MEASURES = {
    "fixed_cash_opex_cny": "CNY",
    "depreciation_amortization_cny": "CNY",
    "finance_cost_cny": "CNY",
    "tax_rate": "ratio",
    "cash_capex_cny": "CNY",
    "change_working_capital_cny": "CNY",
}


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field}_MUST_BE_NUMERIC") from exc
    if not result.is_finite():
        raise ValueError(f"{field}_MUST_BE_FINITE")
    return result


def _render(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _unknown_measure(unit: str, note: str = "未识别或未提供") -> dict[str, Any]:
    return {
        "value": None,
        "claimed_value": None,
        "unit": unit,
        "data_class": "UNKNOWN",
        "basis": "",
        "evidence_refs": [],
        "note": note,
        "calculation_usable": False,
        "evidence_status": "UNKNOWN",
        "issues": [],
    }


def _normalise_measure(
    raw: Any,
    *,
    field: str,
    expected_unit: str,
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
) -> dict[str, Any]:
    """Normalize one typed scalar and refuse unsupported factual/forecast claims."""
    if not isinstance(raw, Mapping):
        return _unknown_measure(expected_unit)

    data_class = str(raw.get("data_class") or "UNKNOWN").strip().upper()
    actual_unit = str(raw.get("unit") or expected_unit).strip()
    basis = str(raw.get("basis") or "").strip()
    note = str(raw.get("note") or "").strip()
    refs_raw = raw.get("evidence_refs")
    refs = sorted({str(item).strip() for item in refs_raw if str(item).strip()}) if isinstance(refs_raw, list) else []
    issues: list[str] = []
    claimed: Decimal | None = None

    if data_class not in DATA_CLASSES:
        return {
            **_unknown_measure(expected_unit, note or "数据分类无效"),
            "data_class": data_class,
            "basis": basis,
            "evidence_refs": refs,
            "issues": [f"{field}:UNSUPPORTED_DATA_CLASS"],
        }

    raw_value = raw.get("value")
    if data_class == "UNKNOWN":
        if raw_value not in (None, ""):
            issues.append(f"{field}:UNKNOWN_CANNOT_CARRY_NUMERIC_VALUE")
        return {
            **_unknown_measure(actual_unit, note or "来源未披露或本次无法识别"),
            "data_class": "UNKNOWN",
            "basis": basis,
            "evidence_refs": refs,
            "issues": issues,
        }

    if raw_value in (None, ""):
        issues.append(f"{field}:VALUE_MISSING")
    else:
        try:
            claimed = _decimal(raw_value, field)
        except ValueError:
            issues.append(f"{field}:VALUE_INVALID")

    if actual_unit != expected_unit:
        issues.append(f"{field}:UNIT_MISMATCH_EXPECTED_{expected_unit}")
    if not basis:
        issues.append(f"{field}:BASIS_REQUIRED")

    # Quantities, capacity, selling price, expenses and tax rate cannot be negative.
    # A change in working capital is signed: positive consumes cash, negative releases cash.
    metric_name = field.rsplit(".", 1)[-1]
    if claimed is not None:
        if metric_name != "change_working_capital_cny" and claimed < 0:
            issues.append(f"{field}:NEGATIVE_VALUE_NOT_ALLOWED")
        if metric_name == "tax_rate" and not (Decimal("0") <= claimed <= Decimal("1")):
            issues.append(f"{field}:TAX_RATE_MUST_BE_RATIO_0_TO_1")

    evidence_status = "NOT_REQUIRED_FOR_ASSUMPTION"
    if data_class in {"OBSERVED_ACTUAL", "ISSUER_FORECAST"}:
        if not refs:
            issues.append(f"{field}:SOURCE_REFERENCE_REQUIRED")
            evidence_status = "SOURCE_REFERENCE_MISSING"
        else:
            absent = set(refs) - set(sources_by_id)
            if absent or set(refs) & unresolved_refs:
                issues.append(f"{field}:SOURCE_REFERENCE_UNRESOLVED")
                evidence_status = "SOURCE_REFERENCE_UNRESOLVED"
            elif set(refs) & after_cutoff_refs:
                issues.append(f"{field}:SOURCE_AFTER_CUTOFF")
                evidence_status = "SOURCE_AFTER_CUTOFF"
            elif set(refs) & uncertain_refs or any(
                str(sources_by_id.get(ref, {}).get("time_status") or "UNKNOWN")
                != "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
                for ref in refs
            ):
                issues.append(f"{field}:SOURCE_TIMING_UNCERTAIN")
                evidence_status = "SOURCE_TIMING_UNCERTAIN"
            else:
                evidence_status = "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"

    usable = claimed is not None and not issues
    return {
        "value": _render(claimed) if usable else None,
        "claimed_value": _render(claimed),
        "unit": actual_unit,
        "data_class": data_class,
        "basis": basis,
        "evidence_refs": refs,
        "note": note,
        "calculation_usable": usable,
        "evidence_status": evidence_status,
        "issues": issues,
    }


def _value(measure: Mapping[str, Any] | None) -> Decimal | None:
    if not isinstance(measure, Mapping) or measure.get("calculation_usable") is not True:
        return None
    raw = measure.get("value")
    if raw in (None, ""):
        return None
    try:
        return _decimal(raw, "NORMALISED_MEASURE")
    except ValueError:
        return None


def _normalise_product_measure_set(
    raw: Any,
    fields: Mapping[str, str],
    prefix: str,
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
    allowed_data_classes: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    row = raw if isinstance(raw, Mapping) else {}
    result: dict[str, dict[str, Any]] = {}
    for key, unit in fields.items():
        field = f"{prefix}.{key}"
        measure = _normalise_measure(
            row.get(key),
            field=field,
            expected_unit=unit,
            sources_by_id=sources_by_id,
            unresolved_refs=unresolved_refs,
            after_cutoff_refs=after_cutoff_refs,
            uncertain_refs=uncertain_refs,
        )
        # Context matters: history is not allowed to borrow forecast values,
        # and forward scenarios cannot silently relabel an observed actual as a
        # forward estimate. Keep the claim visible, but never use it in math.
        data_class = str(measure.get("data_class") or "UNKNOWN")
        if (
            allowed_data_classes is not None
            and data_class != "UNKNOWN"
            and data_class not in allowed_data_classes
        ):
            measure["value"] = None
            measure["calculation_usable"] = False
            measure["evidence_status"] = "DATA_CLASS_NOT_ALLOWED_FOR_CONTEXT"
            measure.setdefault("issues", []).append(
                f"{field}:DATA_CLASS_NOT_ALLOWED_FOR_CONTEXT"
            )
        result[key] = measure
    return result


def _is_full_year_period(period: Any) -> bool:
    """Only compare a period's production against annual nameplate capacity for an explicitly full year."""
    label = "".join(str(period or "").upper().split())
    return bool(re.fullmatch(r"(?:\d{4}FY|FY\d{4}|\d{4}年度|\d{4}全年)", label))


def _product_profit_bridge(
    product_id: str,
    product_name: str,
    metrics: Mapping[str, Mapping[str, Any]],
    capacity: Mapping[str, Any] | None = None,
    period_basis: str | None = None,
) -> dict[str, Any]:
    production = _value(metrics.get("production_tonnes"))
    sales_volume = _value(metrics.get("sales_volume_tonnes"))
    asp = _value(metrics.get("net_asp_cny_per_tonne"))
    unit_cost = _value(metrics.get("variable_cost_cny_per_tonne"))
    capacity_value = _value(capacity)
    revenue = sales_volume * asp if sales_volume is not None and asp is not None else None
    variable_cost = sales_volume * unit_cost if sales_volume is not None and unit_cost is not None else None
    utilization = None
    issues: list[str] = []
    if production is not None and capacity_value is not None and capacity_value > 0:
        if not _is_full_year_period(period_basis):
            issues.append("CAPACITY_PERIOD_ALIGNMENT_UNKNOWN")
        else:
            utilization = production / capacity_value
            if utilization > Decimal("1"):
                issues.append("PRODUCTION_ABOVE_NAMEPLATE_CAPACITY_CHECK_PERIOD_OR_SCOPE")
    return {
        "product_id": product_id,
        "product_name": product_name,
        "production_tonnes": _render(production),
        "sales_volume_tonnes": _render(sales_volume),
        "net_asp_cny_per_tonne": _render(asp),
        "variable_cost_cny_per_tonne": _render(unit_cost),
        "revenue_cny": _render(revenue),
        "variable_cost_cny": _render(variable_cost),
        "production_utilization": _render(utilization),
        "issues": issues,
        "inputs": dict(metrics),
    }


def _calculate_scenario(
    scenario_name: str,
    raw: Any,
    products: list[dict[str, Any]],
    period_basis: str,
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
) -> dict[str, Any]:
    scenario = raw if isinstance(raw, Mapping) else {}
    raw_products = scenario.get("product_lines")
    raw_products = raw_products if isinstance(raw_products, list) else []
    rows_by_id: dict[str, Mapping[str, Any]] = {}
    issues: list[str] = []
    structure_valid = True
    for index, row in enumerate(raw_products):
        if not isinstance(row, Mapping):
            issues.append(f"{scenario_name}:PRODUCT_ROW_{index}_INVALID")
            structure_valid = False
            continue
        product_id = str(row.get("product_id") or "").strip()
        if not product_id:
            issues.append(f"{scenario_name}:PRODUCT_ID_MISSING")
            structure_valid = False
        elif product_id in rows_by_id:
            issues.append(f"{scenario_name}:DUPLICATE_PRODUCT_ID:{product_id}")
            structure_valid = False
            # Conflicting duplicate rows are ambiguous; do not select either value.
            rows_by_id[product_id] = {}
        else:
            rows_by_id[product_id] = row
    expected_ids = {str(product.get("product_id") or "") for product in products}
    missing_ids = sorted(expected_ids - set(rows_by_id))
    extra_ids = sorted(set(rows_by_id) - expected_ids)
    if expected_ids:
        if missing_ids:
            issues.append(f"{scenario_name}:PRODUCT_LINES_MISSING:{','.join(missing_ids)}")
        if extra_ids:
            issues.append(f"{scenario_name}:UNMAPPED_PRODUCT_LINES:{','.join(extra_ids)}")

    product_results: list[dict[str, Any]] = []
    product_revenues: list[Decimal] = []
    revenues_complete = bool(products) and structure_valid and not missing_ids and not extra_ids
    product_costs: list[Decimal] = []
    costs_complete = bool(products) and structure_valid and not missing_ids and not extra_ids
    volume_total = Decimal("0")
    production_total = Decimal("0")
    all_volume_known = bool(products)
    all_production_known = bool(products)

    for product in products:
        product_id = str(product["product_id"])
        product_row = rows_by_id.get(product_id, {})
        measures = _normalise_product_measure_set(
            product_row,
            {
                "production_tonnes": "tonnes",
                "sales_volume_tonnes": "tonnes",
                "net_asp_cny_per_tonne": "CNY/tonne",
                "variable_cost_cny_per_tonne": "CNY/tonne",
            },
            f"{scenario_name}.{product_id}",
            sources_by_id,
            unresolved_refs,
            after_cutoff_refs,
            uncertain_refs,
            allowed_data_classes={"ISSUER_FORECAST", "ANALYST_ASSUMPTION"},
        )
        capacity = product["capacity_tonnes_per_year"]
        result = _product_profit_bridge(
            product_id, product["product_name"], measures, capacity, period_basis=period_basis
        )
        product_results.append(result)
        p_volume = _value(measures.get("sales_volume_tonnes"))
        p_production = _value(measures.get("production_tonnes"))
        p_revenue = _decimal(result["revenue_cny"], "PRODUCT_REVENUE") if result["revenue_cny"] is not None else None
        p_cost = _decimal(result["variable_cost_cny"], "PRODUCT_VARIABLE_COST") if result["variable_cost_cny"] is not None else None
        if p_volume is None:
            all_volume_known = False
        else:
            volume_total += p_volume
        if p_production is None:
            all_production_known = False
        else:
            production_total += p_production
        if p_revenue is None:
            revenues_complete = False
        else:
            product_revenues.append(p_revenue)
        if p_cost is None:
            costs_complete = False
        else:
            product_costs.append(p_cost)
        for measure in measures.values():
            issues.extend(measure.get("issues") or [])
        issues.extend(result["issues"])

    scenario_measures = _normalise_product_measure_set(
        scenario,
        GLOBAL_MEASURES,
        scenario_name,
        sources_by_id,
        unresolved_refs,
        after_cutoff_refs,
        uncertain_refs,
        allowed_data_classes={"ISSUER_FORECAST", "ANALYST_ASSUMPTION"},
    )
    for measure in scenario_measures.values():
        issues.extend(measure.get("issues") or [])

    revenue = sum(product_revenues, Decimal("0")) if revenues_complete else None
    variable_cost = sum(product_costs, Decimal("0")) if costs_complete else None
    cost_ratio = _value(scenario_measures.get("cost_of_revenue_ratio"))
    variable_cost_basis = "PRODUCT_LEVEL_VOLUME_X_UNIT_COST" if costs_complete else None
    if variable_cost is not None and revenue is not None and cost_ratio is not None:
        ratio_implied_cost = revenue * cost_ratio
        if variable_cost != ratio_implied_cost:
            issues.append("AGGREGATE_COST_RATIO_CONFLICTS_WITH_PRODUCT_LEVEL_COSTS")
            variable_cost = None
            variable_cost_basis = None
    elif variable_cost is None and revenue is not None and cost_ratio is not None:
        variable_cost = revenue * cost_ratio
        variable_cost_basis = "AGGREGATE_COST_OF_REVENUE_RATIO"
    contribution = revenue - variable_cost if revenue is not None and variable_cost is not None else None
    fixed_opex = _value(scenario_measures.get("fixed_cash_opex_cny"))
    da = _value(scenario_measures.get("depreciation_amortization_cny"))
    finance_cost = _value(scenario_measures.get("finance_cost_cny"))
    tax_rate = _value(scenario_measures.get("tax_rate"))
    capex = _value(scenario_measures.get("cash_capex_cny"))
    change_wc = _value(scenario_measures.get("change_working_capital_cny"))

    ebitda = contribution - fixed_opex if contribution is not None and fixed_opex is not None else None
    ebit = ebitda - da if ebitda is not None and da is not None else None
    pbt = ebit - finance_cost if ebit is not None and finance_cost is not None else None
    net_profit = (
        pbt - max(pbt, Decimal("0")) * tax_rate
        if pbt is not None and tax_rate is not None else None
    )
    fcf = (
        ebit - max(ebit, Decimal("0")) * tax_rate + da - capex - change_wc
        if ebit is not None and tax_rate is not None and da is not None and capex is not None and change_wc is not None
        else None
    )
    revenue_mix = []
    if revenue is not None and revenue > 0:
        for product in product_results:
            p_revenue = product.get("revenue_cny")
            share = _decimal(p_revenue, "PRODUCT_REVENUE") / revenue if p_revenue is not None else None
            revenue_mix.append({
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "revenue_cny": p_revenue,
                "revenue_mix_ratio": _render(share),
            })

    if revenue is not None and net_profit is not None and fcf is not None:
        calculation_status = "SCENARIO_ARITHMETIC_COMPLETE"
    elif revenue is not None:
        calculation_status = "PARTIAL_SCENARIO_BRIDGE"
    else:
        calculation_status = "SCENARIO_ECONOMICS_NOT_IDENTIFIABLE"

    missing_inputs = []
    metric_values = {
        "total_revenue": revenue,
        "total_variable_cost": variable_cost,
        "fixed_cash_opex": fixed_opex,
        "depreciation_amortization": da,
        "finance_cost": finance_cost,
        "tax_rate": tax_rate,
        "cash_capex": capex,
        "change_working_capital": change_wc,
    }
    if variable_cost is None:
        metric_values["cost_of_revenue_ratio"] = cost_ratio
    missing_inputs.extend(name for name, value in metric_values.items() if value is None)
    return {
        "scenario": scenario_name,
        "calculation_status": calculation_status,
        "product_lines": product_results,
        "production_volume_tonnes": _render(production_total) if all_production_known else None,
        "sales_volume_tonnes": _render(volume_total) if all_volume_known else None,
        "revenue_cny": _render(revenue),
        "variable_cost_cny": _render(variable_cost),
        "variable_cost_basis": variable_cost_basis,
        "cost_of_revenue_ratio": _render(cost_ratio),
        "contribution_after_variable_cost_cny": _render(contribution),
        "fixed_cash_opex_cny": _render(fixed_opex),
        "ebitda_cny": _render(ebitda),
        "depreciation_amortization_cny": _render(da),
        "ebit_cny": _render(ebit),
        "finance_cost_cny": _render(finance_cost),
        "profit_before_tax_cny": _render(pbt),
        "tax_rate": _render(tax_rate),
        "net_profit_cny": _render(net_profit),
        "cash_capex_cny": _render(capex),
        "change_working_capital_cny": _render(change_wc),
        "unlevered_fcf_proxy_cny": _render(fcf),
        "revenue_mix": revenue_mix,
        "missing_inputs": missing_inputs,
        "issues": sorted(set(issues)),
        "is_forecast_not_realized": True,
        "eps_impact": None,
        "per_share_value_impact": None,
    }


def evaluate_operating_driver_forecast(
    raw: Any,
    *,
    evidence_register: list[Mapping[str, Any]] | None = None,
    unresolved_evidence_ids: list[str] | None = None,
    after_cutoff_evidence_ids: list[str] | None = None,
    uncertain_timing_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Normalize and compute a scenario driver tree without upgrading any authority."""
    if not isinstance(raw, Mapping):
        return {
            "schema_version": OPERATING_DRIVER_SCHEMA,
            "input_status": "NOT_PROVIDED",
            "status": "UNKNOWN",
            "scope": "UNKNOWN",
            "summary": "未提供经营驱动因素树；销量、净售价、单位成本、爬坡、折旧、资本开支及营运资金保持 UNKNOWN。",
            "actuals_period": "UNKNOWN",
            "forecast_period": "UNKNOWN",
            "product_lines": [],
            "scenarios": {name: {"scenario": name, "calculation_status": "SCENARIO_ECONOMICS_NOT_IDENTIFIABLE", "missing_inputs": ["product_lines"], "issues": []} for name in SCENARIOS},
            "historical_actuals_status": "NOT_IDENTIFIABLE",
            "valuation_transmission": {
                "status": "NOT_LINKED_TO_PER_SHARE_VALUE",
                "reason": "尚未建立从经营结果到公司归属净利润、股数/摊薄与每股价值的可验证桥接。",
            },
            "formal_forecast_admission_created": False,
            "decision_authority": False,
        }

    if raw.get("schema_version") != OPERATING_DRIVER_SCHEMA:
        return {
            "schema_version": OPERATING_DRIVER_SCHEMA,
            "input_status": "INVALID_SCHEMA",
            "status": "UNKNOWN",
            "scope": "UNKNOWN",
            "summary": str(raw.get("summary") or "经营驱动因素输入版本不兼容。"),
            "actuals_period": str(raw.get("actuals_period") or "UNKNOWN"),
            "forecast_period": str(raw.get("forecast_period") or "UNKNOWN"),
            "product_lines": [],
            "scenarios": {name: {"scenario": name, "calculation_status": "SCENARIO_ECONOMICS_NOT_IDENTIFIABLE", "missing_inputs": ["valid_schema"], "issues": ["OPERATING_DRIVER_SCHEMA_MISMATCH"]} for name in SCENARIOS},
            "input_issues": ["OPERATING_DRIVER_SCHEMA_MISMATCH"],
            "historical_actuals_status": "NOT_IDENTIFIABLE",
            "valuation_transmission": {
                "status": "NOT_LINKED_TO_PER_SHARE_VALUE",
                "reason": "经营预测结构无法解析，不连接每股估值。",
            },
            "formal_forecast_admission_created": False,
            "decision_authority": False,
        }

    sources_by_id = {
        str(row.get("source_id")): row
        for row in evidence_register or []
        if isinstance(row, Mapping) and str(row.get("source_id") or "").strip()
    }
    unresolved_refs = set(unresolved_evidence_ids or [])
    after_cutoff_refs = set(after_cutoff_evidence_ids or [])
    uncertain_refs = set(uncertain_timing_evidence_ids or [])

    scope = str(raw.get("scope") or "UNKNOWN").strip().upper()
    if scope not in SCOPES:
        scope = "UNKNOWN"
    raw_products = raw.get("product_lines")
    raw_products = raw_products if isinstance(raw_products, list) else []
    product_lines: list[dict[str, Any]] = []
    product_ids: set[str] = set()
    input_issues: list[str] = []
    actuals_complete = bool(raw_products)

    for index, row in enumerate(raw_products):
        if not isinstance(row, Mapping):
            input_issues.append(f"PRODUCT_ROW_{index}_INVALID")
            actuals_complete = False
            continue
        product_id = str(row.get("product_id") or "").strip()
        product_name = str(row.get("product_name") or "").strip()
        if not product_id or not product_name:
            input_issues.append(f"PRODUCT_ROW_{index}_IDENTITY_REQUIRED")
            actuals_complete = False
            continue
        if product_id in product_ids:
            input_issues.append(f"DUPLICATE_PRODUCT_ID:{product_id}")
            actuals_complete = False
            continue
        product_ids.add(product_id)
        capacity = _normalise_measure(
            row.get("capacity_tonnes_per_year"),
            field=f"{product_id}.capacity_tonnes_per_year",
            expected_unit="tonnes/year",
            sources_by_id=sources_by_id,
            unresolved_refs=unresolved_refs,
            after_cutoff_refs=after_cutoff_refs,
            uncertain_refs=uncertain_refs,
        )
        actuals = _normalise_product_measure_set(
            row.get("historical_actuals"),
            {
                "production_tonnes": "tonnes",
                "sales_volume_tonnes": "tonnes",
                "net_asp_cny_per_tonne": "CNY/tonne",
                "variable_cost_cny_per_tonne": "CNY/tonne",
            },
            f"{product_id}.historical_actuals",
            sources_by_id,
            unresolved_refs,
            after_cutoff_refs,
            uncertain_refs,
            allowed_data_classes={"OBSERVED_ACTUAL"},
        )
        actual_bridge = _product_profit_bridge(
            product_id, product_name, actuals, capacity,
            period_basis=str(raw.get("actuals_period") or "UNKNOWN"),
        )
        for measure in [capacity, *actuals.values()]:
            if measure.get("issues"):
                input_issues.extend(measure["issues"])
        is_complete_actual = all(
            measure.get("calculation_usable") is True
            and measure.get("data_class") == "OBSERVED_ACTUAL"
            for measure in [actuals[key] for key in ("production_tonnes", "sales_volume_tonnes", "net_asp_cny_per_tonne", "variable_cost_cny_per_tonne")]
        )
        if not is_complete_actual:
            actuals_complete = False
        product_lines.append({
            "product_id": product_id,
            "product_name": product_name,
            "capacity_tonnes_per_year": capacity,
            "historical_actuals": actuals,
            "historical_actual_bridge": actual_bridge,
        })

    scenarios_raw = raw.get("scenarios") if isinstance(raw.get("scenarios"), Mapping) else {}
    forecast_period = str(raw.get("forecast_period") or "UNKNOWN")
    scenarios = {
        name: _calculate_scenario(
            name,
            scenarios_raw.get(name),
            product_lines,
            forecast_period,
            sources_by_id,
            unresolved_refs,
            after_cutoff_refs,
            uncertain_refs,
        )
        for name in SCENARIOS
    }
    any_revenue = any(result.get("revenue_cny") is not None for result in scenarios.values())
    all_net_profit = all(result.get("net_profit_cny") is not None for result in scenarios.values())
    all_fcf = all(result.get("unlevered_fcf_proxy_cny") is not None for result in scenarios.values())
    status = "UNKNOWN" if not product_lines or not any_revenue else ("SCENARIOS_CALCULATED" if all_net_profit and all_fcf else "PARTIAL")
    historical_status = (
        "PRODUCT_LINE_ACTUALS_TYPED_NOT_FORMALLY_ADMITTED"
        if actuals_complete else "NOT_IDENTIFIABLE_OR_INCOMPLETE"
    )
    summary = str(raw.get("summary") or "已处理经营驱动输入；所有计算均为非正式试运行，不等同于已实现项目利润。")
    limits = raw.get("limitations")
    limits = [str(x).strip() for x in limits if str(x).strip()] if isinstance(limits, list) else []
    limits.extend([
        "发行人预测、年化产能释放计划与实际产销量不是同一概念；不得将计划数字写成已实现业绩。",
        "情景数字只描述所填驱动假设下的经营桥接，不自动替代现有 Bear/Base/Bull 每股估值。",
        "尚未建立可靠的公司归属净利润、稀释后股数、存量业务替代/蚕食与每股价值传导链。",
        "数值计算结果仍是 PILOT_NON_CANONICAL；不构成正式 Forecast/Valuation Admission 或投资授权。",
    ])
    if scope == "PROJECT_INCREMENTAL":
        limits.append("项目增量收入/利润必须与既有产品/液体形态转粉体的内部转换区分，不能把收入形态迁移误认为集团新增需求。")
    return {
        "schema_version": OPERATING_DRIVER_SCHEMA,
        "input_status": "PROVIDED",
        "status": status,
        "scope": scope,
        "summary": summary,
        "actuals_period": str(raw.get("actuals_period") or "UNKNOWN"),
        "forecast_period": forecast_period,
        "product_lines": product_lines,
        "scenarios": scenarios,
        "input_issues": sorted(set(input_issues)),
        "historical_actuals_status": historical_status,
        "valuation_transmission": {
            "status": "NOT_LINKED_TO_PER_SHARE_VALUE",
            "reason": "没有可验证的桥接把该经营情景转换为公司归属净利润、每股收益和每股估值；本轮刻意不自动修改估值输入。",
            "required_bridge_inputs": [
                "增量需求与既有业务替代/蚕食分离",
                "项目实际/预测归属税后利润及少数股东或内部交易影响",
                "加权平均及稀释后股数、可转债转股/潜在摊薄情景",
                "与人工选定主估值模型一致的利润、现金流与倍数传导",
            ],
        },
        "limitations": sorted(set(limits)),
        "formal_forecast_admission_created": False,
        "decision_authority": False,
    }


def _display(measure: Any) -> str:
    if not isinstance(measure, Mapping):
        return "UNKNOWN"
    value = measure.get("value")
    if value is None:
        claimed = measure.get("claimed_value")
        if claimed is not None:
            return f"UNKNOWN（未采用声明值 {claimed}；{';'.join(measure.get('issues') or []) or '来源/口径未通过'}）"
        return "UNKNOWN"
    return f"{value} {measure.get('unit') or ''}".strip()


def _display_optional_scalar(value: Any) -> str:
    """Render missing scalar values as UNKNOWN without collapsing numeric zero."""
    return "UNKNOWN" if value is None or value == "" else str(value)


def render_operating_driver_section(
    forecast: Mapping[str, Any],
    valuation_scenarios: Mapping[str, Any] | None,
    currency: str = "CNY",
    valuation_transmission: Mapping[str, Any] | None = None,
) -> list[str]:
    """Render the operating bridge without contradicting the actual B5 transmission result."""
    driver = forecast if isinstance(forecast, Mapping) else {}
    b5 = valuation_transmission if isinstance(valuation_transmission, Mapping) else None
    b5_status = str(b5.get("status") or "UNKNOWN") if b5 is not None else "NOT_PROVIDED"
    b5_applied = bool(
        b5 is not None
        and b5_status == "APPLIED_TO_PER_SHARE_SCENARIOS"
        and b5.get("applied_to_per_share_scenarios") is True
    )
    baseline_already_includes = (
        b5 is not None
        and b5_status == "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT"
    )
    lines = [
        "",
        "### 经营驱动因素与独立预测桥（B4）",
        "",
        f"- 驱动树状态：**{driver.get('status', 'UNKNOWN')}**；范围：{driver.get('scope', 'UNKNOWN')}",
        f"- 历史实际驱动状态：{driver.get('historical_actuals_status', 'NOT_IDENTIFIABLE_OR_INCOMPLETE')}",
        f"- 历史期间：{driver.get('actuals_period', 'UNKNOWN')}；预测期间：{driver.get('forecast_period', 'UNKNOWN')}",
        f"- 研究摘要：{driver.get('summary', '未提供经营驱动因素树。')}",
        "- 下表中 OBSERVED_ACTUAL 是被来源登记与截止时间初步匹配的试运行声明，不等于正式证据准入；ISSUER_FORECAST 是公司计划/预测；ANALYST_ASSUMPTION 是分析假设。",
        "",
        "#### 产品/业务线与历史实际",
        "",
    ]
    products = driver.get("product_lines") if isinstance(driver.get("product_lines"), list) else []
    if not products:
        lines.append("- 产品线未提供：实际产量、销量、净售价及单位成本保持 UNKNOWN，不用公司整体收入除以产量替代实际售价。")
    for product in products:
        if not isinstance(product, Mapping):
            continue
        name = str(product.get("product_name") or product.get("product_id") or "未命名产品")
        cap = product.get("capacity_tonnes_per_year")
        lines.extend([
            f"- **{name}**（{product.get('product_id', 'UNKNOWN')}）",
            f"  - 设计/年度产能：{_display(cap)}",
        ])
        actuals = product.get("historical_actuals") if isinstance(product.get("historical_actuals"), Mapping) else {}
        for key, label in (
            ("production_tonnes", "实际产量"),
            ("sales_volume_tonnes", "实际销量"),
            ("net_asp_cny_per_tonne", "实际净售价"),
            ("variable_cost_cny_per_tonne", "单位变动成本"),
        ):
            measure = actuals.get(key)
            data_class = measure.get("data_class", "UNKNOWN") if isinstance(measure, Mapping) else "UNKNOWN"
            refs = "、".join(measure.get("evidence_refs") or []) if isinstance(measure, Mapping) else ""
            suffix = f"；类别 {data_class}" + (f"；证据引用 {refs}" if refs else "")
            lines.append(f"  - {label}：{_display(measure)}{suffix}")
        bridge = product.get("historical_actual_bridge") if isinstance(product.get("historical_actual_bridge"), Mapping) else {}
        lines.append(f"  - 按已可用的销量×净售价计算收入：{_display_optional_scalar(bridge.get('revenue_cny'))}；销量×单位变动成本：{_display_optional_scalar(bridge.get('variable_cost_cny'))}。")
        if bridge.get("production_utilization") is not None:
            lines.append(f"  - 产能利用率（产量/年产能）：{Decimal(bridge['production_utilization']) * Decimal('100')}%（仅当期间与容量口径可比时成立）")
        for issue in bridge.get("issues") or []:
            lines.append(f"  - 口径复核项：{issue}")
    lines.extend(["", "#### Bear / Base / Bull 经营结果", ""])
    v_scenarios = valuation_scenarios if isinstance(valuation_scenarios, Mapping) else {}
    for name in SCENARIOS:
        result = driver.get("scenarios", {}).get(name, {}) if isinstance(driver.get("scenarios"), Mapping) else {}
        value_row = v_scenarios.get(name, {}) if isinstance(v_scenarios.get(name), Mapping) else {}
        if value_row.get("b5_transmission_applied") is True:
            valuation_label = "B5 传导后的每股估值情景终值"
        elif baseline_already_includes:
            valuation_label = "基准已含项目、未重复叠加的每股估值情景终值"
        elif b5 is None:
            valuation_label = "每股估值情景终值（本节未接收 B5 状态）"
        else:
            valuation_label = "未应用 B5 增量的每股估值情景终值"
        scenario_terminal_value = value_row.get("terminal_value_per_share")
        scenario_terminal_display = (
            "UNKNOWN" if scenario_terminal_value in (None, "") else scenario_terminal_value
        )
        lines.extend([
            f"**{name.upper()}**",
            f"- 桥接计算状态：{result.get('calculation_status', 'SCENARIO_ECONOMICS_NOT_IDENTIFIABLE')}",
            f"- 产量 / 销量：{_display_optional_scalar(result.get('production_volume_tonnes'))} / {_display_optional_scalar(result.get('sales_volume_tonnes'))} 吨",
            f"- 收入：{_display_optional_scalar(result.get('revenue_cny'))}；变动成本：{_display_optional_scalar(result.get('variable_cost_cny'))}；扣变动成本贡献：{_display_optional_scalar(result.get('contribution_after_variable_cost_cny'))}",
            f"- EBITDA / EBIT / 税前利润 / 净利润：{_display_optional_scalar(result.get('ebitda_cny'))} / {_display_optional_scalar(result.get('ebit_cny'))} / {_display_optional_scalar(result.get('profit_before_tax_cny'))} / {_display_optional_scalar(result.get('net_profit_cny'))}",
            f"- 资本开支 / 营运资金变动 / 自由现金流代理：{_display_optional_scalar(result.get('cash_capex_cny'))} / {_display_optional_scalar(result.get('change_working_capital_cny'))} / {_display_optional_scalar(result.get('unlevered_fcf_proxy_cny'))}",
            f"- {valuation_label}：{scenario_terminal_display} {currency}",
        ])
        mix = result.get("revenue_mix") or []
        if mix:
            lines.append("  - 收入产品结构：" + "；".join(
                f"{row.get('product_name')} {Decimal(row['revenue_mix_ratio']) * Decimal('100')}%"
                for row in mix if row.get("revenue_mix_ratio") is not None
            ))
        if result.get("missing_inputs"):
            lines.append("  - 尚缺：" + "、".join(result["missing_inputs"]))
        if result.get("issues"):
            lines.append("  - 口径/来源问题：" + "；".join(result["issues"]))
        if result.get("product_lines"):
            for product in result["product_lines"]:
                lines.append(
                    f"  - {product['product_name']}：产量 {_display(product['inputs'].get('production_tonnes'))}；"
                    f"销量 {_display(product['inputs'].get('sales_volume_tonnes'))}；"
                    f"净售价 {_display(product['inputs'].get('net_asp_cny_per_tonne'))}；"
                    f"单位变动成本 {_display(product['inputs'].get('variable_cost_cny_per_tonne'))}；"
                    f"产能利用率 {_display({'value': str(Decimal(product['production_utilization']) * Decimal('100')), 'unit': '%', 'calculation_usable': True}) if product.get('production_utilization') is not None else 'UNKNOWN'}。"
                )
        lines.append("")
    lines.extend([
        "- 解释：模型按产品“销量×净售价”计算收入，按销量×单位变动成本计算直接变动成本，再扣现金固定运营费用及折旧得到 EBITDA/EBIT；税前利润额外扣融资成本。自由现金流代理 = EBIT − 正 EBIT 对应现金税 + 折旧 − 资本开支 − 营运资金增加（营运资金释放可为负值）。",
    ])
    if b5_applied:
        lines.append("- 传导边界：这只是情景经营桥，不代表实际已实现净利润。当前 B5 已按明确的 EPS_MULTIPLE 增量桥接，将稀释口径的项目增量传导至 Bear/Base/Bull 每股终值与 Base 估值锚；仍是非正式试运行，不构成正式准入或 Decision。")
    elif baseline_already_includes:
        lines.append("- 传导边界：这只是情景经营桥，不代表实际已实现净利润。操作者已确认原每股估值基准包含该项目，B5 因防止重复计价而没有二次叠加；原终值和 Base 估值锚保持不变。")
    elif b5 is not None:
        lines.append(f"- 传导边界：这只是情景经营桥，不代表实际已实现净利润。当前 B5 状态为 {b5_status}；此状态下项目增量未应用到每股终值，具体原因见下方 B5 详情。不得将项目增量默认为已计入估值。")
    else:
        lines.append("- 传导边界：这只是情景经营桥，不代表实际已实现净利润；本节未接收到 B5 传导状态，不得据此假定项目增量已计入每股估值。")
    lines.extend([
        "",
        "#### B4 / B5 估值传导衔接状态",
        "",
    ])
    if b5 is not None:
        lines.extend([
            f"- B5 当前传导状态：{b5_status}",
            f"- B5 传导结论：{b5.get('summary') or '未提供结论。'}",
        ])
        if b5_applied:
            lines.append("- 已应用：Bear/Base/Bull 情景终值和 Base 估值锚使用 B5 调整后的值。")
        elif baseline_already_includes:
            lines.append("- 未重复叠加：原基准已包含项目，保留原估值以避免双重计价。")
        else:
            issues = b5.get("input_issues") if isinstance(b5.get("input_issues"), list) else []
            lines.append("- 尚未应用每股价值增量；" + ("；".join(str(x) for x in issues) if issues else "具体缺口见下方 B5 详情。"))
    else:
        legacy_transmission = driver.get("valuation_transmission") if isinstance(driver.get("valuation_transmission"), Mapping) else {}
        lines.extend([
            f"- B5 状态：NOT_PROVIDED；B4 局部传导状态：{legacy_transmission.get('status', 'NOT_LINKED_TO_PER_SHARE_VALUE')}",
            f"- B4 局部说明：{legacy_transmission.get('reason', '未提供可验证的经营结果到每股价值桥接。')}",
        ])
        if legacy_transmission.get("required_bridge_inputs"):
            lines.append("- B5 待补齐： " + "；".join(str(x) for x in legacy_transmission["required_bridge_inputs"]))
    if driver.get("input_issues"):
        lines.extend(["", "#### 输入结构/来源问题", ""])
        lines.extend(f"- {issue}" for issue in driver["input_issues"])
    limitations = driver.get("limitations") if isinstance(driver.get("limitations"), list) else []
    if limitations:
        lines.extend(["", "#### 限制", ""])
        lines.extend(f"- {item}" for item in limitations)
    lines.append("- 本节只给出非正式试运行计算；不会创建正式 Forecast/Valuation Admission、正式 Decision 或执行授权。")
    return lines
