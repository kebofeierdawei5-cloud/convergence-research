from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Sequence

from .market_model_domain import (
    CandidateMarketModel,
    FeasibleSolution,
    FeasibleSolutionSet,
    FeasibleSolutionStatus,
    FitDiagnostic,
    IdentifiabilityResult,
    IdentifiabilityState,
    MarketModelFamily,
    MarketObservableEvidence,
    ModelFit,
    ModelFitStatus,
    StabilityObservation,
    StabilityResult,
    StabilityState,
)


RATIO_FAMILIES = {
    MarketModelFamily.FORWARD_PE,
    MarketModelFamily.PS,
    MarketModelFamily.PB,
    MarketModelFamily.EV_EBITDA,
}

UNSUPPORTED_FAMILIES = {
    MarketModelFamily.DCF,
    MarketModelFamily.DDM,
    MarketModelFamily.SOTP,
    MarketModelFamily.RNPV,
}

PRIMARY_VARIABLE = {
    MarketModelFamily.FORWARD_PE: "forward_eps",
    MarketModelFamily.PS: "revenue",
    MarketModelFamily.PB: "book_equity",
    MarketModelFamily.EV_EBITDA: "ebitda",
}


def _d(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


@dataclass(frozen=True)
class MarketValuationObservation:
    """Point-in-time observation used by the P3 market-model fitter.

    The observation is deliberately model-neutral; the fitter interprets the
    economic variable according to the candidate model family.
    """

    observation_id: str
    observation_date: date
    known_at: datetime
    price: Decimal
    shares_outstanding: Decimal
    economic_variable: str
    economic_value: Decimal
    unit: str
    basis: str
    evidence_ids: tuple[str, ...]
    source: str
    net_debt: Decimal = Decimal("0")

    def validate(self, cutoff_date: date) -> None:
        if not self.observation_id:
            raise ValueError("observation_id is required")
        if self.observation_date > cutoff_date:
            raise ValueError("observation_date is after cutoff")
        if self.known_at.date() > cutoff_date:
            raise ValueError("known_at is after cutoff")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if self.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be > 0")
        if not self.economic_variable:
            raise ValueError("economic_variable is required")
        if self.economic_value <= 0:
            raise ValueError("economic_value must be > 0")
        if not self.unit or not self.basis or not self.source:
            raise ValueError("unit, basis and source are required")
        if not self.evidence_ids:
            raise ValueError("evidence_ids are required")


@dataclass(frozen=True)
class MarketModelIdentificationInput:
    cutoff_date: date
    current_observation_id: str
    candidates: tuple[CandidateMarketModel, ...]
    observations: tuple[MarketValuationObservation, ...]
    evidence: tuple[MarketObservableEvidence, ...]
    stability_min_historical_points: int = 3

    def validate(self) -> None:
        if not self.current_observation_id:
            raise ValueError("current_observation_id is required")
        if not self.candidates:
            raise ValueError("at least one candidate is required")
        if not self.observations:
            raise ValueError("observations are required")
        if self.stability_min_historical_points < 3:
            raise ValueError("stability_min_historical_points must be >= 3")

        candidate_ids = [candidate.model_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate model_id must be unique")

        observation_ids = [item.observation_id for item in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("observation_id must be unique")
        if self.current_observation_id not in set(observation_ids):
            raise ValueError("current_observation_id not found in observations")

        evidence_ids = {item.evidence_id for item in self.evidence}
        for candidate in self.candidates:
            candidate.validate()
            missing = set(candidate.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(
                    f"candidate {candidate.model_id} references unknown evidence_ids: {sorted(missing)}"
                )
        for item in self.observations:
            item.validate(self.cutoff_date)
        for item in self.evidence:
            item.validate_pit(self.cutoff_date)


@dataclass(frozen=True)
class CandidateEvaluation:
    fit: ModelFit
    feasible_solution_set: FeasibleSolutionSet | None


def _multiple(observation: MarketValuationObservation, family: MarketModelFamily) -> Decimal:
    market_cap = observation.price * observation.shares_outstanding
    if family == MarketModelFamily.FORWARD_PE:
        return observation.price / observation.economic_value
    if family in {MarketModelFamily.PS, MarketModelFamily.PB}:
        return market_cap / observation.economic_value
    if family == MarketModelFamily.EV_EBITDA:
        return (market_cap + observation.net_debt) / observation.economic_value
    raise ValueError(f"no scalar historical multiple for {family.value}")


def _evidence_index(evidence: Iterable[MarketObservableEvidence]) -> dict[str, MarketObservableEvidence]:
    evidence_items = tuple(evidence)
    indexed = {item.evidence_id: item for item in evidence_items}
    if len(indexed) != len(evidence_items):
        raise ValueError("duplicate evidence_id")
    return indexed


def _observation_evidence_ids(
    observations: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
) -> tuple[str, ...]:
    ids: list[str] = []
    for observation in observations:
        for evidence_id in observation.evidence_ids:
            if evidence_id not in evidence_index:
                raise ValueError(f"observation references unknown evidence_id: {evidence_id}")
            ids.append(evidence_id)
    return tuple(sorted(set(ids)))


def _candidate_observations(
    candidate: CandidateMarketModel,
    observations: Sequence[MarketValuationObservation],
) -> tuple[list[MarketValuationObservation], str | None]:
    expected = PRIMARY_VARIABLE.get(candidate.family)
    if expected is None:
        return [], None
    matched = [
        item for item in observations
        if item.economic_variable == expected
    ]
    return sorted(matched, key=lambda x: x.observation_date), expected


def _fit_candidate(
    candidate: CandidateMarketModel,
    observations: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    current_observation_date: date,
    required_historical_points: int = 2,
) -> CandidateEvaluation:
    if candidate.family in UNSUPPORTED_FAMILIES:
        diagnostic = FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:support",
            name="production_solver_support",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=(),
            notes="P3 baseline has no model-specific inverse solver for this family.",
        )
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=(diagnostic,),
            evidence_ids=(),
            constraints=("MODEL_SPECIFIC_SOLVER_REQUIRED",),
        )
        return CandidateEvaluation(fit, None)

    matched, expected_variable = _candidate_observations(candidate, observations)
    if expected_variable is None:
        raise ValueError(f"no primary economic variable defined for {candidate.family.value}")

    current_candidates = [
        item for item in matched
        if item.observation_date == current_observation_date
    ]
    if not current_candidates:
        diagnostic = FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:current_coverage",
            name="current_coverage",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=_observation_evidence_ids(matched, evidence_index),
            notes="No current-date observation exists for the candidate's economic variable.",
        )
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=(diagnostic,),
            evidence_ids=diagnostic.evidence_ids,
            constraints=("CURRENT_OBSERVATION_REQUIRED",),
        )
        return CandidateEvaluation(fit, None)
    current = max(current_candidates, key=lambda x: (x.known_at, x.observation_id))
    historical = [item for item in matched if item.observation_date < current_observation_date]

    all_ids = _observation_evidence_ids(matched, evidence_index)
    diagnostics: list[FitDiagnostic] = []

    if len(historical) < required_historical_points:
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_coverage",
            name="historical_coverage",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=all_ids,
            notes=f"requires at least {required_historical_points} historical observations",
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_ids,
            constraints=("MIN_HISTORICAL_POINTS",),
        )
        return CandidateEvaluation(fit, None)

    multiples = [_multiple(item, candidate.family) for item in historical]
    if any(value <= 0 for value in multiples):
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_validity",
            name="historical_multiple_validity",
            status="INFEASIBLE",
            evidence_ids=all_ids,
            notes="historical market multiple is non-positive",
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INFEASIBLE,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_ids,
            constraints=("POSITIVE_HISTORICAL_MULTIPLE",),
        )
        return CandidateEvaluation(fit, None)

    historical_low = min(multiples)
    historical_high = max(multiples)
    current_multiple = _multiple(current, candidate.family)
    current_consistent = historical_low <= current_multiple <= historical_high

    diagnostics.append(FitDiagnostic(
        diagnostic_id=f"{candidate.model_id}:historical_range",
        name="historical_market_multiple_range",
        status="PASS",
        evidence_ids=all_ids,
        notes=f"range=[{historical_low},{historical_high}] from {len(historical)} historical observations",
    ))
    diagnostics.append(FitDiagnostic(
        diagnostic_id=f"{candidate.model_id}:current_consistency",
        name="current_consistency",
        status="PASS" if current_consistent else "INFEASIBLE",
        evidence_ids=all_ids,
        notes=f"current_multiple={current_multiple}; within_historical_range={current_consistent}",
    ))

    if not current_consistent:
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INFEASIBLE,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_ids,
            constraints=("CURRENT_MULTIPLE_WITHIN_HISTORICAL_RANGE",),
        )
        return CandidateEvaluation(fit, None)

    price = current.price
    if candidate.family == MarketModelFamily.FORWARD_PE:
        implied_low = price / historical_high
        implied_high = price / historical_low
    else:
        current_market_cap = current.price * current.shares_outstanding
        current_ev = current_market_cap + current.net_debt
        denominator = (historical_high, historical_low)
        implied_low = current_ev / denominator[0]
        implied_high = current_ev / denominator[1]

    solution = FeasibleSolution(
        economic_variable=expected_variable,
        unit=current.unit,
        basis=f"current_price_with_historical_{candidate.family.value}_multiple_range",
        model_id=candidate.model_id,
        range_low=implied_low,
        range_high=implied_high,
        evidence_ids=all_ids,
    )
    solution_set = FeasibleSolutionSet(
        model_id=candidate.model_id,
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(solution,),
        constraint_ids=(
            "HISTORICAL_MULTIPLE_RANGE",
            "CURRENT_MULTIPLE_WITHIN_HISTORICAL_RANGE",
        ),
        evidence_ids=all_ids,
        basis=f"current market price divided by historical {candidate.family.value} multiple range",
    )
    solution_set.validate()

    fit = ModelFit(
        model_id=candidate.model_id,
        status=ModelFitStatus.FEASIBLE,
        diagnostics=tuple(diagnostics),
        evidence_ids=all_ids,
        constraints=(
            "MIN_HISTORICAL_POINTS",
            "CURRENT_MULTIPLE_WITHIN_HISTORICAL_RANGE",
        ),
    )
    fit.validate()
    return CandidateEvaluation(fit, solution_set)


