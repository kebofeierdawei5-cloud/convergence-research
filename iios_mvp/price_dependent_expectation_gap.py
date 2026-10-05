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
from .market_implied_expectation import MIEQualification
from .semantic_expectation_gap import ComparisonDirection, evaluate_expectation_gap
from .p4f_mie_snapshot import validate_p4f_snapshot


P2_PRICE_GAP_REVALIDATION_VERSION = "IIOS-P2-PRICE-GAP-REVALIDATION-0.1"

# Only model families whose model-native implied primary variable is
# proportional to price under frozen contemporaneous assumptions are admitted
# in this first P2 vertical slice. Unsupported families fail closed rather
# than pretending an affine/non-linear response is proportional.
PRICE_PROPORTIONAL_MIE_FAMILIES = frozenset({
    "forward_pe",
    "ps",
    "pb",
    "ddm",
})


@dataclass(frozen=True)
class PriceDependentExpectationGapRevalidation:
    revalidation_id: str
    status: str
    reference_snapshot_hash: str
    reference_price: Decimal
    candidate_price: Decimal
    market_model: str
    representation: str
    comparison_direction: str | None
    reference_market_value: Decimal | None
    candidate_market_value: Decimal | None
    independent_value: Decimal | None
    gap_relative: Decimal | None
    gap_positive: bool
    price_response_semantics: str
    price_constraint_type: str | None
    expectation_gap_price_boundary: Decimal | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        def s(value: Any) -> Any:
            return None if value is None else str(value)

        return {
            "revalidation_id": self.revalidation_id,
            "status": self.status,
            "reference_snapshot_hash": self.reference_snapshot_hash,
            "reference_price": s(self.reference_price),
            "candidate_price": s(self.candidate_price),
            "market_model": self.market_model,
            "representation": self.representation,
            "comparison_direction": self.comparison_direction,
            "reference_market_value": s(self.reference_market_value),
            "candidate_market_value": s(self.candidate_market_value),
            "independent_value": s(self.independent_value),
            "gap_relative": s(self.gap_relative),
            "gap_positive": self.gap_positive,
            "price_response_semantics": self.price_response_semantics,
            "price_constraint_type": self.price_constraint_type,
            "expectation_gap_price_boundary": s(self.expectation_gap_price_boundary),
            "reason": self.reason,
        }


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
        raise ValueError(f"{path} must be ISO date") from exc


