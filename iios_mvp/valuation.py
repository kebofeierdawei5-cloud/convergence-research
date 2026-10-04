from __future__ import annotations

from decimal import Decimal
from typing import Any

from .engine import dec

SUPPORTED_MODELS = (
    "forward_pe",
    "dcf",
    "ddm",
    "sotp",
    "ps",
    "pb",
    "ev_ebitda",
    "rnpv",
)

# Deterministic first-pass routing from structured economics. Human/LLM research
# may still override the route, but an override must be explicitly justified.
ECONOMIC_MODEL_ROUTES = {
    "mature_cash_earning_business": ("forward_pe", "dcf", "ev_ebitda"),
    "mature_earnings": ("forward_pe", "dcf", "ev_ebitda"),
    "cash_flow_business": ("dcf", "forward_pe", "ev_ebitda"),
    "dividend_financial": ("ddm", "pb"),
    "financial": ("pb", "ddm"),
    "cyclical_asset_heavy": ("pb", "ev_ebitda", "dcf"),
    "cyclical": ("pb", "ev_ebitda", "forward_pe"),
    "innovative_drug_commercial": ("ps", "rnpv", "sotp"),
    "innovative_drug_pipeline": ("rnpv", "sotp", "ps"),
    "mixed_segments": ("sotp", "dcf", "forward_pe"),
    "enterprise_operating_business": ("ev_ebitda", "dcf", "forward_pe"),
    "asset_heavy": ("pb", "sotp", "ev_ebitda"),
}


def _positive(value: Any, field: str) -> Decimal:
    x = dec(value, field)
    if x <= 0:
        raise ValueError(f"{field} must be > 0")
    return x


def route_model(economic_profile: str) -> dict[str, Any]:
    profile = str(economic_profile or "").strip().lower()
    candidates = ECONOMIC_MODEL_ROUTES.get(profile)
    if not candidates:
        raise ValueError(f"no deterministic model route for economic_profile: {economic_profile}")
    return {
        "economic_profile": profile,
        "recommended_primary_model": candidates[0],
        "candidate_models": list(candidates),
    }


def select_model(valuation: dict[str, Any]) -> dict[str, Any]:
    selection = valuation.get("model_selection") or {}
    economics = selection.get("economic_profile")
    if not economics:
        raise ValueError("valuation.model_selection.economic_profile is required")
    routed = route_model(economics)
    explicit = selection.get("primary_model") or valuation.get("model")
    primary = explicit or routed["recommended_primary_model"]
    if primary not in SUPPORTED_MODELS:
        raise ValueError(f"unsupported valuation model: {primary}")

    override = primary != routed["recommended_primary_model"]
    if override and not selection.get("override_reason"):
        raise ValueError(
            f"valuation model {primary} overrides routed model "
            f"{routed['recommended_primary_model']} without override_reason"
        )

    rationale = selection.get("rationale")
    if not rationale:
        raise ValueError("valuation.model_selection.rationale is required")
    alternatives = selection.get("alternatives") or []
    for model in alternatives:
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"unsupported alternative valuation model: {model}")

    return {
        "primary_model": primary,
        "economic_profile": routed["economic_profile"],
        "rationale": rationale,
        "alternatives": alternatives,
        "route_recommendation": routed["recommended_primary_model"],
        "route_candidates": routed["candidate_models"],
        "route_overridden": override,
        "override_reason": selection.get("override_reason"),
    }


