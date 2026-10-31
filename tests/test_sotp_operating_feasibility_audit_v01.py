from __future__ import annotations

from iios_mvp.sotp_operating_feasibility_audit_v01 import build_sotp_operating_feasibility_audit


def _product(required_sales="130", production="95", inventory_change="-5"):
    return {
        "product_id": "P1",
        "product_name": "Product 1",
        "status": "CALCULATED_CONDITIONAL",
        "current_forward_assumptions": {
            "sales_volume_tonnes": "100",
            "net_asp_cny_per_tonne": "20",
            "variable_cost_cny_per_tonne": "10",
        },
        "single_driver_alternatives": {
            "sales_volume_only": {
                "status": "CALCULATED_CONDITIONAL",
                "required_sales_volume_tonnes": required_sales,
                "change_pct": "30",
            },
            "net_asp_only": {
                "status": "CALCULATED_CONDITIONAL",
                "required_net_asp_cny_per_tonne": "22",
                "change_pct": "10",
            },
            "unit_variable_cost_only": {
                "status": "CALCULATED_CONDITIONAL",
                "required_variable_cost_cny_per_tonne": "8",
                "change_pct": "-20",
            },
        },
        "production_inventory_context": {
            "forward_production_tonnes": production,
            "forward_inventory_change_tonnes": inventory_change,
            "nameplate_capacity_tonnes_per_year": "120",
        },
    }


def _fixtures(required_sales="130", production="95", inventory_change="-5"):
    product = _product(required_sales, production, inventory_change)
    lens = {
        "required_parent_attributable_profit_cny": "500",
        "reverse_engineering": {
            "status": "PARTIAL",
            "product_driver_alternatives": [product],
        },
    }
    return {
        "operating_driver_forecast": {
            "forecast_period": "FY2027",
            "product_lines": [{
                "product_id": "P1",
                "business_segment_id": "SEG_A",
                "capacity_tonnes_per_year": {
                    "value": "120",
                    "data_class": "OBSERVED_ACTUAL",
                    "basis": "Installed nameplate capacity",
                    "evidence_refs": ["CAPACITY-1"],
                    "issues": [],
                },
            }],
            "scenarios": {
                "base": {
                    "product_lines": [{
                        "product_id": "P1",
                        "production_tonnes": production,
                        "sales_volume_tonnes": "100",
                        "inventory_change_tonnes": inventory_change,
                        "production_sales_balance_status": "CALCULATED",
                    }],
                    "inventory_reconciliation_status": "INVENTORY_MOVEMENT_INCLUDED_IN_TOTAL_WORKING_CAPITAL",
                    "inventory_working_capital_treatment": "INCLUDED_IN_CHANGE_WORKING_CAPITAL",
                    "effective_change_working_capital_cny": "10",
                    "cash_capex_cny": "20",
                    "unlevered_fcf_proxy_cny": "80",
                    "financial_outputs_decision_usable": True,
                }
            },
        },
        "operating_requirement_reverse_engineering": {
            "schema_version": "IIOS-SOTP-OPERATING-REQUIREMENT-REVERSE-ENGINEERING-0.1",
            "scenarios": {
                "base": {
                    "segments": [{
                        "segment_id": "SEG_A",
                        "b61_required_profit_lens": lens,
                        "b63_full_b4_vector_lens": {
                            **lens,
                            "required_parent_attributable_profit_cny": "600",
                            "reverse_engineering": {
                                "status": "PARTIAL",
                                "product_driver_alternatives": [_product("110", production, inventory_change)],
                            },
                        },
                    }]
                }
            },
        },
    }


def _run(data):
    return build_sotp_operating_feasibility_audit(**data)


def _base_product(result, lens="B61_SINGLE_SEGMENT_THRESHOLD"):
    rows = result["scenarios"]["base"]["requirement_lenses"]
    row = next(item for item in rows if item["lens"] == lens)
    return row["products"][0]


