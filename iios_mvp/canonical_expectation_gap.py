from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Mapping

from .market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEAssumption,
    MIEEconomicRequirement,
    MIEObservationBasis,
    MIEQualification,
    MIERepresentation,
    MarketImpliedExpectation,
)
from .market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState
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
    market_expectation_id: str
    market_expectation_hash: str
    comparison_direction: ComparisonDirection
    independent_expectation: IndependentExpectation

    def validate(self) -> None:
        if not self.gap_id:
            raise ValueError("gap_id is required")
        if self.evaluator_version != CANONICAL_EXPECTATION_GAP_VERSION:
            raise ValueError("canonical expectation gap evaluator_version mismatch")
        if self.price <= 0:
            raise ValueError("expectation gap price must be > 0")
        if not self.price_observation_id or not self.market_expectation_id:
            raise ValueError("expectation gap evidence references are required")
        if not _SHA256_RE.fullmatch(self.market_expectation_hash):
            raise ValueError("market_expectation_hash must be 64 lowercase hex characters")
        self.independent_expectation.validate()


def _dec(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def market_implied_expectation_content_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


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


def _parse_horizon_years(value: Any, path: str) -> Decimal:
    text = str(value).strip().upper()
    match = _HORIZON_RE.fullmatch(text)
    if not match:
        raise ValueError(f"{path} must use canonical Y/M horizon notation")
    amount = _dec(match.group(1), path)
    unit = match.group(2)
    years = amount if unit == "Y" else amount / Decimal("12")
    if years <= 0:
        raise ValueError(f"{path} must be > 0")
    return years


def _parse_mie(payload: Mapping[str, Any]) -> MarketImpliedExpectation:
    if not isinstance(payload, Mapping):
        raise ValueError("market_implied_expectation must be an object")

    _strict_keys(
        payload,
        required={
            "expectation_id",
            "model_id",
            "market_model",
            "identifiability",
            "stability",
            "candidate_coverage",
            "representation",
            "economic_requirements",
            "observation_basis",
            "assumption_set",
            "evidence_sufficiency",
            "evidence_ids",
            "qualification",
            "qualification_rationale",
        },
        allowed={
            "expectation_id",
            "model_id",
            "market_model",
            "identifiability",
            "stability",
            "candidate_coverage",
            "representation",
            "economic_requirements",
            "observation_basis",
            "assumption_set",
            "evidence_sufficiency",
            "evidence_ids",
            "qualification",
            "qualification_rationale",
        },
        path="market_implied_expectation",
    )

    coverage = payload["candidate_coverage"]
    if not isinstance(coverage, Mapping):
        raise ValueError("market_implied_expectation.candidate_coverage must be an object")
    _strict_keys(
        coverage,
        required={"status", "scope_basis", "candidate_model_ids", "evidence_ids", "rationale"},
        allowed={"status", "scope_basis", "candidate_model_ids", "evidence_ids", "rationale"},
        path="market_implied_expectation.candidate_coverage",
    )

    evidence_sufficiency = payload["evidence_sufficiency"]
    if not isinstance(evidence_sufficiency, Mapping):
        raise ValueError("market_implied_expectation.evidence_sufficiency must be an object")
    _strict_keys(
        evidence_sufficiency,
        required={"status", "rationale", "evidence_ids"},
        allowed={"status", "rationale", "evidence_ids"},
        path="market_implied_expectation.evidence_sufficiency",
    )

    observation = payload["observation_basis"]
    if not isinstance(observation, Mapping):
        raise ValueError("market_implied_expectation.observation_basis must be an object")
    _strict_keys(
        observation,
        required={"price_observation_id", "observation_date", "cutoff_date", "currency", "adjustment_semantics"},
        allowed={"price_observation_id", "observation_date", "cutoff_date", "currency", "adjustment_semantics"},
        path="market_implied_expectation.observation_basis",
    )

    requirements = []
    for index, item in enumerate(payload["economic_requirements"]):
        if not isinstance(item, Mapping):
            raise ValueError(f"market_implied_expectation.economic_requirements[{index}] must be an object")
        _strict_keys(
            item,
            required={"economic_variable", "unit", "basis", "period", "horizon", "accounting_basis", "role", "evidence_ids"},
            allowed={
                "economic_variable", "unit", "basis", "period", "horizon", "accounting_basis",
                "role", "value", "range_low", "range_high", "evidence_ids"
            },
            path=f"market_implied_expectation.economic_requirements[{index}]",
        )
        requirements.append(
            MIEEconomicRequirement(
                economic_variable=str(item["economic_variable"]),
                unit=str(item["unit"]),
                basis=str(item["basis"]),
                period=str(item["period"]),
                horizon=str(item["horizon"]),
                accounting_basis=str(item["accounting_basis"]),
                role=str(item["role"]),
                value=_dec(item["value"], f"economic_requirements[{index}].value") if "value" in item else None,
                range_low=_dec(item["range_low"], f"economic_requirements[{index}].range_low") if "range_low" in item else None,
                range_high=_dec(item["range_high"], f"economic_requirements[{index}].range_high") if "range_high" in item else None,
                evidence_ids=tuple(str(x) for x in item["evidence_ids"]),
            )
        )

    assumptions = []
    for index, item in enumerate(payload["assumption_set"]):
        if not isinstance(item, Mapping):
            raise ValueError(f"market_implied_expectation.assumption_set[{index}] must be an object")
        _strict_keys(
            item,
            required={"variable", "value", "unit", "basis", "period", "horizon", "accounting_basis", "evidence_ids"},
            allowed={"variable", "value", "unit", "basis", "period", "horizon", "accounting_basis", "evidence_ids"},
            path=f"market_implied_expectation.assumption_set[{index}]",
        )
        assumptions.append(
            MIEAssumption(
                variable=str(item["variable"]),
                value=_dec(item["value"], f"assumption_set[{index}].value"),
                unit=str(item["unit"]),
                basis=str(item["basis"]),
                period=str(item["period"]),
                horizon=str(item["horizon"]),
                accounting_basis=str(item["accounting_basis"]),
                evidence_ids=tuple(str(x) for x in item["evidence_ids"]),
            )
        )

    result = MarketImpliedExpectation(
        expectation_id=str(payload["expectation_id"]),
        model_id=str(payload["model_id"]),
        market_model=MarketModelFamily(str(payload["market_model"])),
        identifiability=IdentifiabilityState(str(payload["identifiability"])),
        stability=StabilityState(str(payload["stability"])),
        candidate_coverage=CandidateCoverageAssessment(
            status=CandidateCoverageState(str(coverage["status"])),
            scope_basis=str(coverage["scope_basis"]),
            candidate_model_ids=tuple(str(x) for x in coverage["candidate_model_ids"]),
            evidence_ids=tuple(str(x) for x in coverage["evidence_ids"]),
            rationale=str(coverage["rationale"]),
        ),
        representation=MIERepresentation(str(payload["representation"])),
        economic_requirements=tuple(requirements),
        observation_basis=MIEObservationBasis(
            price_observation_id=str(observation["price_observation_id"]),
            observation_date=_parse_date(observation["observation_date"], "observation_basis.observation_date"),
            cutoff_date=_parse_date(observation["cutoff_date"], "observation_basis.cutoff_date"),
            currency=str(observation["currency"]),
            adjustment_semantics=str(observation["adjustment_semantics"]),
        ),
        assumption_set=tuple(assumptions),
        evidence_sufficiency=EvidenceSufficiencyAssessment(
            status=EvidenceSufficiencyState(str(evidence_sufficiency["status"])),
            rationale=str(evidence_sufficiency["rationale"]),
            evidence_ids=tuple(str(x) for x in evidence_sufficiency["evidence_ids"]),
        ),
        evidence_ids=tuple(str(x) for x in payload["evidence_ids"]),
        qualification=MIEQualification(str(payload["qualification"])),
        qualification_rationale=str(payload["qualification_rationale"]),
    )
    result.validate()
    if result.qualification != MIEQualification.DECISION_GRADE:
        raise ValueError("market_implied_expectation is not decision-grade")
    return result


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
            "market_expectation_id",
            "market_expectation_hash",
            "comparison_direction",
            "independent_expectation",
        },
        allowed={
            "gap_id",
            "evaluator_version",
            "price",
            "price_observation_id",
            "cutoff_date",
            "market_expectation_id",
            "market_expectation_hash",
            "comparison_direction",
            "independent_expectation",
        },
        path="expectation_gap",
    )
    independent = payload["independent_expectation"]
    if not isinstance(independent, Mapping):
        raise ValueError("expectation_gap.independent_expectation must be an object")
    _strict_keys(
        independent,
        required={"variable_id", "value", "unit", "basis", "horizon_years", "evidence_ids"},
        allowed={"variable_id", "value", "unit", "basis", "horizon_years", "evidence_ids"},
        path="expectation_gap.independent_expectation",
    )
    result = CanonicalExpectationGap(
        gap_id=str(payload["gap_id"]),
        evaluator_version=str(payload["evaluator_version"]),
        price=_dec(payload["price"], "expectation_gap.price"),
        price_observation_id=str(payload["price_observation_id"]),
        cutoff_date=_parse_date(payload["cutoff_date"], "expectation_gap.cutoff_date"),
        market_expectation_id=str(payload["market_expectation_id"]),
        market_expectation_hash=str(payload["market_expectation_hash"]),
        comparison_direction=ComparisonDirection(str(payload["comparison_direction"])),
        independent_expectation=IndependentExpectation(
            variable_id=str(independent["variable_id"]),
            value=_dec(independent["value"], "independent_expectation.value"),
            unit=str(independent["unit"]),
            basis=str(independent["basis"]),
            horizon_years=_dec(independent["horizon_years"], "independent_expectation.horizon_years"),
            evidence_ids=tuple(str(x) for x in independent["evidence_ids"]),
        ),
    )
    result.validate()
    return result


