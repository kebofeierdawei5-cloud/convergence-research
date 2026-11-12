from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = (
    ROOT / "examples" / "real_cases"
    / "RC-CN-A-002001-20261105_b76_readiness.json"
)


def _case() -> dict:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def test_xinhecheng_current_case_financial_statements_reconcile():
    case = _case()
    actuals = case["observed_actuals"]

    fy = actuals["2025FY"]
    assert Decimal(fy["consolidated_net_profit_cny"]) == (
        Decimal(fy["parent_attributable_net_profit_cny"])
        + Decimal(fy["minority_interest_net_profit_after_tax_cny"])
    )
    assert Decimal(fy["parent_attributable_net_profit_cny"]) - Decimal(
        fy["adjusted_parent_attributable_net_profit_cny"]
    ) == Decimal("26260750.26")

    q3 = actuals["2026Q1-Q3"]
    assert Decimal(q3["consolidated_net_profit_cny"]) == (
        Decimal(q3["parent_attributable_net_profit_cny"])
        + Decimal(q3["minority_interest_net_profit_after_tax_cny"])
    )
    assert Decimal(q3["parent_attributable_net_profit_cny"]) - Decimal(
        q3["adjusted_parent_attributable_net_profit_cny"]
    ) == Decimal(q3["non_recurring_profit_effect_after_tax_and_minority_cny"])
    assert q3["diluted_eps_cny_per_share_reported_2dp"] == "1.90"
    assert q3["weighted_average_diluted_shares_exact"] is None


def test_xinhecheng_2025_business_line_disclosures_sum_to_contract_totals():
    fy = _case()["observed_actuals"]["2025FY"]
    lines = fy["business_type_revenue_and_cost_of_revenue"]

    revenue = sum((Decimal(row["revenue_cny"]) for row in lines), Decimal("0"))
    cost = sum((Decimal(row["cost_of_revenue_cny"]) for row in lines), Decimal("0"))

    assert revenue == Decimal("22245192040.87")
    assert cost == Decimal("12310264243.06")
    assert revenue != Decimal(fy["revenue_cny"])  # other operating revenue is outside this table
    assert all(row["physical_sales_volume_tonnes"] is None for row in lines)
    assert all(row["blended_net_asp_cny_per_tonne"] is None for row in lines)
    assert all(row["variable_cost_cny_per_tonne"] is None for row in lines)


def test_xinhecheng_b76_readiness_does_not_promote_partial_disclosures_to_eps_or_headroom():
    readiness = _case()["b76_readiness"]

    assert readiness["B55"]["status"] == "BLOCKED_HISTORICAL_PHYSICAL_DRIVER_BASELINE_MISSING"
    assert readiness["B55"]["no_synthetic_substitution"] is True
    assert readiness["B56"]["status"] == "BLOCKED_BY_B55"
    assert readiness["B57"]["status"] == "BLOCKED_BY_B56"
    assert readiness["B57"]["reported_eps_is_not_forward_eps"] is True
    assert readiness["B58"]["status"] == "NOT_COMPARABLE_NO_VALID_FORWARD_B57_AND_PRIMARY_EPS_PAIR"
    assert readiness["B60"]["status"] == "BLOCKED_OPERATOR_ATTESTED_CURRENT_PRICE_MISSING"
    assert readiness["B60"]["current_price"] is None
    assert readiness["external_mie"]["status"] == "NOT_IDENTIFIABLE"
    assert readiness["formal_evidence_pit_admission_created"] is False
    assert readiness["formal_forecast_admission_created"] is False
    assert readiness["formal_valuation_admission_created"] is False
    assert readiness["decision_created"] is False
    assert readiness["execution_authorized"] is False



