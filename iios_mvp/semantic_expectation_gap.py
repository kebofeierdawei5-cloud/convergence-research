from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping


class ExpectationGapStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    INCOMPATIBLE = "INCOMPATIBLE"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class ComparisonDirection(str, Enum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


def _dec(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _require_text(obj: Mapping[str, Any], key: str, path: str) -> str:
    value = str(obj.get(key, "")).strip()
    if not value:
        raise ValueError(f"{path}.{key} is required")
    return value


def _compatibility(independent: Mapping[str, Any], market: Mapping[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key in ("variable_id", "unit", "basis", "horizon_years"):
        if str(independent.get(key, "")).strip() != str(market.get(key, "")).strip():
            mismatches.append(key)
    return mismatches


def evaluate_expectation_gap(
    *,
    independent_expectation: Mapping[str, Any],
    market_expectation: Mapping[str, Any],
    comparison_direction: str,
) -> dict[str, Any]:
    """
    Compare an independently supported expectation with a qualified MIE requirement.

    This function deliberately refuses to coerce ambiguous/blocked MIE into a scalar
    requirement and refuses gaps across incompatible variable/unit/basis/horizon.
    """
    direction = ComparisonDirection(comparison_direction)
    for label, obj in (("independent_expectation", independent_expectation), ("market_expectation", market_expectation)):
        if not isinstance(obj, Mapping):
            raise ValueError(f"{label} must be an object")

    market_status = str(market_expectation.get("qualification", "")).strip()
    resolution = str(market_expectation.get("resolution_state", "")).strip()
    if resolution in {"AMBIGUOUS", "NO_FEASIBLE_MODEL"}:
        return {
            "status": ExpectationGapStatus.AMBIGUOUS.value,
            "reason": "market-implied expectation is not uniquely identifiable",
            "gap_absolute": None,
            "gap_relative": None,
            "comparison_direction": direction.value,
        }
    if resolution in {"INSUFFICIENT_EVIDENCE"} or market_status == "BLOCKED":
        return {
            "status": ExpectationGapStatus.BLOCKED.value,
            "reason": "market-implied expectation lacks sufficient admissible evidence",
            "gap_absolute": None,
            "gap_relative": None,
            "comparison_direction": direction.value,
        }
    if market_status != "DECISION_GRADE" or resolution != "UNIQUE_MODEL":
        return {
            "status": ExpectationGapStatus.BLOCKED.value,
            "reason": "market-implied expectation is not decision-grade and uniquely resolved",
            "gap_absolute": None,
            "gap_relative": None,
            "comparison_direction": direction.value,
        }

    for key in ("variable_id", "value", "unit", "basis", "horizon_years"):
        _require_text(independent_expectation, key, "independent_expectation") if key != "value" else None
        _require_text(market_expectation, key, "market_expectation") if key != "value" else None
    independent_value = _dec(independent_expectation["value"], "independent_expectation.value")
    market_value = _dec(market_expectation["value"], "market_expectation.value")
    if market_value == 0:
        raise ValueError("market_expectation.value cannot be zero for relative expectation gap")

    mismatches = _compatibility(independent_expectation, market_expectation)
    if mismatches:
        return {
            "status": ExpectationGapStatus.INCOMPATIBLE.value,
            "reason": "expectation semantics are incompatible",
            "incompatible_fields": mismatches,
            "gap_absolute": None,
            "gap_relative": None,
            "comparison_direction": direction.value,
        }

    if direction is ComparisonDirection.HIGHER_IS_BETTER:
        gap_absolute = independent_value - market_value
    else:
        gap_absolute = market_value - independent_value
    gap_relative = gap_absolute / abs(market_value)

    return {
        "status": ExpectationGapStatus.PASS.value,
        "reason": "independent and market expectations are semantically compatible",
        "variable_id": independent_expectation["variable_id"],
        "unit": independent_expectation["unit"],
        "basis": independent_expectation["basis"],
        "horizon_years": independent_expectation["horizon_years"],
        "comparison_direction": direction.value,
        "independent_value": independent_value,
        "market_required_value": market_value,
        "gap_absolute": gap_absolute,
        "gap_relative": gap_relative,
    }


__all__ = ["ComparisonDirection", "ExpectationGapStatus", "evaluate_expectation_gap"]
