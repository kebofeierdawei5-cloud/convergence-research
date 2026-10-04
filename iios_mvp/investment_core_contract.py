from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

CONTRACT_VERSION = "IIOS-INVESTMENT-CORE-0.2"
RETURN_HURDLE = Decimal("0.15")

TRUST_STATES = {"PASS", "REVALIDATION", "FAIL", "UNKNOWN"}
THESIS_STATES = {"INTACT", "WATCH", "BROKEN", "UNKNOWN"}
IDENTIFIABILITY_STATES = {"IDENTIFIABLE", "AMBIGUOUS", "UNIDENTIFIABLE", "INSUFFICIENT_EVIDENCE"}
STABILITY_STATES = {"STABLE", "UNSTABLE", "INSUFFICIENT_EVIDENCE"}
DECISION_ACTIONS = {"BUY", "ADD", "HOLD", "REDUCE", "EXIT", "NO-BUY"}
PRICE_ADJUSTMENT_SEMANTICS = {
    "UNADJUSTED",
    "SPLIT_ADJUSTED",
    "DIVIDEND_ADJUSTED",
    "TOTAL_RETURN_ADJUSTED",
    "OTHER_EXPLICIT",
}


def _err(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _date(value: Any, path: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO date YYYY-MM-DD") from exc


def _datetime(value: Any, path: str) -> datetime:
    raw = str(value)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO datetime") from exc


def _decimal(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _required(obj: dict[str, Any], fields: tuple[str, ...], prefix: str, errors: list[dict[str, str]]) -> None:
    for field in fields:
        if field not in obj or obj[field] is None:
            errors.append(_err("CORE-SCHEMA-REQUIRED", f"{prefix}.{field}", "required field is missing"))


def validate_price_observation(
    observation: dict[str, Any],
    cutoff_date: str | date,
    path: str = "current_price_observation",
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(observation, dict):
        return [_err("CORE-SCHEMA-TYPE", path, "must be an object")]

    _required(
        observation,
        ("price", "currency", "observed_at", "known_at", "source", "adjustment_semantics"),
        path,
        errors,
    )
    if errors:
        return errors

    try:
        price = _decimal(observation["price"], f"{path}.price")
        if price <= 0:
            errors.append(_err("CORE-INVARIANT-PRICE-POSITIVE", f"{path}.price", "must be > 0"))
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.price", str(exc)))

    if not isinstance(observation["currency"], str) or not observation["currency"].strip():
        errors.append(_err("CORE-INVARIANT-CURRENCY", f"{path}.currency", "must be a non-empty string"))

    try:
        observed_at = _datetime(observation["observed_at"], f"{path}.observed_at")
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-DATETIME", f"{path}.observed_at", str(exc)))
        observed_at = None

    try:
        known_at = _datetime(observation["known_at"], f"{path}.known_at")
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-DATETIME", f"{path}.known_at", str(exc)))
        known_at = None

    try:
        cutoff = _date(cutoff_date, "cutoff_date")
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-DATE", "cutoff_date", str(exc)))
        cutoff = None

    if observed_at is not None and cutoff is not None and observed_at.date() > cutoff:
        errors.append(_err("CORE-PIT-PRICE", f"{path}.observed_at", "price observation occurs after cutoff_date"))

    if known_at is not None and cutoff is not None and known_at.date() > cutoff:
        errors.append(_err("CORE-PIT-PRICE-KNOWN-AT", f"{path}.known_at", "price became known after cutoff_date"))

    if not isinstance(observation["source"], str) or not observation["source"].strip():
        errors.append(_err("CORE-INVARIANT-SOURCE", f"{path}.source", "must be a non-empty string"))

    semantics = str(observation["adjustment_semantics"]).strip().upper()
    if semantics not in PRICE_ADJUSTMENT_SEMANTICS:
        errors.append(_err(
            "CORE-INVARIANT-PRICE-ADJUSTMENT",
            f"{path}.adjustment_semantics",
            f"unsupported adjustment semantics: {semantics}",
        ))
    if semantics == "OTHER_EXPLICIT" and not str(observation.get("adjustment_note", "")).strip():
        errors.append(_err(
            "CORE-INVARIANT-PRICE-ADJUSTMENT-NOTE",
            f"{path}.adjustment_note",
            "OTHER_EXPLICIT requires adjustment_note",
        ))

    return errors


def validate_probabilities(
    scenarios: dict[str, dict[str, Any]],
    path: str = "return_gate.scenarios",
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    names = ("bear", "base", "bull")
    if not isinstance(scenarios, dict):
        return [_err("CORE-SCHEMA-TYPE", path, "must be an object")]

    probs: list[Decimal] = []
    for name in names:
        item = scenarios.get(name)
        if not isinstance(item, dict):
            errors.append(_err("CORE-SCHEMA-SCENARIO", f"{path}.{name}", "scenario must be an object"))
            continue
        if "probability" not in item:
            errors.append(_err("CORE-SCHEMA-REQUIRED", f"{path}.{name}.probability", "required field is missing"))
            continue
        try:
            p = _decimal(item["probability"], f"{path}.{name}.probability")
            if p < 0 or p > 1:
                errors.append(_err("CORE-INVARIANT-PROBABILITY-RANGE", f"{path}.{name}.probability", "must be in [0,1]"))
            probs.append(p)
        except ValueError as exc:
            errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.{name}.probability", str(exc)))

    if len(probs) == 3 and sum(probs, Decimal("0")) != Decimal("1"):
        errors.append(_err(
            "CORE-INVARIANT-PROBABILITY-SUM",
            path,
            "bear/base/bull probabilities must sum exactly to 1",
        ))
    return errors


def validate_market_implied_expectation(
    expectation: dict[str, Any],
    cutoff_date: str | date,
    path: str = "market_implied_expectation",
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(expectation, dict):
        return [_err("CORE-SCHEMA-TYPE", path, "must be an object")]

    _required(
        expectation,
        (
            "market_model",
            "identifiability",
            "stability",
            "economic_variables",
            "observation_basis",
            "assumption_set",
            "evidence_sufficiency",
        ),
        path,
        errors,
    )
    if errors:
        return errors

    ident = str(expectation["identifiability"]).upper()
    if ident not in IDENTIFIABILITY_STATES:
        errors.append(_err("CORE-INVARIANT-IDENTIFIABILITY", f"{path}.identifiability", f"invalid state: {ident}"))

    stability = str(expectation["stability"]).upper()
    if stability not in STABILITY_STATES:
        errors.append(_err("CORE-INVARIANT-STABILITY", f"{path}.stability", f"invalid state: {stability}"))

    vars_ = expectation["economic_variables"]
    if not isinstance(vars_, list) or not vars_:
        errors.append(_err("CORE-INVARIANT-ECONOMIC-VARIABLES", f"{path}.economic_variables", "must be a non-empty list"))
    else:
        for i, item in enumerate(vars_):
            if not isinstance(item, dict):
                errors.append(_err("CORE-SCHEMA-TYPE", f"{path}.economic_variables[{i}]", "must be an object"))
                continue
            _required(item, ("name", "unit", "basis"), f"{path}.economic_variables[{i}]", errors)

    if not isinstance(expectation["assumption_set"], dict):
        errors.append(_err("CORE-SCHEMA-TYPE", f"{path}.assumption_set", "must be an object"))
    if not isinstance(expectation["evidence_sufficiency"], bool):
        errors.append(_err("CORE-SCHEMA-TYPE", f"{path}.evidence_sufficiency", "must be boolean"))

    basis = expectation["observation_basis"]
    if not isinstance(basis, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", f"{path}.observation_basis", "must be an object"))
    else:
        _required(basis, ("price_observation_date", "cutoff_date"), f"{path}.observation_basis", errors)
        if "cutoff_date" in basis and str(basis["cutoff_date"]) != str(cutoff_date):
            errors.append(_err(
                "CORE-BIND-CUTOFF",
                f"{path}.observation_basis.cutoff_date",
                "must equal case cutoff_date",
            ))

    if ident in {"AMBIGUOUS", "UNIDENTIFIABLE", "INSUFFICIENT_EVIDENCE"} and expectation.get("selected_market_model") is not None:
        errors.append(_err(
            "CORE-INVARIANT-NO-FORCED-WINNER",
            f"{path}.selected_market_model",
            "ambiguous/unidentifiable market expectations cannot declare a selected winner",
        ))
    return errors


def validate_expectation_gap(
    gap: dict[str, Any],
    path: str = "expectation_gap",
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(gap, dict):
        return [_err("CORE-SCHEMA-TYPE", path, "must be an object")]

    _required(
        gap,
        (
            "status",
            "economic_variable",
            "unit",
            "model",
            "independent_value",
            "market_implied_value",
            "gap_direction",
        ),
        path,
        errors,
    )
    if errors:
        return errors

    if not isinstance(gap["economic_variable"], str) or not gap["economic_variable"].strip():
        errors.append(_err("CORE-INVARIANT-GAP-VARIABLE", f"{path}.economic_variable", "must be non-empty"))

    if not isinstance(gap["unit"], str) or not gap["unit"].strip():
        errors.append(_err("CORE-INVARIANT-GAP-UNIT", f"{path}.unit", "must be non-empty"))

    independent = gap["independent_value"]
    market = gap["market_implied_value"]
    for name, value in (("independent_value", independent), ("market_implied_value", market)):
        if not isinstance(value, dict):
            errors.append(_err("CORE-SCHEMA-TYPE", f"{path}.{name}", "must be an object"))
            continue
        _required(value, ("value", "unit", "economic_variable"), f"{path}.{name}", errors)
        if value.get("unit") != gap["unit"]:
            errors.append(_err(
                "CORE-INVARIANT-GAP-UNIT-MISMATCH",
                f"{path}.{name}.unit",
                "must match expectation_gap.unit",
            ))
        if value.get("economic_variable") != gap["economic_variable"]:
            errors.append(_err(
                "CORE-INVARIANT-GAP-VARIABLE-MISMATCH",
                f"{path}.{name}.economic_variable",
                "must match expectation_gap.economic_variable",
            ))
        if "value" in value:
            try:
                _decimal(value["value"], f"{path}.{name}.value")
            except ValueError as exc:
                errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.{name}.value", str(exc)))

    return errors


def validate_return_gate(
    return_gate: dict[str, Any],
    path: str = "return_gate",
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(return_gate, dict):
        return [_err("CORE-SCHEMA-TYPE", path, "must be an object")]

    _required(
        return_gate,
        ("entry_price", "scenario_values", "scenarios", "expected_value", "expected_return_pct", "hurdle_pct", "hurdle_pass"),
        path,
        errors,
    )
    if errors:
        return errors

    try:
        entry = _decimal(return_gate["entry_price"], f"{path}.entry_price")
        if entry <= 0:
            errors.append(_err("CORE-INVARIANT-ENTRY-POSITIVE", f"{path}.entry_price", "must be > 0"))
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.entry_price", str(exc)))
        entry = None

    scenario_values = return_gate["scenario_values"]
    if not isinstance(scenario_values, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", f"{path}.scenario_values", "must be an object"))
    else:
        for name in ("bear", "base", "bull"):
            if name not in scenario_values:
                errors.append(_err("CORE-SCHEMA-REQUIRED", f"{path}.scenario_values.{name}", "required field is missing"))
                continue
            try:
                value = _decimal(scenario_values[name], f"{path}.scenario_values.{name}")
                if value <= 0:
                    errors.append(_err("CORE-INVARIANT-VALUE-POSITIVE", f"{path}.scenario_values.{name}", "must be > 0"))
            except ValueError as exc:
                errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.scenario_values.{name}", str(exc)))

    errors.extend(validate_probabilities(return_gate["scenarios"], f"{path}.scenarios"))

    if entry is not None and isinstance(scenario_values, dict) and all(k in scenario_values for k in ("bear", "base", "bull")):
        probs = return_gate["scenarios"]
        if isinstance(probs, dict) and all(isinstance(probs.get(k), dict) and "probability" in probs[k] for k in ("bear", "base", "bull")):
            try:
                expected_value = sum(
                    _decimal(probs[k]["probability"], f"{path}.scenarios.{k}.probability")
                    * _decimal(scenario_values[k], f"{path}.scenario_values.{k}")
                    for k in ("bear", "base", "bull")
                )
                declared_ev = _decimal(return_gate["expected_value"], f"{path}.expected_value")
                if declared_ev != expected_value:
                    errors.append(_err(
                        "CORE-INVARIANT-EXPECTED-VALUE",
                        f"{path}.expected_value",
                        "must equal probability-weighted scenario value",
                    ))
                expected_return = expected_value / entry - Decimal("1")
                declared_return = _decimal(return_gate["expected_return_pct"], f"{path}.expected_return_pct")
                if declared_return != expected_return * Decimal("100"):
                    errors.append(_err(
                        "CORE-INVARIANT-EXPECTED-RETURN",
                        f"{path}.expected_return_pct",
                        "must equal expected_value / entry_price - 1",
                    ))
            except ValueError as exc:
                errors.append(_err("CORE-SCHEMA-NUMERIC", path, str(exc)))

    try:
        hurdle = _decimal(return_gate["hurdle_pct"], f"{path}.hurdle_pct")
        if hurdle != Decimal("15"):
            errors.append(_err(
                "CORE-INVARIANT-HURDLE",
                f"{path}.hurdle_pct",
                "canonical hurdle is exactly 15%",
            ))
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.hurdle_pct", str(exc)))

    try:
        declared_return = _decimal(return_gate["expected_return_pct"], f"{path}.expected_return_pct")
        declared_pass = bool(return_gate["hurdle_pass"])
        actual_pass = declared_return > Decimal("15")
        if declared_pass != actual_pass:
            errors.append(_err(
                "CORE-INVARIANT-HURDLE-PASS",
                f"{path}.hurdle_pass",
                "must be true iff expected_return_pct is strictly greater than 15%",
            ))
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-NUMERIC", f"{path}.expected_return_pct", str(exc)))

    return errors


def validate_investment_core_case(case: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(case, dict):
        return {"status": "BLOCKED", "errors": [_err("CORE-SCHEMA-TYPE", "$", "case must be an object")]}

    _required(
        case,
        (
            "contract_version",
            "case_id",
            "market",
            "symbol",
            "company",
            "as_of_date",
            "cutoff_date",
            "current_price_observation",
            "trust",
            "reality",
            "forecast",
            "valuation",
            "market_implied_expectation",
            "expectation_gap",
            "return_gate",
            "risk",
            "portfolio",
            "thesis",
            "decision",
        ),
        "$",
        errors,
    )
    if errors:
        return {"status": "BLOCKED", "errors": errors}

    if case["contract_version"] != CONTRACT_VERSION:
        errors.append(_err("CORE-VERSION-EXACT", "contract_version", f"must equal {CONTRACT_VERSION}"))

    try:
        as_of = _date(case["as_of_date"], "as_of_date")
        cutoff = _date(case["cutoff_date"], "cutoff_date")
        if as_of > cutoff:
            errors.append(_err("CORE-INVARIANT-ASOF-CUTOFF", "as_of_date", "as_of_date cannot be after cutoff_date"))
    except ValueError as exc:
        errors.append(_err("CORE-SCHEMA-DATE", "as_of_date/cutoff_date", str(exc)))
        cutoff = None

    for field in ("market", "symbol", "company", "case_id"):
        if not isinstance(case[field], str) or not case[field].strip():
            errors.append(_err("CORE-INVARIANT-IDENTITY", field, "must be a non-empty string"))

    price_errors = validate_price_observation(
        case["current_price_observation"],
        case["cutoff_date"],
    )
    errors.extend(price_errors)

    trust = case["trust"]
    if not isinstance(trust, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", "trust", "must be an object"))
    else:
        status = str(trust.get("status", "UNKNOWN")).upper()
        if status not in TRUST_STATES:
            errors.append(_err("CORE-INVARIANT-TRUST", "trust.status", f"invalid state: {status}"))

    thesis = case["thesis"]
    if not isinstance(thesis, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", "thesis", "must be an object"))
    else:
        status = str(thesis.get("status", "UNKNOWN")).upper()
        if status not in THESIS_STATES:
            errors.append(_err("CORE-INVARIANT-THESIS", "thesis.status", f"invalid state: {status}"))

    errors.extend(validate_market_implied_expectation(case["market_implied_expectation"], case["cutoff_date"]))
    errors.extend(validate_expectation_gap(case["expectation_gap"]))
    errors.extend(validate_return_gate(case["return_gate"]))

    risk = case["risk"]
    if not isinstance(risk, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", "risk", "must be an object"))
    else:
        try:
            max_loss = _decimal(risk.get("max_loss_pct"), "risk.max_loss_pct")
            if max_loss < 0 or max_loss > 100:
                errors.append(_err("CORE-INVARIANT-RISK-LIMIT", "risk.max_loss_pct", "must be within [0,100]"))
        except ValueError as exc:
            errors.append(_err("CORE-SCHEMA-NUMERIC", "risk.max_loss_pct", str(exc)))

    portfolio = case["portfolio"]
    if not isinstance(portfolio, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", "portfolio", "must be an object"))
    else:
        try:
            position = _decimal(portfolio.get("position_pct", 0), "portfolio.position_pct")
            if position < 0 or position > 100:
                errors.append(_err("CORE-INVARIANT-POSITION", "portfolio.position_pct", "must be within [0,100]"))
        except ValueError as exc:
            errors.append(_err("CORE-SCHEMA-NUMERIC", "portfolio.position_pct", str(exc)))

    decision = case["decision"]
    if not isinstance(decision, dict):
        errors.append(_err("CORE-SCHEMA-TYPE", "decision", "must be an object"))
    else:
        action = str(decision.get("action", "")).upper()
        if action not in DECISION_ACTIONS:
            errors.append(_err("CORE-INVARIANT-ACTION", "decision.action", f"invalid action: {action}"))
        if action in {"BUY", "ADD"}:
            trust_status = str(case["trust"].get("status", "UNKNOWN")).upper()
            thesis_status = str(case["thesis"].get("status", "UNKNOWN")).upper()
            market_ident = str(case["market_implied_expectation"].get("identifiability", "UNIDENTIFIABLE")).upper()
            market_stability = str(case["market_implied_expectation"].get("stability", "INSUFFICIENT_EVIDENCE")).upper()
            hurdle_pass = bool(case["return_gate"].get("hurdle_pass", False))
            risk_status = str(risk.get("status", "PASS")).upper() if isinstance(risk, dict) else "UNKNOWN"
            if trust_status != "PASS":
                errors.append(_err("CORE-GATE-BUY-TRUST", "decision.action", "BUY/ADD requires Trust PASS"))
            if thesis_status == "BROKEN":
                errors.append(_err("CORE-GATE-BUY-THESIS", "decision.action", "BUY/ADD is forbidden when thesis is BROKEN"))
            if market_ident != "IDENTIFIABLE":
                errors.append(_err("CORE-GATE-BUY-MARKET-IDENT", "decision.action", "BUY/ADD requires an identifiable market interpretation"))
            if market_stability != "STABLE":
                errors.append(_err("CORE-GATE-BUY-MARKET-STABILITY", "decision.action", "BUY/ADD requires stable market interpretation"))
            if not hurdle_pass:
                errors.append(_err("CORE-GATE-BUY-RETURN", "decision.action", "BUY/ADD requires Expected Return >15%"))
            if risk_status not in {"PASS", "UNKNOWN"}:
                errors.append(_err("CORE-GATE-BUY-RISK", "decision.action", "BUY/ADD requires risk status PASS"))
    return {"status": "PASS" if not errors else "BLOCKED", "errors": errors}


def assert_valid_investment_core_case(case: dict[str, Any]) -> None:
    result = validate_investment_core_case(case)
    if result["status"] != "PASS":
        summary = "; ".join(f'{e["code"]} {e["path"]}: {e["message"]}' for e in result["errors"])
        raise ValueError(summary)