def _pe(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    profit = _positive(forecast[scenario]["net_profit"], f"forecast.{scenario}.net_profit")
    multiple = _positive(valuation[f"{scenario}_multiple"], f"valuation.{scenario}_multiple")
    equity = profit * multiple
    return {
        "model": "forward_pe",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {"net_profit": float(profit), "multiple": float(multiple)},
    }


def _ps(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ps", {})
    row = inp.get(scenario) or inp
    revenue = _positive(
        row.get("revenue", forecast[scenario].get("revenue")),
        f"valuation.model_inputs.ps.{scenario}.revenue",
    )
    multiple = _positive(row.get("multiple", valuation.get(f"{scenario}_multiple")), f"valuation.ps.{scenario}.multiple")
    equity = revenue * multiple
    return {
        "model": "ps",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {"revenue": float(revenue), "multiple": float(multiple)},
    }


def _pb(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("pb", {})
    row = inp.get(scenario) or inp
    book_equity = _positive(
        row.get("book_equity"),
        f"valuation.model_inputs.pb.{scenario}.book_equity",
    )
    multiple = _positive(row.get("multiple"), f"valuation.model_inputs.pb.{scenario}.multiple")
    equity = book_equity * multiple
    return {
        "model": "pb",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {
            "book_equity": float(book_equity),
            "multiple": float(multiple),
            "book_value_basis": row.get("book_value_basis", "current"),
        },
    }


def _ev_ebitda(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ev_ebitda", {})
    row = inp.get(scenario) or inp
    ebitda = _positive(row.get("ebitda"), f"valuation.model_inputs.ev_ebitda.{scenario}.ebitda")
    multiple = _positive(row.get("multiple"), f"valuation.model_inputs.ev_ebitda.{scenario}.multiple")
    net_debt = dec(row.get("net_debt", 0), f"valuation.model_inputs.ev_ebitda.{scenario}.net_debt")
    enterprise_value = ebitda * multiple
    equity = enterprise_value - net_debt
    if equity <= 0:
        raise ValueError("EV/EBITDA implied equity value must be > 0")
    return {
        "model": "ev_ebitda",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {
            "ebitda": float(ebitda),
            "multiple": float(multiple),
            "net_debt": float(net_debt),
        },
    }


def _dcf(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs") or {}
    rows = inp.get("dcf", {}).get(scenario) or inp.get("dcf") or {}
    fcfs = rows.get("fcf")
    if not fcfs:
        raise ValueError(f"valuation.model_inputs.dcf.{scenario}.fcf is required")
    r = _positive(rows.get("discount_rate"), f"valuation.model_inputs.dcf.{scenario}.discount_rate")
    g = dec(rows.get("terminal_growth"), f"valuation.model_inputs.dcf.{scenario}.terminal_growth")
    if g < 0 or g >= r:
        raise ValueError("DCF terminal_growth must be >= 0 and < discount_rate")
    pv = Decimal("0")
    for i, fcf in enumerate(fcfs, 1):
        pv += dec(fcf, f"valuation.model_inputs.dcf.{scenario}.fcf[{i-1}]") / ((Decimal("1") + r) ** i)
    terminal = dec(fcfs[-1], f"valuation.model_inputs.dcf.{scenario}.fcf[-1]") * (Decimal("1") + g) / (r - g)
    pv += terminal / ((Decimal("1") + r) ** len(fcfs))
    net_debt = dec(inp.get("net_debt", 0), "valuation.model_inputs.net_debt")
    equity = pv - net_debt
    if equity <= 0:
        raise ValueError("DCF implied equity value must be > 0")
    return {
        "model": "dcf",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {"discount_rate": float(r), "terminal_growth": float(g), "net_debt": float(net_debt)},
    }


def _ddm(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ddm", {})
    row = inp.get(scenario) or inp
    dividend = _positive(row.get("dividend_per_share"), f"valuation.model_inputs.ddm.{scenario}.dividend_per_share")
    r = _positive(row.get("required_return"), f"valuation.model_inputs.ddm.{scenario}.required_return")
    g = dec(row.get("growth"), f"valuation.model_inputs.ddm.{scenario}.growth")
    if g < 0 or g >= r:
        raise ValueError("DDM growth must be >= 0 and < required_return")
    value = dividend * (Decimal("1") + g) / (r - g)
    equity = value * shares
    return {
        "model": "ddm",
        "equity_value": float(equity),
        "value_per_share": float(value),
        "drivers": {"dividend_per_share": float(dividend), "required_return": float(r), "growth": float(g)},
    }


def _rnpv(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("rnpv", {})
    row = inp.get(scenario) or inp
    cash_flows = row.get("cash_flows")
    probabilities = row.get("probability_of_success")
    if not cash_flows or probabilities is None or len(cash_flows) != len(probabilities):
        raise ValueError(
            f"valuation.model_inputs.rnpv.{scenario}.cash_flows and probability_of_success "
            "must have equal non-zero lengths"
        )
    discount_rate = _positive(row.get("discount_rate"), f"valuation.model_inputs.rnpv.{scenario}.discount_rate")
    pv = Decimal("0")
    for i, (cash_flow, probability) in enumerate(zip(cash_flows, probabilities), 1):
        p = dec(probability, f"valuation.model_inputs.rnpv.{scenario}.probability_of_success[{i-1}]")
        if p < 0 or p > 1:
            raise ValueError("rNPV probability_of_success must be between 0 and 1")
        cf = dec(cash_flow, f"valuation.model_inputs.rnpv.{scenario}.cash_flows[{i-1}]")
        pv += cf * p / ((Decimal("1") + discount_rate) ** i)
    net_debt = dec(row.get("net_debt", inp.get("net_debt", 0)), f"valuation.model_inputs.rnpv.{scenario}.net_debt")
    equity = pv - net_debt
    if equity <= 0:
        raise ValueError("rNPV implied equity value must be > 0")
    return {
        "model": "rnpv",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {
            "discount_rate": float(discount_rate),
            "periods": len(cash_flows),
            "probability_method": "period_cash_flow_probability",
            "net_debt": float(net_debt),
        },
    }


def _segment_value(segment: dict[str, Any]) -> Decimal:
    model = segment.get("model")
    if model == "forward_pe":
        return _positive(segment.get("net_profit"), "sotp.segment.net_profit") * _positive(segment.get("multiple"), "sotp.segment.multiple")
    if model == "ps":
        return _positive(segment.get("revenue"), "sotp.segment.revenue") * _positive(segment.get("multiple"), "sotp.segment.multiple")
    if model == "pb":
        return _positive(segment.get("book_equity"), "sotp.segment.book_equity") * _positive(segment.get("multiple"), "sotp.segment.multiple")
    if model == "ev_ebitda":
        ebitda = _positive(segment.get("ebitda"), "sotp.segment.ebitda")
        multiple = _positive(segment.get("multiple"), "sotp.segment.multiple")
        return ebitda * multiple - dec(segment.get("net_debt", 0), "sotp.segment.net_debt")
    if model == "dcf":
        fcfs = segment.get("fcf") or []
        r = _positive(segment.get("discount_rate"), "sotp.segment.discount_rate")
        g = dec(segment.get("terminal_growth"), "sotp.segment.terminal_growth")
        if not fcfs or g < 0 or g >= r:
            raise ValueError("invalid SOTP DCF segment")
        pv = sum((dec(x, "sotp.segment.fcf") / ((Decimal("1") + r) ** i) for i, x in enumerate(fcfs, 1)), Decimal("0"))
        terminal = dec(fcfs[-1], "sotp.segment.fcf[-1]") * (Decimal("1") + g) / (r - g)
        return pv + terminal / ((Decimal("1") + r) ** len(fcfs))
    if model == "ddm":
        d = _positive(segment.get("dividend_per_share"), "sotp.segment.dividend_per_share")
        r = _positive(segment.get("required_return"), "sotp.segment.required_return")
        g = dec(segment.get("growth"), "sotp.segment.growth")
        if g < 0 or g >= r:
            raise ValueError("invalid SOTP DDM segment")
        return d * (Decimal("1") + g) / (r - g) * _positive(segment.get("shares"), "sotp.segment.shares")
    if model == "rnpv":
        cash_flows = segment.get("cash_flows") or []
        probabilities = segment.get("probability_of_success")
        r = _positive(segment.get("discount_rate"), "sotp.segment.discount_rate")
        if not cash_flows or probabilities is None or len(cash_flows) != len(probabilities):
            raise ValueError("invalid SOTP rNPV segment")
        pv = Decimal("0")
        for i, (cf, probability) in enumerate(zip(cash_flows, probabilities), 1):
            p = dec(probability, "sotp.segment.probability_of_success")
            if p < 0 or p > 1:
                raise ValueError("invalid SOTP rNPV probability")
            pv += dec(cf, "sotp.segment.cash_flow") * p / ((Decimal("1") + r) ** i)
        return pv - dec(segment.get("net_debt", 0), "sotp.segment.net_debt")
    raise ValueError(f"unsupported SOTP segment model: {model}")


def _sotp(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("sotp", {})
    segments = inp.get(scenario) or inp.get("segments") or []
    if not segments:
        raise ValueError(f"valuation.model_inputs.sotp.{scenario} is required")
    gross = sum((_segment_value(s) for s in segments), Decimal("0"))
    net_debt = dec(inp.get("net_debt", 0), "valuation.model_inputs.sotp.net_debt")
    other = dec(inp.get("other_assets", 0), "valuation.model_inputs.sotp.other_assets")
    equity = gross + other - net_debt
    if equity <= 0:
        raise ValueError("SOTP implied equity value must be > 0")
    return {
        "model": "sotp",
        "equity_value": float(equity),
        "value_per_share": float(equity / shares),
        "drivers": {
            "segment_count": len(segments),
            "other_assets": float(other),
            "net_debt": float(net_debt),
            "segment_models": [str(s.get("model")) for s in segments],
        },
    }


def value_scenario(
    forecast: dict[str, Any],
    valuation: dict[str, Any],
    scenario: str,
    shares: Decimal,
) -> dict[str, Any]:
    model = select_model(valuation)["primary_model"]
    if model == "forward_pe":
        return _pe(forecast, valuation, scenario, shares)
    if model == "dcf":
        return _dcf(forecast, valuation, scenario, shares)
    if model == "ddm":
        return _ddm(forecast, valuation, scenario, shares)
    if model == "sotp":
        return _sotp(forecast, valuation, scenario, shares)
    if model == "ps":
        return _ps(forecast, valuation, scenario, shares)
    if model == "pb":
        return _pb(forecast, valuation, scenario, shares)
    if model == "ev_ebitda":
        return _ev_ebitda(forecast, valuation, scenario, shares)
    if model == "rnpv":
        return _rnpv(forecast, valuation, scenario, shares)
    raise AssertionError(model)
