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

# Deterministic economic-profile-to-model suitability map.
# Scores are routing priors, not valuation outputs.
MODEL_SUITABILITY = {
    "mature_cash_earning_business": {
        "forward_pe": 95, "dcf": 88, "ev_ebitda": 82, "sotp": 62, "pb": 45, "ddm": 55, "ps": 25, "rnpv": 10
    },
    "mature_earnings": {
        "forward_pe": 95, "dcf": 88, "ev_ebitda": 82, "sotp": 60, "pb": 48, "ddm": 55, "ps": 20, "rnpv": 10
    },
    "cash_flow_business": {
        "dcf": 95, "forward_pe": 88, "ev_ebitda": 85, "sotp": 58, "ddm": 52, "pb": 40, "ps": 25, "rnpv": 10
    },
    "dividend_financial": {
        "ddm": 96, "pb": 92, "forward_pe": 78, "dcf": 72, "ev_ebitda": 40, "sotp": 55, "ps": 15, "rnpv": 5
    },
    "financial": {
        "pb": 96, "ddm": 90, "forward_pe": 80, "dcf": 70, "sotp": 58, "ev_ebitda": 35, "ps": 10, "rnpv": 5
    },
    "cyclical_asset_heavy": {
        "pb": 95, "ev_ebitda": 88, "dcf": 75, "forward_pe": 58, "sotp": 68, "ddm": 35, "ps": 25, "rnpv": 5
    },
    "cyclical": {
        "pb": 92, "ev_ebitda": 90, "forward_pe": 62, "dcf": 70, "sotp": 55, "ddm": 30, "ps": 30, "rnpv": 5
    },
    "innovative_drug_commercial": {
        "ps": 94, "rnpv": 90, "sotp": 88, "dcf": 70, "forward_pe": 45, "ev_ebitda": 38, "pb": 20, "ddm": 10
    },
    "innovative_drug_pipeline": {
        "rnpv": 98, "sotp": 94, "ps": 58, "dcf": 45, "forward_pe": 18, "ev_ebitda": 12, "pb": 10, "ddm": 5
    },
    "mixed_businesses": {
        "sotp": 98, "dcf": 78, "forward_pe": 72, "ev_ebitda": 70, "ps": 55, "rnpv": 50, "pb": 45, "ddm": 35
    },
    "mixed_segments": {
        "sotp": 98, "dcf": 78, "forward_pe": 72, "ev_ebitda": 70, "ps": 55, "rnpv": 50, "pb": 45, "ddm": 35
    },
    "enterprise_operating_business": {
        "ev_ebitda": 96, "dcf": 90, "forward_pe": 78, "sotp": 62, "pb": 42, "ps": 35, "ddm": 20, "rnpv": 10
    },
    "asset_heavy": {
        "pb": 95, "sotp": 90, "ev_ebitda": 82, "dcf": 72, "forward_pe": 48, "ps": 20, "ddm": 20, "rnpv": 5
    },
}

MODEL_ROUTE_FALLBACK = {
    profile: tuple(model for model, _score in sorted(scores.items(), key=lambda item: (-item[1], item[0])))
    for profile, scores in MODEL_SUITABILITY.items()
}


def _positive(value: Any, field: str) -> Decimal:
    x = dec(value, field)
    if x <= 0:
        raise ValueError(f"{field} must be > 0")
    return x


def assess_model_suitability(economic_profile: str) -> dict[str, Any]:
    profile = str(economic_profile or "").strip().lower()
    if profile == "mixed_businesses":
        profile = "mixed_segments"
    scores = MODEL_SUITABILITY.get(profile)
    if not scores:
        raise ValueError(f"no deterministic model suitability profile for: {economic_profile}")
    ranked = [
        {"model": model, "score": score, "rank": rank + 1}
        for rank, (model, score) in enumerate(sorted(scores.items(), key=lambda item: (-item[1], item[0])))
    ]
    return {"economic_profile": profile, "ranked_models": ranked}


