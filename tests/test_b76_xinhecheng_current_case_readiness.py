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
