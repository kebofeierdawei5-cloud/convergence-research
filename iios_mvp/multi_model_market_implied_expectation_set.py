from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from .market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEQualification,
    MarketImpliedExpectation,
)

class MIEModelEvaluationState(str, Enum):
    MATERIALIZED = "MATERIALIZED"
    NO_FEASIBLE_SOLUTION = "NO_FEASIBLE_SOLUTION"
    BLOCKED = "BLOCKED"

class MIESetResolutionState(str, Enum):
    UNIQUE_MODEL = "UNIQUE_MODEL"
    AMBIGUOUS = "AMBIGUOUS"
    NO_FEASIBLE_MODEL = "NO_FEASIBLE_MODEL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

@dataclass(frozen=True)
class MIEModelEvaluation:
    model_id: str
    state: MIEModelEvaluationState
    expectation: MarketImpliedExpectation | None
    evidence_ids: tuple[str, ...]
    rationale: str

    @classmethod
    def from_expectation(cls, expectation: MarketImpliedExpectation, *, rationale: str | None = None) -> "MIEModelEvaluation":
        expectation.validate()
        blocked = expectation.qualification == MIEQualification.BLOCKED
        return cls(
            model_id=expectation.model_id,
            state=MIEModelEvaluationState.BLOCKED if blocked else MIEModelEvaluationState.MATERIALIZED,
            expectation=None if blocked else expectation,
            evidence_ids=expectation.evidence_ids,
            rationale=rationale or f"Consumed P4 MIE with qualification={expectation.qualification.value}.",
        )

    @classmethod
    def no_feasible_solution(cls, *, model_id: str, evidence_ids: tuple[str, ...], rationale: str) -> "MIEModelEvaluation":
        return cls(model_id, MIEModelEvaluationState.NO_FEASIBLE_SOLUTION, None, evidence_ids, rationale)

    @classmethod
    def blocked(cls, *, model_id: str, evidence_ids: tuple[str, ...], rationale: str) -> "MIEModelEvaluation":
        return cls(model_id, MIEModelEvaluationState.BLOCKED, None, evidence_ids, rationale)

    def validate(self) -> None:
        if not self.model_id or not self.evidence_ids or not self.rationale:
            raise ValueError("model evaluation metadata is required")
        if self.state == MIEModelEvaluationState.MATERIALIZED:
            if self.expectation is None:
                raise ValueError("MATERIALIZED evaluation requires an expectation")
            if self.expectation.model_id != self.model_id:
                raise ValueError("MIE model evaluation model_id/expectation mismatch")
            self.expectation.validate()
        elif self.expectation is not None:
            raise ValueError("non-materialized evaluation cannot carry an expectation")

@dataclass(frozen=True)
class MultiModelMarketImpliedExpectationSet:
    set_id: str
    candidate_coverage: CandidateCoverageAssessment
    evidence_sufficiency: EvidenceSufficiencyAssessment
    model_evaluations: tuple[MIEModelEvaluation, ...]
    resolution_state: MIESetResolutionState
    qualification: MIEQualification
    qualification_rationale: str
    evidence_ids: tuple[str, ...]

    def validate(self) -> None:
        if not self.set_id or not self.evidence_ids or not self.qualification_rationale:
            raise ValueError("P4-E set metadata is required")
        self.candidate_coverage.validate()
        self.evidence_sufficiency.validate()
        candidate_ids = self.candidate_coverage.candidate_model_ids
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate coverage model IDs must be unique")
        if not self.model_evaluations:
            raise ValueError("P4-E requires one evaluation record per admitted candidate model")
        for item in self.model_evaluations:
            item.validate()
        evaluation_ids = tuple(item.model_id for item in self.model_evaluations)
        if len(set(evaluation_ids)) != len(evaluation_ids):
            raise ValueError("model evaluation model_ids must be unique")
        if set(evaluation_ids) != set(candidate_ids):
            raise ValueError("P4-E requires exactly one evaluation record for every admitted candidate model")
        materialized = [
            item.expectation for item in self.model_evaluations
            if item.state == MIEModelEvaluationState.MATERIALIZED and item.expectation is not None
        ]
        if materialized and len({x.observation_basis for x in materialized}) != 1:
            raise ValueError("P4-E materialized expectations must share the exact same observation basis")
        referenced = set(self.candidate_coverage.evidence_ids) | set(self.evidence_sufficiency.evidence_ids)
        for item in self.model_evaluations:
            referenced.update(item.evidence_ids)
            if item.expectation is not None:
                referenced.update(item.expectation.evidence_ids)
        if not referenced.issubset(self.evidence_ids):
            raise ValueError("P4-E evidence_ids must cover candidate/evidence/evaluation nested evidence")
        if self.resolution_state != self.expected_resolution():
            raise ValueError(f"P4-E resolution mismatch: expected {self.expected_resolution().value}, got {self.resolution_state.value}")
        if self.qualification != self.expected_qualification():
            raise ValueError(f"P4-E qualification mismatch: expected {self.expected_qualification().value}, got {self.qualification.value}")

    def expected_resolution(self) -> MIESetResolutionState:
        if self.candidate_coverage.status != CandidateCoverageState.SUFFICIENT:
            return MIESetResolutionState.INSUFFICIENT_EVIDENCE
        if self.evidence_sufficiency.status != EvidenceSufficiencyState.SUFFICIENT:
            return MIESetResolutionState.INSUFFICIENT_EVIDENCE
        if any(item.state == MIEModelEvaluationState.BLOCKED for item in self.model_evaluations):
            return MIESetResolutionState.INSUFFICIENT_EVIDENCE
        count = sum(item.state == MIEModelEvaluationState.MATERIALIZED for item in self.model_evaluations)
        if count == 0:
            return MIESetResolutionState.NO_FEASIBLE_MODEL
        if count > 1:
            return MIESetResolutionState.AMBIGUOUS
        return MIESetResolutionState.UNIQUE_MODEL

    def expected_qualification(self) -> MIEQualification:
        if self.resolution_state in {MIESetResolutionState.INSUFFICIENT_EVIDENCE, MIESetResolutionState.NO_FEASIBLE_MODEL}:
            return MIEQualification.BLOCKED
        if self.resolution_state == MIESetResolutionState.AMBIGUOUS:
            return MIEQualification.CONDITIONAL_ONLY
        materialized = self.materialized_expectations()
        if len(materialized) != 1:
            raise ValueError("P4-E UNIQUE_MODEL requires exactly one materialized expectation")
        return materialized[0].qualification

    def materialized_expectations(self) -> tuple[MarketImpliedExpectation, ...]:
        return tuple(item.expectation for item in self.model_evaluations if item.state == MIEModelEvaluationState.MATERIALIZED and item.expectation is not None)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "set_id": self.set_id,
            "candidate_coverage": _coverage_to_dict(self.candidate_coverage),
            "evidence_sufficiency": _evidence_to_dict(self.evidence_sufficiency),
            "model_evaluations": [_evaluation_to_dict(item) for item in self.model_evaluations],
            "resolution_state": self.resolution_state.value,
            "qualification": self.qualification.value,
            "qualification_rationale": self.qualification_rationale,
            "evidence_ids": list(self.evidence_ids),
        }