def _identify(
    evaluations: Sequence[CandidateEvaluation],
) -> IdentifiabilityResult:
    feasible = tuple(sorted(
        evaluation.fit.model_id
        for evaluation in evaluations
        if evaluation.fit.status == ModelFitStatus.FEASIBLE
        and evaluation.feasible_solution_set is not None
    ))
    insufficient = any(
        evaluation.fit.status == ModelFitStatus.INSUFFICIENT_EVIDENCE
        for evaluation in evaluations
    )
    evidence_ids = tuple(sorted(set(
        evidence_id
        for evaluation in evaluations
        for evidence_id in evaluation.fit.evidence_ids
    )))

    if len(feasible) >= 2:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.AMBIGUOUS,
            feasible_model_ids=feasible,
            selected_model_id=None,
            competing_model_ids=feasible[1:],
            evidence_ids=evidence_ids,
            rationale="Multiple candidate models remain materially feasible under the same evidence boundary.",
    elif len(feasible) == 1 and insufficient:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.INSUFFICIENT_EVIDENCE,
            feasible_model_ids=feasible,
            selected_model_id=None,
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="One candidate is feasible, but another candidate remains unevaluable; uniqueness cannot be established conservatively.",
        )
    elif len(feasible) == 1:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.IDENTIFIABLE,
            feasible_model_ids=feasible,
            selected_model_id=feasible[0],
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="Exactly one candidate model has sufficient historical evidence and current consistency.",
        )
        )
    elif insufficient:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.INSUFFICIENT_EVIDENCE,
            feasible_model_ids=(),
            selected_model_id=None,
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="At least one candidate lacks sufficient model-specific evidence and no candidate is currently identifiable.",
        )
    else:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.UNIDENTIFIABLE,
            feasible_model_ids=(),
            selected_model_id=None,
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="All admitted candidates are infeasible under the current evidence and constraints.",
        )
    result.validate()
    return result


