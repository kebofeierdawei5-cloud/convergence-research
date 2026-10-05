from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .canonical_expectation_gap import evaluate_canonical_expectation_gap
from .evidence_root_admission import EvidenceRootResolver
from .canonical_current_price import CanonicalCurrentPriceResolver, validate_current_price_binding
from .canonical_independent_forecast import CanonicalIndependentForecastResolver
from .horizon_semantics import validate_horizon_selection
from .decision_state_machine_v01 import DecisionStateInputs, evaluate_decision_state
from .price_dependent_expectation_gap import (
    P2_PRICE_GAP_REVALIDATION_VERSION,
    combine_target_entry_price_v2,
    revalidate_expectation_gap_at_price,
)
from .p2_1_canonical_price_response import (
    PRICE_RESPONSE_VERSION,
    build_canonical_price_response,
)
from .canonical_entry_evaluation import (
    CANONICAL_ENTRY_EVALUATION_VERSION,
    admit_decision,
    build_canonical_entry_evaluation,
)

CONTRACT_VERSION = "IIOS-INVESTMENT-CORE-0.3"
BUY_ENTRY_RETURN_CUSHION_THRESHOLD = Decimal("0.15")
FUNDAMENTAL_TARGET_ANNUALIZED_RETURN = Decimal("0.15")

TRUST_STATES = {"PASS", "REVALIDATION", "FAIL", "UNKNOWN"}
THESIS_STATES = {"INTACT", "WATCH", "BROKEN", "UNKNOWN"}
RISK_STATES = {"PASS", "FAIL", "UNKNOWN"}
PORTFOLIO_CONSTRAINT_STATES = {"PASS", "BLOCKED", "UNKNOWN"}
INVESTABILITY_STATES = {"INVESTABLE", "WATCH", "NOT_INVESTABLE", "UNKNOWN"}
DECISION_ACTIONS = {"BUY", "ADD", "HOLD", "REDUCE", "EXIT", "NO-BUY", "WATCH", "REVIEW_REQUIRED"}
DECISION_STATUSES = {"READY", "BLOCKED", "REVIEW_REQUIRED", "SUPERSEDED"}
EXPECTATION_GAP_STATES = {"PASS", "BLOCKED", "INCOMPATIBLE", "AMBIGUOUS", "UNKNOWN"}
SCENARIOS = ("bear", "base", "bull")

def _err(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}

def _dec(value: Any, path: str) -> Decimal:
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not value.is_finite():
        raise ValueError(f"{path} must be finite")
    return value


