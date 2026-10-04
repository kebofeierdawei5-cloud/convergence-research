from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

DEFAULT_HORIZON_YEARS = Decimal("1")
MIN_HORIZON_YEARS = Decimal("1")
MAX_HORIZON_YEARS = Decimal("3")

THREE_YEAR_EXCEPTION_BASIS = {
    "MAJOR_INDUSTRY_LEADER",
    "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX",
}

def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result

def validate_horizon_selection(
    *,
    horizon_years: Any,
    horizon_override: Any,
    horizon_override_basis: Iterable[Any] | None,
    horizon_selection_rationale: Any,
    path: str = "horizon",
) -> dict[str, Any]:
    horizon = _decimal(horizon_years, f"{path}.horizon_years")
    if horizon < MIN_HORIZON_YEARS or horizon > MAX_HORIZON_YEARS:
        raise ValueError(f"{path}.horizon_years must be within [1,3]")

    if not isinstance(horizon_override, bool):
        raise ValueError(f"{path}.horizon_override must be boolean")

    rationale = str(horizon_selection_rationale or "").strip()
    if not rationale:
        raise ValueError(f"{path}.horizon_selection_rationale is required")

    if horizon_override_basis is None:
        basis: list[str] = []
    elif not isinstance(horizon_override_basis, (list, tuple)):
        raise ValueError(f"{path}.horizon_override_basis must be a list")
    else:
        basis = [str(item).strip() for item in horizon_override_basis if str(item).strip()]
        if len(basis) != len(set(basis)):
            raise ValueError(f"{path}.horizon_override_basis must be unique")
        unknown = [item for item in basis if item not in THREE_YEAR_EXCEPTION_BASIS]
        if unknown:
            raise ValueError(f"{path}.horizon_override_basis contains unsupported value(s): {unknown}")

    if horizon == Decimal("3"):
        if horizon_override is not True:
            raise ValueError(f"{path}.horizon_override must be true for a 3-year horizon")
        if not basis:
            raise ValueError(f"{path}.horizon_override_basis is required for a 3-year horizon")
    else:
        if horizon_override is not False:
            raise ValueError(f"{path}.horizon_override must be false unless horizon_years is exactly 3")
        if basis:
            raise ValueError(f"{path}.horizon_override_basis must be empty unless horizon_years is exactly 3")

    return {
        "horizon_years": str(horizon),
        "horizon_override": horizon_override,
        "horizon_override_basis": basis,
        "horizon_selection_rationale": rationale,
        "default_policy": str(DEFAULT_HORIZON_YEARS),
    }

__all__ = [
    "DEFAULT_HORIZON_YEARS",
    "MIN_HORIZON_YEARS",
    "MAX_HORIZON_YEARS",
    "THREE_YEAR_EXCEPTION_BASIS",
    "validate_horizon_selection",
]
