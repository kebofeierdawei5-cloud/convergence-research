from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from typing import Any

ENGINE_VERSION = "0.1.1"
ACTIONS = ("BUY", "ADD", "HOLD", "REDUCE", "EXIT", "NO-BUY")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def dec(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def pct(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def validate_case(case: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    required = {
        "case_id", "symbol", "company", "cutoff_date", "evidence", "trust",
        "reality", "forecast", "valuation", "risk", "portfolio", "thesis"
    }
    missing = sorted(required - set(case))
    if missing:
        blockers.extend(f"MISSING_FIELD:{item}" for item in missing)
        return blockers

    cutoff = _date(case["cutoff_date"], "cutoff_date")
    valuation = case.get("valuation") or {}
    current_price = dec(valuation.get("current_price"), "valuation.current_price")
    if current_price <= 0:
        blockers.append("INVALID_CURRENT_PRICE")

    evidence = case.get("evidence") or []
    if not evidence:
        blockers.append("NO_EVIDENCE")
    for i, item in enumerate(evidence):
        known_at = item.get("known_at")
        for field in ("source", "known_at", "claim"):
            if not item.get(field):
                blockers.append(f"EVIDENCE_{i}_MISSING_{field.upper()}")
        if known_at:
            try:
                if _date(known_at, f"evidence[{i}].known_at") > cutoff:
                    blockers.append(f"PIT_LEAK_EVIDENCE_{i}")
            except ValueError:
                blockers.append(f"INVALID_EVIDENCE_DATE_{i}")

    trust_status = str((case.get("trust") or {}).get("status", "UNKNOWN")).upper()
    if trust_status not in {"PASS", "REVALIDATION", "FAIL", "UNKNOWN"}:
        blockers.append("INVALID_TRUST_STATUS")

    reality = case.get("reality") or {}
    points = reality.get("periods") or []
    if not points:
        blockers.append("NO_REALITY")
    for i, item in enumerate(points):
        known_at = item.get("known_at")
        if not known_at:
            blockers.append(f"REALITY_{i}_MISSING_KNOWN_AT")
        else:
            try:
                if _date(known_at, f"reality[{i}].known_at") > cutoff:
                    blockers.append(f"PIT_LEAK_REALITY_{i}")
            except ValueError:
                blockers.append(f"INVALID_REALITY_DATE_{i}")

    forecast = case.get("forecast") or {}
    for scenario in ("bear", "base", "bull"):
        item = forecast.get(scenario) or {}
        try:
            value = dec(item.get("net_profit"), f"forecast.{scenario}.net_profit")
        except ValueError:
            value = Decimal("0")
        if value <= 0:
            blockers.append(f"INVALID_FORECAST_{scenario.upper()}")
    if not forecast.get("method") or not forecast.get("assumptions"):
        blockers.append("FORECAST_METHOD_OR_ASSUMPTIONS_MISSING")
    if forecast.get("prepared_using_current_price", True):
        blockers.append("CURRENT_PRICE_IN_FORECAST_INPUTS")

    try:
        shares = dec(valuation.get("shares_outstanding"), "valuation.shares_outstanding")
    except ValueError:
        shares = Decimal("0")
    try:
        required_return = dec(valuation.get("required_return_pct"), "valuation.required_return_pct")
    except ValueError:
        required_return = Decimal("-1")
    if shares <= 0:
        blockers.append("INVALID_SHARES_OUTSTANDING")
    if required_return < 0:
        blockers.append("INVALID_REQUIRED_RETURN")
    try:
        from .valuation import SUPPORTED_MODELS, select_model
        selection = select_model(valuation)
        if selection["primary_model"] not in SUPPORTED_MODELS:
            blockers.append("UNSUPPORTED_VALUATION_MODEL")
    except ValueError as exc:
        blockers.append(f"VALUATION_MODEL_SELECTION_INVALID:{exc}")
    model = str((valuation.get("model_selection") or {}).get("primary_model") or valuation.get("model") or "")
    if model == "forward_pe":
        for scenario in ("bear", "base", "bull"):
            try:
                multiple = dec(valuation.get(f"{scenario}_multiple"), f"valuation.{scenario}_multiple")
            except ValueError:
                multiple = Decimal("0")
            if multiple <= 0:
                blockers.append(f"INVALID_{scenario.upper()}_MULTIPLE")

    risk = case.get("risk") or {}
    try:
        max_loss = dec(risk.get("max_loss_pct"), "risk.max_loss_pct")
    except ValueError:
        max_loss = Decimal("-1")
    if max_loss < 0:
        blockers.append("INVALID_MAX_LOSS")
    if not risk.get("thesis_breaks"):
        blockers.append("NO_THESIS_BREAKS")

    portfolio = case.get("portfolio") or {}
    try:
        position = dec(portfolio.get("position_pct", 0), "portfolio.position_pct")
    except ValueError:
        position = Decimal("-1")
    if position < 0 or position > 100:
        blockers.append("INVALID_POSITION_PCT")
    return blockers


def _scenario(forecast: dict[str, Any], valuation: dict[str, Any], scenario: str, shares: Decimal) -> dict[str, Any]:
    from .valuation import value_scenario
    result = value_scenario(forecast, valuation, scenario, shares)
    result["scenario"] = scenario
    return result


def decide(case: dict[str, Any]) -> dict[str, Any]:
    case = deepcopy(case)
    blockers = validate_case(case)
    validation = {"status": "BLOCKED" if blockers else "PASS", "blockers": blockers}

    valuation = case["valuation"]
    forecast = case["forecast"]
    risk = case["risk"]
    portfolio = case["portfolio"]
    if blockers:
        position_raw = (portfolio or {}).get("position_pct", 0)
        try:
            position = dec(position_raw, "portfolio.position_pct")
        except ValueError:
            position = Decimal("0")
        action = "HOLD" if position > 0 else "NO-BUY"
        if str((case.get("thesis") or {}).get("status", "")).upper() == "BROKEN":
            action = "EXIT" if position > 0 else "NO-BUY"
        return {
            "engine_version": ENGINE_VERSION,
            "case_id": case["case_id"], "symbol": case["symbol"], "company": case["company"],
            "cutoff_date": case["cutoff_date"], "validation": validation,
            "gates": {"trust": str((case.get("trust") or {}).get("status", "UNKNOWN")).upper(),
                      "new_buy_add_allowed": False, "evidence_pit": False,
                      "forecast_ready": False, "valuation_ready": False},
            "forecast": forecast,
            "valuation": {},
            "risk": risk,
            "decision": {"action": action, "primary_reason": "VALIDATION_BLOCKED",
                         "position_package_complete": False, "human_approval_required": True,
                         "auto_execution": False},
            "monitoring": case.get("monitoring") or [],
        }
    current_price = dec(valuation["current_price"], "valuation.current_price")
    shares = dec(valuation["shares_outstanding"], "valuation.shares_outstanding")
    required_return = dec(valuation["required_return_pct"], "valuation.required_return_pct") / Decimal("100")
    max_loss = dec(risk["max_loss_pct"], "risk.max_loss_pct") / Decimal("100")

    from .valuation import build_intrinsic_valuation, select_model
    intrinsic = build_intrinsic_valuation(forecast, valuation, shares)
    selection = intrinsic["model_selection"]
    primary_model = selection["primary_model"]
    scenarios = {
        s: {
            "model": primary_model,
            "value_per_share": intrinsic["scenarios"][f"{s}_value_per_share"],
        }
        for s in ("bear", "base", "bull")
    }
    base_value = dec(intrinsic["scenarios"]["base_value_per_share"], "base_value")
    bear_value = dec(intrinsic["scenarios"]["bear_value_per_share"], "bear_value")
    expected_return = base_value / current_price - Decimal("1")
    bear_loss = bear_value / current_price - Decimal("1")

    implied_multiple = dec(valuation.get("market_implied_multiple", valuation["base_multiple"]), "valuation.market_implied_multiple")
    market_cap = current_price * shares
    implied_net_profit = market_cap / implied_multiple
    forecast_net_profit = dec(forecast["base"]["net_profit"], "forecast.base.net_profit")
    expectation_gap = forecast_net_profit / implied_net_profit - Decimal("1")

    trust_status = str(case["trust"].get("status", "UNKNOWN")).upper()
    thesis_status = str(case["thesis"].get("status", "WATCH")).upper()
    position = dec(portfolio.get("position_pct", 0), "portfolio.position_pct")
    can_add = bool(portfolio.get("can_add", True))

    value_gap_pass = expected_return >= required_return and expectation_gap > 0 and bear_loss >= -max_loss
    new_buy_add_allowed = validation["status"] == "PASS" and trust_status == "PASS" and thesis_status != "BROKEN" and value_gap_pass

    if thesis_status == "BROKEN":
        action = "EXIT" if position > 0 else "NO-BUY"
        primary_reason = "THESIS_BROKEN"
    elif position == 0 and validation["status"] != "PASS":
        action = "NO-BUY"
        primary_reason = "VALIDATION_BLOCKED"
    elif position == 0 and trust_status in {"FAIL", "UNKNOWN"}:
        action = "NO-BUY"
        primary_reason = "TRUST_NOT_PASS"
    elif position > 0 and trust_status in {"FAIL", "UNKNOWN"}:
        action = "HOLD"
        primary_reason = "TRUST_GATES_NEW_BUY_ADD_ONLY"
    elif expected_return < 0:
        action = "REDUCE" if position > 0 else "NO-BUY"
        primary_reason = "NEGATIVE_EXPECTED_RETURN"
    elif bear_loss < -max_loss:
        action = "REDUCE" if position > 0 else "NO-BUY"
        primary_reason = "BEAR_DOWNSIDE_EXCEEDS_LIMIT"
    elif new_buy_add_allowed:
        action = "ADD" if position > 0 and can_add else "BUY"
        primary_reason = "VALUE_AND_EXPECTATION_GAP_PASS"
    else:
        action = "HOLD" if position > 0 else "NO-BUY"
        primary_reason = "INSUFFICIENT_MARGIN_OR_EXPECTATION_GAP"

    package_complete = True
    position_package = portfolio.get("buy_add_package") or {}
    if action in {"BUY", "ADD"}:
        package_complete = all(field in position_package for field in (
            "entry_zone", "initial_position_pct", "target_position_pct", "max_position_pct"
        ))
        if not package_complete:
            action = "NO-BUY" if position == 0 else "HOLD"
            primary_reason = "BUY_ADD_PACKAGE_INCOMPLETE"

    return {
        "engine_version": ENGINE_VERSION,
        "case_id": case["case_id"],
        "symbol": case["symbol"],
        "company": case["company"],
        "cutoff_date": case["cutoff_date"],
        "validation": validation,
        "gates": {
            "trust": trust_status,
            "new_buy_add_allowed": new_buy_add_allowed and package_complete,
            "evidence_pit": not any(x.startswith(("PIT_LEAK_", "INVALID_EVIDENCE_DATE_")) for x in blockers),
            "forecast_ready": not any(x.startswith(("CURRENT_PRICE_IN_FORECAST", "INVALID_FORECAST")) for x in blockers),
            "valuation_ready": not any(x.startswith(("INVALID_CURRENT_PRICE", "INVALID_SHARES", "INVALID_BASE", "UNSUPPORTED_MVP")) for x in blockers),
        },
        "forecast": {s: forecast[s] for s in ("bear", "base", "bull")},
        "valuation": {
            "model": primary_model,
            "model_selection": selection,
            "current_price": float(current_price),
            "scenarios": scenarios,
            "intrinsic_value_per_share": float(base_value),
            "intrinsic_value_range": intrinsic["intrinsic_value_range"],
            "model_status": intrinsic["model_status"],
            "model_cross_check_dispersion": intrinsic["model_cross_check_dispersion"],
            "aggregation": intrinsic["aggregation"],
            "expected_return_pct": pct(expected_return * 100),
            "required_return_pct": float(required_return * 100),
            "bear_loss_pct": pct(bear_loss * 100),
            "market_implied_multiple": float(implied_multiple),
            "market_implied_net_profit": float(implied_net_profit),
            "base_forecast_net_profit": float(forecast_net_profit),
            "expectation_gap_pct": pct(expectation_gap * 100),
        },
        "risk": {
            "max_loss_limit_pct": float(max_loss * 100),
            "bear_loss_pct": pct(bear_loss * 100),
            "thesis_breaks": risk["thesis_breaks"],
        },
        "decision": {
            "action": action,
            "primary_reason": primary_reason,
            "position_package_complete": package_complete,
            "human_approval_required": True,
            "auto_execution": False,
        },
        "monitoring": case.get("monitoring") or [],
    }


def run_case(case: dict[str, Any]) -> tuple[dict[str, Any], str]:
    decision = decide(case)
    snapshot = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.1.1",
        "engine_version": ENGINE_VERSION,
        "input": case,
        "decision": decision,
    }
    snapshot["snapshot_hash"] = sha256_obj(snapshot)
    return snapshot, snapshot["snapshot_hash"]


def replay(snapshot: dict[str, Any]) -> dict[str, Any]:
    fresh = decide(snapshot["input"])
    same = canonical_json(fresh) == canonical_json(snapshot["decision"])
    expected_hash = sha256_obj({
        "snapshot_schema": snapshot["snapshot_schema"],
        "engine_version": snapshot["engine_version"],
        "input": snapshot["input"],
        "decision": snapshot["decision"],
    })
    return {
        "snapshot_hash": snapshot.get("snapshot_hash"),
        "engine_version": ENGINE_VERSION,
        "replay_status": "PASS" if same and expected_hash == snapshot.get("snapshot_hash") else "FAIL",
        "same_decision": same,
        "integrity_status": "PASS" if expected_hash == snapshot.get("snapshot_hash") else "FAIL",
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    d = snapshot["decision"]
    v = d["valuation"]
    r = d["risk"]
    inp = snapshot["input"]
    lines = [
        f"# IIOS MVP Investment Decision — {d['company']} ({d['symbol']})",
        f"**Cutoff:** {d['cutoff_date']}  ",
        f"**Action proposal:** **{d['decision']['action']}**  ",
        f"**Reason:** {d['decision']['primary_reason']}",
        "",
        "## 1. Investment Thesis",
        inp["thesis"].get("summary", "未提供"),
        "",
        "## 2. Trust & Evidence",
        f"- Trust: {d['gates']['trust']}",
        f"- Validation: {d['validation']['status']}",
        f"- PIT evidence gate: {d['gates']['evidence_pit']}",
        "",
        "## 3. Reality",
    ]
    for row in inp["reality"].get("periods", []):
        lines.append(f"- {row.get('period')}: value={row.get('value')} known_at={row.get('known_at')} source={row.get('source', '')}")
    lines += [
        "",
        "## 4. Independent Forecast",
        f"- Method: {inp['forecast'].get('method')}",
        f"- Prepared without current price: {not inp['forecast'].get('prepared_using_current_price', True)}",
        f"- Bear / Base / Bull net profit: {inp['forecast']['bear']['net_profit']} / {inp['forecast']['base']['net_profit']} / {inp['forecast']['bull']['net_profit']}",
        "",
        "## 5. Valuation",
        f"- Model: {v['model']}",
        f"- Current price: {v['current_price']}",
        f"- Intrinsic value (Base): {v['intrinsic_value_per_share']:.2f}",
        f"- Expected return: {v['expected_return_pct']:.2f}%",
        f"- Required return: {v['required_return_pct']:.2f}%",
        f"- Bear loss: {v['bear_loss_pct']:.2f}%",
        "",
        "## 6. Market Implied Expectation",
        f"- Implied multiple: {v['market_implied_multiple']:.2f}x",
        f"- Market-implied net profit: {v['market_implied_net_profit']:.2f}",
        f"- Base forecast net profit: {v['base_forecast_net_profit']:.2f}",
        f"- Expectation gap: {v['expectation_gap_pct']:.2f}%",
        "",
        "## 7. Risk & Thesis Breaks",
        f"- Bear loss limit: {r['max_loss_limit_pct']:.2f}%",
    ]
    lines.extend(f"- {x}" for x in r["thesis_breaks"])
    lines += [
        "",
        "## 8. Decision Boundary",
        f"- New BUY/ADD permitted by deterministic gates: {d['gates']['new_buy_add_allowed']}",
        "- Final execution: human approval only; no auto-ordering.",
        "",
        "## 9. Monitoring",
    ]
    for item in d["monitoring"]:
        lines.append(f"- {item.get('metric', '')}: {item.get('condition', '')}")
    return "\n".join(lines) + "\n"