def _date(value: Any, path: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO date YYYY-MM-DD") from exc


def _datetime(value: Any, path: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO datetime") from exc

def _required(obj: dict[str, Any], fields: tuple[str, ...], path: str, errors: list[dict[str, str]]) -> None:
    for field in fields:
        if field not in obj or obj[field] is None:
            errors.append(_err("V03-SCHEMA-REQUIRED", f"{path}.{field}", "required field is missing"))

def _annualize(ratio: Decimal, horizon: Decimal) -> Decimal:
    if ratio <= 0:
        raise ValueError("terminal wealth / entry price must be > 0")
    if horizon <= 0:
        raise ValueError("horizon_years must be > 0")
    return (ratio.ln() / horizon).exp() - Decimal("1")


def _compound_factor(annual_rate: Decimal, horizon: Decimal) -> Decimal:
    factor_base = Decimal("1") + annual_rate
    if factor_base <= 0:
        raise ValueError("annual rate must be greater than -100%")
    if horizon <= 0:
        raise ValueError("horizon_years must be > 0")
    return (factor_base.ln() * horizon).exp()


def _price_cap_for_annualized_return(
    expected_wealth: Decimal,
    annual_rate: Decimal,
    horizon: Decimal,
) -> Decimal:
    if annual_rate <= Decimal("-1"):
        raise ValueError("annualized target/required return must be greater than -100%")
    return expected_wealth / _compound_factor(annual_rate, horizon)


def _price_cap_for_risk(
    bear_wealth: Decimal,
    max_loss_rate: Decimal | None,
) -> Decimal | None:
    if max_loss_rate is None:
        return None
    if max_loss_rate < Decimal("0") or max_loss_rate >= Decimal("1"):
        raise ValueError("max_loss_pct must be within [0,100)")
    return bear_wealth / (Decimal("1") - max_loss_rate)


def calculate_return_metrics(
    return_gate: dict[str, Any],
    *,
    max_loss_pct: Any | None = None,
) -> dict[str, Any]:
    entry = _dec(return_gate["entry_price"], "return_gate.entry_price")
    entry_ref = _dec(return_gate["entry_value_reference"], "return_gate.entry_value_reference")
    horizon_selection = validate_horizon_selection(
        horizon_years=return_gate["horizon_years"],
        horizon_override=return_gate["horizon_override"],
        horizon_override_basis=return_gate["horizon_override_basis"],
        horizon_selection_rationale=return_gate["horizon_selection_rationale"],
        path="return_gate",
    )
    horizon = _dec(horizon_selection["horizon_years"], "return_gate.horizon_years")
    threshold = _dec(return_gate["buy_entry_return_cushion_threshold"], "return_gate.buy_entry_return_cushion_threshold")
    target = _dec(return_gate["fundamental_target_annualized_return"], "return_gate.fundamental_target_annualized_return")
    rr = _dec(return_gate["required_return_annualized"], "return_gate.required_return_annualized")
    if entry <= 0 or entry_ref <= 0:
        raise ValueError("entry_price and entry_value_reference must be > 0")
    if threshold != BUY_ENTRY_RETURN_CUSHION_THRESHOLD:
        raise ValueError("buy_entry_return_cushion_threshold must equal 15%")
    if target != FUNDAMENTAL_TARGET_ANNUALIZED_RETURN:
        raise ValueError("fundamental_target_annualized_return must equal 15%")
    if rr <= Decimal("-1"):
        raise ValueError("required_return_annualized must be > -100%")

    risk_rate: Decimal | None = None
    if max_loss_pct is not None:
        risk_rate = _dec(max_loss_pct, "risk.max_loss_pct") / Decimal("100")

    scenarios = return_gate["scenarios"]
    probabilities = []
    wealth = {}
    for name in SCENARIOS:
        item = scenarios[name]
        p = _dec(item["probability"], f"return_gate.scenarios.{name}.probability")
        terminal = _dec(item["terminal_value_per_share"], f"return_gate.scenarios.{name}.terminal_value_per_share")
        distributions = _dec(item["cash_distributions_per_share"], f"return_gate.scenarios.{name}.cash_distributions_per_share")
        rationale = str(item.get("probability_rationale", "")).strip()
        if p < 0 or p > 1:
            raise ValueError(f"return_gate.scenarios.{name}.probability must be in [0,1]")
        if terminal < 0 or distributions < 0:
            raise ValueError(f"return_gate.scenarios.{name} terminal value/distributions must be >= 0")
        if not rationale:
            raise ValueError(f"return_gate.scenarios.{name}.probability_rationale is required")
        probabilities.append(p)
        wealth[name] = terminal + distributions
    if sum(probabilities, Decimal("0")) != Decimal("1"):
        raise ValueError("scenario probabilities must sum exactly to 1")
    expected_wealth = sum(
        _dec(scenarios[name]["probability"], f"return_gate.scenarios.{name}.probability") * wealth[name]
        for name in SCENARIOS
    )
    total_return = expected_wealth / entry - Decimal("1")
    annualized_return = _annualize(expected_wealth / entry, horizon)
    entry_cushion = entry_ref / entry - Decimal("1")
    mos = Decimal("1") - (entry / entry_ref)
    entry_pass = entry_cushion >= threshold
    target_pass = annualized_return >= target
    rr_pass = annualized_return >= rr
    bear_return = wealth["bear"] / entry - Decimal("1")
    risk_pass = True if risk_rate is None else bear_return >= -risk_rate

    target_entry_price_for_return = _price_cap_for_annualized_return(
        expected_wealth, target, horizon
    )
    target_entry_price_for_required_return = _price_cap_for_annualized_return(
        expected_wealth, rr, horizon
    )
    target_entry_price_for_entry_cushion = entry_ref / (Decimal("1") + threshold)
    target_entry_price_for_risk = _price_cap_for_risk(wealth["bear"], risk_rate)

    price_caps = [
        target_entry_price_for_return,
        target_entry_price_for_required_return,
        target_entry_price_for_entry_cushion,
    ]
    if target_entry_price_for_risk is not None:
        price_caps.append(target_entry_price_for_risk)
    target_entry_price = min(price_caps)

    return {
        "entry_return_cushion": entry_cushion,
        "margin_of_safety": mos,
        "horizon_years": horizon_selection["horizon_years"],
        "horizon_override": horizon_selection["horizon_override"],
        "horizon_override_basis": horizon_selection["horizon_override_basis"],
        "horizon_selection_rationale": horizon_selection["horizon_selection_rationale"],
        "scenario_terminal_wealth": wealth,
        "expected_terminal_wealth": expected_wealth,
        "expected_total_return": total_return,
        "expected_annualized_return": annualized_return,
        "buy_entry_return_cushion_pass": entry_pass,
        "fundamental_target_pass": target_pass,
        "required_return_pass": rr_pass,
        "bear_return": bear_return,
        "risk_pass": risk_pass,
        "target_entry_price_for_return": target_entry_price_for_return,
        "target_entry_price_for_required_return": target_entry_price_for_required_return,
        "target_entry_price_for_entry_cushion": target_entry_price_for_entry_cushion,
        "target_entry_price_for_risk": target_entry_price_for_risk,
        "target_entry_price": target_entry_price,
        "target_entry_price_binding": "MIN_OF_RETURN_REQUIRED_RETURN_ENTRY_CUSHION_AND_RISK_CAPS",
        "target_entry_price_semantics": "CONDITIONAL_THRESHOLD_REQUIRES_EXPECTATION_GAP_REVALIDATION",
        "target_entry_price_requires_gap_revalidation": True,
        "return_gate_pass": entry_pass and target_pass and rr_pass and risk_pass,
    }

def validate_return_gate_v03(return_gate: Any, path: str = "return_gate") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(return_gate, dict):
        return [_err("V03-SCHEMA-TYPE", path, "must be an object")]
    fields = (
        "entry_price", "entry_value_reference", "horizon_years",
        "horizon_override", "horizon_override_basis", "horizon_selection_rationale",
        "buy_entry_return_cushion_threshold", "fundamental_target_annualized_return",
        "required_return_annualized", "scenarios",
    )
    _required(return_gate, fields, path, errors)
    if errors:
        return errors
    scenarios = return_gate["scenarios"]
    if not isinstance(scenarios, dict):
        return [_err("V03-SCHEMA-TYPE", f"{path}.scenarios", "must be an object")]
    for name in SCENARIOS:
        item = scenarios.get(name)
        if not isinstance(item, dict):
            errors.append(_err("V03-SCHEMA-SCENARIO", f"{path}.scenarios.{name}", "must be an object"))
            continue
        _required(item, ("probability", "terminal_value_per_share", "cash_distributions_per_share", "probability_rationale"), f"{path}.scenarios.{name}", errors)
    if errors:
        return errors
    try:
        calculate_return_metrics(return_gate)
    except ValueError as exc:
        errors.append(_err("V03-INVARIANT-RETURN", path, str(exc)))
    return errors

def _serialize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Convert exact Decimal metrics to JSON-stable strings without losing precision."""
    out: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, Decimal):
            out[key] = str(value)
        elif isinstance(value, dict):
            out[key] = {
                subkey: (str(subvalue) if isinstance(subvalue, Decimal) else subvalue)
                for subkey, subvalue in value.items()
            }
        else:
            out[key] = value
    return out


def _serialize_nested(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _serialize_nested(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_nested(v) for v in value]
    return value


def _position(case: dict[str, Any]) -> Decimal:
    return _dec((case.get("portfolio") or {}).get("position_pct", "0"), "portfolio.position_pct")

def _portfolio_status(case: dict[str, Any]) -> str:
    return str((case.get("portfolio") or {}).get("constraint_status", "UNKNOWN")).upper()

def _risk_status(case: dict[str, Any]) -> str:
    return str((case.get("risk") or {}).get("status", "UNKNOWN")).upper()

def validate_case_v03(case: Any, *, evidence_root_resolver: EvidenceRootResolver | None = None, current_price_resolver: CanonicalCurrentPriceResolver | None = None, independent_forecast_resolver: CanonicalIndependentForecastResolver | None = None) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(case, dict):
        return {"status": "BLOCKED", "errors": [_err("V03-SCHEMA-TYPE", "$", "case must be an object")]}
    required = (
        "contract_version", "case_id", "market", "symbol", "company",
        "as_of_date", "cutoff_date", "current_price_observation",
        "company_evidence_manifest", "trust", "reality", "forecast",
        "valuation", "risk", "portfolio", "thesis", "return_gate",
    )
    _required(case, required, "$", errors)
    if errors:
        return {"status": "BLOCKED", "errors": errors}
    if case["contract_version"] != CONTRACT_VERSION:
        errors.append(_err("V03-VERSION-EXACT", "contract_version", f"must equal {CONTRACT_VERSION}"))
    try:
        as_of = _date(case["as_of_date"], "as_of_date")
        cutoff = _date(case["cutoff_date"], "cutoff_date")
        if as_of > cutoff:
            errors.append(_err("V03-ASOF-CUTOFF", "as_of_date", "as_of_date cannot be after cutoff_date"))
    except ValueError as exc:
        errors.append(_err("V03-DATE", "as_of_date/cutoff_date", str(exc)))
        cutoff = None
    try:
        obs = _datetime(case["current_price_observation"]["observed_at"], "current_price_observation.observed_at")
        known = _datetime(case["current_price_observation"]["known_at"], "current_price_observation.known_at")
        if cutoff is not None and obs.date() > cutoff:
            errors.append(_err("V03-PIT-PRICE", "current_price_observation.observed_at", "price observation occurs after cutoff_date"))
        if cutoff is not None and known.date() > cutoff:
            errors.append(_err("V03-PIT-PRICE-KNOWN-AT", "current_price_observation.known_at", "price became known after cutoff_date"))
    except (KeyError, ValueError) as exc:
        errors.append(_err("V03-PIT-PRICE", "current_price_observation", str(exc)))
    try:
        price = _dec(case["current_price_observation"]["price"], "current_price_observation.price")
        if price <= 0:
            errors.append(_err("V03-PRICE-POSITIVE", "current_price_observation.price", "must be > 0"))
    except (KeyError, ValueError) as exc:
        errors.append(_err("V03-PRICE", "current_price_observation.price", str(exc)))
    if not str(case["current_price_observation"].get("price_observation_id", "")).strip():
        errors.append(
            _err(
                "V03-PRICE-OBSERVATION-ID",
                "current_price_observation.price_observation_id",
                "price_observation_id is required for canonical price evidence",
            )
        )
    if not str(case["current_price_observation"].get("price_observation_admission_hash", "")).strip():
        errors.append(
            _err(
                "V03-PRICE-ADMISSION-HASH",
                "current_price_observation.price_observation_admission_hash",
                "price_observation_admission_hash is required for canonical price evidence",
            )
        )
    if current_price_resolver is None:
        errors.append(
            _err(
                "V03-PRICE-RESOLVER",
                "current_price_observation",
                "canonical current price resolver is required at runtime",
            )
        )
    else:
        try:
            canonical_price = current_price_resolver.resolve_current_price(
                {
                    "price_observation_id": case["current_price_observation"].get("price_observation_id", ""),
                    "admission_record_hash": case["current_price_observation"].get("price_observation_admission_hash", ""),
                },
                case_id=case["case_id"],
                market=case["market"],
                symbol=case["symbol"],
                cutoff_date=cutoff,
            )
            validate_current_price_binding(case["current_price_observation"], canonical_price)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(
                _err(
                    "V03-PRICE-CANONICAL",
                    "current_price_observation",
                    str(exc),
                )
            )
    try:
        position = _position(case)
        if position < 0 or position > 100:
            errors.append(_err("V03-POSITION", "portfolio.position_pct", "must be within [0,100]"))
    except ValueError as exc:
        errors.append(_err("V03-POSITION", "portfolio.position_pct", str(exc)))
    trust = case["trust"]
    if not isinstance(trust, dict) or str(trust.get("status", "UNKNOWN")).upper() not in TRUST_STATES:
        errors.append(_err("V03-TRUST", "trust.status", "invalid Trust state"))
    thesis = case["thesis"]
    if not isinstance(thesis, dict) or str(thesis.get("status", "UNKNOWN")).upper() not in THESIS_STATES:
        errors.append(_err("V03-THESIS", "thesis.status", "invalid Thesis state"))
    risk = case["risk"]
    if not isinstance(risk, dict) or _risk_status(case) not in RISK_STATES:
        errors.append(_err("V03-RISK", "risk.status", "invalid Risk state"))
    elif "max_loss_pct" not in risk or risk["max_loss_pct"] is None:
        errors.append(
            _err(
                "V03-RISK-MAX-LOSS-REQUIRED",
                "risk.max_loss_pct",
                "max_loss_pct is required for v0.3 risk fail-closed semantics",
            )
        )
    else:
        try:
            max_loss = _dec(risk["max_loss_pct"], "risk.max_loss_pct")
            if max_loss < 0 or max_loss >= 100:
                errors.append(_err("V03-RISK-MAX-LOSS", "risk.max_loss_pct", "must be within [0,100)"))
        except ValueError as exc:
            errors.append(_err("V03-RISK-MAX-LOSS", "risk.max_loss_pct", str(exc)))
    portfolio = case["portfolio"]
    if not isinstance(portfolio, dict) or _portfolio_status(case) not in PORTFOLIO_CONSTRAINT_STATES:
        errors.append(_err("V03-PORTFOLIO", "portfolio.constraint_status", "invalid Portfolio Constraint state"))
    errors.extend(validate_return_gate_v03(case["return_gate"]))

    try:
        observed_price = _dec(
            case["current_price_observation"]["price"],
            "current_price_observation.price",
        )
        entry_price = _dec(
            case["return_gate"]["entry_price"],
            "return_gate.entry_price",
        )
        if observed_price != entry_price:
            errors.append(
                _err(
                    "V03-CURRENT-PRICE-BIND",
                    "return_gate.entry_price",
                    "must equal current_price_observation.price for current-price decision",
                )
            )
    except (KeyError, ValueError):
        pass

    if "target_entry_price_reference" in case and "expectation_gap" in case:
        errors.append(_err(
            "V03-TARGET-ENTRY-REF-CONFLICT",
            "target_entry_price_reference",
            "target_entry_price_reference and expectation_gap cannot coexist; "
            "the target-entry MIE/forecast binding must use one canonical path",
        ))
    target_entry_reference = case.get("target_entry_price_reference")
    if target_entry_reference is not None:
        if not isinstance(target_entry_reference, dict):
            errors.append(_err(
                "V03-TARGET-ENTRY-REF-TYPE",
                "target_entry_price_reference",
                "must be an object",
            ))
        else:
            required_ref_fields = {"market_expectation_id", "independent_forecast_ref"}
            if set(target_entry_reference) != required_ref_fields:
                errors.append(_err(
                    "V03-TARGET-ENTRY-REF-FIELDS",
                    "target_entry_price_reference",
                    "must contain exactly market_expectation_id and independent_forecast_ref",
                ))
            else:
                forecast_ref = target_entry_reference.get("independent_forecast_ref")
                if not isinstance(forecast_ref, dict):
                    errors.append(_err(
                        "V03-TARGET-ENTRY-REF-FORECAST",
                        "target_entry_price_reference.independent_forecast_ref",
                        "canonical independent forecast reference is required",
                    ))
                else:
                    if set(forecast_ref) != {"forecast_id", "admission_record_hash"}:
                        errors.append(_err(
                            "V03-TARGET-ENTRY-REF-FORECAST-FIELDS",
                            "target_entry_price_reference.independent_forecast_ref",
                            "must contain exactly forecast_id and admission_record_hash",
                        ))
                    if evidence_root_resolver is None:
                        errors.append(_err(
                            "V03-TARGET-ENTRY-REF-RESOLVER",
                            "target_entry_price_reference",
                            "canonical evidence root resolver is required at runtime",
                        ))
                    elif not isinstance(case.get("market_implied_expectation_snapshot_ref"), dict):
                        errors.append(_err(
                            "V03-TARGET-ENTRY-REF-SNAPSHOT",
                            "market_implied_expectation_snapshot_ref",
                            "canonical evidence root reference is required when target_entry_price_reference is supplied",
                        ))
    expectation_gap = case.get("expectation_gap")
    if expectation_gap is not None:
        precondition_failed = False
        try:
            decision_horizon = str(
                validate_horizon_selection(
                    horizon_years=case["return_gate"]["horizon_years"],
                    horizon_override=case["return_gate"]["horizon_override"],
                    horizon_override_basis=case["return_gate"]["horizon_override_basis"],
                    horizon_selection_rationale=case["return_gate"]["horizon_selection_rationale"],
                    path="return_gate",
                )["horizon_years"]
            )
            forecast_ref = expectation_gap.get("independent_forecast_ref")
            if not isinstance(forecast_ref, dict):
                errors.append(
                    _err(
                        "V03-INDEPENDENT-FORECAST-REF",
                        "expectation_gap.independent_forecast_ref",
                        "canonical independent forecast reference is required",
                    )
                )
                precondition_failed = True
            elif independent_forecast_resolver is None:
                errors.append(
                    _err(
                        "V03-INDEPENDENT-FORECAST-RESOLVER",
                        "expectation_gap.independent_forecast_ref",
                        "canonical independent forecast resolver is required at runtime",
                    )
                )
                precondition_failed = True
            else:
                try:
                    forecast_record = independent_forecast_resolver.resolve_independent_forecast(
                        forecast_ref,
                        case_id=case["case_id"],
                        market=case["market"],
                        symbol=case["symbol"],
                        cutoff_date=cutoff,
                    )
                    gap_horizon = _dec(
                        forecast_record["horizon_years"],
                        "canonical independent forecast.horizon_years",
                    )
                    if gap_horizon != _dec(
                        decision_horizon,
                        "return_gate.horizon_years",
                    ):
                        errors.append(
                            _err(
                                "V03-EXPECTATION-GAP-HORIZON",
                                "expectation_gap.independent_forecast_ref",
                                "canonical forecast horizon must equal the decision horizon selected by return_gate",
                            )
                        )
                        precondition_failed = True
                except (KeyError, TypeError, ValueError):
                    # Canonical expectation-gap evaluation below emits the authoritative blocker.
                    pass
            gap_price = _dec(expectation_gap["price"], "expectation_gap.price")
            observed_price = _dec(
                case["current_price_observation"]["price"],
                "current_price_observation.price",
            )
            if gap_price != observed_price:
                errors.append(
                    _err(
                        "V03-EXPECTATION-GAP-PRICE",
                        "expectation_gap.price",
                        "must equal current_price_observation.price; gap must be revalidated when price changes",
                    )
                )
                precondition_failed = True
        except (KeyError, TypeError, ValueError):
            # Canonical boundary below produces the authoritative blocker for malformed input.
            pass

        if not precondition_failed:
            try:
                _canonical_expectation_gap(expectation_gap, case, evidence_root_resolver=evidence_root_resolver, independent_forecast_resolver=independent_forecast_resolver)
            except ValueError as exc:
                errors.append(
                    _err(
                        "V03-EXPECTATION-GAP-CANONICAL",
                        "expectation_gap",
                        str(exc),
                    )
                )

    if "market_implied_expectation_snapshot" in case:
        errors.append(
            _err(
                "V03-EVIDENCE-ROOT-INLINE",
                "market_implied_expectation_snapshot",
                "embedded P4-F snapshot is not accepted; use market_implied_expectation_snapshot_ref",
            )
        )
    mie_snapshot_ref = case.get("market_implied_expectation_snapshot_ref")
    if mie_snapshot_ref is not None and not isinstance(mie_snapshot_ref, dict):
        errors.append(
            _err(
                "V03-EVIDENCE-ROOT-REF-TYPE",
                "market_implied_expectation_snapshot_ref",
                "canonical evidence root reference must be an object when supplied",
            )
        )
    if expectation_gap is not None:
        if not isinstance(mie_snapshot_ref, dict):
            errors.append(
                _err(
                    "V03-EVIDENCE-ROOT-REF-REQUIRED",
                    "market_implied_expectation_snapshot_ref",
                    "canonical evidence root reference is required when expectation_gap is supplied",
                )
            )
        elif evidence_root_resolver is None:
            errors.append(
                _err(
                    "V03-EVIDENCE-ROOT-RESOLVER",
                    "market_implied_expectation_snapshot_ref",
                    "canonical evidence root resolver is required at runtime",
                )
            )
    decision = case.get("decision")
    if decision is not None:
        if not isinstance(decision, dict):
            errors.append(_err("V03-DECISION-TYPE", "decision", "must be an object"))
        else:
            action = str(decision.get("action", "")).upper()
            status = str(decision.get("decision_status", "READY")).upper()
            if action not in DECISION_ACTIONS:
                errors.append(_err("V03-ACTION", "decision.action", f"invalid action: {action}"))
            if status not in DECISION_STATUSES:
                errors.append(_err("V03-DECISION-STATUS", "decision.decision_status", f"invalid status: {status}"))
    return {"status": "PASS" if not errors else "BLOCKED", "errors": errors}

def _canonical_expectation_gap(payload: Any, case: dict[str, Any], *, evidence_root_resolver: EvidenceRootResolver | None = None, independent_forecast_resolver: CanonicalIndependentForecastResolver | None = None) -> dict[str, Any]:
    mie_ref = case.get("market_implied_expectation_snapshot_ref")
    if not isinstance(mie_ref, dict):
        raise ValueError("market_implied_expectation_snapshot_ref is required for a canonical expectation gap")
    if evidence_root_resolver is None:
        raise ValueError("canonical evidence root resolver is required for a canonical expectation gap")
    try:
        snapshot = evidence_root_resolver.resolve_p4f_snapshot(
            mie_ref,
            case_id=case["case_id"],
            cutoff_date=_date(case["cutoff_date"], "cutoff_date"),
        )
        return evaluate_canonical_expectation_gap(
            payload,
            market_implied_expectation_snapshot=snapshot,
            current_price=case["current_price_observation"]["price"],
            current_price_observation=case["current_price_observation"],
            cutoff_date=case["cutoff_date"],
            case_id=case["case_id"],
            market=case["market"],
            symbol=case["symbol"],
            independent_forecast_resolver=independent_forecast_resolver,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def _expectation_gap(case: dict[str, Any], *, evidence_root_resolver: EvidenceRootResolver | None = None, independent_forecast_resolver: CanonicalIndependentForecastResolver | None = None) -> tuple[str, Decimal | None]:
    payload = case.get("expectation_gap")
    if payload is None:
        return "UNKNOWN", None
    try:
        evaluated = _canonical_expectation_gap(payload, case, evidence_root_resolver=evidence_root_resolver, independent_forecast_resolver=independent_forecast_resolver)
    except ValueError:
        return "UNKNOWN", None
    status = str(evaluated["status"]).upper()
    gap = evaluated.get("gap_relative")
    return status, gap if isinstance(gap, Decimal) else None


def decide_v03(case: dict[str, Any], *, evidence_root_resolver: EvidenceRootResolver | None = None, current_price_resolver: CanonicalCurrentPriceResolver | None = None, independent_forecast_resolver: CanonicalIndependentForecastResolver | None = None) -> dict[str, Any]:
    validation = validate_case_v03(case, evidence_root_resolver=evidence_root_resolver, current_price_resolver=current_price_resolver, independent_forecast_resolver=independent_forecast_resolver)
    position = _position(case) if isinstance(case.get("portfolio"), dict) else Decimal("0")
    trust_status = str((case.get("trust") or {}).get("status", "UNKNOWN")).upper()
    thesis_status = str((case.get("thesis") or {}).get("status", "UNKNOWN")).upper()
    risk_status = _risk_status(case)
    portfolio_status = _portfolio_status(case)
    gap_status, gap_relative = _expectation_gap(case, evidence_root_resolver=evidence_root_resolver, independent_forecast_resolver=independent_forecast_resolver)
    gap_positive = gap_status == "PASS" and gap_relative is not None and gap_relative > 0

    metrics = None
    if validation["status"] == "PASS":
        try:
            metrics = calculate_return_metrics(
                case["return_gate"],
                max_loss_pct=(case.get("risk") or {}).get("max_loss_pct"),
            )
        except ValueError:
            metrics = None

    current_price: Decimal | None = None
    try:
        current_price = _dec(
            case["current_price_observation"]["price"],
            "current_price_observation.price",
        )
    except (KeyError, ValueError):
        pass

    gates = {
        "trust": trust_status,
        "horizon_years": metrics["horizon_years"] if metrics else None,
        "horizon_override": metrics["horizon_override"] if metrics else None,
        "horizon_override_basis": metrics["horizon_override_basis"] if metrics else [],
        "portfolio_constraint": portfolio_status,
        "risk": risk_status,
        "thesis": thesis_status,
        "expectation_gap_status": gap_status,
        "positive_expectation_gap_pass": gap_positive,
        "expectation_gap_required_for_buy_add": True,
        "current_price": str(current_price) if current_price is not None else None,
        "new_capital_allowed": False,
    }

    package = (case.get("portfolio") or {}).get("buy_add_package") or {}
    package_fields = (
        "entry_zone",
        "initial_position_pct",
        "target_position_pct",
        "max_position_pct",
        "thesis_break_triggers",
        "monitoring_triggers",
    )
    package_complete = all(field in package for field in package_fields)
    can_add = bool((case.get("portfolio") or {}).get("can_add", True))

    state = evaluate_decision_state(
        DecisionStateInputs(
            validation_pass=validation["status"] == "PASS",
            trust_status=trust_status,
            thesis_status=thesis_status,
            risk_status=risk_status,
            portfolio_status=portfolio_status,
            position_pct=position,
            gap_status=gap_status,
            gap_positive=gap_positive,
            expected_annualized_return=(
                metrics["expected_annualized_return"] if metrics is not None else None
            ),
            return_gate_pass=(
                metrics["return_gate_pass"] if metrics is not None else False
            ),
            risk_gate_pass=(
                metrics["risk_pass"] if metrics is not None else False
            ),
            can_add=can_add,
            package_complete=package_complete,
            return_metrics_ready=metrics is not None,
        )
    )

    action = state["action"]
    status = "REVIEW_REQUIRED" if action == "REVIEW_REQUIRED" else "READY"
    reason = state["primary_reason"]
    investability = (
        "UNKNOWN" if action == "REVIEW_REQUIRED"
        else "INVESTABLE" if action in {"BUY", "ADD"}
        else "WATCH" if action in {"HOLD", "WATCH"}
        else "NOT_INVESTABLE"
    )
    gates["new_capital_allowed"] = state["new_capital_allowed"]
    gates["decision_precedence_version"] = state["precedence_version"]
    gates["decision_precedence_rule_id"] = state["precedence_rule_id"]
    gates["decision_precedence_rank"] = state["precedence_rank"]
    gates["decision_scope"] = state["decision_scope"]
    gates["capital_effect"] = state["capital_effect"]
    p2_revalidation = None
    p2_target = None
    p2_1_price_response = None
    canonical_entry_evaluation = None

    target_ref = (
        case.get("target_entry_price_reference")
        if isinstance(case.get("target_entry_price_reference"), dict)
        else None
    )
    # Canonical expectation-gap cases reuse the same admitted MIE + forecast identity.
    if target_ref is None and isinstance(case.get("expectation_gap"), dict):
        target_ref = {
            "market_expectation_id": case["expectation_gap"]["market_expectation_id"],
            "independent_forecast_ref": case["expectation_gap"]["independent_forecast_ref"],
        }

    if metrics is not None and target_ref is not None:
        try:
            if evidence_root_resolver is None:
                raise ValueError("canonical evidence root resolver is required for P2.1 target-entry revalidation")
            if independent_forecast_resolver is None:
                raise ValueError("canonical independent forecast resolver is required for P2.1 target-entry revalidation")
            snapshot = evidence_root_resolver.resolve_p4f_snapshot(
                case["market_implied_expectation_snapshot_ref"],
                case_id=case["case_id"],
                cutoff_date=_date(case["cutoff_date"], "cutoff_date"),
            )
            p2_1_price_response = build_canonical_price_response(
                market_implied_expectation_snapshot=snapshot,
                current_price_observation=case["current_price_observation"],
                candidate_price=metrics["target_entry_price"],
                cutoff_date=case["cutoff_date"],
                case_id=case["case_id"],
                market=case["market"],
                symbol=case["symbol"],
                market_expectation_id=target_ref["market_expectation_id"],
                independent_forecast_ref=target_ref["independent_forecast_ref"],
                independent_forecast_resolver=independent_forecast_resolver,
            )
            p2_target = combine_target_entry_price_v2(
                return_target_entry_price=metrics["target_entry_price"],
                revalidation=p2_1_price_response,
            )
        except (KeyError, TypeError, ValueError) as exc:
            p2_1_price_response = {
                "status": "REVIEW_REQUIRED",
                "response_version": PRICE_RESPONSE_VERSION,
                "reason": str(exc),
                "candidate_price": str(metrics["target_entry_price"]),
            }
            p2_target = {
                "status": "REVIEW_REQUIRED",
                "target_entry_price": None,
                "return_target_entry_price": str(metrics["target_entry_price"]),
                "expectation_gap_price_boundary": None,
                "binding": "P2.1_PRICE_RESPONSE_UNRESOLVED",
                "price_constraint_type": None,
                "target_entry_price_inclusive": False,
                "reason": str(exc),
            }

    if metrics is not None and isinstance(case.get("expectation_gap"), dict):
        try:
            if evidence_root_resolver is None:
                raise ValueError("canonical evidence root resolver is required for P2 target-entry revalidation")
            p2_revalidation = revalidate_expectation_gap_at_price(
                market_implied_expectation_snapshot=evidence_root_resolver.resolve_p4f_snapshot(
                    case["market_implied_expectation_snapshot_ref"],
                    case_id=case["case_id"],
                    cutoff_date=_date(case["cutoff_date"], "cutoff_date"),
                ),
                current_price_observation=case["current_price_observation"],
                candidate_price=metrics["target_entry_price"],
                cutoff_date=case["cutoff_date"],
                case_id=case["case_id"],
                market=case["market"],
                symbol=case["symbol"],
                market_expectation_id=case["expectation_gap"]["market_expectation_id"],
                independent_forecast_ref=case["expectation_gap"]["independent_forecast_ref"],
                independent_forecast_resolver=independent_forecast_resolver,
            )
        except (KeyError, TypeError, ValueError) as exc:
            p2_revalidation = {
                "status": "REVIEW_REQUIRED",
                "reason": str(exc),
                "reference_snapshot_hash": (
                    case.get("expectation_gap", {}).get("mie_snapshot_hash")
                    if isinstance(case.get("expectation_gap"), dict)
                    else None
                ),
                "candidate_price": str(metrics["target_entry_price"]),
            }

    if metrics is not None:
        try:
            canonical_entry_evaluation = build_canonical_entry_evaluation(
                current_price=current_price,
                return_target_entry_price=metrics["target_entry_price"],
                p2_1_price_response=p2_1_price_response,
                entry_reference_source=(
                    "TARGET_ENTRY_REFERENCE"
                    if isinstance(case.get("target_entry_price_reference"), dict)
                    else "EXPECTATION_GAP"
                    if isinstance(case.get("expectation_gap"), dict)
                    else "NONE"
                ),
                market_expectation_id=(
                    target_ref.get("market_expectation_id")
                    if isinstance(target_ref, dict)
                    else None
                ),
                independent_forecast_ref=(
                    target_ref.get("independent_forecast_ref")
                    if isinstance(target_ref, dict)
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            canonical_entry_evaluation = {
                "evaluation_id": None,
                "evaluation_version": CANONICAL_ENTRY_EVALUATION_VERSION,
                "status": "REVIEW_REQUIRED",
                "qualification": "UNKNOWN",
                "current_price": str(current_price) if current_price is not None else None,
                "return_target_entry_price": str(metrics["target_entry_price"]),
                "entry_reference_source": (
                    "TARGET_ENTRY_REFERENCE"
                    if isinstance(case.get("target_entry_price_reference"), dict)
                    else "EXPECTATION_GAP"
                    if isinstance(case.get("expectation_gap"), dict)
                    else "NONE"
                ),
                "market_expectation_id": target_ref.get("market_expectation_id") if isinstance(target_ref, dict) else None,
                "independent_forecast_ref": target_ref.get("independent_forecast_ref") if isinstance(target_ref, dict) else None,
                "effective_target_entry_price": None,
                "price_constraint_type": None,
                "target_entry_price_inclusive": False,
                "current_price_eligible": False,
                "binding": "CANONICAL_ENTRY_EVALUATION_ERROR",
                "binding_components": [],
                "reason": str(exc),
                "p2_1_response_version": PRICE_RESPONSE_VERSION if p2_1_price_response is not None else None,
                "p2_1_response_id": p2_1_price_response.get("response_id") if isinstance(p2_1_price_response, dict) else None,
                "p2_1_response_hash": None,
                "snapshot_hash": p2_1_price_response.get("snapshot_hash") if isinstance(p2_1_price_response, dict) else None,
                "model_id": p2_1_price_response.get("model_id") if isinstance(p2_1_price_response, dict) else None,
                "expectation_id": p2_1_price_response.get("expectation_id") if isinstance(p2_1_price_response, dict) else None,
            }

    entry_admission = admit_decision(
        pre_admission_action=state["action"],
        pre_admission_status=("REVIEW_REQUIRED" if state["action"] == "REVIEW_REQUIRED" else "READY"),
        pre_admission_reason=state["primary_reason"],
        pre_admission_capital_effect=state["capital_effect"],
        position_pct=position,
        entry_evaluation=canonical_entry_evaluation,
    )

    action = entry_admission["action"]
    status = entry_admission["decision_status"]
    reason = entry_admission["primary_reason"]
    investability = (
        "UNKNOWN" if action == "REVIEW_REQUIRED"
        else "INVESTABLE" if action in {"BUY", "ADD"}
        else "WATCH" if action in {"HOLD", "WATCH"}
        else "NOT_INVESTABLE"
    )
    gates["new_capital_allowed"] = entry_admission["new_capital_allowed"]
    gates["decision_precedence_version"] = state["precedence_version"]
    gates["decision_precedence_rule_id"] = state["precedence_rule_id"]
    gates["decision_precedence_rank"] = state["precedence_rank"]
    gates["decision_scope"] = state["decision_scope"]
    gates["capital_effect"] = entry_admission["capital_effect"]
    gates["decision_admission_status"] = entry_admission["status"]
    gates["decision_admission_rule_id"] = entry_admission["rule_id"]
    gates["canonical_entry_evaluation_status"] = (
        canonical_entry_evaluation["status"] if canonical_entry_evaluation is not None else "SKIPPED"
    )
    gates["canonical_entry_price_eligible"] = (
        canonical_entry_evaluation.get("current_price_eligible")
        if canonical_entry_evaluation is not None else None
    )

    if metrics is not None:
        gates["target_entry_price_for_return"] = str(metrics["target_entry_price_for_return"])
        gates["target_entry_price_for_required_return"] = str(metrics["target_entry_price_for_required_return"])
        gates["target_entry_price_for_entry_cushion"] = str(metrics["target_entry_price_for_entry_cushion"])
        gates["target_entry_price_for_risk"] = (
            str(metrics["target_entry_price_for_risk"])
            if metrics["target_entry_price_for_risk"] is not None else None
        )
        gates["target_entry_price_v2_status"] = p2_target["status"] if p2_target is not None else "SKIPPED"
        gates["target_entry_price_v2_binding"] = p2_target["binding"] if p2_target is not None else None
        gates["target_entry_price_for_expectation_gap"] = (
            str(p2_target["expectation_gap_price_boundary"])
            if p2_target is not None and p2_target.get("expectation_gap_price_boundary") is not None
            else None
        )
        gates["target_entry_price"] = (
            str(p2_target["target_entry_price"])
            if p2_target is not None and p2_target.get("status") == "PASS"
            else None
        )

    output = {
        "contract_version": CONTRACT_VERSION,
        "decision_status": status,
        "investability_status": investability,
        "action": action,
        "primary_reason": reason,
        "human_approval_required": True,
        "auto_execution": False,
        "gates": gates,
        "position_package_complete": package_complete,
        "target_entry_price": (
            str(p2_target["target_entry_price"])
            if p2_target is not None and p2_target.get("status") == "PASS" else None
        ),
        "target_entry_price_return_only": (
            _serialize_metrics(metrics)["target_entry_price"] if metrics is not None else None
        ),
        "target_entry_price_semantics": (
            "P2_PRICE_DEPENDENT_EXPECTATION_GAP_REVALIDATED_CONDITIONAL_THRESHOLD"
            if p2_target is not None and p2_target.get("status") == "PASS"
            else "P2_PRICE_DEPENDENT_EXPECTATION_GAP_REVALIDATION_UNRESOLVED"
            if p2_target is not None
            else (_serialize_metrics(metrics)["target_entry_price_semantics"] if metrics is not None else None)
        ),
        "target_entry_price_requires_gap_revalidation": True if metrics is not None else None,
        "target_entry_price_v2_version": P2_PRICE_GAP_REVALIDATION_VERSION if p2_target is not None else None,
        "target_entry_price_v2": _serialize_nested(p2_target),
        "target_entry_price_gap_revalidation": _serialize_nested(p2_revalidation),
        "target_entry_price_p2_1_version": PRICE_RESPONSE_VERSION if p2_1_price_response is not None else None,
        "target_entry_price_p2_1": _serialize_nested(p2_target) if p2_1_price_response is not None else None,
        "target_entry_price_p2_1_price_response": _serialize_nested(p2_1_price_response),
        "canonical_entry_evaluation_version": (
            CANONICAL_ENTRY_EVALUATION_VERSION if canonical_entry_evaluation is not None else None
        ),
        "canonical_entry_evaluation": _serialize_nested(canonical_entry_evaluation),
        "decision_pre_admission_action": state["action"],
        "decision_admission_version": entry_admission["admission_version"],
        "decision_admission": _serialize_nested(entry_admission),
        "decision_admission_status": entry_admission["status"],
        "decision_admission_rule_id": entry_admission["rule_id"],
        "current_price": str(current_price) if current_price is not None else None,
        "decision_precedence_version": state["precedence_version"],
        "decision_precedence_rule_id": state["precedence_rule_id"],
        "decision_precedence_rank": state["precedence_rank"],
        "decision_scope": state["decision_scope"],
        "capital_effect": entry_admission["capital_effect"],
    }
    if metrics is not None:
        output["return_metrics"] = _serialize_metrics(metrics)
    return output

def assert_valid_v03_case(case: dict[str, Any]) -> None:
    result = validate_case_v03(case)
    if result["status"] != "PASS":
        summary = "; ".join(f'{e["code"]} {e["path"]}: {e["message"]}' for e in result["errors"])
        raise ValueError(summary)