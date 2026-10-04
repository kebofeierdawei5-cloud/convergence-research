from __future__ import annotations

from decimal import Decimal
from typing import Any

from .engine import dec

SUPPORTED_MODELS = ("forward_pe", "dcf", "ddm", "sotp")


def _positive(value: Any, field: str) -> Decimal:
    x = dec(value, field)
    if x <= 0:
        raise ValueError(f"{field} must be > 0")
    return x


def select_model(valuation: dict[str, Any]) -> dict[str, Any]:
    selection = valuation.get("model_selection") or {}
    primary = selection.get("primary_model") or valuation.get("model")
    if primary not in SUPPORTED_MODELS:
        raise ValueError(f"unsupported valuation model: {primary}")
    economics = selection.get("economic_profile")
    if not economics:
        raise ValueError("valuation.model_selection.economic_profile is required")
    rationale = selection.get("rationale")
    if not rationale:
        raise ValueError("valuation.model_selection.rationale is required")
    alternatives = selection.get("alternatives") or []
    return {
        "primary_model": primary,
        "economic_profile": economics,
        "rationale": rationale,
        "alternatives": alternatives,
    }


def _pe(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    profit = _positive(forecast[scenario]["net_profit"], f"forecast.{scenario}.net_profit")
    multiple = _positive(valuation[f"{scenario}_multiple"], f"valuation.{scenario}_multiple")
    equity = profit * multiple
    return {"model": "forward_pe", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"net_profit": float(profit), "multiple": float(multiple)}}


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
    return {"model": "dcf", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"discount_rate": float(r), "terminal_growth": float(g), "net_debt": float(net_debt)}}


def _ddm(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ddm", {})
    dividend = _positive((inp.get(scenario) or {}).get("dividend_per_share"), f"valuation.model_inputs.ddm.{scenario}.dividend_per_share")
    r = _positive((inp.get(scenario) or {}).get("required_return"), f"valuation.model_inputs.ddm.{scenario}.required_return")
    g = dec((inp.get(scenario) or {}).get("growth"), f"valuation.model_inputs.ddm.{scenario}.growth")
    if g < 0 or g >= r:
        raise ValueError("DDM growth must be >= 0 and < required_return")
    value = dividend * (Decimal("1") + g) / (r - g)
    equity = value * shares
    return {"model": "ddm", "equity_value": float(equity), "value_per_share": float(value),
            "drivers": {"dividend_per_share": float(dividend), "required_return": float(r), "growth": float(g)}}


def _segment_value(segment: dict[str, Any]) -> Decimal:
    model = segment.get("model")
    if model == "forward_pe":
        return _positive(segment.get("net_profit"), "sotp.segment.net_profit") * _positive(segment.get("multiple"), "sotp.segment.multiple")
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
    return {"model": "sotp", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"segment_count": len(segments), "other_assets": float(other), "net_debt": float(net_debt)}}


def value_scenario(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    model = select_model(valuation)["primary_model"]
    if model == "forward_pe":
        return _pe(forecast, valuation, scenario, shares)
    if model == "dcf":
        return _dcf(forecast, valuation, scenario, shares)
    if model == "ddm":
        return _ddm(forecast, valuation, scenario, shares)
    if model == "sotp":
        return _sotp(forecast, valuation, scenario, shares)
    raise AssertionError(model)