def evaluate_canonical_expectation_gap(
    payload: Mapping[str, Any],
    *,
    market_implied_expectation_payload: Mapping[str, Any],
    current_price: Any,
    cutoff_date: Any,
) -> dict[str, Any]:
    gap = _parse_gap(payload)
    mie = _parse_mie(market_implied_expectation_payload)

    if gap.market_expectation_id != mie.expectation_id:
        raise ValueError("expectation_gap.market_expectation_id does not match market_implied_expectation.expectation_id")
    if gap.market_expectation_hash != market_implied_expectation_content_hash(market_implied_expectation_payload):
        raise ValueError("expectation_gap.market_expectation_hash does not match canonical MIE content")
    if gap.price != _dec(current_price, "current_price_observation.price"):
        raise ValueError("expectation_gap.price must equal current_price_observation.price")
    case_cutoff = _parse_date(cutoff_date, "cutoff_date")
    if gap.cutoff_date != case_cutoff:
        raise ValueError("expectation_gap.cutoff_date must equal case cutoff_date")
    if mie.observation_basis.cutoff_date != case_cutoff:
        raise ValueError("market_implied_expectation observation_basis.cutoff_date must equal case cutoff_date")
    if gap.price_observation_id != mie.observation_basis.price_observation_id:
        raise ValueError("expectation_gap.price_observation_id must equal MIE observation_basis.price_observation_id")

    matches = []
    for item in mie.economic_requirements:
        try:
            item_horizon_years = _parse_horizon_years(item.horizon, "market expectation horizon")
        except ValueError:
            continue
        if (
            item.economic_variable == gap.independent_expectation.variable_id
            and item.unit == gap.independent_expectation.unit
            and item.basis == gap.independent_expectation.basis
            and item_horizon_years == gap.independent_expectation.horizon_years
        ):
            matches.append((item, item_horizon_years))

    if len(matches) != 1:
        raise ValueError(
            "canonical MIE must contain exactly one point-valued economic requirement matching the independent expectation semantics"
        )

    requirement, market_horizon_years = matches[0]
    if requirement.value is None or requirement.range_low is not None or requirement.range_high is not None:
        raise ValueError("expectation gap requires a point-valued MIE economic requirement")

    independent = {
        "variable_id": gap.independent_expectation.variable_id,
        "value": gap.independent_expectation.value,
        "unit": gap.independent_expectation.unit,
        "basis": gap.independent_expectation.basis,
        "horizon_years": str(gap.independent_expectation.horizon_years),
    }
    market = {
        "qualification": mie.qualification.value,
        "resolution_state": "UNIQUE_MODEL",
        "variable_id": requirement.economic_variable,
        "value": requirement.value,
        "unit": requirement.unit,
        "basis": requirement.basis,
        "horizon_years": str(market_horizon_years),
    }
    evaluated = evaluate_expectation_gap(
        independent_expectation=independent,
        market_expectation=market,
        comparison_direction=gap.comparison_direction.value,
    )

    evidence_ids = set(gap.independent_expectation.evidence_ids)
    evidence_ids.update(mie.evidence_ids)
    requirement_ids = set(requirement.evidence_ids)
    if not requirement_ids.issubset(set(mie.evidence_ids)):
        raise ValueError("MIE requirement evidence is outside the MIE top-level evidence closure")

    return {
        **evaluated,
        "gap_id": gap.gap_id,
        "evaluator_version": gap.evaluator_version,
        "price": gap.price,
        "price_observation_id": gap.price_observation_id,
        "cutoff_date": gap.cutoff_date,
        "market_expectation_id": mie.expectation_id,
        "market_expectation_hash": gap.market_expectation_hash,
        "market_model_id": mie.model_id,
        "market_model": mie.market_model.value,
        "evidence_ids": tuple(sorted(evidence_ids)),
        "independent_evidence_ids": tuple(sorted(gap.independent_expectation.evidence_ids)),
        "mie_evidence_ids": tuple(sorted(mie.evidence_ids)),
    }


__all__ = [
    "CANONICAL_EXPECTATION_GAP_VERSION",
    "CanonicalExpectationGap",
    "IndependentExpectation",
    "evaluate_canonical_expectation_gap",
    "market_implied_expectation_content_hash",
]