def route_model(economic_profile: str) -> dict[str, Any]:
    assessment = assess_model_suitability(economic_profile)
    ranked = assessment["ranked_models"]
    return {
        "economic_profile": assessment["economic_profile"],
        "recommended_primary_model": ranked[0]["model"],
        "recommended_secondary_models": [x["model"] for x in ranked[1:2]],
        "recommended_cross_check_models": [x["model"] for x in ranked[2:3]],
        "candidate_models": [x["model"] for x in ranked[:4]],
        "suitability": ranked,
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

    alternatives = list(selection.get("alternatives") or [])
    secondary = list(selection.get("secondary_models") or routed["recommended_secondary_models"])
    cross_checks = list(selection.get("cross_check_models") or [])

    if not cross_checks and alternatives:
        cross_checks = alternatives
        secondary = [m for m in secondary if m not in cross_checks]
        if not secondary:
            secondary = [x["model"] for x in routed["suitability"] if x["model"] != primary and x["model"] not in cross_checks][:1]
    if not selection.get("secondary_models") and not alternatives:
        cross_checks = routed["recommended_cross_check_models"]

    for model in secondary + cross_checks:
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"unsupported secondary/cross-check model: {model}")
    if primary in secondary or primary in cross_checks:
        raise ValueError("primary model cannot also be a secondary/cross-check model")
    if set(secondary) & set(cross_checks):
        raise ValueError("secondary and cross-check model sets must be disjoint")

    return {
        "primary_model": primary,
        "secondary_models": secondary,
        "cross_check_models": cross_checks,
        "economic_profile": routed["economic_profile"],
        "rationale": rationale,
        "alternatives": alternatives,
        "route_recommendation": routed["recommended_primary_model"],
        "route_candidates": routed["candidate_models"],
        "suitability": routed["suitability"],
        "route_overridden": override,
        "override_reason": selection.get("override_reason"),
    }


def _pe(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    profit = _positive(forecast[scenario]["net_profit"], f"forecast.{scenario}.net_profit")
    multiple = _positive(valuation[f"{scenario}_multiple"], f"valuation.{scenario}_multiple")
    equity = profit * multiple
    return {
        "model": "forward_pe", "equity_value": float(equity), "value_per_share": float(equity / shares),
        "drivers": {"net_profit": float(profit), "multiple": float(multiple)},
    }


def _ps(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ps", {})
    row = inp.get(scenario) or inp
    revenue = _positive(row.get("revenue", forecast[scenario].get("revenue")), f"valuation.model_inputs.ps.{scenario}.revenue")
    multiple = _positive(row.get("multiple", valuation.get(f"{scenario}_multiple")), f"valuation.ps.{scenario}.multiple")
    equity = revenue * multiple
    return {"model": "ps", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"revenue": float(revenue), "multiple": float(multiple)}}


def _pb(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("pb", {})
    row = inp.get(scenario) or inp
    book_equity = _positive(row.get("book_equity"), f"valuation.model_inputs.pb.{scenario}.book_equity")
    multiple = _positive(row.get("multiple"), f"valuation.model_inputs.pb.{scenario}.multiple")
    equity = book_equity * multiple
    return {"model": "pb", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"book_equity": float(book_equity), "multiple": float(multiple),
                        "book_value_basis": row.get("book_value_basis", "current")}}


def _ev_ebitda(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ev_ebitda", {})
    row = inp.get(scenario) or inp
    ebitda = _positive(row.get("ebitda"), f"valuation.model_inputs.ev_ebitda.{scenario}.ebitda")
    multiple = _positive(row.get("multiple"), f"valuation.model_inputs.ev_ebitda.{scenario}.multiple")
    net_debt = dec(row.get("net_debt", 0), f"valuation.model_inputs.ev_ebitda.{scenario}.net_debt")
    equity = ebitda * multiple - net_debt
    if equity <= 0:
        raise ValueError("EV/EBITDA implied equity value must be > 0")
    return {"model": "ev_ebitda", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"ebitda": float(ebitda), "multiple": float(multiple), "net_debt": float(net_debt)}}


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
    return {"model": "dcf", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"discount_rate": float(r), "terminal_growth": float(g), "net_debt": float(net_debt)}}