def _stability(
    inp: MarketModelIdentificationInput,
    full_evaluations: Sequence[CandidateEvaluation],
    full_ident: IdentifiabilityResult,
) -> StabilityResult:
    anchor = next(
        item for item in inp.observations
        if item.observation_id == inp.current_observation_id
    )
    current_observation_date = anchor.observation_date
    current_observations = tuple(
        item for item in inp.observations
        if item.observation_date == current_observation_date
    )
    historical = sorted(
        (item for item in inp.observations if item.observation_date < current_observation_date),
        key=lambda x: x.observation_date,
    )

    if len(historical) < inp.stability_min_historical_points:
        result = StabilityResult(
            state=StabilityState.INSUFFICIENT_EVIDENCE,
            assessment_method="leave_one_out_historical_window",
            observations=(),
            evidence_ids=full_ident.evidence_ids,
            rationale=f"requires at least {inp.stability_min_historical_points} historical observations",
        )
        result.validate()
        return result

    windows = [historical]
    for index in range(len(historical)):
        remaining = historical[:index] + historical[index + 1:]
        if len(remaining) >= inp.stability_min_historical_points:
            windows.append(remaining)

    observations: list[StabilityObservation] = []
    state_signature: list[tuple[str, tuple[str, ...]]] = [
        (full_ident.state.value, full_ident.feasible_model_ids)
    ]

    for index, historical_window in enumerate(windows):
        window_observations = tuple(historical_window) + current_observations
        evaluations = [
            _fit_candidate(candidate, window_observations, _evidence_index(inp.evidence), current_observation_date)
            for candidate in inp.candidates
        ]
        ident = _identify(evaluations)
        state_signature.append((ident.state.value, ident.feasible_model_ids))
        observations.append(StabilityObservation(
            perturbation_id=f"loo-{index}",
            perturbation="full historical set" if index == 0 else f"leave out {historical[index - 1].observation_id}",
            resulting_state=StabilityState.STABLE if (
                ident.state == full_ident.state
                and ident.feasible_model_ids == full_ident.feasible_model_ids
                and ident.selected_model_id == full_ident.selected_model_id
            ) else StabilityState.UNSTABLE,
            selected_model_id=ident.selected_model_id,
        ))

    stable = all(
        state == full_ident.state.value and feasible == full_ident.feasible_model_ids
        for state, feasible in state_signature
    )
    result = StabilityResult(
        state=StabilityState.STABLE if stable else StabilityState.UNSTABLE,
        assessment_method="leave_one_out_historical_window",
        observations=tuple(observations),
        evidence_ids=full_ident.evidence_ids,
        rationale=(
            "Market-model identifiability is invariant across the full and admissible leave-one-out historical windows."
            if stable else
            "Market-model identifiability changes under an admissible historical-window perturbation."
        ),
    )
    result.validate()
    return result


def identify_market_models(inp: MarketModelIdentificationInput) -> dict[str, object]:
    """Evidence-backed P3 baseline identification.

    Ratio-model families are identified from historical/current observed
    economics and the resulting market-multiple range. Complex model families
    remain explicitly insufficient until a model-specific inverse solver is
    available. No numeric score or LLM judgment is used to select a winner.
    """

    inp.validate()
    evidence_index = _evidence_index(inp.evidence)

    evaluations = [
        _fit_candidate(
            candidate,
            inp.observations,
            evidence_index,
            next(
                item.observation_date
                for item in inp.observations
                if item.observation_id == inp.current_observation_id
            ),
        )
        for candidate in inp.candidates
    ]
    ident = _identify(evaluations)
    stability = _stability(inp, evaluations, ident)

    return {
        "status": "PASS",
        "method": "historical_multiple_range_v0.2",
        "identifiability": ident,
        "stability": stability,
        "evaluations": tuple(evaluations),
    }
