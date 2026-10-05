from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

from .market_implied_expectation import MIEQualification
from .canonical_independent_forecast import (
    CanonicalIndependentForecastReference,
    CanonicalIndependentForecastResolver,
    canonical_independent_expectation_from_record,
)
from .p4f_mie_snapshot import validate_p4f_snapshot
from .semantic_expectation_gap import ComparisonDirection, evaluate_expectation_gap

CANONICAL_EXPECTATION_GAP_VERSION = "IIOS-EXPECTATION-GAP-0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HORIZON_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)(Y|M)$")


@dataclass(frozen=True)
class IndependentExpectation:
    variable_id: str
    value: Decimal
    unit: str
    basis: str
    horizon_years: Decimal
    evidence_ids: tuple[str, ...]

    def validate(self) -> None:
        if not self.variable_id or not self.unit or not self.basis:
            raise ValueError("independent expectation semantic identity is required")
        if self.horizon_years <= 0:
            raise ValueError("independent expectation horizon_years must be > 0")
        if not self.evidence_ids:
            raise ValueError("independent expectation evidence_ids are required")


@dataclass(frozen=True)
class CanonicalExpectationGap:
    gap_id: str
    evaluator_version: str
    price: Decimal
    price_observation_id: str
    cutoff_date: date
    mie_snapshot_hash: str
    market_expectation_id: str
    independent_forecast_ref: CanonicalIndependentForecastReference

    def validate(self) -> None:
        if not self.gap_id:
            raise ValueError("gap_id is required")
        if self.evaluator_version != CANONICAL_EXPECTATION_GAP_VERSION:
            raise ValueError("canonical expectation gap evaluator_version mismatch")
        if self.price <= 0:
            raise ValueError("expectation gap price must be > 0")
        if not self.price_observation_id or not self.mie_snapshot_hash or not self.market_expectation_id:
            raise ValueError("expectation gap evidence references are required")
        if not _SHA256_RE.fullmatch(self.mie_snapshot_hash):
            raise ValueError("mie_snapshot_hash must be 64 lowercase hex characters")
        self.independent_forecast_ref.validate()


def _dec(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _strict_keys(payload: Mapping[str, Any], *, required: set[str], allowed: set[str], path: str) -> None:
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"{path} missing required fields: {missing}")
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ValueError(f"{path} contains unsupported fields: {extra}")


