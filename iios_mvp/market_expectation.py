from __future__ import annotations

from decimal import Decimal
from typing import Any


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


def _q(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.0001")))


def _grid(low: Decimal, high: Decimal, steps: int = 9) -> list[Decimal]:
    if steps < 2 or high < low:
        raise ValueError("invalid market expectation grid")
    if high == low:
        return [low]
    step = (high - low) / Decimal(steps - 1)
    return [low + step * i for i in range(steps)]


def _solve_pe(price: Decimal, shares: Decimal, profit_low: Decimal, profit_high: Decimal) -> dict[str, Any]:
    market_cap = price * shares
    return {
        "model": "forward_pe",
        "feasible": profit_low > 0 and profit_high >= profit_low,
        "implied_net_profit_range": [_q(profit_low), _q(profit_high)],
        "implied_multiple_range": [_q(market_cap / profit_high), _q(market_cap / profit_low)],
    }


def _solve_ps(price: Decimal, shares: Decimal, revenue_low: Decimal, revenue_high: Decimal) -> dict[str, Any]:
    market_cap = price * shares
    return {
        "model": "ps",
        "feasible": revenue_low > 0 and revenue_high >= revenue_low,
        "implied_revenue_range": [_q(revenue_low), _q(revenue_high)],
        "implied_multiple_range": [_q(market_cap / revenue_high), _q(market_cap / revenue_low)],
    }


def _solve_pb(price: Decimal, shares: Decimal, equity_low: Decimal, equity_high: Decimal) -> dict[str, Any]:
    market_cap = price * shares
    return {
        "model": "pb",
        "feasible": equity_low > 0 and equity_high >= equity_low,
        "implied_book_equity_range": [_q(equity_low), _q(equity_high)],
        "implied_multiple_range": [_q(market_cap / equity_high), _q(market_cap / equity_low)],
    }


def _solve_ev_ebitda(price: Decimal, shares: Decimal, ebitda_low: Decimal, ebitda_high: Decimal, net_debt: Decimal) -> dict[str, Any]:
    market_cap = price * shares
    ev = market_cap + net_debt
    return {
        "model": "ev_ebitda",
        "feasible": ebitda_low > 0 and ebitda_high >= ebitda_low,
        "implied_ebitda_range": [_q(ebitda_low), _q(ebitda_high)],
        "implied_multiple_range": [_q(ev / ebitda_high), _q(ev / ebitda_low)],
    }


def identify_market_model(valuation: dict[str, Any], forecast: dict[str, Any], intrinsic: dict[str, Any]) -> dict[str, Any]:
    """
    Batch-2 MVP: infer feasible market valuation models from independently supplied
    operating ranges. This deliberately returns a solution set, not a forced winner.
    """
    price = _d(valuation["current_price"])
    shares = _d(valuation["shares_outstanding"])
    inputs = valuation.get("market_model_inputs") or {}
    candidates: list[dict[str, Any]] = []

    p = inputs.get("forward_pe")
    if p:
        candidates.append(_solve_pe(price, shares, _d(p["profit_low"]), _d(p["profit_high"])))
    p = inputs.get("ps")
    if p:
        candidates.append(_solve_ps(price, shares, _d(p["revenue_low"]), _d(p["revenue_high"])))
    p = inputs.get("pb")
    if p:
        candidates.append(_solve_pb(price, shares, _d(p["equity_low"]), _d(p["equity_high"])))
    p = inputs.get("ev_ebitda")
    if p:
        candidates.append(_solve_ev_ebitda(price, shares, _d(p["ebitda_low"]), _d(p["ebitda_high"]), _d(p.get("net_debt", 0))))

    feasible = [x for x in candidates if x["feasible"]]
    if not feasible:
        status = "BLOCKED"
        blockers = ["NO_FEASIBLE_MARKET_MODEL"]
    else:
        status = "PASS"
        blockers = []

    # Identifiability is intentionally conservative: one feasible model, or one model
    # materially narrower than alternatives. With no comparative evidence, return AMBIGUOUS.
    if len(feasible) == 1:
        ident = "IDENTIFIABLE"
    elif len(feasible) > 1:
        ident = "AMBIGUOUS"
    else:
        ident = "UNIDENTIFIABLE"

    # Stability is measured from the width of each implied-multiple interval.
    stability: list[dict[str, Any]] = []
    for x in feasible:
        lo, hi = map(_d, x["implied_multiple_range"])
        mid = (lo + hi) / 2
        rel_width = (hi - lo) / mid if mid else Decimal("999")
        stability.append({
            "model": x["model"],
            "relative_range_width": _q(rel_width),
            "status": "STABLE" if rel_width <= Decimal("0.30") else "UNSTABLE",
        })

    return {
        "status": status,
        "market_model_set": feasible,
        "identifiability": {"status": ident, "candidate_count": len(feasible)},
        "stability": stability,
        "method": "current_price_reverse_valuation_v1",
        "blockers": blockers,
    }


def compute_expectation_gap(current_price: Decimal, intrinsic_value: Decimal, market_expectation_value: Decimal) -> dict[str, float]:
    if current_price <= 0 or market_expectation_value <= 0:
        raise ValueError("expectation-gap inputs must be positive")
    independent_return = intrinsic_value / current_price - Decimal(1)
    market_return_to_intrinsic = intrinsic_value / market_expectation_value - Decimal(1)
    return {
        "intrinsic_expected_return_pct": _q(independent_return * 100),
        "expectation_gap_pct": _q((intrinsic_value / market_expectation_value - 1) * 100),
        "market_expectation_value": _q(market_expectation_value),
    }


def compute_probability_payoff(scenarios: dict[str, dict[str, Any]], current_price: Decimal) -> dict[str, Any]:
    if current_price <= 0:
        raise ValueError("current_price must be positive")
    names = ("bear", "base", "bull")
    probs = [_d(scenarios[n]["probability"]) for n in names]
    if any(p < 0 or p > 1 for p in probs) or sum(probs) != Decimal(1):
        raise ValueError("scenario probabilities must be in [0,1] and sum exactly to 1")
    returns = {n: _q((_d(scenarios[n]["value"]) / current_price - 1)) for n in names}
    expected = sum(probs[i] * _d(returns[n]) for i, n in enumerate(names))
    downside = abs(min(Decimal(0), min((_d(returns[n]) for n in names))))
    upside = max(Decimal(0), max((_d(returns[n]) for n in names)))
    payoff = upside / downside if downside > 0 else Decimal("999")
    win_probability = sum(probs[i] for i, n in enumerate(names) if _d(returns[n]) > 0)
    return {
        "scenario_returns": returns,
        "expected_return": _q(expected),
        "win_probability": _q(win_probability),
        "payoff_ratio": _q(payoff),
        "edge": _q(win_probability * payoff - (Decimal(1) - win_probability)),
    }


def compute_position_size(edge: Decimal, win_probability: Decimal, payoff_ratio: Decimal, portfolio: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    max_position = _d(portfolio.get("max_position_pct", 100))
    current_position = _d(portfolio.get("position_pct", 0))
    risk_budget = _d(risk.get("position_risk_budget_pct", 1))
    if edge <= 0 or win_probability <= 0 or payoff_ratio <= 0:
        recommended = Decimal(0)
    else:
        # Conservative fractional-Kelly proxy, additionally capped by portfolio and risk budgets.
        q = Decimal(1) - win_probability
        kelly = (win_probability - q / payoff_ratio) if payoff_ratio else Decimal(0)
        recommended = max(Decimal(0), kelly) * Decimal("0.25") * Decimal(100)
        recommended = min(recommended, max_position, risk_budget)
    return {
        "current_position_pct": _q(current_position),
        "recommended_additional_position_pct": _q(recommended),
        "recommended_total_position_pct": _q(min(max_position, current_position + recommended)),
        "method": "fractional_kelly_25pct_capped",
    }
