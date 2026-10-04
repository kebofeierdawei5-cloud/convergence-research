from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from .market_implied_expectation import (
    CandidateCoverageAssessment,
    EvidenceSufficiencyAssessment,
    MarketImpliedExpectation,
    MIEEconomicRequirement,
    MIEObservationBasis,
    MIEQualification,
    MIERepresentation,
    qualify_market_implied_expectation,
)
from .market_model_domain import (
    CandidateMarketModel,
    FeasibleSolution,
    IdentifiabilityResult,
    IdentifiabilityState,
    MarketModelFamily,
    StabilityResult,
)
from .market_model_identification import (
    CandidateEvaluation,
    MarketModelIdentificationInput,
    RATIO_FAMILIES,
)


RATIO_MIE_FAMILIES = frozenset(RATIO_FAMILIES)


def _ratio_evaluations(
    identification: Mapping[str, object],
    candidates: Sequence[CandidateMarketModel],
) -> tuple[CandidateEvaluation, ...]:
    if identification.get("status") != "PASS":
        raise ValueError("P4-B requires a PASS P3 identification result")
    if identification.get("method") != "model_specific_inverse_v0.2":
        raise ValueError("P4-B requires the accepted P3 model-specific inverse method")

    evaluations = identification.get("evaluations")
    if not isinstance(evaluations, tuple):
        raise ValueError("P3 evaluations must be a tuple of CandidateEvaluation")

    if any(candidate.family not in RATIO_MIE_FAMILIES for candidate in candidates):
        raise ValueError("P4-B accepts only forward PE, PS, PB and EV/EBITDA candidates")

    for evaluation in evaluations:
        if not isinstance(evaluation, CandidateEvaluation):
            raise ValueError("P3 evaluations contain an invalid type")
    return evaluations


def _typed_p3_states(
    identification: Mapping[str, object],
) -> tuple[IdentifiabilityResult, StabilityResult]:
    ident = identification.get("identifiability")
    stability = identification.get("stability")
    if not isinstance(ident, IdentifiabilityResult):
        raise ValueError("P3 identifiability result has an invalid type")
    if not isinstance(stability, StabilityResult):
        raise ValueError("P3 stability result has an invalid type")
    return ident, stability


def _validate_context(
    identification_input: MarketModelIdentificationInput,
    candidate_coverage: CandidateCoverageAssessment,
    evidence_sufficiency: EvidenceSufficiencyAssessment,
) -> tuple[CandidateMarketModel, ...]:
    identification_input.validate()
    candidates = identification_input.candidates
    candidate_ids = {candidate.model_id for candidate in candidates}
    coverage_ids = set(candidate_coverage.candidate_model_ids)
    if not coverage_ids.issubset(candidate_ids):
        raise ValueError("candidate coverage references an unknown model_id")
    if candidate_coverage.status.value == "SUFFICIENT" and coverage_ids != candidate_ids:
        raise ValueError("SUFFICIENT candidate coverage must enumerate the full admitted candidate set")

    evidence_ids = {item.evidence_id for item in identification_input.evidence}
    if not set(candidate_coverage.evidence_ids).issubset(evidence_ids):
        raise ValueError("candidate coverage references unknown evidence_id")
    if not set(evidence_sufficiency.evidence_ids).issubset(evidence_ids):
        raise ValueError("evidence sufficiency references unknown evidence_id")
    evidence_sufficiency.validate()
    candidate_coverage.validate()
    return candidates


def _solution_for_ratio(
    evaluation: CandidateEvaluation,
) -> FeasibleSolution:
    if evaluation.fit.status.value != "FEASIBLE" or evaluation.feasible_solution_set is None:
        raise ValueError("P4-B requires a feasible P3 ratio solution")
    if len(evaluation.feasible_solution_set.solutions) != 1:
        raise ValueError("P4-B ratio vertical slice requires exactly one P3 feasible solution")
    solution = evaluation.feasible_solution_set.solutions[0]
    if not isinstance(solution, FeasibleSolution):
        raise ValueError("P3 feasible solution has an invalid type")
    if solution.range_low is None or solution.range_high is None:
        raise ValueError("P3 ratio solution must expose a bounded implied range")
    if solution.economic_variable == "market_implied_net_profit":
        raise ValueError("generic implied net profit is forbidden")
    return solution