def _parse_date(value: Any, path: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO date") from exc


def _parse_datetime(value: Any, path: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{path} must be timezone-aware")
    return result


def _parse_horizon_years(value: Any, path: str) -> Decimal:
    text = str(value).strip().upper()
    match = _HORIZON_RE.fullmatch(text)
    if not match:
        raise ValueError(f"{path} must use canonical Y/M horizon notation")
    amount = _dec(match.group(1), path)
    years = amount if match.group(2) == "Y" else amount / Decimal("12")
    if years <= 0:
        raise ValueError(f"{path} must be > 0")
    return years


def _parse_gap(payload: Mapping[str, Any]) -> CanonicalExpectationGap:
    if not isinstance(payload, Mapping):
        raise ValueError("expectation_gap must be an object")
    _strict_keys(
        payload,
        required={
            "gap_id",
            "evaluator_version",
            "price",
            "price_observation_id",
            "cutoff_date",
            "mie_snapshot_hash",
            "market_expectation_id",
            "independent_forecast_ref",
        },
        allowed={
            "gap_id",
            "evaluator_version",
            "price",
            "price_observation_id",
            "cutoff_date",
            "mie_snapshot_hash",
            "market_expectation_id",
            "independent_forecast_ref",
        },
        path="expectation_gap",
    )
    forecast_ref = payload["independent_forecast_ref"]
    if not isinstance(forecast_ref, Mapping):
        raise ValueError("expectation_gap.independent_forecast_ref must be an object")
    result = CanonicalExpectationGap(
        gap_id=str(payload["gap_id"]),
        evaluator_version=str(payload["evaluator_version"]),
        price=_dec(payload["price"], "expectation_gap.price"),
        price_observation_id=str(payload["price_observation_id"]),
        cutoff_date=_parse_date(payload["cutoff_date"], "expectation_gap.cutoff_date"),
        mie_snapshot_hash=str(payload["mie_snapshot_hash"]),
        market_expectation_id=str(payload["market_expectation_id"]),
        independent_forecast_ref=CanonicalIndependentForecastReference.from_mapping(
            forecast_ref
        ),
    )
    result.validate()
    return result


def _materialized_expectation(snapshot: Mapping[str, Any], expectation_id: str) -> Mapping[str, Any]:
    mie_set = snapshot.get("mie_set")
    if not isinstance(mie_set, Mapping):
        raise ValueError("P4-F snapshot mie_set is invalid")
    if mie_set.get("resolution_state") != "UNIQUE_MODEL":
        raise ValueError("P4-F snapshot must resolve to UNIQUE_MODEL for expectation gap")
    if mie_set.get("qualification") != MIEQualification.DECISION_GRADE.value:
        raise ValueError("P4-F snapshot must be DECISION_GRADE for expectation gap")
    matches = []
    for evaluation in mie_set.get("model_evaluations") or []:
        if evaluation.get("state") != "MATERIALIZED":
            continue
        expectation = evaluation.get("expectation")
        if isinstance(expectation, Mapping) and expectation.get("expectation_id") == expectation_id:
            matches.append(expectation)
    if len(matches) != 1:
        raise ValueError("expectation_gap.market_expectation_id must identify exactly one materialized MIE in snapshot")
    return matches[0]


def _require_snapshot_price_binding(
    *,
    snapshot: Mapping[str, Any],
    expectation: Mapping[str, Any],
    current_price_observation: Mapping[str, Any],
) -> None:
    observation = expectation.get("observation_basis")
    if not isinstance(observation, Mapping):
        raise ValueError("materialized MIE observation_basis is required")

    observed_date = _parse_datetime(
        current_price_observation.get("observed_at"),
        "current_price_observation.observed_at",
    ).date()
    if observation.get("observation_date") != observed_date.isoformat():
        raise ValueError("MIE observation_basis.observation_date must equal current_price_observation.observed_at date")
    if observation.get("cutoff_date") != snapshot.get("cutoff_date"):
        raise ValueError("MIE observation_basis.cutoff_date must equal snapshot.cutoff_date")
    if observation.get("price_observation_id") != current_price_observation.get("price_observation_id"):
        raise ValueError("MIE observation_basis.price_observation_id must equal current_price_observation.price_observation_id")
    if observation.get("currency") != current_price_observation.get("currency"):
        raise ValueError("MIE observation_basis.currency must equal current_price_observation.currency")
    if observation.get("adjustment_semantics") != current_price_observation.get("adjustment_semantics"):
        raise ValueError("MIE observation_basis.adjustment_semantics must equal current_price_observation.adjustment_semantics")


def _require_point_requirement(
    *,
    expectation: Mapping[str, Any],
    independent: IndependentExpectation,
) -> tuple[Decimal, Decimal, ComparisonDirection]:
    requirements = expectation.get("economic_requirements") or []
    matches = []
    for item in requirements:
        if not isinstance(item, Mapping):
            continue
        try:
            horizon_years = _parse_horizon_years(item.get("horizon"), "market expectation horizon")
        except ValueError:
            continue
        if (
            item.get("economic_variable") == independent.variable_id
            and item.get("unit") == independent.unit
            and item.get("basis") == independent.basis
            and horizon_years == independent.horizon_years
        ):
            matches.append((item, horizon_years))
    if len(matches) != 1:
        raise ValueError(
            "canonical P4-F MIE snapshot must contain exactly one point-valued economic requirement matching the independent expectation semantics"
        )
    requirement, horizon_years = matches[0]
    if "value" not in requirement or "range_low" in requirement or "range_high" in requirement:
        raise ValueError("expectation gap requires a point-valued MIE economic requirement")
    try:
        direction = ComparisonDirection(str(requirement["comparison_direction"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("canonical MIE economic requirement comparison_direction is required") from exc
    return _dec(requirement["value"], "market_implied_expectation.economic_requirements.value"), horizon_years, direction


def evaluate_canonical_expectation_gap(
    payload: Mapping[str, Any],
    *,
    market_implied_expectation_snapshot: Mapping[str, Any],
    current_price: Any,
    current_price_observation: Mapping[str, Any],
    cutoff_date: Any,
    case_id: str,
    market: str,
    symbol: str,
    independent_forecast_resolver: CanonicalIndependentForecastResolver,
) -> dict[str, Any]:
    gap = _parse_gap(payload)
    snapshot = dict(market_implied_expectation_snapshot)

    if independent_forecast_resolver is None:
        raise ValueError("canonical independent forecast resolver is required for expectation gap")
    try:
        validate_p4f_snapshot(snapshot)
    except ValueError as exc:
        raise ValueError(f"invalid canonical P4-F MIE snapshot: {exc}") from exc

    if snapshot.get("snapshot_hash") != gap.mie_snapshot_hash:
        raise ValueError("expectation_gap.mie_snapshot_hash does not match canonical P4-F snapshot")
    if snapshot.get("case_id") != case_id:
        raise ValueError("P4-F snapshot.case_id must equal investment core case_id")
    case_cutoff = _parse_date(cutoff_date, "cutoff_date")
    if snapshot.get("cutoff_date") != case_cutoff.isoformat():
        raise ValueError("P4-F snapshot.cutoff_date must equal case cutoff_date")
    if gap.cutoff_date != case_cutoff:
        raise ValueError("expectation_gap.cutoff_date must equal case cutoff_date")
    if gap.price != _dec(current_price, "current_price_observation.price"):
        raise ValueError("expectation_gap.price must equal current_price_observation.price")

    independent_record = independent_forecast_resolver.resolve_independent_forecast(
        gap.independent_forecast_ref.to_dict(),
        case_id=case_id,
        market=market,
        symbol=symbol,
        cutoff_date=case_cutoff,
    )
    independent_payload = canonical_independent_expectation_from_record(independent_record)
    independent = IndependentExpectation(
        variable_id=independent_payload["variable_id"],
        value=independent_payload["value"],
        unit=independent_payload["unit"],
        basis=independent_payload["basis"],
        horizon_years=independent_payload["horizon_years"],
        evidence_ids=independent_payload["evidence_ids"],
    )

    expectation = _materialized_expectation(snapshot, gap.market_expectation_id)
    _require_snapshot_price_binding(
        snapshot=snapshot,
        expectation=expectation,
        current_price_observation=current_price_observation,
    )

    market_value, market_horizon_years, comparison_direction = _require_point_requirement(
        expectation=expectation,
        independent=independent,
    )
    independent_expectation_payload = {
        "variable_id": independent.variable_id,
        "value": independent.value,
        "unit": independent.unit,
        "basis": independent.basis,
        "horizon_years": str(independent.horizon_years),
    }
    market = {
        "qualification": MIEQualification.DECISION_GRADE.value,
        "resolution_state": "UNIQUE_MODEL",
        "variable_id": independent.variable_id,
        "value": market_value,
        "unit": independent.unit,
        "basis": independent.basis,
        "horizon_years": str(market_horizon_years),
    }
    evaluated = evaluate_expectation_gap(
        independent_expectation=independent_expectation_payload,
        market_expectation=market,
        comparison_direction=comparison_direction.value,
    )

    return {
        **evaluated,
        "gap_id": gap.gap_id,
        "evaluator_version": gap.evaluator_version,
        "price": gap.price,
        "price_observation_id": gap.price_observation_id,
        "independent_forecast_id": independent_record["forecast_id"],
        "independent_forecast_version": independent_record["forecast_version"],
        "independent_forecast_model_version": independent_record["model_version"],
        "cutoff_date": gap.cutoff_date,
        "mie_snapshot_hash": snapshot["snapshot_hash"],
        "market_expectation_id": gap.market_expectation_id,
        "mie_set_hash": snapshot["mie_set_hash"],
        "provenance_hash": snapshot["provenance_hash"],
        "evidence_ids": tuple(sorted(set(independent.evidence_ids) | set(snapshot["mie_set"].get("evidence_ids") or []))),
        "independent_evidence_ids": tuple(sorted(independent.evidence_ids)),
        "mie_evidence_ids": tuple(sorted(snapshot["mie_set"].get("evidence_ids") or [])),
    }


__all__ = [
    "CANONICAL_EXPECTATION_GAP_VERSION",
    "CanonicalExpectationGap",
    "IndependentExpectation",
    "evaluate_canonical_expectation_gap",
]