def build_multi_model_market_implied_expectation_set(*, set_id: str, candidate_coverage: CandidateCoverageAssessment, evidence_sufficiency: EvidenceSufficiencyAssessment, model_evaluations: Sequence[MIEModelEvaluation], qualification_rationale: str, evidence_ids: tuple[str, ...]) -> MultiModelMarketImpliedExpectationSet:
    result = MultiModelMarketImpliedExpectationSet(set_id, candidate_coverage, evidence_sufficiency, tuple(model_evaluations), MIESetResolutionState.INSUFFICIENT_EVIDENCE, MIEQualification.BLOCKED, qualification_rationale, evidence_ids)
    result = MultiModelMarketImpliedExpectationSet(result.set_id, result.candidate_coverage, result.evidence_sufficiency, result.model_evaluations, result.expected_resolution(), MIEQualification.BLOCKED, result.qualification_rationale, result.evidence_ids)
    result = MultiModelMarketImpliedExpectationSet(result.set_id, result.candidate_coverage, result.evidence_sufficiency, result.model_evaluations, result.resolution_state, result.expected_qualification(), result.qualification_rationale, result.evidence_ids)
    result.validate()
    return result

def _coverage_to_dict(value: CandidateCoverageAssessment) -> dict[str, Any]:
    return {"status": value.status.value, "scope_basis": value.scope_basis, "candidate_model_ids": list(value.candidate_model_ids), "evidence_ids": list(value.evidence_ids), "rationale": value.rationale}

def _evidence_to_dict(value: EvidenceSufficiencyAssessment) -> dict[str, Any]:
    return {"status": value.status.value, "rationale": value.rationale, "evidence_ids": list(value.evidence_ids)}

def _evaluation_to_dict(value: MIEModelEvaluation) -> dict[str, Any]:
    payload = {"model_id": value.model_id, "state": value.state.value, "evidence_ids": list(value.evidence_ids), "rationale": value.rationale}
    if value.expectation is not None:
        payload["expectation"] = _mie_to_dict(value.expectation)
    return payload

def _mie_to_dict(value: MarketImpliedExpectation) -> dict[str, Any]:
    return {
        "expectation_id": value.expectation_id, "model_id": value.model_id, "market_model": value.market_model.value,
        "identifiability": value.identifiability.value, "stability": value.stability.value,
        "candidate_coverage": _coverage_to_dict(value.candidate_coverage), "representation": value.representation.value,
        "economic_requirements": [_requirement_to_dict(x) for x in value.economic_requirements],
        "observation_basis": {"price_observation_id": value.observation_basis.price_observation_id, "observation_date": value.observation_basis.observation_date.isoformat(), "cutoff_date": value.observation_basis.cutoff_date.isoformat(), "currency": value.observation_basis.currency, "adjustment_semantics": value.observation_basis.adjustment_semantics},
        "assumption_set": [_assumption_to_dict(x) for x in value.assumption_set],
        "evidence_sufficiency": _evidence_to_dict(value.evidence_sufficiency), "evidence_ids": list(value.evidence_ids),
        "qualification": value.qualification.value, "qualification_rationale": value.qualification_rationale,
    }

def _requirement_to_dict(value) -> dict[str, Any]:
    payload = {"economic_variable": value.economic_variable, "unit": value.unit, "basis": value.basis, "period": value.period, "horizon": value.horizon, "accounting_basis": value.accounting_basis, "role": value.role, "evidence_ids": list(value.evidence_ids)}
    if value.value is not None: payload["value"] = str(value.value)
    else: payload["range_low"] = str(value.range_low); payload["range_high"] = str(value.range_high)
    return payload

def _assumption_to_dict(value) -> dict[str, Any]:
    return {"variable": value.variable, "value": str(value.value), "unit": value.unit, "basis": value.basis, "period": value.period, "horizon": value.horizon, "accounting_basis": value.accounting_basis, "evidence_ids": list(value.evidence_ids)}