def _ddm(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("ddm", {})
    row = inp.get(scenario) or inp
    dividend = _positive(row.get("dividend_per_share"), f"valuation.model_inputs.ddm.{scenario}.dividend_per_share")
    r = _positive(row.get("required_return"), f"valuation.model_inputs.ddm.{scenario}.required_return")
    g = dec(row.get("growth"), f"valuation.model_inputs.ddm.{scenario}.growth")
    if g < 0 or g >= r:
        raise ValueError("DDM growth must be >= 0 and < required_return")
    value = dividend * (Decimal("1") + g) / (r - g)
    return {"model": "ddm", "equity_value": float(value * shares), "value_per_share": float(value),
            "drivers": {"dividend_per_share": float(dividend), "required_return": float(r), "growth": float(g)}}


def _rnpv_asset_value(asset: dict[str, Any], default_discount_rate: Decimal, prefix: str) -> tuple[Decimal, dict[str, Any]]:
    cash_flows = asset.get("cash_flows") or []
    if not cash_flows:
        raise ValueError(f"{prefix}.cash_flows is required")

    discount_rate = _positive(asset.get("discount_rate", default_discount_rate), f"{prefix}.discount_rate")
    launch_delay = asset.get("launch_delay_periods", 0)
    try:
        launch_delay = int(launch_delay)
    except (TypeError, ValueError):
        raise ValueError(f"{prefix}.launch_delay_periods must be an integer")
    if launch_delay < 0:
        raise ValueError(f"{prefix}.launch_delay_periods must be >= 0")

    probabilities = asset.get("probability_of_success", 1)
    if isinstance(probabilities, list):
        if len(probabilities) != len(cash_flows):
            raise ValueError(f"{prefix}.probability_of_success length must equal cash_flows length")
        probability_path = probabilities
    else:
        probability_path = [probabilities] * len(cash_flows)

    pv = Decimal("0")
    for i, (cf_item, probability) in enumerate(zip(cash_flows, probability_path), 1):
        if isinstance(cf_item, dict):
            cf = dec(cf_item.get("cash_flow"), f"{prefix}.cash_flows[{i-1}].cash_flow")
            risk_adjust = bool(cf_item.get("risk_adjust", True))
        else:
            cf = dec(cf_item, f"{prefix}.cash_flows[{i-1}]")
            risk_adjust = True

        p = dec(probability, f"{prefix}.probability_of_success[{i-1}]")
        if p < 0 or p > 1:
            raise ValueError(f"{prefix}.probability_of_success must be between 0 and 1")

        period = launch_delay + i
        adjusted_cf = cf * p if risk_adjust else cf
        pv += adjusted_cf / ((Decimal("1") + discount_rate) ** period)

    return pv, {
        "name": asset.get("name"),
        "periods": len(cash_flows),
        "launch_delay_periods": launch_delay,
        "discount_rate": float(discount_rate),
    }


def _rnpv(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("rnpv", {})
    row = inp.get(scenario) or inp

    pipeline = row.get("pipeline") or row.get("assets")
    if pipeline:
        default_discount_rate = _positive(row.get("discount_rate"), f"valuation.model_inputs.rnpv.{scenario}.discount_rate")
        asset_values = []
        pv = Decimal("0")
        for index, asset in enumerate(pipeline):
            if not isinstance(asset, dict):
                raise ValueError(f"valuation.model_inputs.rnpv.{scenario}.pipeline[{index}] must be an object")
            value, meta = _rnpv_asset_value(
                asset, default_discount_rate,
                f"valuation.model_inputs.rnpv.{scenario}.pipeline[{index}]",
            )
            pv += value
            meta["pv"] = float(value)
            asset_values.append(meta)

        other_assets = dec(row.get("other_assets", 0), f"valuation.model_inputs.rnpv.{scenario}.other_assets")
        net_debt = dec(row.get("net_debt", 0), f"valuation.model_inputs.rnpv.{scenario}.net_debt")
        equity = pv + other_assets - net_debt
        if equity <= 0:
            raise ValueError("rNPV implied equity value must be > 0")
        return {
            "model": "rnpv",
            "equity_value": float(equity),
            "value_per_share": float(equity / shares),
            "drivers": {
                "asset_count": len(asset_values),
                "discount_rate": float(default_discount_rate),
                "other_assets": float(other_assets),
                "net_debt": float(net_debt),
                "assets": asset_values,
                "probability_method": "asset_level_risk_adjusted_cash_flows",
            },
        }

    # Backward-compatible legacy rNPV contract.
    cash_flows = row.get("cash_flows")
    probabilities = row.get("probability_of_success")
    if not cash_flows or probabilities is None or len(cash_flows) != len(probabilities):
        raise ValueError(f"valuation.model_inputs.rnpv.{scenario}.cash_flows and probability_of_success must have equal non-zero lengths")
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
    return {"model": "rnpv", "equity_value": float(equity), "value_per_share": float(equity / shares),
            "drivers": {"discount_rate": float(discount_rate), "periods": len(cash_flows),
                        "probability_method": "period_cash_flow_probability", "net_debt": float(net_debt)}}

def _segment_value(segment: dict[str, Any]) -> Decimal:
    model = segment.get("model")
    if model == "forward_pe":
        value = _positive(segment.get("net_profit"), "sotp.segment.net_profit") * _positive(segment.get("multiple"), "sotp.segment.multiple")
    elif model == "ps":
        value = _positive(segment.get("revenue"), "sotp.segment.revenue") * _positive(segment.get("multiple"), "sotp.segment.multiple")
    elif model == "pb":
        value = _positive(segment.get("book_equity"), "sotp.segment.book_equity") * _positive(segment.get("multiple"), "sotp.segment.multiple")
    elif model == "ev_ebitda":
        ebitda = _positive(segment.get("ebitda"), "sotp.segment.ebitda")
        value = ebitda * _positive(segment.get("multiple"), "sotp.segment.multiple") - dec(segment.get("net_debt", 0), "sotp.segment.net_debt")
    elif model == "dcf":
        fcfs = segment.get("fcf") or []
        r = _positive(segment.get("discount_rate"), "sotp.segment.discount_rate")
        g = dec(segment.get("terminal_growth"), "sotp.segment.terminal_growth")
        if not fcfs or g < 0 or g >= r:
            raise ValueError("invalid SOTP DCF segment")
        pv = sum((dec(x, "sotp.segment.fcf") / ((Decimal("1") + r) ** i) for i, x in enumerate(fcfs, 1)), Decimal("0"))
        terminal = dec(fcfs[-1], "sotp.segment.fcf[-1]") * (Decimal("1") + g) / (r - g)
        value = pv + terminal / ((Decimal("1") + r) ** len(fcfs))
    elif model == "ddm":
        d = _positive(segment.get("dividend_per_share"), "sotp.segment.dividend_per_share")
        r = _positive(segment.get("required_return"), "sotp.segment.required_return")
        g = dec(segment.get("growth"), "sotp.segment.growth")
        if g < 0 or g >= r:
            raise ValueError("invalid SOTP DDM segment")
        value = d * (Decimal("1") + g) / (r - g) * _positive(segment.get("shares"), "sotp.segment.shares")
    elif model == "rnpv":
        cash_flows = segment.get("cash_flows") or []
        probabilities = segment.get("probability_of_success")
        r = _positive(segment.get("discount_rate"), "sotp.segment.discount_rate")
        if not cash_flows or probabilities is None:
            raise ValueError("invalid SOTP rNPV segment")
        if not isinstance(probabilities, list):
            probabilities = [probabilities] * len(cash_flows)
        if len(cash_flows) != len(probabilities):
            raise ValueError("invalid SOTP rNPV probability path")
        pv = Decimal("0")
        delay = int(segment.get("launch_delay_periods", 0))
        for i, (cf, probability) in enumerate(zip(cash_flows, probabilities), 1):
            p = dec(probability, "sotp.segment.probability_of_success")
            if p < 0 or p > 1:
                raise ValueError("invalid SOTP rNPV probability")
            pv += dec(cf, "sotp.segment.cash_flow") * p / ((Decimal("1") + r) ** (delay + i))
        value = pv - dec(segment.get("net_debt", 0), "sotp.segment.net_debt")
    else:
        raise ValueError(f"unsupported SOTP segment model: {model}")

    ownership = dec(segment.get("ownership_pct", 100), "sotp.segment.ownership_pct")
    if ownership < 0 or ownership > 100:
        raise ValueError("sotp.segment.ownership_pct must be between 0 and 100")
    return value * ownership / Decimal("100")


def _sotp(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    inp = valuation.get("model_inputs", {}).get("sotp", {})
    segments = inp.get(scenario) or inp.get("segments")
    if isinstance(segments, dict):
        segments = segments.get("segments")
    if not segments:
        raise ValueError(f"valuation.model_inputs.sotp.{scenario} is required")
    segment_values = []
    gross = Decimal("0")
    for index, segment in enumerate(segments):
        value = _segment_value(segment)
        gross += value
        segment_values.append({
            "name": segment.get("name", f"segment-{index + 1}"),
            "model": segment.get("model"),
            "ownership_pct": float(dec(segment.get("ownership_pct", 100), "sotp.segment.ownership_pct")),
            "equity_value": float(value),
        })
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
            "segment_count": len(segment_values),
            "other_assets": float(other),
            "net_debt": float(net_debt),
            "segments": segment_values,
        },
    }


def evaluate_intrinsic_value_gate(result: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    selection = result.get("model_selection") or {}
    scenarios = result.get("scenarios") or {}
    for key in ("bear_value_per_share", "base_value_per_share", "bull_value_per_share"):
        value = scenarios.get(key)
        if value is None:
            blockers.append(f"MISSING_SCENARIO_VALUE:{key}")
    if blockers:
        return {"status": "BLOCKED", "blockers": blockers}

    bear = dec(scenarios["bear_value_per_share"], "scenarios.bear")
    base = dec(scenarios["base_value_per_share"], "scenarios.base")
    bull = dec(scenarios["bull_value_per_share"], "scenarios.bull")
    if not (bear <= base <= bull):
        blockers.append("SCENARIO_ORDER_INVALID")
    if bear <= 0 or base <= 0 or bull <= 0:
        blockers.append("NON_POSITIVE_INTRINSIC_VALUE")

    if not selection.get("primary_model"):
        blockers.append("PRIMARY_MODEL_MISSING")
    if not selection.get("economic_profile"):
        blockers.append("ECONOMIC_PROFILE_MISSING")
    if not selection.get("rationale"):
        blockers.append("MODEL_SELECTION_RATIONALE_MISSING")

    primary = selection.get("primary_model")
    primary_status = (result.get("model_status") or {}).get(primary) or {}
    for scenario in ("bear", "base", "bull"):
        if primary_status.get(f"{scenario}_status") != "PASS":
            blockers.append(f"PRIMARY_MODEL_{scenario.upper()}_NOT_PASS")

    aggregation = result.get("aggregation") or {}
    weights = aggregation.get("weights") or {}
    total = sum((dec(v, f"aggregation.weights.{k}") for k, v in weights.items()), Decimal("0"))
    if abs(total - Decimal("1")) > Decimal("0.0000001"):
        blockers.append("AGGREGATION_WEIGHTS_NOT_ONE")

    return {"status": "PASS" if not blockers else "BLOCKED", "blockers": blockers}

def value_scenario(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    model = select_model(valuation)["primary_model"]
    return _value_by_model(forecast, valuation, model, scenario, shares)


def _value_by_model(forecast: dict[str, Any], valuation: dict[str, Any], model: str, scenario: str, shares: Decimal) -> dict[str, Any]:
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
    raise ValueError(f"unsupported valuation model: {model}")


def build_intrinsic_valuation(
    forecast: dict[str, Any],
    valuation: dict[str, Any],
    shares: Decimal,
) -> dict[str, Any]:
    selection = select_model(valuation)
    models = [selection["primary_model"]] + selection["secondary_models"] + selection["cross_check_models"]

    scenario_values: dict[str, dict[str, dict[str, Any]]] = {}
    model_status: dict[str, dict[str, Any]] = {}
    for model in models:
        model_status[model] = {"role": (
            "primary" if model == selection["primary_model"]
            else "secondary" if model in selection["secondary_models"]
            else "cross_check"
        )}
        scenario_values[model] = {}
        for scenario in ("bear", "base", "bull"):
            try:
                scenario_values[model][scenario] = _value_by_model(forecast, valuation, model, scenario, shares)
                model_status[model][f"{scenario}_status"] = "PASS"
            except (KeyError, TypeError, ValueError) as exc:
                scenario_values[model][scenario] = None
                model_status[model][f"{scenario}_status"] = f"BLOCKED:{exc}"

    primary = selection["primary_model"]
    if any(scenario_values[primary][s] is None for s in ("bear", "base", "bull")):
        raise ValueError(f"primary valuation model {primary} cannot produce all Bear/Base/Bull values")

    aggregation = valuation.get("aggregation") or {}
    explicit_weights = aggregation.get("model_weights")
    weights: dict[str, Decimal] = {}
    if explicit_weights is not None:
        for model, weight in explicit_weights.items():
            if model not in models:
                raise ValueError(f"aggregation weight references unused model: {model}")
            w = dec(weight, f"valuation.aggregation.model_weights.{model}")
            if w < 0:
                raise ValueError("aggregation model weights must be >= 0")
            weights[model] = w
        total = sum(weights.values(), Decimal("0"))
        if total != Decimal("1"):
            raise ValueError("aggregation model weights must sum exactly to 1")
        for model, weight in weights.items():
            if weight > 0 and any(scenario_values[model][s] is None for s in ("bear", "base", "bull")):
                raise ValueError(f"weighted model {model} is not fully valued")
    else:
        # No arbitrary averaging: primary is authoritative; other models are checks only.
        weights = {primary: Decimal("1")}
    
    aggregated_scenarios = {}
    for scenario in ("bear", "base", "bull"):
        value = Decimal("0")
        for model, weight in weights.items():
            value += dec(scenario_values[model][scenario]["value_per_share"], f"{model}.{scenario}.value_per_share") * weight
        aggregated_scenarios[scenario] = float(value)

    scenario_range = {
        "bear_value_per_share": aggregated_scenarios["bear"],
        "base_value_per_share": aggregated_scenarios["base"],
        "bull_value_per_share": aggregated_scenarios["bull"],
        "low": aggregated_scenarios["bear"],
        "high": aggregated_scenarios["bull"],
    }

    dispersion = None
    base_values = [
        scenario_values[model]["base"]["value_per_share"]
        for model in models
        if scenario_values[model].get("base") is not None
    ]
    if len(base_values) >= 2:
        low = min(base_values)
        high = max(base_values)
        midpoint = (low + high) / 2
        dispersion = {
            "min_base_model_value": float(low),
            "max_base_model_value": float(high),
            "relative_dispersion_pct": float(((high - low) / midpoint) * 100) if midpoint else None,
        }

    return {
        "model_selection": selection,
        "models": scenario_values,
        "model_status": model_status,
        "aggregation": {
            "method": "explicit_weighted_average" if explicit_weights is not None else "primary_authoritative_no_arbitrary_average",
            "weights": {model: float(weight) for model, weight in weights.items()},
        },
        "scenarios": scenario_range,
        "intrinsic_value_per_share": aggregated_scenarios["base"],
        "intrinsic_value_range": {"low": aggregated_scenarios["bear"], "base": aggregated_scenarios["base"], "high": aggregated_scenarios["bull"]},
        "model_cross_check_dispersion": dispersion,
    }
