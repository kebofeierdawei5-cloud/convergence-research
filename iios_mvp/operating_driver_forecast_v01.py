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
INVENTORY_WORKING_CAPITAL_TREATMENTS = {
    "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
    "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
    "NOT_APPLICABLE",
    "UNKNOWN",
}

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
    "cost_of_revenue_ratio": "ratio",
    "cash_capex_cny": "CNY",
    "change_working_capital_cny": "CNY",
}

NET_PROFIT_BRIDGE_MEASURES = {
    "fixed_cash_opex_cny": "CNY",
    "depreciation_amortization_cny": "CNY",
    "finance_cost_cny": "CNY",
    "tax_rate": "ratio",
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


def _normalise_product_name(value: Any) -> str:
    """Collapse leading, trailing and repeated Unicode whitespace in product labels."""
    return " ".join(str(value or "").split())


def _normalise_inventory_working_capital_treatment(value: Any) -> str:
    """Normalize the explicit inventory inclusion contract without guessing."""
    raw = " ".join(str(value or "UNKNOWN").split()).upper()
    aliases = {
        "INCLUDED": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
        "EXCLUDED": "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
        "INCLUDED_IN_TOTAL_WORKING_CAPITAL": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
        "EXCLUDED_FROM_TOTAL_WORKING_CAPITAL": "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL",
    }
    return aliases.get(raw, raw)


def _is_identifiable_basis(value: Any) -> bool:
    """A numeric assumption needs an identifiable rationale, not a placeholder token."""
    raw = str(value or "").strip()
    if not raw:
        return False
    normalized = re.sub(r"[^A-Z0-9]+", "_", raw.upper()).strip("_")
    placeholders = {
        "UNKNOWN", "N_A", "NA", "NONE", "NULL", "NOT_IDENTIFIABLE",
        "UNIDENTIFIABLE", "UNSPECIFIED", "NOT_SPECIFIED", "TBD", "NOT_PROVIDED",
        "NOT_AVAILABLE", "UNAVAILABLE", "UNVERIFIED", "UNCONFIRMED", "NOT_KNOWN",
        "UNKNOWN_BASIS", "BASIS_UNKNOWN", "NO_BASIS", "NO_RATIONALE",
        "MISSING", "UNRESOLVED",
    }
    chinese_placeholders = {
        "未知", "不详", "不明确", "未提供", "未提供依据", "无依据",
        "待补充", "待核实", "缺失",
    }
    return normalized not in placeholders and raw not in chinese_placeholders


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
    elif not _is_identifiable_basis(basis):
        issues.append(f"{field}:BASIS_NOT_IDENTIFIABLE")

    # Quantities, capacity, selling price, expenses and tax rate cannot be negative.
    # A change in working capital is signed: positive consumes cash, negative releases cash.
    metric_name = field.rsplit(".", 1)[-1]
    if claimed is not None:
        if metric_name != "change_working_capital_cny" and claimed < 0:
            issues.append(f"{field}:NEGATIVE_VALUE_NOT_ALLOWED")
        if metric_name == "tax_rate" and not (Decimal("0") <= claimed <= Decimal("1")):
            issues.append(f"{field}:TAX_RATE_MUST_BE_RATIO_0_TO_1")
        if metric_name == "cost_of_revenue_ratio" and not (Decimal("0") <= claimed <= Decimal("1")):
            issues.append(f"{field}:COST_OF_REVENUE_RATIO_MUST_BE_0_TO_1")

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
    inventory_change_tonnes = production - sales_volume if production is not None and sales_volume is not None else None
    inventory_cash_impact_proxy = (
        Decimal("0") if inventory_change_tonnes == 0
        else inventory_change_tonnes * unit_cost
        if inventory_change_tonnes is not None and unit_cost is not None
        else None
    )
    if inventory_change_tonnes is None:
        production_sales_balance_status = "NOT_IDENTIFIABLE"
    elif inventory_change_tonnes > 0:
        production_sales_balance_status = "PRODUCTION_EXCEEDS_SALES_INVENTORY_BUILD"
    elif inventory_change_tonnes < 0:
        production_sales_balance_status = "SALES_EXCEEDS_PRODUCTION_INVENTORY_DRAWDOWN"
    else:
        production_sales_balance_status = "BALANCED_NO_INVENTORY_CHANGE"
    calculated_revenue = sales_volume * asp if sales_volume is not None and asp is not None else None
    direct_revenue = _value(metrics.get("revenue_cny"))
    calculated_variable_cost = sales_volume * unit_cost if sales_volume is not None and unit_cost is not None else None
    direct_variable_cost = _value(metrics.get("variable_cost_cny"))
    utilization = None
    issues: list[str] = []
    if calculated_revenue is not None and direct_revenue is not None and calculated_revenue != direct_revenue:
        issues.append("EXPLICIT_REVENUE_CONFLICTS_WITH_VOLUME_X_ASP")
        revenue = None
        revenue_basis = None
    else:
        revenue = calculated_revenue if calculated_revenue is not None else direct_revenue
        revenue_basis = (
            "VOLUME_X_NET_ASP" if calculated_revenue is not None
            else "DIRECT_REPORTED_REVENUE" if direct_revenue is not None
            else None
        )
    if calculated_variable_cost is not None and direct_variable_cost is not None and calculated_variable_cost != direct_variable_cost:
        issues.append("EXPLICIT_VARIABLE_COST_CONFLICTS_WITH_VOLUME_X_UNIT_COST")
        variable_cost = None
    else:
        variable_cost = calculated_variable_cost if calculated_variable_cost is not None else direct_variable_cost
    if production is not None and capacity_value is not None and capacity_value > 0:
        if not _is_full_year_period(period_basis):
            issues.append("CAPACITY_PERIOD_ALIGNMENT_UNKNOWN")
        else:
            utilization = production / capacity_value
            if utilization > Decimal("1"):
                issues.append("PRODUCTION_ABOVE_NAMEPLATE_CAPACITY_CHECK_PERIOD_OR_SCOPE")
    return {
        "product_id": product_id,
        "product_name": _normalise_product_name(product_name),
        "production_tonnes": _render(production),
        "sales_volume_tonnes": _render(sales_volume),
        "inventory_change_tonnes": _render(inventory_change_tonnes),
        "production_sales_balance_status": production_sales_balance_status,
        "inventory_cash_impact_proxy_cny": _render(inventory_cash_impact_proxy),
        "inventory_cash_impact_proxy_basis": (
            "PRODUCTION_MINUS_SALES_X_VARIABLE_UNIT_COST_PROXY"
            if inventory_cash_impact_proxy is not None else None
        ),
        "net_asp_cny_per_tonne": _render(asp),
        "variable_cost_cny_per_tonne": _render(unit_cost),
        "revenue_cny": _render(revenue),
        "revenue_basis": revenue_basis,
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
                "revenue_cny": "CNY",
                "variable_cost_cny": "CNY",
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
    variable_cost_basis = "PRODUCT_LEVEL_COSTS" if costs_complete else None
    if variable_cost is not None and revenue is not None and cost_ratio is not None:
        ratio_implied_cost = revenue * cost_ratio
        if variable_cost != ratio_implied_cost:
            issues.append("AGGREGATE_COST_RATIO_CONFLICTS_WITH_PRODUCT_LEVEL_COSTS")
            variable_cost = None
            variable_cost_basis = None
    elif variable_cost is None and revenue is not None and cost_ratio is not None:
        product_cost_conflict = any(
            "EXPLICIT_VARIABLE_COST_CONFLICTS_WITH_VOLUME_X_UNIT_COST" in (row.get("issues") or [])
            for row in product_results
        )
        if product_cost_conflict:
            # Do not overwrite a contradiction between explicit product-level
            # cost declarations with an aggregate ratio. The ratio may be used
            # as a fallback when product cost is simply unavailable, but a
            # conflicting declared cost basis requires human/analyst resolution.
            issues.append("AGGREGATE_COST_RATIO_FALLBACK_BLOCKED_BY_PRODUCT_COST_CONFLICT")
        else:
            variable_cost = revenue * cost_ratio
            variable_cost_basis = "AGGREGATE_COST_OF_REVENUE_RATIO"
    contribution = revenue - variable_cost if revenue is not None and variable_cost is not None else None
    fixed_opex = _value(scenario_measures.get("fixed_cash_opex_cny"))
    da = _value(scenario_measures.get("depreciation_amortization_cny"))
    finance_cost = _value(scenario_measures.get("finance_cost_cny"))
    tax_rate = _value(scenario_measures.get("tax_rate"))
    capex = _value(scenario_measures.get("cash_capex_cny"))
    change_wc = _value(scenario_measures.get("change_working_capital_cny"))
    inventory_treatment = _normalise_inventory_working_capital_treatment(
        scenario.get("inventory_working_capital_treatment")
    )
    tonnage_basis_present = any(
        _value(product.get("capacity_tonnes_per_year")) is not None
        or _value(result.get("inputs", {}).get("production_tonnes")) is not None
        or _value(result.get("inputs", {}).get("sales_volume_tonnes")) is not None
        for product, result in zip(products, product_results)
    )
    inventory_balance_complete = bool(product_results) and all(
        result.get("inventory_change_tonnes") is not None for result in product_results
    )
    zero_inventory_movement = inventory_balance_complete and all(
        _decimal(result.get("inventory_change_tonnes"), "INVENTORY_CHANGE_TONNES") == 0
        for result in product_results
    )
    inventory_proxy_complete = inventory_balance_complete and all(
        result.get("inventory_cash_impact_proxy_cny") is not None for result in product_results
    )
    inventory_cash_proxy_total = (
        sum(
            (
                _decimal(result["inventory_cash_impact_proxy_cny"], "INVENTORY_CASH_IMPACT_PROXY")
                for result in product_results
            ),
            Decimal("0"),
        )
        if inventory_proxy_complete else None
    )
    effective_change_wc: Decimal | None = None
    inventory_reconciliation_issues: list[str] = []
    if inventory_treatment not in INVENTORY_WORKING_CAPITAL_TREATMENTS:
        inventory_reconciliation_status = "INVALID_INVENTORY_WORKING_CAPITAL_TREATMENT"
        inventory_reconciliation_issues.append("INVENTORY_WORKING_CAPITAL_TREATMENT_INVALID")
    elif not tonnage_basis_present:
        effective_change_wc = change_wc
        inventory_reconciliation_status = "NOT_APPLICABLE_NO_TONNAGE_BASIS"
    elif inventory_treatment == "INCLUDED_IN_CHANGE_WORKING_CAPITAL":
        effective_change_wc = change_wc
        inventory_reconciliation_status = (
            "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL"
            if inventory_balance_complete
            else "INVENTORY_MOVEMENT_NOT_IDENTIFIABLE_TOTAL_WORKING_CAPITAL_DECLARED_INCLUDED"
        )
    elif inventory_treatment == "EXCLUDED_FROM_CHANGE_WORKING_CAPITAL":
        if not inventory_balance_complete:
            inventory_reconciliation_status = "INVENTORY_BALANCE_NOT_IDENTIFIABLE_FOR_EXCLUDED_WORKING_CAPITAL"
            inventory_reconciliation_issues.append("INVENTORY_BALANCE_REQUIRED_WHEN_WORKING_CAPITAL_EXCLUDES_INVENTORY")
        elif not inventory_proxy_complete:
            inventory_reconciliation_status = "INVENTORY_COST_PROXY_UNAVAILABLE_FOR_EXCLUDED_WORKING_CAPITAL"
            inventory_reconciliation_issues.append("INVENTORY_COST_PROXY_REQUIRED_BUT_UNAVAILABLE")
        elif change_wc is None:
            inventory_reconciliation_status = "NON_INVENTORY_WORKING_CAPITAL_AMOUNT_UNKNOWN"
            inventory_reconciliation_issues.append("NON_INVENTORY_WORKING_CAPITAL_AMOUNT_REQUIRED")
        else:
            effective_change_wc = change_wc + inventory_cash_proxy_total
            inventory_reconciliation_status = "INVENTORY_COST_PROXY_ADDED_TO_NONINVENTORY_WORKING_CAPITAL"
    elif inventory_treatment == "NOT_APPLICABLE":
        if zero_inventory_movement:
            effective_change_wc = change_wc
            inventory_reconciliation_status = "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED"
        else:
            inventory_reconciliation_status = "NOT_APPLICABLE_CONTRADICTS_TONNAGE_INVENTORY_BASIS"
            inventory_reconciliation_issues.append("INVENTORY_TREATMENT_NOT_APPLICABLE_DESPITE_NONZERO_OR_UNKNOWN_BALANCE")
    else:
        if zero_inventory_movement:
            effective_change_wc = change_wc
            inventory_reconciliation_status = "ZERO_INVENTORY_CHANGE_NO_ADJUSTMENT_REQUIRED"
        else:
            inventory_reconciliation_status = "INVENTORY_WORKING_CAPITAL_TREATMENT_REQUIRED"
            inventory_reconciliation_issues.append("INVENTORY_WORKING_CAPITAL_TREATMENT_REQUIRED_FOR_NONZERO_OR_UNKNOWN_BALANCE")
    issues.extend(inventory_reconciliation_issues)

    ebitda = contribution - fixed_opex if contribution is not None and fixed_opex is not None else None
    ebit = ebitda - da if ebitda is not None and da is not None else None
    pbt = ebit - finance_cost if ebit is not None and finance_cost is not None else None
    net_profit = (
        pbt - max(pbt, Decimal("0")) * tax_rate
        if pbt is not None and tax_rate is not None else None
    )
    fcf = (
        ebit - max(ebit, Decimal("0")) * tax_rate + da - capex - effective_change_wc
        if ebit is not None and tax_rate is not None and da is not None and capex is not None and effective_change_wc is not None
        else None
    )

    capacity_overrun_issues = sorted({
        issue
        for product in product_results
        for issue in (product.get("issues") or [])
        if issue == "PRODUCTION_ABOVE_NAMEPLATE_CAPACITY_CHECK_PERIOD_OR_SCOPE"
    })
    capacity_period_alignment_unknown = any(
        "CAPACITY_PERIOD_ALIGNMENT_UNKNOWN" in (product.get("issues") or [])
        for product in product_results
    )
    diagnostic_net_profit = net_profit if capacity_overrun_issues else None
    diagnostic_fcf = fcf if capacity_overrun_issues else None
    if capacity_overrun_issues:
        # For an explicitly full-year forecast, production above a known annual
        # nameplate capacity is an unresolved physical operating constraint.
        # Keep unconstrained arithmetic for review, but do not expose it as
        # usable net profit/FCF because B5 could otherwise price infeasible volume.
        net_profit = None
        fcf = None
        issues.append(
            f"{scenario_name}:CAPACITY_CONSTRAINT_UNRESOLVED_FINANCIAL_OUTPUTS_NOT_DECISION_USABLE"
        )

    if capacity_overrun_issues:
        capacity_feasibility_status = "UNRESOLVED_OVER_NAMEPLATE_CAPACITY"
    elif capacity_period_alignment_unknown:
        capacity_feasibility_status = "PERIOD_ALIGNMENT_UNKNOWN"
    else:
        capacity_feasibility_status = "NO_OVERRUN_IDENTIFIED"

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

    # "Decision usable" means the complete downstream financial bridge exists,
    # not merely that no explicit capacity-overrun issue was found.
    financial_outputs_decision_usable = (
        not capacity_overrun_issues
        and calculation_status == "SCENARIO_ARITHMETIC_COMPLETE"
        and net_profit is not None
        and fcf is not None
    )
    if not financial_outputs_decision_usable and not capacity_overrun_issues:
        issues.append(
            f"{scenario_name}:FINANCIAL_OUTPUTS_INCOMPLETE_NOT_DECISION_USABLE"
        )

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
        "effective_change_working_capital": effective_change_wc,
    }
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
        "effective_change_working_capital_cny": _render(effective_change_wc),
        "inventory_working_capital_treatment": inventory_treatment,
        "inventory_cash_impact_proxy_cny": _render(inventory_cash_proxy_total),
        "inventory_reconciliation_status": inventory_reconciliation_status,
        "unlevered_fcf_proxy_cny": _render(fcf),
        "capacity_feasibility_status": capacity_feasibility_status,
        "financial_outputs_decision_usable": financial_outputs_decision_usable,
        "diagnostic_net_profit_if_capacity_resolved_cny": _render(diagnostic_net_profit),
        "diagnostic_unlevered_fcf_proxy_if_capacity_resolved_cny": _render(diagnostic_fcf),
        "unresolved_constraints": (
            ["PRODUCTION_ABOVE_NAMEPLATE_CAPACITY"]
            if capacity_overrun_issues else []
        ),
        "revenue_mix": revenue_mix,
        "missing_inputs": missing_inputs,
        "issues": sorted(set(issues)),
        "is_forecast_not_realized": True,
        "eps_impact": None,
        "per_share_value_impact": None,
    }


