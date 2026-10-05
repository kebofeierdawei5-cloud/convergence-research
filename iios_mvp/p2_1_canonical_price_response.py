
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Mapping

from .canonical_independent_forecast import (
    CanonicalIndependentForecastResolver,
    canonical_independent_expectation_from_record,
)
from .market_model_domain import MarketModelFamily
from .semantic_expectation_gap import ComparisonDirection
from .p4f_mie_snapshot import validate_p4f_snapshot


PRICE_RESPONSE_VERSION = "IIOS-P2.1-CANONICAL-PRICE-RESPONSE-0.1"
PRICE_RESPONSE_REPLAY_SCHEMA = "IIOS-P2.1-PRICE-RESPONSE-REPLAY-0.1"

SUPPORTED_MODEL_FAMILIES = frozenset({
    MarketModelFamily.EV_EBITDA.value,
    MarketModelFamily.DCF.value,
    MarketModelFamily.DDM.value,
    MarketModelFamily.SOTP.value,
    MarketModelFamily.RNPV.value,
})


@dataclass(frozen=True)
class PriceResponseResult:
    response_id: str
    status: str
    response_schema: str
    response_version: str
    case_id: str
    cutoff_date: str
    snapshot_hash: str
    mie_set_hash: str
    provenance_hash: str
    model_id: str
    market_model: str
    expectation_id: str
    representation: str
    qualification: str
    price_observation_id: str
    reference_price: Decimal
    candidate_price: Decimal
    response_form: str
    formula_id: str
    formula_version: str
    variable_id: str
    unit: str
    basis: str
    comparison_direction: str
    reference_value_low: Decimal
    reference_value_high: Decimal
    candidate_value_low: Decimal
    candidate_value_high: Decimal
    affine_slope: Decimal
    affine_intercept: Decimal
    affine_slope_high: Decimal
    affine_intercept_high: Decimal
    assumption_fingerprint: str
    evidence_ids: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        def s(value: Any) -> Any:
            return None if value is None else str(value)

        return {
            "response_id": self.response_id,
            "status": self.status,
            "response_schema": self.response_schema,
            "response_version": self.response_version,
            "case_id": self.case_id,
            "cutoff_date": self.cutoff_date,
            "snapshot_hash": self.snapshot_hash,
            "mie_set_hash": self.mie_set_hash,
            "provenance_hash": self.provenance_hash,
            "model_id": self.model_id,
            "market_model": self.market_model,
            "expectation_id": self.expectation_id,
            "representation": self.representation,
            "qualification": self.qualification,
            "price_observation_id": self.price_observation_id,
            "reference_price": s(self.reference_price),
            "candidate_price": s(self.candidate_price),
            "response_form": self.response_form,
            "formula_id": self.formula_id,
            "formula_version": self.formula_version,
            "variable_id": self.variable_id,
            "unit": self.unit,
            "basis": self.basis,
            "comparison_direction": self.comparison_direction,
            "reference_value_low": s(self.reference_value_low),
            "reference_value_high": s(self.reference_value_high),
            "candidate_value_low": s(self.candidate_value_low),
            "candidate_value_high": s(self.candidate_value_high),
            "affine_slope": s(self.affine_slope),
            "affine_intercept": s(self.affine_intercept),
            "affine_slope_high": s(self.affine_slope_high),
            "affine_intercept_high": s(self.affine_intercept_high),
            "assumption_fingerprint": self.assumption_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
        }