def _datetime(value: Any, path: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{path} must be timezone-aware")
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _revalidation_id(
    *,
    snapshot_hash: str,
    candidate_price: Decimal,
    forecast_id: str,
) -> str:
    payload = {
        "version": P2_PRICE_GAP_REVALIDATION_VERSION,
        "snapshot_hash": snapshot_hash,
        "candidate_price": str(candidate_price),
        "forecast_id": forecast_id,
    }
    return "p2-gap-" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


def _materialized_expectation(
    snapshot: Mapping[str, Any],
    expectation_id: str,
) -> Mapping[str, Any]:
    mie_set = snapshot.get("mie_set")
    if not isinstance(mie_set, Mapping):
        raise ValueError("P4-F snapshot mie_set is invalid")
    if mie_set.get("resolution_state") != "UNIQUE_MODEL":
        raise ValueError("P2 price revalidation requires UNIQUE_MODEL MIE")
    if mie_set.get("qualification") != MIEQualification.DECISION_GRADE.value:
        raise ValueError("P2 price revalidation requires DECISION_GRADE MIE")

    matches = []
    for evaluation in mie_set.get("model_evaluations") or []:
        if evaluation.get("state") != "MATERIALIZED":
            continue
        expectation = evaluation.get("expectation")
        if (
            isinstance(expectation, Mapping)
            and expectation.get("expectation_id") == expectation_id
        ):
            matches.append(expectation)
    if len(matches) != 1:
        raise ValueError(
            "market_expectation_id must identify exactly one materialized MIE in snapshot"
        )
    return matches[0]


def _point_requirement(expectation: Mapping[str, Any]) -> tuple[Mapping[str, Any], Decimal]:
    requirements = expectation.get("economic_requirements") or []
    points = [
        item
        for item in requirements
        if (
            isinstance(item, Mapping)
            and "value" in item
            and "range_low" not in item
            and "range_high" not in item
        )
    ]
    if len(points) != 1:
        raise ValueError(
            "P2 price revalidation requires exactly one point-valued MIE economic requirement"
        )
    value = _dec(
        points[0]["value"],
        "market_implied_expectation.economic_requirements.value",
    )
    if value == 0:
        raise ValueError("reference market expectation value cannot be zero")
    return points[0], value


def _require_reference_binding(
    *,
    snapshot: Mapping[str, Any],
    expectation: Mapping[str, Any],
    current_price_observation: Mapping[str, Any],
    cutoff_date: date,
) -> Decimal:
    observation = expectation.get("observation_basis")
    if not isinstance(observation, Mapping):
        raise ValueError("materialized MIE observation_basis is required")

    observed_date = _datetime(
        current_price_observation.get("observed_at"),
        "current_price_observation.observed_at",
    ).date()
    if observation.get("observation_date") != observed_date.isoformat():
        raise ValueError("MIE observation basis date does not match canonical current price")
    if observation.get("cutoff_date") != cutoff_date.isoformat():
        raise ValueError("MIE observation basis cutoff does not match case cutoff")
    if observation.get("price_observation_id") != current_price_observation.get(
        "price_observation_id"
    ):
        raise ValueError(
            "MIE observation basis price_observation_id does not match canonical current price"
        )
    if observation.get("currency") != current_price_observation.get("currency"):
        raise ValueError(
            "MIE observation basis currency does not match canonical current price"
        )
    if observation.get("adjustment_semantics") != current_price_observation.get(
        "adjustment_semantics"
    ):
        raise ValueError(
            "MIE observation basis adjustment semantics do not match canonical current price"
        )

    reference_price = _dec(
        current_price_observation.get("price"),
        "current_price_observation.price",
    )
    if reference_price <= 0:
        raise ValueError("canonical current price must be > 0")
    return reference_price


def _candidate_market_value(
    *,
    reference_market_value: Decimal,
    reference_price: Decimal,
    candidate_price: Decimal,
) -> Decimal:
    if reference_market_value == 0:
        raise ValueError("reference market expectation value cannot be zero")
    return reference_market_value * candidate_price / reference_price


def revalidate_expectation_gap_at_price(
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

    if snapshot.get("case_id") != case_id:
        raise ValueError("P4-F snapshot.case_id must equal investment core case_id")
    cutoff = _date(cutoff_date, "cutoff_date")
    if snapshot.get("cutoff_date") != cutoff.isoformat():
        raise ValueError("P4-F snapshot.cutoff_date must equal case cutoff_date")
    if independent_forecast_resolver is None:
        raise ValueError("canonical independent forecast resolver is required for P2")

    candidate = _dec(candidate_price, "candidate_price")
    if candidate <= 0:
        raise ValueError("candidate_price must be > 0")

    expectation = _materialized_expectation(snapshot, market_expectation_id)
    reference_price = _require_reference_binding(
        snapshot=snapshot,
        expectation=expectation,
        current_price_observation=current_price_observation,
        cutoff_date=cutoff,
    )
    requirement, reference_market_value = _point_requirement(expectation)
    market_model = str(expectation.get("market_model", "")).strip()
    representation = str(expectation.get("representation", "")).strip()
    direction = ComparisonDirection(
        str(
            requirement.get(
                "comparison_direction",
                ComparisonDirection.HIGHER_IS_BETTER.value,
            )
        )
    )

    if market_model not in PRICE_PROPORTIONAL_MIE_FAMILIES:
        raise ValueError(
            "P2 price revalidation does not yet support non-proportional market model family: "
            f"{market_model}"
        )

    record = independent_forecast_resolver.resolve_independent_forecast(
        independent_forecast_ref,
        case_id=case_id,
        market=market,
        symbol=symbol,
        cutoff_date=cutoff,
    )
    independent_payload = canonical_independent_expectation_from_record(record)
    independent_value = _dec(
        independent_payload["value"],
        "independent_forecast.value",
    )

    candidate_market_value = _candidate_market_value(
        reference_market_value=reference_market_value,
        reference_price=reference_price,
        candidate_price=candidate,
    )

    market_payload = {
        "qualification": MIEQualification.DECISION_GRADE.value,
        "resolution_state": "UNIQUE_MODEL",
        "variable_id": requirement["economic_variable"],
        "value": candidate_market_value,
        "unit": requirement["unit"],
        "basis": requirement["basis"],
        "horizon_years": str(
            requirement.get("horizon_years")
            if requirement.get("horizon_years") is not None
            else independent_payload["horizon_years"]
        ),
    }
    independent_expectation = {
        "variable_id": independent_payload["variable_id"],
        "value": independent_value,
        "unit": independent_payload["unit"],
        "basis": independent_payload["basis"],
        "horizon_years": str(independent_payload["horizon_years"]),
    }

    evaluated = evaluate_expectation_gap(
        independent_expectation=independent_expectation,
        market_expectation=market_payload,
        comparison_direction=direction.value,
    )

    common = {
        "reference_snapshot_hash": snapshot["snapshot_hash"],
        "reference_price": reference_price,
        "candidate_price": candidate,
        "market_model": market_model,
        "representation": representation,
        "comparison_direction": direction.value,
        "reference_market_value": reference_market_value,
        "candidate_market_value": candidate_market_value,
        "independent_value": independent_value,
        "price_response_semantics": "PRICE_PROPORTIONAL_MODEL_WITH_ASSUMPTIONS_FROZEN",
    }

    if evaluated["status"] != "PASS":
        result = PriceDependentExpectationGapRevalidation(
            revalidation_id=_revalidation_id(
                snapshot_hash=snapshot["snapshot_hash"],
                candidate_price=candidate,
                forecast_id=record["forecast_id"],
            ),
            status=evaluated["status"],
            gap_relative=None,
            gap_positive=False,
            price_constraint_type=None,
            expectation_gap_price_boundary=None,
            reason=evaluated["reason"],
            **common,
        )
        return {**result.to_dict(), "gap_absolute": None}

    gap_relative = _dec(evaluated["gap_relative"], "gap_relative")
    gap_positive = gap_relative > 0

    boundary = reference_price * independent_value / reference_market_value
    constraint_type = (
        "UPPER_BOUND_STRICT"
        if direction is ComparisonDirection.HIGHER_IS_BETTER
        else "LOWER_BOUND_STRICT"
    )

    result = PriceDependentExpectationGapRevalidation(
        revalidation_id=_revalidation_id(
            snapshot_hash=snapshot["snapshot_hash"],
            candidate_price=candidate,
            forecast_id=record["forecast_id"],
        ),
        status="PASS" if gap_positive else "NON_POSITIVE",
        gap_relative=gap_relative,
        gap_positive=gap_positive,
        price_constraint_type=constraint_type,
        expectation_gap_price_boundary=boundary,
        reason=(
            "candidate price preserves a positive expectation gap"
            if gap_positive
            else "candidate price eliminates the positive expectation gap"
        ),
        **common,
    )
    return {
        **result.to_dict(),
        "gap_absolute": evaluated["gap_absolute"],
    }


def combine_target_entry_price_v2(
    *,
    return_target_entry_price: Any,
    revalidation: Mapping[str, Any],
) -> dict[str, Any]:
    base_target = _dec(return_target_entry_price, "return_target_entry_price")
    if base_target <= 0:
        raise ValueError("return_target_entry_price must be > 0")

    status = str(revalidation.get("status", "")).upper()
    direction = str(revalidation.get("comparison_direction", "")).upper()
    boundary_raw = revalidation.get("expectation_gap_price_boundary")
    boundary = (
        None
        if boundary_raw is None
        else _dec(boundary_raw, "expectation_gap_price_boundary")
    )

    if status in {
        "BLOCKED",
        "AMBIGUOUS",
        "INCOMPATIBLE",
        "UNKNOWN",
        "UNSUPPORTED",
    }:
        return {
            "status": "REVIEW_REQUIRED",
            "target_entry_price": None,
            "return_target_entry_price": base_target,
            "expectation_gap_price_boundary": boundary,
            "binding": "P2_PRICE_GAP_REVALIDATION_UNRESOLVED",
            "price_constraint_type": None,
            "target_entry_price_inclusive": False,
            "reason": "price-dependent expectation-gap revalidation is unresolved",
        }

    if status == "NON_POSITIVE":
        return {
            "status": "NO_FEASIBLE_PRICE",
            "target_entry_price": None,
            "return_target_entry_price": base_target,
            "expectation_gap_price_boundary": boundary,
            "binding": "P2_NO_POSITIVE_EXPECTATION_GAP_AT_PRICE_BOUNDARY",
            "price_constraint_type": revalidation.get("price_constraint_type"),
            "target_entry_price_inclusive": False,
            "reason": "price-dependent expectation gap is non-positive at the supplied candidate price",
        }

    if status != "PASS":
        return {
            "status": "REVIEW_REQUIRED",
            "target_entry_price": None,
            "return_target_entry_price": base_target,
            "expectation_gap_price_boundary": boundary,
            "binding": "P2_UNKNOWN_REVALIDATION_STATE",
            "price_constraint_type": None,
            "target_entry_price_inclusive": False,
            "reason": "unknown P2 revalidation state",
        }

    if boundary is None:
        raise ValueError("PASS P2 revalidation requires expectation_gap_price_boundary")

    if direction == ComparisonDirection.HIGHER_IS_BETTER.value:
        target = min(base_target, boundary)
        gap_binding = boundary < base_target
        return {
            "status": "PASS",
            "target_entry_price": target,
            "return_target_entry_price": base_target,
            "expectation_gap_price_boundary": boundary,
            "binding": (
                "EXPECTATION_GAP_UPPER_BOUND"
                if gap_binding
                else "RETURN_TARGET_ENTRY_PRICE"
            ),
            "price_constraint_type": "UPPER_BOUND_STRICT" if gap_binding else "RETURN_TARGET_ENTRY_PRICE",
            "target_entry_price_inclusive": not gap_binding,
            "reason": "target entry price combines return/risk caps with price-dependent expectation-gap ceiling",
        }

    if direction == ComparisonDirection.LOWER_IS_BETTER.value:
        if base_target <= boundary:
            return {
                "status": "NO_FEASIBLE_PRICE",
                "target_entry_price": None,
                "return_target_entry_price": base_target,
                "expectation_gap_price_boundary": boundary,
                "binding": "P2_NO_OVERLAP_BETWEEN_RETURN_CAP_AND_EXPECTATION_GAP_FLOOR",
                "price_constraint_type": "LOWER_BOUND_STRICT",
                "target_entry_price_inclusive": False,
                "reason": "return/risk target price is not above the expectation-gap floor",
            }
        return {
            "status": "PASS",
            "target_entry_price": base_target,
            "return_target_entry_price": base_target,
            "expectation_gap_price_boundary": boundary,
            "binding": "RETURN_TARGET_ENTRY_PRICE_WITH_EXPECTATION_GAP_FLOOR",
            "price_constraint_type": "LOWER_BOUND_STRICT",
            "target_entry_price_inclusive": True,
            "reason": "target entry price remains the return/risk cap but only prices above the expectation-gap floor preserve a positive gap",
        }

    raise ValueError("unsupported comparison direction")


__all__ = [
    "P2_PRICE_GAP_REVALIDATION_VERSION",
    "PRICE_PROPORTIONAL_MIE_FAMILIES",
    "PriceDependentExpectationGapRevalidation",
    "revalidate_expectation_gap_at_price",
    "combine_target_entry_price_v2",
]