def _period_year(period: Any) -> int | None:
    """Return a year only for an explicitly complete fiscal/calendar-year label."""
    label = "".join(str(period or "").upper().split())
    if not _is_full_year_period(label):
        return None
    match = re.fullmatch(r"(?:(\d{4})FY|FY(\d{4})|(\d{4})(?:年度|全年))", label)
    if not match:
        return None
    return int(next(group for group in match.groups() if group))


def _build_baseline_transition_bridge(
    *,
    scope: str,
    actuals_period: str,
    forecast_period: str,
    product_lines: list[Mapping[str, Any]],
    scenarios: Mapping[str, Any],
) -> dict[str, Any]:
    """Connect observed product contribution baseline to forward scenarios without implying net profit."""
    schema = "IIOS-B55-BASELINE-TO-FORWARD-DRIVER-BRIDGE-0.1"
    base = {
        "schema_version": schema,
        "scope": scope,
        "baseline_period": actuals_period or "UNKNOWN",
        "forecast_period": forecast_period or "UNKNOWN",
        "comparison_method": "SYMMETRIC_SHAPLEY_CONTRIBUTION_DECOMPOSITION_VOLUME_ASP_UNIT_COST_V0.1",
        "metric": "PRODUCT_LEVEL_CONTRIBUTION_AFTER_VARIABLE_COST_CNY",
        "baseline_issues": [],
        "scenarios": {},
        "limitations": [
            "该桥只解释已映射产品/业务线的销售贡献减变动成本，不等于公司整体净利润、FCF 或每股价值变化。",
            "销量效应、净售价效应和单位成本效应采用对称分解；不代表这些变量具有因果识别或预测确定性。",
            "没有同口径历史固定现金费用、折旧、融资成本、税率、非控股权益与稀释股数时，不得推导完整净利润/EPS 变化。",
            "产量与产销差额单独披露，不并入销量贡献效应；库存/营运资金影响沿既有 B42/B43 现金路径处理，避免重复计数。",
            "历史 OBSERVED_ACTUAL 及前瞻 ISSUER_FORECAST 仍只是来源时点初步匹配的声明，不等于正式 Evidence/PIT 或 Forecast Admission。",
        ],
        "formal_forecast_admission_created": False,
        "decision_authority": False,
    }
    normalized_scope = str(scope or "UNKNOWN").strip().upper()
    if normalized_scope not in {"COMPANY_WIDE", "PRODUCT_LINE"}:
        reason = (
            "PROJECT_INCREMENTAL 的前瞻输入不能与存量业务历史实际直接对比；"
            "增量项目必须通过 B5 增量传导及存量业务替代/蚕食桥处理。"
            if normalized_scope == "PROJECT_INCREMENTAL"
            else "B4 范围未确认或不可比较；不能把产品基线与未明确范围的未来预测直接相连。"
        )
        return {
            **base,
            "status": "NOT_COMPARABLE_SCOPE",
            "reason": reason,
        }

    baseline_year = _period_year(actuals_period)
    forecast_year = _period_year(forecast_period)
    if baseline_year is None or forecast_year is None or forecast_year != baseline_year + 1:
        return {
            **base,
            "status": "PERIOD_NOT_COMPARABLE",
            "reason": (
                "本桥用于一年度基线到前瞻情景的经营变量变化解释；只接受相邻的完整年度。"
                "半年/季度/滚动期间、相同/倒序年度、跨越多个年度或不明确期间均保持 UNKNOWN，"
                "除非先建立明确的中间年度基线桥。"
            ),
        }
    if not product_lines:
        return {
            **base,
            "status": "NOT_IDENTIFIABLE",
            "reason": "没有可映射的历史产品/业务线基线。",
        }

    ids = [str(row.get("product_id") or "").strip() for row in product_lines]
    if not all(ids) or len(set(ids)) != len(ids):
        return {
            **base,
            "status": "NOT_IDENTIFIABLE",
            "reason": "历史产品/业务线 ID 缺失或重复；无法可靠映射前瞻情景。",
        }

    def numeric_measure(raw: Any, *, data_classes: set[str]) -> tuple[Decimal | None, dict[str, Any] | None]:
        if not isinstance(raw, Mapping):
            return None, None
        if raw.get("calculation_usable") is not True:
            return None, {
                "data_class": str(raw.get("data_class") or "UNKNOWN"),
                "basis": str(raw.get("basis") or ""),
                "evidence_refs": list(raw.get("evidence_refs") or []),
                "issues": list(raw.get("issues") or []),
            }
        if str(raw.get("data_class") or "UNKNOWN").strip().upper() not in data_classes:
            return None, {
                "data_class": str(raw.get("data_class") or "UNKNOWN"),
                "basis": str(raw.get("basis") or ""),
                "evidence_refs": list(raw.get("evidence_refs") or []),
                "issues": ["DATA_CLASS_NOT_ALLOWED_FOR_BASELINE_TRANSITION"],
            }
        try:
            return _decimal(raw.get("value"), "B55_TYPED_MEASURE"), {
                "data_class": str(raw.get("data_class") or "UNKNOWN"),
                "basis": str(raw.get("basis") or ""),
                "evidence_refs": sorted({str(x).strip() for x in raw.get("evidence_refs", []) if str(x).strip()})
                if isinstance(raw.get("evidence_refs"), list) else [],
                "evidence_status": str(raw.get("evidence_status") or "UNKNOWN"),
                "issues": list(raw.get("issues") or []),
            }
        except ValueError:
            return None, {
                "data_class": str(raw.get("data_class") or "UNKNOWN"),
                "basis": str(raw.get("basis") or ""),
                "evidence_refs": list(raw.get("evidence_refs") or []),
                "issues": ["VALUE_NOT_NUMERIC"],
            }

    field_names = {
        "sales_volume_tonnes": "sales volume",
        "net_asp_cny_per_tonne": "net ASP",
        "variable_cost_cny_per_tonne": "unit variable cost",
    }
    baseline_values: dict[str, dict[str, Any]] = {}
    baseline_issues: list[str] = []
    for product in product_lines:
        product_id = str(product.get("product_id") or "")
        actuals = product.get("historical_actuals") if isinstance(product.get("historical_actuals"), Mapping) else {}
        values: dict[str, Any] = {}
        for field in field_names:
            value, lineage = numeric_measure(actuals.get(field), data_classes={"OBSERVED_ACTUAL"})
            values[field] = value
            values.setdefault("lineage", {})[field] = lineage or {"data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "issues": ["MEASURE_NOT_USABLE"]}
            if value is None:
                baseline_issues.append(f"{product_id}.{field}:HISTORICAL_BASELINE_NOT_USABLE")
        actual_bridge = product.get("historical_actual_bridge") if isinstance(product.get("historical_actual_bridge"), Mapping) else {}
        raw_actual_bridge_issues = actual_bridge.get("issues")
        relevant_actual_conflicts = [
            str(issue) for issue in raw_actual_bridge_issues
            if issue in {
                "EXPLICIT_REVENUE_CONFLICTS_WITH_VOLUME_X_ASP",
                "EXPLICIT_VARIABLE_COST_CONFLICTS_WITH_VOLUME_X_UNIT_COST",
            }
        ] if isinstance(raw_actual_bridge_issues, list) else []
        values["explicit_bridge_conflicts"] = relevant_actual_conflicts
        if relevant_actual_conflicts:
            baseline_issues.extend(f"{product_id}:{issue}" for issue in relevant_actual_conflicts)
        baseline_values[product_id] = values

    scenario_results: dict[str, Any] = {}
    for scenario_name in SCENARIOS:
        scenario = scenarios.get(scenario_name) if isinstance(scenarios.get(scenario_name), Mapping) else {}
        raw_rows = scenario.get("product_lines") if isinstance(scenario.get("product_lines"), list) else []
        rows_by_id: dict[str, Mapping[str, Any]] = {}
        structure_issues: list[str] = []
        for row in raw_rows:
            if not isinstance(row, Mapping):
                structure_issues.append("FORWARD_PRODUCT_ROW_INVALID")
                continue
            product_id = str(row.get("product_id") or "").strip()
            if not product_id:
                structure_issues.append("FORWARD_PRODUCT_ID_MISSING")
            elif product_id in rows_by_id:
                structure_issues.append(f"DUPLICATE_FORWARD_PRODUCT_ID:{product_id}")
            else:
                rows_by_id[product_id] = row
        expected_ids = set(ids)
        actual_ids = set(rows_by_id)
        if expected_ids != actual_ids:
            structure_issues.append("FORWARD_PRODUCT_UNIVERSE_MISMATCH")
        product_results: list[dict[str, Any]] = []
        scenario_issues = list(structure_issues) + list(baseline_issues)
        base_revenue = Decimal("0")
        forward_revenue = Decimal("0")
        base_variable_cost = Decimal("0")
        forward_variable_cost = Decimal("0")
        base_contribution = Decimal("0")
        forward_contribution = Decimal("0")
        volume_effect_total = Decimal("0")
        asp_effect_total = Decimal("0")
        unit_cost_effect_total = Decimal("0")
        all_products_comparable = not structure_issues
        for product in product_lines:
            product_id = str(product.get("product_id") or "")
            historical = baseline_values.get(product_id, {})
            forward_row = rows_by_id.get(product_id, {})
            forward_inputs = forward_row.get("inputs") if isinstance(forward_row.get("inputs"), Mapping) else {}
            raw_forward_product_issues = forward_row.get("issues")
            relevant_forward_conflicts = [
                str(issue) for issue in raw_forward_product_issues
                if issue in {
                    "EXPLICIT_REVENUE_CONFLICTS_WITH_VOLUME_X_ASP",
                    "EXPLICIT_VARIABLE_COST_CONFLICTS_WITH_VOLUME_X_UNIT_COST",
                }
            ] if isinstance(raw_forward_product_issues, list) else []
            lineage_by_field: dict[str, Any] = {}
            forward_values: dict[str, Decimal | None] = {}
            for field in field_names:
                value, lineage = numeric_measure(
                    forward_inputs.get(field),
                    data_classes={"ISSUER_FORECAST", "ANALYST_ASSUMPTION"},
                )
                forward_values[field] = value
                lineage_by_field[field] = lineage or {
                    "data_class": "UNKNOWN",
                    "basis": "",
                    "evidence_refs": [],
                    "issues": ["MEASURE_NOT_USABLE"],
                }
                if value is None:
                    scenario_issues.append(f"{scenario_name}.{product_id}.{field}:FORWARD_MEASURE_NOT_USABLE")
            base_values = {field: historical.get(field) for field in field_names}
            baseline_conflicts = historical.get("explicit_bridge_conflicts") if isinstance(historical.get("explicit_bridge_conflicts"), list) else []
            product_conflicts = baseline_conflicts + relevant_forward_conflicts
            if (
                any(base_values[field] is None for field in field_names)
                or any(forward_values[field] is None for field in field_names)
                or product_conflicts
            ):
                all_products_comparable = False
                missing = [
                    field for field in field_names
                    if base_values[field] is None or forward_values[field] is None
                ]
                if product_conflicts:
                    scenario_issues.extend(
                        f"{scenario_name}.{product_id}:EXPLICIT_REVENUE_OR_COST_CONFLICT:{issue}"
                        for issue in product_conflicts
                    )
                product_results.append({
                    "product_id": product_id,
                    "product_name": str(product.get("product_name") or product_id),
                    "status": "NOT_IDENTIFIABLE",
                    "missing_or_unusable_fields": missing,
                    "explicit_bridge_conflicts": product_conflicts,
                    "baseline_issues": sorted(set(
                        issue for issue in baseline_issues if issue.startswith(f"{product_id}:")
                    )),
                    "historical_baseline": {
                        "period": actuals_period,
                        "measures": {field: historical.get("lineage", {}).get(field) for field in field_names},
                    },
                    "forward_scenario": {
                        "period": forecast_period,
                        "measures": lineage_by_field,
                    },
                    "issues": [f"{product_id}.{field}:BASELINE_OR_FORECAST_NOT_USABLE" for field in missing],
                })
                continue

            q0 = base_values["sales_volume_tonnes"]
            p0 = base_values["net_asp_cny_per_tonne"]
            c0 = base_values["variable_cost_cny_per_tonne"]
            q1 = forward_values["sales_volume_tonnes"]
            p1 = forward_values["net_asp_cny_per_tonne"]
            c1 = forward_values["variable_cost_cny_per_tonne"]
            # Symmetric Shapley decomposition: the three effects sum exactly to
            # Q1*(P1-C1) - Q0*(P0-C0), regardless of the order of driver changes.
            volume_effect = (q1 - q0) * ((p0 - c0 + p1 - c1) / Decimal("2"))
            asp_effect = (p1 - p0) * ((q0 + q1) / Decimal("2"))
            unit_cost_effect = -(c1 - c0) * ((q0 + q1) / Decimal("2"))
            baseline_revenue = q0 * p0
            forward_revenue_value = q1 * p1
            baseline_cost = q0 * c0
            forward_cost = q1 * c1
            baseline_contribution = baseline_revenue - baseline_cost
            forward_contribution_value = forward_revenue_value - forward_cost
            delta = forward_contribution_value - baseline_contribution
            attribution_sum = volume_effect + asp_effect + unit_cost_effect
            residual = delta - attribution_sum

            actual_bridge = product.get("historical_actual_bridge") if isinstance(product.get("historical_actual_bridge"), Mapping) else {}
            projected_production = forward_inputs.get("production_tonnes") if isinstance(forward_inputs.get("production_tonnes"), Mapping) else {}
            raw_historical_actuals = product.get("historical_actuals")
            historical_production = (
                raw_historical_actuals.get("production_tonnes")
                if isinstance(raw_historical_actuals, Mapping) else {}
            )
            inventory_details = {
                "historical_production_tonnes": historical_production.get("value") if isinstance(historical_production, Mapping) else None,
                "forward_production_tonnes": projected_production.get("value"),
                "historical_inventory_change_tonnes": actual_bridge.get("inventory_change_tonnes"),
                "forward_inventory_change_tonnes": forward_row.get("inventory_change_tonnes"),
                "note": "产量/库存变化单列展示，不纳入基于销售量、净售价与单位变动成本的贡献利润分解。",
            }
            status = "CALCULATED_AND_RECONCILED" if abs(residual) <= Decimal("1") else "RECONCILIATION_MISMATCH"
            if status != "CALCULATED_AND_RECONCILED":
                all_products_comparable = False
                scenario_issues.append(f"{scenario_name}.{product_id}:DRIVER_CONTRIBUTIONS_DO_NOT_RECONCILE_WITHIN_CNY_1")
            base_revenue += baseline_revenue
            forward_revenue += forward_revenue_value
            base_variable_cost += baseline_cost
            forward_variable_cost += forward_cost
            base_contribution += baseline_contribution
            forward_contribution += forward_contribution_value
            volume_effect_total += volume_effect
            asp_effect_total += asp_effect
            unit_cost_effect_total += unit_cost_effect
            product_results.append({
                "product_id": product_id,
                "product_name": str(product.get("product_name") or product_id),
                "status": status,
                "historical_baseline": {
                    "period": actuals_period,
                    "sales_volume_tonnes": _render(q0),
                    "net_asp_cny_per_tonne": _render(p0),
                    "variable_cost_cny_per_tonne": _render(c0),
                    "revenue_cny": _render(baseline_revenue),
                    "variable_cost_cny": _render(baseline_cost),
                    "contribution_after_variable_cost_cny": _render(baseline_contribution),
                    "measure_lineage": historical.get("lineage", {}),
                },
                "forward_scenario": {
                    "period": forecast_period,
                    "sales_volume_tonnes": _render(q1),
                    "net_asp_cny_per_tonne": _render(p1),
                    "variable_cost_cny_per_tonne": _render(c1),
                    "revenue_cny": _render(forward_revenue_value),
                    "variable_cost_cny": _render(forward_cost),
                    "contribution_after_variable_cost_cny": _render(forward_contribution_value),
                    "measure_lineage": lineage_by_field,
                },
                "changes": {
                    "sales_volume_tonnes": _render(q1 - q0),
                    "net_asp_cny_per_tonne": _render(p1 - p0),
                    "variable_cost_cny_per_tonne": _render(c1 - c0),
                    "revenue_cny": _render(forward_revenue_value - baseline_revenue),
                    "variable_cost_cny": _render(forward_cost - baseline_cost),
                    "contribution_after_variable_cost_cny": _render(delta),
                },
                "contribution_effects_cny": {
                    "sales_volume_effect": _render(volume_effect),
                    "net_asp_effect": _render(asp_effect),
                    "unit_variable_cost_effect": _render(unit_cost_effect),
                    "attribution_sum": _render(attribution_sum),
                    "reconciliation_residual": _render(residual),
                    "tolerance_cny": "1",
                },
                "production_inventory_context": inventory_details,
                "issues": [],
            })

        scenario_status = (
            "RECONCILIATION_MISMATCH"
            if any(row.get("status") == "RECONCILIATION_MISMATCH" for row in product_results)
            else "CALCULATED_AND_RECONCILED"
            if all_products_comparable and len(product_results) == len(ids)
            else "NOT_IDENTIFIABLE"
        )
        if scenario_status == "CALCULATED_AND_RECONCILED":
            residual_total = (forward_contribution - base_contribution) - (
                volume_effect_total + asp_effect_total + unit_cost_effect_total
            )
            scenario_results[scenario_name] = {
                "status": scenario_status,
                "baseline_revenue_cny": _render(base_revenue),
                "forward_revenue_cny": _render(forward_revenue),
                "change_revenue_cny": _render(forward_revenue - base_revenue),
                "baseline_variable_cost_cny": _render(base_variable_cost),
                "forward_variable_cost_cny": _render(forward_variable_cost),
                "change_variable_cost_cny": _render(forward_variable_cost - base_variable_cost),
                "baseline_contribution_after_variable_cost_cny": _render(base_contribution),
                "forward_contribution_after_variable_cost_cny": _render(forward_contribution),
                "change_contribution_after_variable_cost_cny": _render(forward_contribution - base_contribution),
                "sales_volume_effect_cny": _render(volume_effect_total),
                "net_asp_effect_cny": _render(asp_effect_total),
                "unit_variable_cost_effect_cny": _render(unit_cost_effect_total),
                "attribution_sum_cny": _render(volume_effect_total + asp_effect_total + unit_cost_effect_total),
                "reconciliation_residual_cny": _render(residual_total),
                "tolerance_cny": "1",
                "product_lines": product_results,
                "issues": [],
            }
        else:
            scenario_results[scenario_name] = {
                "status": scenario_status,
                "baseline_contribution_after_variable_cost_cny": None,
                "forward_contribution_after_variable_cost_cny": None,
                "change_contribution_after_variable_cost_cny": None,
                "sales_volume_effect_cny": None,
                "net_asp_effect_cny": None,
                "unit_variable_cost_effect_cny": None,
                "reconciliation_residual_cny": None,
                "product_lines": product_results,
                "issues": sorted(set(scenario_issues)),
            }

    statuses = [str(scenario_results[name].get("status") or "UNKNOWN") for name in SCENARIOS]
    if all(status == "CALCULATED_AND_RECONCILED" for status in statuses):
        overall = "DIAGNOSTIC_CALCULATED"
        reason = "三个情景均由同一历史产品基线映射到前瞻经营假设，销量/净售价/单位成本贡献分解在 CNY 1 内对账。"
    elif any(status == "RECONCILIATION_MISMATCH" for status in statuses):
        overall = "RECONCILIATION_MISMATCH"
        reason = "至少一个情景的驱动贡献未能在 CNY 1 容差内对账；不得使用该桥解释前瞻利润变化。"
    elif any(status == "CALCULATED_AND_RECONCILED" for status in statuses):
        overall = "PARTIAL"
        reason = "只有部分情景具备可比较输入；不完整情景保持 UNKNOWN，不能将部分结果误认为完整 Bear/Base/Bull 链。"
    else:
        overall = "NOT_IDENTIFIABLE"
        reason = "至少一个关键范围、期间、历史基线或前瞻经营变量不可识别；贡献变化保持 UNKNOWN。"
    return {
        **base,
        "status": overall,
        "reason": reason,
        "baseline_issues": sorted(set(baseline_issues)),
        "scenarios": scenario_results,
    }


def _build_baseline_net_profit_bridge(
    *,
    baseline_transition: Mapping[str, Any],
    historical_financials_raw: Any,
    scenarios_raw: Mapping[str, Any],
    forward_scenarios: Mapping[str, Any],
    sources_by_id: Mapping[str, Mapping[str, Any]],
    unresolved_refs: set[str],
    after_cutoff_refs: set[str],
    uncertain_refs: set[str],
) -> dict[str, Any]:
    """Extend B55 contribution deltas to a modeled, tax-adjusted net-profit proxy."""
    schema = "IIOS-B56-BASELINE-TO-FORWARD-NET-PROFIT-BRIDGE-0.1"
    base = {
        "schema_version": schema,
        "status": "NOT_IDENTIFIABLE",
        "baseline_period": baseline_transition.get("baseline_period", "UNKNOWN"),
        "forecast_period": baseline_transition.get("forecast_period", "UNKNOWN"),
        "method": "B55_CONTRIBUTION_MINUS_FIXED_OPEX_DA_FINANCE_AND_MODELED_TAX_V0.1",
        "metric": "MODELED_NET_PROFIT_PROXY_CNY_NOT_REPORTED_OR_PARENT_ATTRIBUTABLE_NET_PROFIT",
        "historical_baseline_inputs": {},
        "scenarios": {},
        "limitations": [
            "本桥必须逐情景依赖 B55 已对账的同一产品/业务线贡献变化；B55 未闭合时，不推导净利润变化。",
            "历史固定现金运营费用、折旧摊销、融资成本和有效税率必须分别作为 OBSERVED_ACTUAL 提供；前瞻值必须是有明确依据的 ISSUER_FORECAST 或 ANALYST_ASSUMPTION。",
            "模型税费代理=max(PBT,0)×有效税率；不模拟亏损抵税、递延税、税收优惠、非经常性税项或其他所得税调整。",
            "输出是模型化税后利润代理，不是财报报告净利润或归母净利润；非控股权益、稀释股数、EPS 和每股价值仍不在本桥中计算。",
            "该桥只用于解释假设间的算术变化，不构成正式 Forecast/Valuation Admission、投资决策或执行授权。",
        ],
        "formal_forecast_admission_created": False,
        "decision_authority": False,
        "eps_impact": None,
        "per_share_value_impact": None,
    }

    historical_inputs = _normalise_product_measure_set(
        historical_financials_raw,
        NET_PROFIT_BRIDGE_MEASURES,
        "historical_financials",
        sources_by_id,
        unresolved_refs,
        after_cutoff_refs,
        uncertain_refs,
        allowed_data_classes={"OBSERVED_ACTUAL"},
    )
    base["historical_baseline_inputs"] = historical_inputs
    transition_scenarios = (
        baseline_transition.get("scenarios")
        if isinstance(baseline_transition.get("scenarios"), Mapping) else {}
    )

    for scenario_name in SCENARIOS:
        transition_row = (
            transition_scenarios.get(scenario_name)
            if isinstance(transition_scenarios.get(scenario_name), Mapping) else {}
        )
        raw_forward = (
            scenarios_raw.get(scenario_name)
            if isinstance(scenarios_raw.get(scenario_name), Mapping) else {}
        )
        forward_inputs = _normalise_product_measure_set(
            raw_forward,
            NET_PROFIT_BRIDGE_MEASURES,
            f"B56.{scenario_name}",
            sources_by_id,
            unresolved_refs,
            after_cutoff_refs,
            uncertain_refs,
            allowed_data_classes={"ISSUER_FORECAST", "ANALYST_ASSUMPTION"},
        )
        normalized_forward_scenario = (
            forward_scenarios.get(scenario_name)
            if isinstance(forward_scenarios.get(scenario_name), Mapping) else {}
        )
        row: dict[str, Any] = {
            "scenario": scenario_name,
            "status": "NOT_IDENTIFIABLE",
            "historical_baseline": {},
            "forward_scenario": {},
            "changes": {},
            "missing_inputs": [],
            "issues": [],
            "formal_forecast_admission_created": False,
            "decision_authority": False,
            "eps_impact": None,
            "per_share_value_impact": None,
        }

        b55_status = str(transition_row.get("status") or "UNKNOWN")
        if b55_status != "CALCULATED_AND_RECONCILED":
            row["status"] = "BLOCKED_BY_B55"
            row["missing_inputs"] = ["B55_RECONCILED_CONTRIBUTION_BRIDGE"]
            row["issues"] = [f"B55_SCENARIO_STATUS:{b55_status}"]
            base["scenarios"][scenario_name] = row
            continue

        feasibility = str(normalized_forward_scenario.get("capacity_feasibility_status") or "UNKNOWN")
        if feasibility == "UNRESOLVED_OVER_NAMEPLATE_CAPACITY":
            row["status"] = "BLOCKED_BY_OPERATING_CONSTRAINT"
            row["missing_inputs"] = ["RESOLVED_ANNUAL_CAPACITY_CONSTRAINT"]
            row["issues"] = ["FORWARD_PRODUCTION_EXCEEDS_REGISTERED_NAMEPLATE_CAPACITY"]
            base["scenarios"][scenario_name] = row
            continue

        historical_values = {field: _value(measure) for field, measure in historical_inputs.items()}
        forward_values = {field: _value(measure) for field, measure in forward_inputs.items()}
        missing = [
            f"historical.{field}" for field, value in historical_values.items() if value is None
        ] + [
            f"forward.{field}" for field, value in forward_values.items() if value is None
        ]
        row["historical_baseline"] = {
            "period": base["baseline_period"],
            "contribution_after_variable_cost_cny": transition_row.get("baseline_contribution_after_variable_cost_cny"),
            "fixed_cash_opex_cny": _render(historical_values.get("fixed_cash_opex_cny")),
            "depreciation_amortization_cny": _render(historical_values.get("depreciation_amortization_cny")),
            "finance_cost_cny": _render(historical_values.get("finance_cost_cny")),
            "tax_rate": _render(historical_values.get("tax_rate")),
            "ebitda_proxy_cny": None,
            "ebit_proxy_cny": None,
            "profit_before_tax_proxy_cny": None,
            "modeled_tax_expense_proxy_cny": None,
            "net_profit_proxy_cny": None,
            "measure_lineage": historical_inputs,
        }
        row["forward_scenario"] = {
            "period": base["forecast_period"],
            "contribution_after_variable_cost_cny": transition_row.get("forward_contribution_after_variable_cost_cny"),
            "fixed_cash_opex_cny": _render(forward_values.get("fixed_cash_opex_cny")),
            "depreciation_amortization_cny": _render(forward_values.get("depreciation_amortization_cny")),
            "finance_cost_cny": _render(forward_values.get("finance_cost_cny")),
            "tax_rate": _render(forward_values.get("tax_rate")),
            "ebitda_proxy_cny": None,
            "ebit_proxy_cny": None,
            "profit_before_tax_proxy_cny": None,
            "modeled_tax_expense_proxy_cny": None,
            "net_profit_proxy_cny": None,
            "measure_lineage": forward_inputs,
        }
        input_issues = []
        for side, measures in (("historical", historical_inputs), ("forward", forward_inputs)):
            for field, measure in measures.items():
                for issue in measure.get("issues") or []:
                    input_issues.append(f"{side}.{field}:{issue}")
        row["missing_inputs"] = missing
        row["issues"] = sorted(set(input_issues))
        if missing:
            row["status"] = "NOT_IDENTIFIABLE"
            base["scenarios"][scenario_name] = row
            continue

        baseline_contribution = _decimal(
            transition_row.get("baseline_contribution_after_variable_cost_cny"),
            "B56_BASELINE_CONTRIBUTION",
        )
        forward_contribution = _decimal(
            transition_row.get("forward_contribution_after_variable_cost_cny"),
            "B56_FORWARD_CONTRIBUTION",
        )

        def calculate_period(contribution: Decimal, values: Mapping[str, Decimal]) -> dict[str, Decimal]:
            ebitda = contribution - values["fixed_cash_opex_cny"]
            ebit = ebitda - values["depreciation_amortization_cny"]
            pbt = ebit - values["finance_cost_cny"]
            modeled_tax = max(pbt, Decimal("0")) * values["tax_rate"]
            net_profit_proxy = pbt - modeled_tax
            return {
                "contribution_after_variable_cost_cny": contribution,
                "ebitda_proxy_cny": ebitda,
                "depreciation_amortization_cny": values["depreciation_amortization_cny"],
                "ebit_proxy_cny": ebit,
                "finance_cost_cny": values["finance_cost_cny"],
                "profit_before_tax_proxy_cny": pbt,
                "tax_rate": values["tax_rate"],
                "modeled_tax_expense_proxy_cny": modeled_tax,
                "net_profit_proxy_cny": net_profit_proxy,
            }

        historical_financial_values = {
            field: value for field, value in historical_values.items() if value is not None
        }
        forward_financial_values = {
            field: value for field, value in forward_values.items() if value is not None
        }
        historical_period = calculate_period(baseline_contribution, historical_financial_values)
        forward_period = calculate_period(forward_contribution, forward_financial_values)
        delta_contribution = forward_contribution - baseline_contribution
        fixed_effect = -(forward_values["fixed_cash_opex_cny"] - historical_values["fixed_cash_opex_cny"])
        depreciation_effect = -(
            forward_values["depreciation_amortization_cny"]
            - historical_values["depreciation_amortization_cny"]
        )
        finance_effect = -(forward_values["finance_cost_cny"] - historical_values["finance_cost_cny"])
        tax_effect = -(
            forward_period["modeled_tax_expense_proxy_cny"]
            - historical_period["modeled_tax_expense_proxy_cny"]
        )
        attribution_sum = delta_contribution + fixed_effect + depreciation_effect + finance_effect + tax_effect
        net_profit_change = forward_period["net_profit_proxy_cny"] - historical_period["net_profit_proxy_cny"]
        residual = net_profit_change - attribution_sum
        status = "CALCULATED_AND_RECONCILED" if abs(residual) <= Decimal("1") else "RECONCILIATION_MISMATCH"
        row.update({
            "status": status,
            "historical_baseline": {
                **{key: _render(value) for key, value in historical_period.items()},
                "period": base["baseline_period"],
                "fixed_cash_opex_cny": _render(historical_values["fixed_cash_opex_cny"]),
                "measure_lineage": historical_inputs,
            },
            "forward_scenario": {
                **{key: _render(value) for key, value in forward_period.items()},
                "period": base["forecast_period"],
                "fixed_cash_opex_cny": _render(forward_values["fixed_cash_opex_cny"]),
                "measure_lineage": forward_inputs,
            },
            "changes": {
                "contribution_after_variable_cost_cny": _render(delta_contribution),
                "fixed_cash_opex_effect_cny": _render(fixed_effect),
                "ebitda_proxy_cny": _render(forward_period["ebitda_proxy_cny"] - historical_period["ebitda_proxy_cny"]),
                "depreciation_amortization_effect_cny": _render(depreciation_effect),
                "ebit_proxy_cny": _render(forward_period["ebit_proxy_cny"] - historical_period["ebit_proxy_cny"]),
                "finance_cost_effect_cny": _render(finance_effect),
                "profit_before_tax_proxy_cny": _render(forward_period["profit_before_tax_proxy_cny"] - historical_period["profit_before_tax_proxy_cny"]),
                "modeled_tax_effect_cny": _render(tax_effect),
                "net_profit_proxy_cny": _render(net_profit_change),
                "attribution_sum_cny": _render(attribution_sum),
                "reconciliation_residual_cny": _render(residual),
                "tolerance_cny": "1",
            },
            "missing_inputs": [],
            "issues": [] if status == "CALCULATED_AND_RECONCILED" else ["NET_PROFIT_ATTRIBUTION_DOES_NOT_RECONCILE_WITHIN_CNY_1"],
        })
        base["scenarios"][scenario_name] = row

    statuses = [str(base["scenarios"][name].get("status") or "UNKNOWN") for name in SCENARIOS]
    if all(status == "CALCULATED_AND_RECONCILED" for status in statuses):
        base["status"] = "DIAGNOSTIC_CALCULATED"
        base["reason"] = "三个情景均基于 B55 已对账贡献和同期间历史/前瞻费用、折旧、融资成本与税率，模型税后利润变化在 CNY 1 内对账。"
    elif any(status in {"CALCULATED_AND_RECONCILED", "RECONCILIATION_MISMATCH"} for status in statuses):
        base["status"] = "PARTIAL"
        base["reason"] = "只有部分情景的完整历史与前瞻财务输入可用；其余情景保持 UNKNOWN/受阻，不能据此概括完整 Bear/Base/Bull 链。"
    elif all(status == "BLOCKED_BY_B55" for status in statuses):
        base["status"] = "BLOCKED_BY_B55"
        base["reason"] = "B55 的范围、期间或产品贡献桥未闭合，B56 不计算税后利润变化。"
    else:
        base["status"] = "NOT_IDENTIFIABLE"
        base["reason"] = "缺少同口径历史基线或明确的前瞻固定费用、折旧、融资成本或税率假设；税后利润变化保持 UNKNOWN。"
    return base


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
            "baseline_transition": {
                "schema_version": "IIOS-B55-BASELINE-TO-FORWARD-DRIVER-BRIDGE-0.1",
                "status": "NOT_PROVIDED",
                "scope": "UNKNOWN",
                "baseline_period": "UNKNOWN",
                "forecast_period": "UNKNOWN",
                "scenarios": {},
                "baseline_issues": [],
                "reason": "未提供 B4 经营驱动输入，无法连接当前历史基线与前瞻情景。",
                "net_profit_bridge": {
                    "schema_version": "IIOS-B56-BASELINE-TO-FORWARD-NET-PROFIT-BRIDGE-0.1",
                    "status": "NOT_PROVIDED",
                    "baseline_period": "UNKNOWN",
                    "forecast_period": "UNKNOWN",
                    "historical_baseline_inputs": {},
                    "scenarios": {},
                    "reason": "未提供 B4 输入，无法连接历史财务基线与前瞻税后利润。",
                    "formal_forecast_admission_created": False,
                    "decision_authority": False,
                    "eps_impact": None,
                    "per_share_value_impact": None,
                },
                "formal_forecast_admission_created": False,
                "decision_authority": False,
            },
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
            "baseline_transition": {
                "schema_version": "IIOS-B55-BASELINE-TO-FORWARD-DRIVER-BRIDGE-0.1",
                "status": "INVALID_SCHEMA",
                "scope": "UNKNOWN",
                "baseline_period": str(raw.get("actuals_period") or "UNKNOWN"),
                "forecast_period": str(raw.get("forecast_period") or "UNKNOWN"),
                "scenarios": {},
                "baseline_issues": ["OPERATING_DRIVER_SCHEMA_MISMATCH"],
                "reason": "B4 输入结构版本不兼容，无法可靠连接历史基线与前瞻情景。",
                "net_profit_bridge": {
                    "schema_version": "IIOS-B56-BASELINE-TO-FORWARD-NET-PROFIT-BRIDGE-0.1",
                    "status": "INVALID_SCHEMA",
                    "baseline_period": str(raw.get("actuals_period") or "UNKNOWN"),
                    "forecast_period": str(raw.get("forecast_period") or "UNKNOWN"),
                    "historical_baseline_inputs": {},
                    "scenarios": {},
                    "reason": "B4 输入结构无效，不能计算历史到前瞻税后利润桥。",
                    "formal_forecast_admission_created": False,
                    "decision_authority": False,
                    "eps_impact": None,
                    "per_share_value_impact": None,
                },
                "formal_forecast_admission_created": False,
                "decision_authority": False,
            },
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
        product_name = _normalise_product_name(row.get("product_name"))
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
                "revenue_cny": "CNY",
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
    baseline_transition = _build_baseline_transition_bridge(
        scope=scope,
        actuals_period=str(raw.get("actuals_period") or "UNKNOWN"),
        forecast_period=forecast_period,
        product_lines=product_lines,
        scenarios=scenarios,
    )
    baseline_transition["net_profit_bridge"] = _build_baseline_net_profit_bridge(
        baseline_transition=baseline_transition,
        historical_financials_raw=raw.get("historical_financials"),
        scenarios_raw=scenarios_raw,
        forward_scenarios=scenarios,
        sources_by_id=sources_by_id,
        unresolved_refs=unresolved_refs,
        after_cutoff_refs=after_cutoff_refs,
        uncertain_refs=uncertain_refs,
    )
    summary = str(raw.get("summary") or "已处理经营驱动输入；所有计算均为非正式试运行，不等同于已实现项目利润。")
    limits = raw.get("limitations")
    limits = [str(x).strip() for x in limits if str(x).strip()] if isinstance(limits, list) else []
    limits.extend([
        "发行人预测、年化产能释放计划与实际产销量不是同一概念；不得将计划数字写成已实现业绩。",
        "产量−销量的差额作为产品级库存变动处理；FCF 必须声明营运资金是否已包含库存，未闭合时保留 UNKNOWN，不把库存现金影响重复计算或漏算。",
        "库存现金影响使用产销差额×单位变动成本作为简化代理，不等同于完整财务报表存货计价（可能遗漏固定制造成本、在制品、损耗及产品结构差异）。",
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
        "baseline_transition": baseline_transition,
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
            ("revenue_cny", "已披露历史收入"),
        ):
            measure = actuals.get(key)
            data_class = measure.get("data_class", "UNKNOWN") if isinstance(measure, Mapping) else "UNKNOWN"
            refs = "、".join(measure.get("evidence_refs") or []) if isinstance(measure, Mapping) else ""
            suffix = f"；类别 {data_class}" + (f"；证据引用 {refs}" if refs else "")
            lines.append(f"  - {label}：{_display(measure)}{suffix}")
        bridge = product.get("historical_actual_bridge") if isinstance(product.get("historical_actual_bridge"), Mapping) else {}
        lines.append(
            f"  - 历史收入：{_display_optional_scalar(bridge.get('revenue_cny'))}；识别口径：{bridge.get('revenue_basis') or 'UNKNOWN'}；"
            f"销量×单位变动成本：{_display_optional_scalar(bridge.get('variable_cost_cny'))}。"
        )
        lines.append(
            f"  - 历史产销差额（产量−销量）：{_display_optional_scalar(bridge.get('inventory_change_tonnes'))} 吨；"
            f"库存现金影响代理：{_display_optional_scalar(bridge.get('inventory_cash_impact_proxy_cny'))} CNY（产销差额×单位变动成本，仅为代理）。"
        )
        if bridge.get("production_utilization") is not None:
            lines.append(f"  - 产能利用率（产量/年产能）：{Decimal(bridge['production_utilization']) * Decimal('100')}%（仅当期间与容量口径可比时成立）")
        for issue in bridge.get("issues") or []:
            lines.append(f"  - 口径复核项：{issue}")
    lines.extend(["", "#### B55 当前历史基线 → 前瞻经营变量变化桥", ""])
    transition = driver.get("baseline_transition") if isinstance(driver.get("baseline_transition"), Mapping) else {}
    transition_status = str(transition.get("status") or "UNKNOWN")
    lines.extend([
        f"- 状态：**{transition_status}**；范围：{transition.get('scope', 'UNKNOWN')}；"
        f"历史基线期间：{transition.get('baseline_period', 'UNKNOWN')}；前瞻期间：{transition.get('forecast_period', 'UNKNOWN')}",
        f"- 方法：{transition.get('comparison_method', 'UNKNOWN')}；指标：{transition.get('metric', 'UNKNOWN')}",
        f"- 结果说明：{transition.get('reason') or '未提供状态说明。'}",
    ])
    baseline_issues = transition.get("baseline_issues") if isinstance(transition.get("baseline_issues"), list) else []
    if baseline_issues:
        lines.append("- 历史基线待复核：" + "；".join(str(issue) for issue in baseline_issues[:8]))
        if len(baseline_issues) > 8:
            lines.append(f"  - 另有 {len(baseline_issues) - 8} 项结构化保留，未在摘要中展开。")
    transition_scenarios = transition.get("scenarios") if isinstance(transition.get("scenarios"), Mapping) else {}
    for scenario_name in SCENARIOS:
        row = transition_scenarios.get(scenario_name) if isinstance(transition_scenarios.get(scenario_name), Mapping) else {}
        lines.append(f"**B55 {scenario_name.upper()} — {row.get('status', 'UNKNOWN')}**")
        if row.get("status") == "CALCULATED_AND_RECONCILED":
            lines.extend([
                f"- 收入：历史 {row.get('baseline_revenue_cny')} → 前瞻 {row.get('forward_revenue_cny')}；变化 {row.get('change_revenue_cny')} CNY",
                f"- 变动成本：历史 {row.get('baseline_variable_cost_cny')} → 前瞻 {row.get('forward_variable_cost_cny')}；变化 {row.get('change_variable_cost_cny')} CNY",
                f"- 扣变动成本贡献：历史 {row.get('baseline_contribution_after_variable_cost_cny')} → 前瞻 {row.get('forward_contribution_after_variable_cost_cny')}；变化 {row.get('change_contribution_after_variable_cost_cny')} CNY",
                f"- 变化归因：销量 {row.get('sales_volume_effect_cny')} CNY；净售价 {row.get('net_asp_effect_cny')} CNY；单位变动成本 {row.get('unit_variable_cost_effect_cny')} CNY；对账残差 {row.get('reconciliation_residual_cny')} CNY（容差 {row.get('tolerance_cny')}）",
            ])
        product_rows = row.get("product_lines") if isinstance(row.get("product_lines"), list) else []
        if not product_rows:
            if row.get("issues"):
                lines.append("  - 未闭合：" + "；".join(str(issue) for issue in row.get("issues")[:8]))
            else:
                lines.append("  - 产品/业务线贡献变化：UNKNOWN（未形成可比较的产品级行）。")
        for product_row in product_rows[:8]:
            if not isinstance(product_row, Mapping):
                continue
            if product_row.get("status") != "CALCULATED_AND_RECONCILED":
                lines.append(
                    f"  - {product_row.get('product_name') or product_row.get('product_id') or 'UNKNOWN'}："
                    f"UNKNOWN；未闭合字段 {', '.join(product_row.get('missing_or_unusable_fields') or []) or '范围/映射/对账'}"
                )
                row_issues = product_row.get("issues") if isinstance(product_row.get("issues"), list) else []
                conflicts = product_row.get("explicit_bridge_conflicts") if isinstance(product_row.get("explicit_bridge_conflicts"), list) else []
                if conflicts:
                    lines.append("    显式收入/成本冲突：" + "；".join(str(issue) for issue in conflicts))
                if row_issues:
                    lines.append("    待复核：" + "；".join(str(issue) for issue in row_issues[:5]))
                historical_node = product_row.get("historical_baseline") if isinstance(product_row.get("historical_baseline"), Mapping) else {}
                forward_node = product_row.get("forward_scenario") if isinstance(product_row.get("forward_scenario"), Mapping) else {}
                historical_measures = historical_node.get("measures") if isinstance(historical_node.get("measures"), Mapping) else {}
                forward_measures = forward_node.get("measures") if isinstance(forward_node.get("measures"), Mapping) else {}
                failed_lineage = []
                for field, label in (
                    ("sales_volume_tonnes", "销量"),
                    ("net_asp_cny_per_tonne", "净售价"),
                    ("variable_cost_cny_per_tonne", "单位成本"),
                ):
                    hist = historical_measures.get(field) if isinstance(historical_measures.get(field), Mapping) else {}
                    fwd = forward_measures.get(field) if isinstance(forward_measures.get(field), Mapping) else {}
                    hist_refs = "、".join(hist.get("evidence_refs") or []) or "无显式引用"
                    fwd_refs = "、".join(fwd.get("evidence_refs") or []) or "无显式引用"
                    failed_lineage.append(
                        f"{label} {hist.get('data_class', 'UNKNOWN')}[{hist_refs}]→"
                        f"{fwd.get('data_class', 'UNKNOWN')}[{fwd_refs}]"
                    )
                if failed_lineage:
                    lines.append("    数据分类/来源引用（含未通过输入）：" + "；".join(failed_lineage))
                continue
            baseline = product_row.get("historical_baseline") if isinstance(product_row.get("historical_baseline"), Mapping) else {}
            forward = product_row.get("forward_scenario") if isinstance(product_row.get("forward_scenario"), Mapping) else {}
            changes = product_row.get("changes") if isinstance(product_row.get("changes"), Mapping) else {}
            effects = product_row.get("contribution_effects_cny") if isinstance(product_row.get("contribution_effects_cny"), Mapping) else {}
            lines.append(
                f"  - {product_row.get('product_name') or product_row.get('product_id')}："
                f"销量 {baseline.get('sales_volume_tonnes')}→{forward.get('sales_volume_tonnes')} 吨；"
                f"净售价 {baseline.get('net_asp_cny_per_tonne')}→{forward.get('net_asp_cny_per_tonne')} CNY/吨；"
                f"单位成本 {baseline.get('variable_cost_cny_per_tonne')}→{forward.get('variable_cost_cny_per_tonne')} CNY/吨"
            )
            lines.append(
                f"    贡献变化 {changes.get('contribution_after_variable_cost_cny')} CNY；"
                f"销量效应 {effects.get('sales_volume_effect')}；净售价效应 {effects.get('net_asp_effect')}；"
                f"单位成本效应 {effects.get('unit_variable_cost_effect')}；"
                f"归因残差 {effects.get('reconciliation_residual')}"
            )
            inventory = product_row.get("production_inventory_context") if isinstance(product_row.get("production_inventory_context"), Mapping) else {}
            lines.append(
                f"    独立库存上下文（不纳入贡献归因）：产量 "
                f"{inventory.get('historical_production_tonnes') or 'UNKNOWN'}→"
                f"{inventory.get('forward_production_tonnes') or 'UNKNOWN'} 吨；"
                f"产销差额 {inventory.get('historical_inventory_change_tonnes') or 'UNKNOWN'}→"
                f"{inventory.get('forward_inventory_change_tonnes') or 'UNKNOWN'} 吨"
            )
            lineage = []
            baseline_lineage = baseline.get("measure_lineage") if isinstance(baseline.get("measure_lineage"), Mapping) else {}
            forward_lineage = forward.get("measure_lineage") if isinstance(forward.get("measure_lineage"), Mapping) else {}
            for field, label in (
                ("sales_volume_tonnes", "销量"),
                ("net_asp_cny_per_tonne", "净售价"),
                ("variable_cost_cny_per_tonne", "单位成本"),
            ):
                b = baseline_lineage.get(field) if isinstance(baseline_lineage.get(field), Mapping) else {}
                fw = forward_lineage.get(field) if isinstance(forward_lineage.get(field), Mapping) else {}
                b_refs = "、".join(b.get("evidence_refs") or []) or "无显式引用"
                f_refs = "、".join(fw.get("evidence_refs") or []) or "无显式引用"
                lineage.append(
                    f"{label} {b.get('data_class', 'UNKNOWN')}[{b_refs}]→"
                    f"{fw.get('data_class', 'UNKNOWN')}[{f_refs}]"
                )
            lines.append("    数据分类/来源引用：" + "；".join(lineage))
        if len(product_rows) > 8:
            lines.append(f"  - 其余 {len(product_rows) - 8} 个产品/业务线未在此摘要展开，仍保留在结构化结果中。")
    lines.extend([
        "- 解释边界：该桥只解释产品/业务线“销量 ×（净售价−单位变动成本）”贡献变化，不是完整净利润/FCF 变动归因，更不直接进入 EPS、每股估值或 15% 回报计算。",
        "- 固定费用、折旧、融资成本、税、少数股东损益及稀释股数若缺少同期间历史基线与可比假设，必须单独研究；不能用本桥残差或贡献变化替代。",
        "- 产量及产销差额仅作为库存上下文展示，不计入上列贡献归因；库存/营运资金效果继续按 B42/B43 的明确口径处理，避免双重计价。",
        "",
    ])
    net_profit_bridge = (
        transition.get("net_profit_bridge")
        if isinstance(transition.get("net_profit_bridge"), Mapping) else {}
    )
    lines.extend([
        "",
        "#### B56 产品贡献 → 模型税后利润变化桥",
        "",
        f"- 状态：**{net_profit_bridge.get('status', 'UNKNOWN')}**；历史基线期间：{net_profit_bridge.get('baseline_period', 'UNKNOWN')}；前瞻期间：{net_profit_bridge.get('forecast_period', 'UNKNOWN')}",
        f"- 方法：{net_profit_bridge.get('method', 'UNKNOWN')}；指标：{net_profit_bridge.get('metric', 'UNKNOWN')}",
    ])
    historical_financial_inputs = (
        net_profit_bridge.get("historical_baseline_inputs")
        if isinstance(net_profit_bridge.get("historical_baseline_inputs"), Mapping) else {}
    )
    for field, label in (
        ("fixed_cash_opex_cny", "固定现金运营费用"),
        ("depreciation_amortization_cny", "折旧与摊销"),
        ("finance_cost_cny", "融资成本"),
        ("tax_rate", "有效税率"),
    ):
        measure = historical_financial_inputs.get(field) if isinstance(historical_financial_inputs.get(field), Mapping) else {}
        refs = "、".join(measure.get("evidence_refs") or []) or "无显式引用"
        lines.append(
            f"- 历史 {label}：{_display(measure)}；数据分类 {measure.get('data_class', 'UNKNOWN')}；依据 {measure.get('basis') or 'UNKNOWN'}；来源引用 {refs}"
        )
    net_profit_scenarios = net_profit_bridge.get("scenarios") if isinstance(net_profit_bridge.get("scenarios"), Mapping) else {}
    for scenario_name in SCENARIOS:
        row = net_profit_scenarios.get(scenario_name) if isinstance(net_profit_scenarios.get(scenario_name), Mapping) else {}
        historical = row.get("historical_baseline") if isinstance(row.get("historical_baseline"), Mapping) else {}
        forward = row.get("forward_scenario") if isinstance(row.get("forward_scenario"), Mapping) else {}
        changes = row.get("changes") if isinstance(row.get("changes"), Mapping) else {}
        lines.append(f"**B56 {scenario_name.upper()} — {row.get('status', 'UNKNOWN')}**")
        if row.get("status") == "CALCULATED_AND_RECONCILED":
            lines.extend([
                f"- 模型化税后利润代理：历史 {_display_optional_scalar(historical.get('net_profit_proxy_cny'))} → 前瞻 {_display_optional_scalar(forward.get('net_profit_proxy_cny'))} CNY；变化 {_display_optional_scalar(changes.get('net_profit_proxy_cny'))} CNY",
                f"- 中间桥：EBITDA {_display_optional_scalar(historical.get('ebitda_proxy_cny'))} → {_display_optional_scalar(forward.get('ebitda_proxy_cny'))}；EBIT {_display_optional_scalar(historical.get('ebit_proxy_cny'))} → {_display_optional_scalar(forward.get('ebit_proxy_cny'))}；税前利润 {_display_optional_scalar(historical.get('profit_before_tax_proxy_cny'))} → {_display_optional_scalar(forward.get('profit_before_tax_proxy_cny'))}",
                f"- 净利润变化归因：产品贡献 {_display_optional_scalar(changes.get('contribution_after_variable_cost_cny'))}；固定费用效应 {_display_optional_scalar(changes.get('fixed_cash_opex_effect_cny'))}；折旧效应 {_display_optional_scalar(changes.get('depreciation_amortization_effect_cny'))}；融资成本效应 {_display_optional_scalar(changes.get('finance_cost_effect_cny'))}；模型税费效应 {_display_optional_scalar(changes.get('modeled_tax_effect_cny'))} CNY",
                f"- 对账：归因合计 {_display_optional_scalar(changes.get('attribution_sum_cny'))}；残差 {_display_optional_scalar(changes.get('reconciliation_residual_cny'))} CNY（容差 {_display_optional_scalar(changes.get('tolerance_cny'))}）",
            ])
        if row.get("missing_inputs"):
            lines.append("- 保持 UNKNOWN / 阻塞输入：" + "、".join(str(x) for x in row["missing_inputs"]))
        if row.get("issues"):
            lines.append("- 来源/口径待复核：" + "；".join(str(x) for x in row["issues"][:8]))
    lines.extend([
        "- 模型边界：税费代理=max(税前利润,0)×有效税率，不模拟亏损抵税、递延税、税收优惠或非经常性税项；因此结果不是已报告净利润或归母净利润。",
        "- 尚未连接非控股权益与稀释股数，EPS / 每股价值影响仍为 UNKNOWN；B56 不修改估值输入、15% 年化收益门槛或现有决策状态，也不创建正式准入/交易授权。",
        "",
    ])
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
            f"- 成本率：{_display_optional_scalar(result.get('cost_of_revenue_ratio'))}；变动成本计算口径：{result.get('variable_cost_basis') or 'UNKNOWN'}",
            f"- EBITDA / EBIT / 税前利润 / 净利润：{_display_optional_scalar(result.get('ebitda_cny'))} / {_display_optional_scalar(result.get('ebit_cny'))} / {_display_optional_scalar(result.get('profit_before_tax_cny'))} / {_display_optional_scalar(result.get('net_profit_cny'))}",
            f"- 资本开支 / 声明营运资金变动 / 纳入 FCF 的有效营运资金变动 / 自由现金流代理：{_display_optional_scalar(result.get('cash_capex_cny'))} / {_display_optional_scalar(result.get('change_working_capital_cny'))} / {_display_optional_scalar(result.get('effective_change_working_capital_cny'))} / {_display_optional_scalar(result.get('unlevered_fcf_proxy_cny'))}",
            f"- 库存衔接：{result.get('inventory_reconciliation_status', 'UNKNOWN')}；处理口径：{result.get('inventory_working_capital_treatment', 'UNKNOWN')}；库存现金影响代理：{_display_optional_scalar(result.get('inventory_cash_impact_proxy_cny'))} CNY（产销差额×单位变动成本，非完整会计存货估值）。",
            f"- 产能可行性：{result.get('capacity_feasibility_status', 'UNKNOWN')}；财务结果可用于下游估值：{result.get('financial_outputs_decision_usable', False)}",
            f"- {valuation_label}：{scenario_terminal_display} {currency}",
        ])
        mix = result.get("revenue_mix") or []
        if mix:
            lines.append("  - 收入产品结构：" + "；".join(
                f"{row.get('product_name')} {Decimal(row['revenue_mix_ratio']) * Decimal('100')}%"
                for row in mix if row.get("revenue_mix_ratio") is not None
            ))
        if result.get("capacity_feasibility_status") == "UNRESOLVED_OVER_NAMEPLATE_CAPACITY":
            lines.append(
                "  - 产能约束未闭合：当前产量假设超过已登记的全年名义产能；净利润/FCF 已停止用于下游 B5 传导。"
                "仅供诊断的条件算术值（待产能/期间/范围核实）：净利润 "
                f"{_display_optional_scalar(result.get('diagnostic_net_profit_if_capacity_resolved_cny'))}；"
                f"FCF {_display_optional_scalar(result.get('diagnostic_unlevered_fcf_proxy_if_capacity_resolved_cny'))}。"
            )
        if result.get("missing_inputs"):
            lines.append("  - 尚缺：" + "、".join(result["missing_inputs"]))
        if result.get("issues"):
            lines.append("  - 口径/来源问题：" + "；".join(result["issues"]))
        if result.get("product_lines"):
            for product in result["product_lines"]:
                lines.append(
                    f"  - {product['product_name']}：产量 {_display(product['inputs'].get('production_tonnes'))}；"
                    f"销量 {_display(product['inputs'].get('sales_volume_tonnes'))}；"
                    f"产销差额（产量−销量）{_display_optional_scalar(product.get('inventory_change_tonnes'))} 吨；"
                    f"库存现金影响代理 {_display_optional_scalar(product.get('inventory_cash_impact_proxy_cny'))} CNY；"
                    f"净售价 {_display(product['inputs'].get('net_asp_cny_per_tonne'))}；"
                    f"单位变动成本 {_display(product['inputs'].get('variable_cost_cny_per_tonne'))}；"
                    f"产能利用率 {_display({'value': str(Decimal(product['production_utilization']) * Decimal('100')), 'unit': '%', 'calculation_usable': True}) if product.get('production_utilization') is not None else 'UNKNOWN'}。"
                )
        lines.append("")
    reconciliation = driver.get("valuation_reconciliation")
    if isinstance(reconciliation, Mapping):
        lines.extend([
            "",
            "#### B4 与主估值经营桥一致性复核",
            "",
            f"- 总体复核状态：{reconciliation.get('status', 'UNKNOWN')}",
        ])
        links = driver.get("cross_node_assumption_links")
        if isinstance(links, list) and links:
            linked_descriptions = [
                f"{item.get('scenario', 'UNKNOWN').upper()} {item.get('field', 'UNKNOWN')}={item.get('value', 'UNKNOWN')}（{item.get('source_assumption_id') or item.get('source_assumption_name') or '同一估值假设'}）"
                for item in links if isinstance(item, Mapping) and item.get("status") == "LINKED_SAME_SCENARIO_ASSUMPTION"
            ]
            if linked_descriptions:
                lines.append("- 跨节点共享假设：" + "；".join(linked_descriptions))
        scenario_checks = reconciliation.get("scenarios") if isinstance(reconciliation.get("scenarios"), Mapping) else {}
        for scenario_name in SCENARIOS:
            check_row = scenario_checks.get(scenario_name) if isinstance(scenario_checks.get(scenario_name), Mapping) else {}
            checks = check_row.get("checks") if isinstance(check_row.get("checks"), list) else []
            mismatches = [
                str(item.get("driver_field"))
                for item in checks if isinstance(item, Mapping) and item.get("status") == "MISMATCH"
            ]
            not_comparable = [
                str(item.get("driver_field"))
                for item in checks if isinstance(item, Mapping) and item.get("status") == "NOT_COMPARABLE"
            ]
            detail = []
            if mismatches:
                detail.append("不一致字段：" + "、".join(mismatches))
            if not_comparable:
                detail.append("未能比较字段：" + "、".join(not_comparable))
            lines.append(
                f"- {scenario_name.upper()}：{check_row.get('status', 'UNKNOWN')}"
                + (f"；{'；'.join(detail)}" if detail else "")
            )
        for excluded in reconciliation.get("excluded_metrics") or []:
            if isinstance(excluded, Mapping):
                lines.append(f"- 未作数值相等比较：{excluded.get('field', 'UNKNOWN')}；{excluded.get('reason', '')}")
    lines.extend([
        "- 解释：模型按销量×净售价计算产品收入；当业务是研发/测试等服务、实物吨位口径不可识别时，也可使用明确标记的直接业务线收入假设。变动成本优先按销量×单位成本计算；若该口径不可用，可复用同一估值情景中明确给出的营业成本率。再扣固定现金运营费用及折旧得到 EBITDA/EBIT，税前利润额外扣融资成本。自由现金流代理 = EBIT − 正 EBIT 对应现金税 + 折旧 − 资本开支 − 营运资金增加（营运资金释放可为负值）。",
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
