from decimal import Decimal
import pytest

from iios_mvp.market_expectation import (
    identify_market_model,
    compute_probability_payoff,
    compute_position_size,
)


def test_market_model_identification_returns_feasible_solution_set():
    result = identify_market_model(
        {"current_price": 100, "shares_outstanding": 10,
         "market_model_inputs": {
             "forward_pe": {"profit_low": 90, "profit_high": 110},
             "ps": {"revenue_low": 500, "revenue_high": 700},
         }},
        {},
        {},
    )
    assert result["status"] == "PASS"
    assert len(result["market_model_set"]) == 2
    assert result["identifiability"]["status"] == "AMBIGUOUS"


def test_market_model_is_identifiable_when_only_one_model_is_feasible():
    result = identify_market_model(
        {"current_price": 100, "shares_outstanding": 10,
         "market_model_inputs": {
             "forward_pe": {"profit_low": 90, "profit_high": 110},
         }},
        {},
        {},
    )
    assert result["identifiability"]["status"] == "IDENTIFIABLE"
    assert result["market_model_set"][0]["model"] == "forward_pe"


def test_probability_payoff_requires_exact_probability_sum_and_returns_edge():
    result = compute_probability_payoff(
        {"bear": {"probability": .2, "value": 70},
         "base": {"probability": .5, "value": 110},
         "bull": {"probability": .3, "value": 150}},
        Decimal("100"),
    )
    assert result["win_probability"] == .8
    assert result["payoff_ratio"] > 1
    assert result["expected_return"] > 0
    assert result["edge"] > 0
    with pytest.raises(ValueError):
        compute_probability_payoff(
            {"bear": {"probability": .2, "value": 70},
             "base": {"probability": .5, "value": 110},
             "bull": {"probability": .2, "value": 150}},
            Decimal("100"),
        )


def test_position_size_is_capped_by_portfolio_and_risk_budget():
    result = compute_position_size(
        Decimal(".5"), Decimal(".8"), Decimal("2"),
        {"position_pct": 0, "max_position_pct": 15},
        {"position_risk_budget_pct": 5},
    )
    assert result["recommended_additional_position_pct"] <= 5
    assert result["recommended_total_position_pct"] <= 15


def test_market_model_identification_fails_closed_without_feasible_model():
    result = identify_market_model(
        {"current_price": 100, "shares_outstanding": 10,
         "market_model_inputs": {"forward_pe": {"profit_low": 0, "profit_high": 0}}},
        {}, {},
    )
    assert result["status"] == "BLOCKED"
    assert result["identifiability"]["status"] == "UNIDENTIFIABLE"