def test_xinhecheng_financial_statement_amount_bridge_reconciles_2025_and_2026_ytd():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    bridge = _build_financial_statement_amount_bridge(_case()["financial_statement_amount_bridge"])
    assert bridge["status"] == "ACTUALS_RECONCILED_FORECAST_NOT_PROVIDED"
    assert bridge["actual_period_status"] == "ALL_ACTUAL_PERIODS_RECONCILED"
    assert bridge["actual_periods"]["2025FY"]["status"] == "RECONCILED_REPORTED_ACTUAL"
    assert bridge["actual_periods"]["2026Q1-Q3"]["status"] == "RECONCILED_REPORTED_ACTUAL"
    for period in bridge["actual_periods"].values():
        assert max(abs(Decimal(value)) for value in period["reconciliation_residuals_cny"].values()) <= Decimal("1")
        assert period["source_admission_status"] == "SOURCE_REFERENCE_PRESENT_NOT_PIT_VALIDATED_NOT_FORMALLY_ADMITTED"
        assert period["source_reference_status"] == "SOURCE_ID_AND_PUBLICATION_DATE_PRESENT_ONLY"
        assert period["evidence_ids"] == []
        assert period["raw_bytes_verified"] is False
        assert period["pit_validation_performed"] is False
    assert bridge["forecast_status"] == "Q4_SCENARIOS_NOT_PROVIDED"
    assert bridge["formal_forecast_admission_created"] is False
    assert bridge["decision_authority"] is False


def test_xinhecheng_financial_statement_amount_bridge_fails_closed_when_reported_lines_are_missing():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    raw = _case()["financial_statement_amount_bridge"]
    raw["actual_periods"][0]["line_items"].pop("financial_expense")
    bridge = _build_financial_statement_amount_bridge(raw)
    row = bridge["actual_periods"]["2025FY"]
    assert row["status"] == "BLOCKED_REQUIRED_REPORTED_LINE_ITEMS_MISSING"
    assert "line_items.financial_expense" in row["missing_inputs"]
    assert bridge["actual_period_status"] == "PARTIAL_OR_BLOCKED"


def test_operating_driver_financial_statement_amount_bridge_does_not_upgrade_b55_or_b56():
    from iios_mvp.operating_driver_forecast_v01 import (
        OPERATING_DRIVER_SCHEMA,
        evaluate_operating_driver_forecast,
    )

    case = _case()
    raw = {
        "schema_version": OPERATING_DRIVER_SCHEMA,
        "scope": "COMPANY_WIDE",
        "actuals_period": "2025FY",
        "forecast_period": "2026FY",
        "summary": "Actual-only statement amount bridge test.",
        "product_lines": [],
        "historical_financials": {},
        "historical_earnings_attribution": {},
        "scenarios": {"bear": {}, "base": {}, "bull": {}},
        "financial_statement_amount_bridge": case["financial_statement_amount_bridge"],
    }
    result = evaluate_operating_driver_forecast(raw)
    assert result["financial_statement_amount_bridge"]["actual_period_status"] == "ALL_ACTUAL_PERIODS_RECONCILED"
    assert result["baseline_transition"]["status"] == "NOT_IDENTIFIABLE"
    assert result["baseline_transition"]["net_profit_bridge"]["status"] == "BLOCKED_BY_B55"
    assert result["valuation_transmission"]["status"] == "NOT_LINKED_TO_PER_SHARE_VALUE"



def test_q4_financial_statement_scenarios_require_typed_assumptions_and_annual_diluted_shares():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    raw = _case()["financial_statement_amount_bridge"]
    raw["q4_forecast"]["scenarios"] = {"bear": {"q4_line_items": {}}, "base": None, "bull": None}
    bridge = _build_financial_statement_amount_bridge(raw)
    row = bridge["forecast_scenarios"]["bear"]
    assert row["status"] == "BLOCKED_Q4_ASSUMPTIONS_INCOMPLETE"
    assert "q4_line_items.revenue" in row["missing_inputs"]
    assert "annual_weighted_average_diluted_shares" in row["missing_inputs"]
    assert bridge["forecast_status"] == "NOT_IDENTIFIABLE_OR_BLOCKED"