def _qualification_rationale(
    model_id: str,
    identifiability: IdentifiabilityState,
    stability: StabilityResult,
    candidate_coverage: CandidateCoverageAssessment,
    evidence_sufficiency: EvidenceSufficiencyAssessment,
    representation: MIERepresentation,
) -> str:
    return (
        f"P4-B ratio MIE for {model_id}: identifiability={identifiability.value}, "
        f"stability={stability.state.value}, candidate_coverage={candidate_coverage.status.value}, "
        f"evidence_sufficiency={evidence_sufficiency.status.value}, "
        f"representation={representation.value}. "
        "The economic requirement is copied from the accepted P3 feasible solution without "
        "changing its model-native variable semantics."
    )


def build_ratio_market_implied_expectations(
    *,
    identification_input: MarketModelIdentificationInput,
    identification: Mapping[str, object],
    candidate_coverage: CandidateCoverageAssessment,
    evidence_sufficiency: EvidenceSufficiencyAssessment,
    currency: str,
    adjustment_semantics: str,
    period: str,
    horizon: str,
    accounting_basis: str,
) -> tuple[MarketImpliedExpectation, ...]:
    """Convert accepted P3 ratio feasible solutions into P4-A MIE artifacts.

    P4-B does not recompute the inverse. It preserves the P3 feasible solution,
    model-native economic variable, provenance and PIT anchor while applying
    P4-A qualification rules.
    """
    candidates = _validate_context(
        identification_input,
        candidate_coverage,
        evidence_sufficiency,
    )
    evaluations = _ratio_evaluations(identification, candidates)
    ident, stability = _typed_p3_states(identification)

    anchor = next(
        item
        for item in identification_input.observations
        if item.observation_id == identification_input.current_observation_id
    )

    by_model = {
        evaluation.fit.model_id: evaluation
        for evaluation in evaluations
        if evaluation.fit.model_id in {candidate.model_id for candidate in candidates}
    }
    feasible_model_ids = set(ident.feasible_model_ids)
    outputs: list[MarketImpliedExpectation] = []

    for model_id in sorted(feasible_model_ids):
        evaluation = by_model.get(model_id)
        if evaluation is None:
            raise ValueError(f"P3 identifiability references unknown evaluation model_id: {model_id}")
        candidate = next(candidate for candidate in candidates if candidate.model_id == model_id)
        if candidate.family not in RATIO_MIE_FAMILIES:
            raise ValueError("P4-B encountered a non-ratio candidate")
        solution = _solution_for_ratio(evaluation)

        expected_variable = {
            MarketModelFamily.FORWARD_PE: "forward_eps",
            MarketModelFamily.PS: "revenue",
            MarketModelFamily.PB: "book_equity",
            MarketModelFamily.EV_EBITDA: "ebitda",
        }[candidate.family]
        if solution.economic_variable != expected_variable:
            raise ValueError(
                f"P3 solution variable mismatch for {model_id}: "
                f"{solution.economic_variable} != {expected_variable}"
            )

        requirement = MIEEconomicRequirement(
            economic_variable=solution.economic_variable,
            unit=solution.unit,
            basis=solution.basis,
            period=period,
            horizon=horizon,
            accounting_basis=accounting_basis,
            role="IMPLIED_PRIMARY",
            range_low=solution.range_low,
            range_high=solution.range_high,
            evidence_ids=solution.evidence_ids,
        )

        evidence_ids = tuple(sorted(set(
            solution.evidence_ids
            + candidate_coverage.evidence_ids
            + evidence_sufficiency.evidence_ids
        )))

        output = qualify_market_implied_expectation(
            expectation_id=f"mie-p4b-{model_id}",
            model_id=model_id,
            market_model=candidate.family,
            identifiability=ident.state,
            stability=stability.state,
            candidate_coverage=candidate_coverage,
            representation=MIERepresentation.IMPLIED_RANGE,
            economic_requirements=(requirement,),
            observation_basis=MIEObservationBasis(
                price_observation_id=anchor.observation_id,
                observation_date=anchor.observation_date,
                cutoff_date=identification_input.cutoff_date,
                currency=currency,
                adjustment_semantics=adjustment_semantics,
            ),
            assumption_set=(),
            evidence_sufficiency=evidence_sufficiency,
            evidence_ids=evidence_ids,
            qualification_rationale=_qualification_rationale(
                model_id,
                ident.state,
                stability,
                candidate_coverage,
                evidence_sufficiency,
                MIERepresentation.IMPLIED_RANGE,
            ),
        )
        if ident.state == IdentifiabilityState.AMBIGUOUS and output.qualification == MIEQualification.DECISION_GRADE:
            raise ValueError("ambiguous P3 interpretation cannot become decision-grade MIE")
        outputs.append(output)

    if not outputs:
        raise ValueError("no feasible ratio market model; P4-B cannot materialize an MIE")
    return tuple(outputs)