def _dec(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _date(value: Any, path: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO date") from exc


def _datetime(value: Any, path: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO datetime") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{path} must be timezone-aware")
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _response_id(snapshot_hash: str, model_id: str, expectation_id: str, candidate_price: Decimal, forecast_id: str) -> str:
    return "p21-price-response-" + _hash({
        "version": PRICE_RESPONSE_VERSION,
        "snapshot_hash": snapshot_hash,
        "model_id": model_id,
        "expectation_id": expectation_id,
        "candidate_price": str(candidate_price),
        "forecast_id": forecast_id,
    })


def _materialized_expectation(snapshot: Mapping[str, Any], expectation_id: str) -> Mapping[str, Any]:
    mie_set = snapshot.get("mie_set")
    if not isinstance(mie_set, Mapping):
        raise ValueError("P4-F snapshot mie_set is invalid")
    if mie_set.get("resolution_state") != "UNIQUE_MODEL":
        raise ValueError("P2.1 requires UNIQUE_MODEL MIE resolution")
    matches = [
        evaluation.get("expectation")
        for evaluation in mie_set.get("model_evaluations") or []
        if evaluation.get("state") == "MATERIALIZED"
        and isinstance(evaluation.get("expectation"), Mapping)
        and evaluation.get("expectation", {}).get("expectation_id") == expectation_id
    ]
    if len(matches) != 1:
        raise ValueError("market_expectation_id must identify exactly one materialized MIE")
    qualification = str(matches[0].get("qualification", ""))
    if qualification not in {"DECISION_GRADE", "CONDITIONAL_ONLY"}:
        raise ValueError("P2.1 requires DECISION_GRADE or CONDITIONAL_ONLY materialized MIE")
    return matches[0]


def _parse_horizon_years(value: Any) -> Decimal:
    text = str(value).strip().upper()
    if text.endswith("Y"):
        return _dec(text[:-1], "horizon")
    if text.endswith("M"):
        return _dec(text[:-1], "horizon") / Decimal("12")
    return _dec(text, "horizon")


def _independent_match(requirement: Mapping[str, Any], independent: Mapping[str, Any]) -> bool:
    try:
        return (
            requirement.get("economic_variable") == independent.get("variable_id")
            and requirement.get("unit") == independent.get("unit")
            and requirement.get("basis") == independent.get("basis")
            and _parse_horizon_years(requirement.get("horizon"))
            == _dec(independent.get("horizon_years"), "forecast.horizon_years")
        )
    except (TypeError, ValueError):
        return False


def _matching_requirements(expectation: Mapping[str, Any], independent: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item for item in expectation.get("economic_requirements") or []
        if isinstance(item, Mapping) and _independent_match(item, independent)
    ]


def _provenance_index(snapshot: Mapping[str, Any], cutoff: date) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for item in snapshot.get("provenance_manifest") or []:
        evidence_id = str(item.get("evidence_id", ""))
        if not evidence_id or evidence_id in indexed:
            raise ValueError("P2.1 provenance manifest has duplicate/invalid evidence_id")
        _date(item.get("observation_date"), "provenance.observation_date")
        known_at = _datetime(item.get("known_at"), "provenance.known_at")
        if known_at.date() > cutoff:
            raise ValueError("P2.1 PIT violation: provenance known_at after cutoff")
        indexed[evidence_id] = item
    return indexed


def _value_context(
    provenance: Mapping[str, Mapping[str, Any]],
    *,
    variable: str,
    model_id: str,
) -> Decimal:
    expected_basis = f"model_context:{model_id}:{variable}"
    matches = [
        item for item in provenance.values()
        if item.get("variable") == variable
        and item.get("basis") == expected_basis
        and item.get("value") is not None
    ]
    if len(matches) != 1:
        raise ValueError(
            f"P2.1 requires exactly one canonical provenance value for {expected_basis}"
        )
    return _dec(matches[0]["value"], f"provenance.{variable}.value")


def _context_evidence_ids(
    provenance: Mapping[str, Mapping[str, Any]],
    *,
    family: str,
    model_id: str,
) -> tuple[str, ...]:
    variables = {"shares_outstanding"}
    if family in {
        MarketModelFamily.EV_EBITDA.value,
        MarketModelFamily.DCF.value,
        MarketModelFamily.RNPV.value,
    }:
        variables.add("net_debt")
    ids = []
    for variable in sorted(variables):
        basis = f"model_context:{model_id}:{variable}"
        matches = [
            item for item in provenance.values()
            if item.get("variable") == variable
            and item.get("basis") == basis
            and item.get("value") is not None
        ]
        if len(matches) != 1:
            raise ValueError(f"P2.1 requires exactly one canonical provenance context for {basis}")
        ids.append(str(matches[0]["evidence_id"]))
    return tuple(ids)


def _assumption_value(expectation: Mapping[str, Any], variable: str, basis: str | None = None) -> Decimal:
    matches = [
        item for item in expectation.get("assumption_set") or []
        if item.get("variable") == variable
        and (basis is None or item.get("basis") == basis)
    ]
    if len(matches) != 1:
        suffix = f" basis={basis}" if basis else ""
        raise ValueError(f"P2.1 requires exactly one admitted assumption {variable}{suffix}")
    return _dec(matches[0]["value"], f"assumption.{variable}.value")


def _assumption_fingerprint(expectation: Mapping[str, Any]) -> str:
    assumptions = sorted(
        [dict(item) for item in expectation.get("assumption_set") or []],
        key=lambda item: (str(item.get("variable")), str(item.get("basis"))),
    )
    return _hash(assumptions)


def _reference_price(expectation: Mapping[str, Any], observation: Mapping[str, Any]) -> Decimal:
    basis = expectation.get("observation_basis") or {}
    observed_date = _datetime(
        observation.get("observed_at"),
        "current_price_observation.observed_at",
    ).date()
    if basis.get("observation_date") != observed_date.isoformat():
        raise ValueError("P2.1 MIE observation_date does not match canonical current price")
    if basis.get("price_observation_id") != observation.get("price_observation_id"):
        raise ValueError("P2.1 MIE price_observation_id does not match canonical current price")
    if basis.get("currency") != observation.get("currency"):
        raise ValueError("P2.1 MIE currency does not match canonical current price")
    if basis.get("adjustment_semantics") != observation.get("adjustment_semantics"):
        raise ValueError("P2.1 MIE adjustment semantics do not match canonical current price")
    price = _dec(observation.get("price"), "current_price_observation.price")
    if price <= 0:
        raise ValueError("canonical current price must be > 0")
    return price


def _reference_interval(requirement: Mapping[str, Any]) -> tuple[Decimal, Decimal]:
    if "value" in requirement:
        value = _dec(requirement["value"], "requirement.value")
        return value, value
    if "range_low" in requirement and "range_high" in requirement:
        low = _dec(requirement["range_low"], "requirement.range_low")
        high = _dec(requirement["range_high"], "requirement.range_high")
        if high < low:
            raise ValueError("P2.1 reference requirement range is invalid")
        return low, high
    raise ValueError("P2.1 requirement must be point-valued or a complete range")


def _model_relation(
    *,
    expectation: Mapping[str, Any],
    requirement: Mapping[str, Any],
    reference_price: Decimal,
    candidate_price: Decimal,
    provenance: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    family = str(expectation.get("market_model", "")).strip()
    variable = str(requirement.get("economic_variable", "")).strip()
    reference_low, reference_high = _reference_interval(requirement)
    model_id = str(expectation.get("model_id", ""))
    if not model_id:
        raise ValueError("P2.1 MIE model_id is required")
    shares = _value_context(provenance, variable="shares_outstanding", model_id=model_id)
    ev_based = {
        MarketModelFamily.EV_EBITDA.value,
        MarketModelFamily.DCF.value,
        MarketModelFamily.RNPV.value,
    }
    net_debt = _value_context(provenance, variable="net_debt", model_id=model_id) if family in ev_based else Decimal("0")

    if family == MarketModelFamily.EV_EBITDA.value:
        if variable != "ebitda":
            raise ValueError("EV/EBITDA P2.1 requirement must be ebitda")
        reference_ev = reference_price * shares + net_debt
        if reference_ev <= 0:
            raise ValueError("EV/EBITDA reference enterprise value must be > 0")
        low_slope = shares * reference_low / reference_ev
        low_intercept = net_debt * reference_low / reference_ev
        high_slope = shares * reference_high / reference_ev
        high_intercept = net_debt * reference_high / reference_ev
        return (
            "AFFINE_RANGE",
            "EV_EBITDA_IMPLIED_EBITDA_FROM_ENTERPRISE_VALUE_AND_FROZEN_MULTIPLE_RANGE",
            low_slope * candidate_price + low_intercept,
            high_slope * candidate_price + high_intercept,
            low_slope,
            low_intercept,
            high_slope,
            high_intercept,
        )

    if family == MarketModelFamily.DCF.value:
        if variable != "fcf":
            raise ValueError("DCF P2.1 requirement must be fcf")
        growth = _assumption_value(expectation, "growth")
        discount = _assumption_value(expectation, "discount_rate")
        if discount <= growth or growth <= Decimal("-1"):
            raise ValueError("DCF P2.1 requires discount_rate > growth > -1")
        coefficient = (discount - growth) / (Decimal("1") + growth)
        slope = shares * coefficient
        intercept = net_debt * coefficient
        value = slope * candidate_price + intercept
        return "AFFINE", "DCF_IMPLIED_FCF_FROM_ENTERPRISE_VALUE_AND_FROZEN_ASSUMPTIONS", value, value, slope, intercept, slope, intercept

    if family == MarketModelFamily.DDM.value:
        if variable != "dividend":
            raise ValueError("DDM P2.1 requirement must be dividend")
        growth = _assumption_value(expectation, "growth")
        discount = _assumption_value(expectation, "discount_rate")
        if discount <= growth or growth <= Decimal("-1"):
            raise ValueError("DDM P2.1 requires discount_rate > growth > -1")
        slope = (discount - growth) / (Decimal("1") + growth)
        value = slope * candidate_price
        return "AFFINE", "DDM_IMPLIED_DIVIDEND_FROM_PRICE_AND_FROZEN_RATES", value, value, slope, Decimal("0"), slope, Decimal("0")

    if family == MarketModelFamily.SOTP.value:
        if variable != "residual_value":
            raise ValueError("SOTP P2.1 requirement must be residual_value")
        segment_total = sum(
            _dec(item["value"], "SOTP segment assumption.value")
            for item in expectation.get("assumption_set") or []
            if item.get("variable") == "segment_value"
        )
        if segment_total <= 0:
            raise ValueError("SOTP P2.1 requires positive segment value total")
        slope = shares
        intercept = -segment_total
        value = slope * candidate_price + intercept
        return "AFFINE", "SOTP_IMPLIED_RESIDUAL_VALUE_FROM_MARKET_CAP_AND_FROZEN_SEGMENTS", value, value, slope, intercept, slope, intercept

    if family == MarketModelFamily.RNPV.value:
        if variable != "pipeline_value":
            raise ValueError("rNPV P2.1 requirement must be pipeline_value")
        basis = str(requirement.get("basis", ""))
        parts = basis.split(":")
        if len(parts) < 2 or parts[0] != "pipeline":
            raise ValueError("rNPV P2.1 requirement basis must identify pipeline:<id>")
        pipeline_id = parts[1]
        pipeline_value = _assumption_value(
            expectation,
            "pipeline_value",
            f"pipeline:{pipeline_id}:observed_composition_anchor",
        )
        probability = _assumption_value(
            expectation,
            "probability",
            f"pipeline:{pipeline_id}:observed_probability_condition",
        )
        timing = _assumption_value(
            expectation,
            "timing",
            f"pipeline:{pipeline_id}:observed_timing_condition",
        )
        discount = _assumption_value(expectation, "discount_rate", "rnpv:global_condition")
        base_value = _assumption_value(expectation, "base_value", "rnpv:global_condition")
        all_pipeline_values = [
            _dec(item["value"], "rNPV pipeline_value assumption")
            for item in expectation.get("assumption_set") or []
            if item.get("variable") == "pipeline_value"
            and ":observed_composition_anchor" in str(item.get("basis", ""))
        ]
        observed_total = sum(all_pipeline_values)
        if observed_total <= 0:
            raise ValueError("rNPV P2.1 observed pipeline total must be > 0")
        if not 0 <= probability <= 1:
            raise ValueError("rNPV P2.1 probability must be within [0,1]")
        if timing < 0 or discount <= Decimal("-1"):
            raise ValueError("rNPV P2.1 timing/discount assumptions are invalid")
        weight = probability / ((Decimal("1") + discount) ** timing)
        if weight <= 0:
            raise ValueError("rNPV P2.1 pipeline weight must be > 0")
        weighted_total = Decimal("0")
        for item in expectation.get("assumption_set") or []:
            if item.get("variable") != "pipeline_value":
                continue
            item_basis = str(item.get("basis", ""))
            if ":observed_composition_anchor" not in item_basis:
                continue
            item_id = item_basis.split(":", 2)[1]
            p = _assumption_value(
                expectation,
                "probability",
                f"pipeline:{item_id}:observed_probability_condition",
            )
            t = _assumption_value(
                expectation,
                "timing",
                f"pipeline:{item_id}:observed_timing_condition",
            )
            if not 0 <= p <= 1 or t < 0:
                raise ValueError("rNPV P2.1 pipeline probability/timing assumptions are invalid")
            item_weight = p / ((Decimal("1") + discount) ** t)
            weighted_total += _dec(item["value"], "rNPV pipeline_value assumption") * item_weight
        observed_risk_adjusted_weight = weighted_total / observed_total
        if observed_risk_adjusted_weight <= 0:
            raise ValueError("rNPV P2.1 observed composition weight must be > 0")
        composition = pipeline_value / observed_total
        slope = shares * composition / observed_risk_adjusted_weight
        intercept = (net_debt - base_value) * composition / observed_risk_adjusted_weight
        value = slope * candidate_price + intercept
        return "AFFINE", "RNPV_IMPLIED_PIPELINE_VALUE_FROM_ENTERPRISE_VALUE_AND_FROZEN_COMPOSITION", value, value, slope, intercept, slope, intercept

    raise ValueError(f"P2.1 unsupported model family: {family}")


def build_canonical_price_response(
    *,
    market_implied_expectation_snapshot: Mapping[str, Any],
    current_price_observation: Mapping[str, Any],
    candidate_price: Any,
    cutoff_date: Any,
    case_id: str,
    market: str,
    symbol: str,
    market_expectation_id: str,
    independent_forecast_ref: Mapping[str, Any],
    independent_forecast_resolver: CanonicalIndependentForecastResolver,
) -> dict[str, Any]:
    snapshot = dict(market_implied_expectation_snapshot)
    validate_p4f_snapshot(snapshot)
    cutoff = _date(cutoff_date, "cutoff_date")
    if snapshot.get("case_id") != case_id:
        raise ValueError("P2.1 P4-F snapshot.case_id mismatch")
    if snapshot.get("cutoff_date") != cutoff.isoformat():
        raise ValueError("P2.1 P4-F snapshot.cutoff_date mismatch")

    candidate = _dec(candidate_price, "candidate_price")
    if candidate <= 0:
        raise ValueError("candidate_price must be > 0")
    if independent_forecast_resolver is None:
        raise ValueError("canonical independent forecast resolver is required")

    expectation = _materialized_expectation(snapshot, market_expectation_id)
    reference_price = _reference_price(expectation, current_price_observation)
    family = str(expectation.get("market_model", "")).strip()
    if family not in SUPPORTED_MODEL_FAMILIES:
        raise ValueError(f"P2.1 unsupported model family: {family}")

    record = independent_forecast_resolver.resolve_independent_forecast(
        independent_forecast_ref,
        case_id=case_id,
        market=market,
        symbol=symbol,
        cutoff_date=cutoff,
    )
    independent = canonical_independent_expectation_from_record(record)
    matches = _matching_requirements(expectation, independent)
    if len(matches) != 1:
        raise ValueError("P2.1 requires exactly one MIE requirement matching the independent forecast semantics")
    requirement = matches[0]

    direction = ComparisonDirection(
        str(requirement.get("comparison_direction", ComparisonDirection.HIGHER_IS_BETTER.value))
    )
    provenance = _provenance_index(snapshot, cutoff)

    nested_evidence = set(snapshot.get("mie_set", {}).get("evidence_ids") or [])
    nested_evidence.update(expectation.get("evidence_ids") or [])
    nested_evidence.update(requirement.get("evidence_ids") or [])
    nested_evidence.update(
        evidence_id
        for item in expectation.get("assumption_set") or []
        for evidence_id in item.get("evidence_ids") or []
    )
    response_evidence = tuple(sorted(
        nested_evidence
        | set(independent.get("evidence_ids") or [])
        | set(_context_evidence_ids(provenance, family=family, model_id=str(expectation["model_id"])))
    ))
    missing = [eid for eid in response_evidence if eid not in provenance and eid not in set(independent.get("evidence_ids") or [])]
    if missing:
        raise ValueError(f"P2.1 provenance missing evidence IDs: {sorted(missing)}")

    form, formula_id, candidate_low, candidate_high, slope_low, intercept_low, slope_high, intercept_high = _model_relation(
        expectation=expectation,
        requirement=requirement,
        reference_price=reference_price,
        candidate_price=candidate,
        provenance=provenance,
    )
    reference_low, reference_high = _reference_interval(requirement)

    ref_form, _ref_formula, ref_low, ref_high, _ref_sl, _ref_il, _ref_sh, _ref_ih = _model_relation(
        expectation=expectation,
        requirement=requirement,
        reference_price=reference_price,
        candidate_price=reference_price,
        provenance=provenance,
    )
    if ref_form != form or ref_low != reference_low or ref_high != reference_high:
        raise ValueError("P2.1 canonical model response is inconsistent with the reference MIE at the canonical price")

    independent_value = independent["value"]
    if direction is ComparisonDirection.HIGHER_IS_BETTER:
        gap_abs = independent_value - candidate_high
        denom = abs(candidate_high)
        if slope_high == 0:
            raise ValueError("P2.1 high-endpoint response slope cannot be zero")
        boundary = (independent_value - intercept_high) / slope_high
        positive = independent_value > candidate_high
    else:
        gap_abs = candidate_low - independent_value
        denom = abs(candidate_low)
        if slope_low == 0:
            raise ValueError("P2.1 low-endpoint response slope cannot be zero")
        boundary = (independent_value - intercept_low) / slope_low
        positive = candidate_low > independent_value

    if denom == 0:
        raise ValueError("P2.1 candidate market value cannot be zero")
    gap_relative = gap_abs / denom

    response = PriceResponseResult(
        response_id=_response_id(
            snapshot_hash=snapshot["snapshot_hash"],
            model_id=str(expectation["model_id"]),
            expectation_id=str(expectation["expectation_id"]),
            candidate_price=candidate,
            forecast_id=record["forecast_id"],
        ),
        status="PASS" if positive else "NON_POSITIVE",
        response_schema=PRICE_RESPONSE_REPLAY_SCHEMA,
        response_version=PRICE_RESPONSE_VERSION,
        case_id=case_id,
        cutoff_date=cutoff.isoformat(),
        snapshot_hash=snapshot["snapshot_hash"],
        mie_set_hash=snapshot["mie_set_hash"],
        provenance_hash=snapshot["provenance_hash"],
        model_id=str(expectation["model_id"]),
        market_model=family,
        expectation_id=str(expectation["expectation_id"]),
        representation=str(expectation.get("representation", "")),
        qualification=str(expectation.get("qualification", "")),
        price_observation_id=str(current_price_observation["price_observation_id"]),
        reference_price=reference_price,
        candidate_price=candidate,
        response_form=form,
        formula_id=formula_id,
        formula_version=PRICE_RESPONSE_VERSION,
        variable_id=str(requirement["economic_variable"]),
        unit=str(requirement["unit"]),
        basis=str(requirement["basis"]),
        comparison_direction=direction.value,
        reference_value_low=reference_low,
        reference_value_high=reference_high,
        candidate_value_low=candidate_low,
        candidate_value_high=candidate_high,
        affine_slope=slope_low,
        affine_intercept=intercept_low,
        affine_slope_high=slope_high,
        affine_intercept_high=intercept_high,
        assumption_fingerprint=_assumption_fingerprint(expectation),
        evidence_ids=response_evidence,
        reason=(
            "candidate price preserves a positive expectation gap under the admitted "
            "model-specific price response"
            if positive
            else "candidate price eliminates the positive expectation gap under the admitted "
            "model-specific price response"
        ),
    )
    result = response.to_dict()
    result.update({
        "gap_absolute": str(gap_abs),
        "gap_relative": str(gap_relative),
        "gap_positive": positive,
        "expectation_gap_price_boundary": str(boundary),
        "price_constraint_type": (
            "UPPER_BOUND_STRICT"
            if direction is ComparisonDirection.HIGHER_IS_BETTER
            else "LOWER_BOUND_STRICT"
        ),
        "independent_value": str(independent_value),
        "independent_forecast_id": record["forecast_id"],
        "independent_forecast_version": record["forecast_version"],
        "independent_forecast_model_version": record["model_version"],
        "independent_evidence_ids": list(independent.get("evidence_ids") or []),
    })
    return result


def replay_canonical_price_response(
    *,
    response: Mapping[str, Any],
    market_implied_expectation_snapshot: Mapping[str, Any],
    current_price_observation: Mapping[str, Any],
    market: str,
    symbol: str,
    independent_forecast_ref: Mapping[str, Any],
    independent_forecast_resolver: CanonicalIndependentForecastResolver,
) -> dict[str, Any]:
    try:
        regenerated = build_canonical_price_response(
            market_implied_expectation_snapshot=market_implied_expectation_snapshot,
            current_price_observation=current_price_observation,
            candidate_price=response.get("candidate_price"),
            cutoff_date=response.get("cutoff_date"),
            case_id=str(response.get("case_id", "")),
            market=market,
            symbol=symbol,
            market_expectation_id=str(response.get("expectation_id", "")),
            independent_forecast_ref=independent_forecast_ref,
            independent_forecast_resolver=independent_forecast_resolver,
        )
        if regenerated != dict(response):
            raise ValueError("P2.1 deterministic response replay mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "replay_status": "FAIL",
            "integrity_status": "FAIL",
            "pit_status": "FAIL",
            "provenance_status": "FAIL",
            "semantic_status": "FAIL",
            "reason": str(exc),
        }
    return {
        "replay_status": "PASS",
        "integrity_status": "PASS",
        "pit_status": "PASS",
        "provenance_status": "PASS",
        "semantic_status": "PASS",
        "response_id": response["response_id"],
        "snapshot_hash": response["snapshot_hash"],
    }


__all__ = [
    "PRICE_RESPONSE_REPLAY_SCHEMA",
    "PRICE_RESPONSE_VERSION",
    "SUPPORTED_MODEL_FAMILIES",
    "build_canonical_price_response",
    "replay_canonical_price_response",
]