def test_q4_financial_statement_scenarios_calculate_conditional_eps_only_from_complete_analyst_assumptions():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    raw = _case()["financial_statement_amount_bridge"]
    q4_values = {
        "revenue": "6500000000",
        "cost_of_revenue": "3700000000",
        "taxes_and_surcharges": "80000000",
        "selling_expense": "45000000",
        "administrative_expense": "155000000",
        "rd_expense": "300000000",
        "financial_expense": "100000000",
        "other_income": "55000000",
        "investment_income": "30000000",
        "fair_value_change": "0",
        "credit_impairment_gain_loss": "-10000000",
        "asset_impairment_gain_loss": "-5000000",
        "asset_disposal_gain_loss": "1000000",
        "non_operating_income": "1000000",
        "non_operating_expense": "5000000",
        "income_tax_expense": "450000000",
        "minority_interest_net_profit_after_tax": "5000000",
    }
    def assumption(value, unit="CNY"):
        return {
            "value": value,
            "unit": unit,
            "data_class": "ANALYST_ASSUMPTION",
            "basis": "Synthetic test-only explicit Q4 scenario assumption.",
            "evidence_refs": [],
        }
    scenario = {
        "q4_line_items": {key: assumption(value) for key, value in q4_values.items()},
        "annual_weighted_average_diluted_shares": assumption("3073421680", "shares"),
    }
    raw["q4_forecast"]["scenarios"] = {"bear": scenario, "base": scenario, "bull": scenario}
    bridge = _build_financial_statement_amount_bridge(raw)
    assert bridge["forecast_status"] == "CONDITIONAL_ANALYST_SCENARIOS_CALCULATED"
    row = bridge["forecast_scenarios"]["base"]
    assert row["status"] == "CONDITIONAL_ANALYST_ASSUMPTION_CALCULATED"
    assert Decimal(row["q4_calculated_totals_cny"]["consolidated_net_profit"]) == Decimal("1737000000")
    expected_parent = Decimal("5867744277.98") + Decimal("1732000000")
    assert Decimal(row["fy_calculated_totals_cny"]["parent_attributable_net_profit"]) == expected_parent
    expected_eps = expected_parent / Decimal("3073421680")
    assert Decimal(row["conditional_fy_all_items_parent_attributable_eps_cny_per_share"]) == expected_eps
    assert row["annual_weighted_average_diluted_shares_data_class"] == "ANALYST_ASSUMPTION"
    assert row["q4_assumption_inputs"]["financial_expense"] == {
        "value": "100000000",
        "unit": "CNY",
        "data_class": "ANALYST_ASSUMPTION",
        "basis": "Synthetic test-only explicit Q4 scenario assumption.",
        "evidence_refs": [],
    }
    assert row["annual_weighted_average_diluted_shares_assumption"] == {
        "value": "3073421680",
        "unit": "shares",
        "data_class": "ANALYST_ASSUMPTION",
        "basis": "Synthetic test-only explicit Q4 scenario assumption.",
        "evidence_refs": [],
    }
    assert row["formal_forecast_admission_created"] is False
    assert row["decision_authority"] is False



def test_q4_financial_statement_scenarios_reject_cross_year_or_non_q1_q3_actual_periods():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    raw = _case()["financial_statement_amount_bridge"]
    scenario = {"q4_line_items": {}, "annual_weighted_average_diluted_shares": {}}
    raw["q4_forecast"]["scenarios"] = {"bear": scenario, "base": scenario, "bull": scenario}
    raw["q4_forecast"]["actual_period"] = "2025FY"
    raw["q4_forecast"]["forecast_period"] = "2026FY"
    bridge = _build_financial_statement_amount_bridge(raw)
    assert bridge["forecast_status"] == "BLOCKED_PERIOD_ALIGNMENT"
    assert bridge["forecast_scenarios"] == {}


def test_q4_financial_statement_scenarios_require_exact_bear_base_bull_set():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    raw = _case()["financial_statement_amount_bridge"]
    raw["q4_forecast"]["scenarios"] = {"bear": {}, "base": {}}
    bridge = _build_financial_statement_amount_bridge(raw)
    assert bridge["forecast_status"] == "BLOCKED_SCENARIO_SET_INCOMPLETE_OR_INVALID"
    assert bridge["forecast_scenarios"] == {}



def test_xinhecheng_q4_input_template_is_complete_in_shape_but_numerically_blocked():
    template_path = ROOT / "examples" / "real_cases" / "RC-CN-A-002001-20261105_q4_scenario_template.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    assert set(template["scenarios"]) == {"bear", "base", "bull"}
    for scenario in template["scenarios"].values():
        assert len(scenario["q4_line_items"]) == 17
        assert all(row["value"] is None for row in scenario["q4_line_items"].values())
        assert scenario["annual_weighted_average_diluted_shares"]["value"] is None

    raw = _case()["financial_statement_amount_bridge"]
    raw["q4_forecast"]["scenarios"] = template["scenarios"]
    bridge = _build_financial_statement_amount_bridge(raw)
    assert bridge["forecast_status"] == "NOT_IDENTIFIABLE_OR_BLOCKED"
    assert all(
        row["status"] == "BLOCKED_Q4_ASSUMPTIONS_INCOMPLETE"
        for row in bridge["forecast_scenarios"].values()
    )
    assert all(
        row["conditional_fy_all_items_parent_attributable_eps_cny_per_share"] is None
        for row in bridge["forecast_scenarios"].values()
    )