def test_b69_flags_required_production_above_nameplate_capacity():
    result = _run(_fixtures())
    product = _base_product(result)
    assert product["required_production_tonnes_under_unchanged_inventory_movement"] == "125"
    assert product["capacity_status"] == "EXCEEDS_NAMEPLATE_CAPACITY"
    assert result["scenarios"]["base"]["status"] == "CAPACITY_CONSTRAINT_IDENTIFIED"


def test_b69_capacity_is_only_conditional_when_required_production_fits():
    result = _run(_fixtures(required_sales="110"))
    product = _base_product(result)
    assert product["required_production_tonnes_under_unchanged_inventory_movement"] == "105"
    assert product["capacity_status"] == "WITHIN_NAMEPLATE_CAPACITY_CONDITIONAL"


def test_b69_does_not_infer_production_when_inventory_movement_is_unknown():
    result = _run(_fixtures(production=None, inventory_change=None))
    product = _base_product(result)
    assert product["required_production_tonnes_under_unchanged_inventory_movement"] is None
    assert product["capacity_status"] == "NOT_IDENTIFIABLE_INVENTORY_POLICY"


def test_b69_requires_full_year_period_for_annual_capacity_comparison():
    data = _fixtures()
    data["operating_driver_forecast"]["forecast_period"] = "2027H1"
    result = _run(data)
    product = _base_product(result)
    assert product["capacity_status"] == "NOT_IDENTIFIABLE_PERIOD_NOT_FULL_YEAR"


def test_b69_missing_capacity_remains_not_identifiable():
    data = _fixtures()
    data["operating_driver_forecast"]["product_lines"][0]["capacity_tonnes_per_year"] = None
    result = _run(data)
    product = _base_product(result)
    assert product["capacity_status"] == "NOT_IDENTIFIABLE_NAMEPLATE_CAPACITY"


def test_b69_demand_price_elasticity_and_cost_curve_are_never_inferred():
    result = _run(_fixtures())
    product = _base_product(result)
    assert product["demand_feasibility_status"].startswith("NOT_IDENTIFIABLE")
    assert product["pricing_feasibility_status"].startswith("NOT_IDENTIFIABLE")
    assert product["unit_cost_feasibility_status"].startswith("NOT_IDENTIFIABLE")
    assert product["incremental_capex_and_working_capital_status"].startswith("NOT_IDENTIFIABLE")


def test_b69_keeps_b61_and_b63_requirement_lenses_separate():
    result = _run(_fixtures())
    rows = result["scenarios"]["base"]["requirement_lenses"]
    assert [row["lens"] for row in rows] == [
        "B61_SINGLE_SEGMENT_THRESHOLD",
        "B63_FULL_B4_VECTOR_THRESHOLD",
    ]
    assert all(row["non_additive"] is True for row in rows)
    assert rows[0]["required_parent_attributable_profit_cny"] == "500"
    assert rows[1]["required_parent_attributable_profit_cny"] == "600"


def test_b69_rechecks_production_sales_inventory_balance():
    data = _fixtures()
    data["operating_driver_forecast"]["scenarios"]["base"]["product_lines"][0]["inventory_change_tonnes"] = "0"
    result = _run(data)
    product = _base_product(result)
    assert product["capacity_status"] == "NOT_IDENTIFIABLE_INVENTORY_POLICY"
    assert "B69_B4_B68_PRODUCTION_SALES_BALANCE_MISMATCH" in product["issues"]


def test_b69_preserves_b4_cash_capex_and_effective_working_capital_without_recalculating_fcf():
    result = _run(_fixtures())
    plan = result["scenarios"]["base"]["b4_existing_financial_plan"]
    assert plan["effective_change_working_capital_cny"] == "10"
    assert plan["cash_capex_cny"] == "20"
    assert plan["unlevered_fcf_proxy_cny"] == "80"
    assert result["b4_inputs_modified"] is False
    assert result["formal_forecast_admission_created"] is False
    assert result["decision_authority"] is False