def _complete_q4_statement_amount_scenario_fixture():
    from iios_mvp.operating_driver_forecast_v01 import _build_financial_statement_amount_bridge

    raw = _case()["financial_statement_amount_bridge"]
    q4_values = {
        "revenue": "6500000000",
        "cost_of_revenue": "3700000000",
        "taxes_and_surcharges": "80000000",
        "selling_expense": "45000000",
        "administrative_expense": "155000000",
        "rd_expense": "300000000",
        "financial_expense": "100000000",
        "other_income": "55000000",
        "investment_income": "30000000",
        "fair_value_change": "0",
        "credit_impairment_gain_loss": "-10000000",
        "asset_impairment_gain_loss": "-5000000",
        "asset_disposal_gain_loss": "1000000",
        "non_operating_income": "1000000",
        "non_operating_expense": "5000000",
        "income_tax_expense": "450000000",
        "minority_interest_net_profit_after_tax": "5000000",
    }

    def assumption(value, unit="CNY"):
        return {
            "value": value,
            "unit": unit,
            "data_class": "ANALYST_ASSUMPTION",
            "basis": "Synthetic test-only explicit Q4 statement amount assumption.",
            "evidence_refs": [],
        }

    scenario = {
        "q4_line_items": {key: assumption(value) for key, value in q4_values.items()},
        "annual_weighted_average_diluted_shares": assumption("3073421680", "shares"),
    }
    raw["q4_forecast"]["scenarios"] = {
        "bear": scenario, "base": scenario, "bull": scenario
    }
    return raw


def test_b57_accepts_forward_all_items_eps_from_statement_amount_bridge_without_upgrading_b55_b56():
    from iios_mvp.operating_driver_forecast_v01 import (
        OPERATING_DRIVER_SCHEMA,
        evaluate_operating_driver_forecast,
    )

    raw = {
        "schema_version": OPERATING_DRIVER_SCHEMA,
        "scope": "COMPANY_WIDE",
        "actuals_period": "2025FY",
        "forecast_period": "2026FY",
        "summary": "B77 synthetic B57 forward-only EPS integration test.",
        "product_lines": [],
        "historical_financials": {},
        "historical_earnings_attribution": {},
        "scenarios": {"bear": {}, "base": {}, "bull": {}},
        "financial_statement_amount_bridge": _complete_q4_statement_amount_scenario_fixture(),
    }
    result = evaluate_operating_driver_forecast(raw)
    transition = result["baseline_transition"]
    b57 = transition["per_share_earnings_bridge"]
    assert transition["status"] == "NOT_IDENTIFIABLE"
    assert transition["net_profit_bridge"]["scenarios"]["base"]["status"] == "BLOCKED_BY_B55"
    assert b57["status"] == "PARTIAL"
    for name in ("bear", "base", "bull"):
        row = b57["scenarios"][name]
        assert row["status"] == "FORWARD_ALL_ITEMS_EPS_CALCULATED_HISTORICAL_NORMALIZATION_NOT_IDENTIFIABLE"
        assert row["forward_scenario"]["data_class"] == "ANALYST_ASSUMPTION"
        assert row["forward_scenario"]["source_data_classes"] == ["ANALYST_ASSUMPTION", "OBSERVED_ACTUAL"]
        assert row["forward_scenario"]["combined_output_data_class"] == "MIXED_OBSERVED_ACTUAL_AND_ANALYST_ASSUMPTION"
        assert row["forward_scenario"]["provenance_components"]["reported_actual_periods"]["data_class"] == "OBSERVED_ACTUAL"
        assert row["forward_scenario"]["provenance_components"]["q4_forecast_line_items"]["data_class"] == "ANALYST_ASSUMPTION"
        lineage = row["forward_scenario"]["source_lineage_assessment"]
        assert lineage["status"] == "REPORTED_ACTUAL_SOURCE_REFERENCES_PRESENT_NOT_PIT_VALIDATED_PLUS_ANALYST_ASSUMPTIONS"
        assert lineage["formal_evidence_pit_admission_status"] == "NOT_FORMALLY_ADMITTED"
        assert lineage["formal_forecast_admission_status"] == "NOT_CREATED_BY_LOCAL_PILOT"
        assert lineage["pit_validation_performed"] is False
        assert lineage["raw_bytes_verified"] is False
        assert lineage["decision_grade_forecast_eligible"] is False
        assert lineage["claimed_evidence_refs"] == []
        assert row["forward_scenario"]["normalized_diluted_eps_proxy_cny_per_share"] is None
        assert Decimal(row["forward_scenario"]["all_items_diluted_eps_proxy_cny_per_share"]) > 0
        assert row["formal_forecast_admission_created"] is False
    assert result["valuation_transmission"]["status"] == "NOT_LINKED_TO_PER_SHARE_VALUE"
    assert result["formal_forecast_admission_created"] is False
    assert result["decision_authority"] is False
    assert all(row["formal_evidence_pit_admission_created"] is False for row in b57["scenarios"].values())
    assert all(row["formal_forecast_admission_created"] is False for row in b57["scenarios"].values())
    assert all(row["decision_grade_forecast_eligible"] is False for row in b57["scenarios"].values())


def test_b58_can_compare_statement_amount_b57_forward_eps_to_primary_eps_assumption_without_claiming_match():
    from iios_mvp.operating_driver_forecast_v01 import (
        OPERATING_DRIVER_SCHEMA,
        evaluate_operating_driver_forecast,
    )
    from iios_mvp.local_investment_pilot_v01 import _build_b58_primary_eps_consistency

    raw = {
        "schema_version": OPERATING_DRIVER_SCHEMA,
        "scope": "COMPANY_WIDE",
        "actuals_period": "2026Q1-Q3",
        "forecast_period": "2026FY",
        "summary": "B77 synthetic B58 assumption-only comparison test.",
        "product_lines": [],
        "historical_financials": {},
        "historical_earnings_attribution": {},
        "scenarios": {"bear": {}, "base": {}, "bull": {}},
        "financial_statement_amount_bridge": _complete_q4_statement_amount_scenario_fixture(),
    }
    operating = evaluate_operating_driver_forecast(raw)
    b57_rows = operating["baseline_transition"]["per_share_earnings_bridge"]["scenarios"]
    declared_eps = b57_rows["base"]["forward_scenario"]["all_items_diluted_eps_proxy_cny_per_share"]
    eps_bridge = {
        "status": "ASSUMPTION_ONLY",
        "forecast_period": "2026FY",
        "valuation_terminal_date": "2026-12-31",
        "scenarios": {
            name: {
                "status": "ASSUMPTION_ONLY",
                "declared_eps_per_share": declared_eps,
                "calculated_eps_per_share": None,
                "diluted_shares": None,
                "other_after_tax_attribution_adjustment": None,
            }
            for name in ("bear", "base", "bull")
        },
    }
    eps_valuation = {
        "status": "CALCULATED",
        "selected_for_primary_model": True,
        "forecast_period": "2026FY",
        "valuation_terminal_date": "2026-12-31",
        "scenarios": {
            name: {"eps_per_share": {"value": declared_eps}}
            for name in ("bear", "base", "bull")
        },
    }
    result = _build_b58_primary_eps_consistency(
        selected_model_family="EPS_MULTIPLE",
        expected_currency="CNY",
        operating_driver_forecast=operating,
        eps_earnings_bridge=eps_bridge,
        eps_multiple_valuation=eps_valuation,
    )
    assert result["status"] == "ASSUMPTION_ONLY"
    assert all(
        row["status"] == "PRIMARY_EPS_ASSUMPTION_ONLY"
        for row in result["scenarios"].values()
    )
    assert all(row["eps_match"] is None for row in result["scenarios"].values())
    assert all(row["numeric_similarity_to_primary_declared_eps"] is True for row in result["scenarios"].values())
    assert all(row["independent_confirmation_status"] == "NOT_ESTABLISHED_PRIMARY_EPS_ASSUMPTION_ONLY" for row in result["scenarios"].values())
    assert all(
        row["b57_source_lineage_assessment"]["status"]
        == "REPORTED_ACTUAL_SOURCE_REFERENCES_PRESENT_NOT_PIT_VALIDATED_PLUS_ANALYST_ASSUMPTIONS"
        for row in result["scenarios"].values()
    )
    assert all(row["formal_evidence_pit_admission_created"] is False for row in result["scenarios"].values())
    assert all(row["formal_forecast_admission_created"] is False for row in result["scenarios"].values())
    assert all(row["decision_grade_forecast_eligible"] is False for row in result["scenarios"].values())
