from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from .market_implied_expectation import (
    CandidateCoverageAssessment,
    EvidenceSufficiencyAssessment,
    MIEAssumption,
    MIEEconomicRequirement,
    MIEObservationBasis,
    MIERepresentation,
    MarketImpliedExpectation,
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
)


COMPLEX_CONDITIONAL_FAMILIES = frozenset({
    MarketModelFamily.DCF,
    MarketModelFamily.DDM,
})

CONDITIONAL_ASSUMPTIONS = {
    MarketModelFamily.DCF: (
        "growth",
        "margin",
        "reinvestment",
        "terminal_value",
        "discount_rate",
    ),
    MarketModelFamily.DDM: (
        "payout",
        "growth",
        "discount_rate",
    ),
}

PRIMARY_VARIABLE = {
    MarketModelFamily.DCF: "fcf",
    MarketModelFamily.DDM: "dividend",
}


def _typed_complex_evaluations(
    identification: Mapping[str, object],
    candidates: Sequence[CandidateMarketModel],
) -> tuple[CandidateEvaluation, ...]:
    if identification.get("status") != "PASS":
        raise ValueError("P4-C requires a PASS P3 identification result")
    if identification.get("method") != "model_specific_inverse_v0.2":
        raise ValueError("P4-C requires the accepted P3 model-specific inverse method")
    if any(candidate.family not in COMPLEX_CONDITIONAL_FAMILIES for candidate in candidates):
        raise ValueError("P4-C accepts only DCF and DDM candidates")

    evaluations = identification.get("evaluations")
    if not isinstance(evaluations, tuple):
        raise ValueError("P3 evaluations must be a tuple of CandidateEvaluation")
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
    if (
        candidate_coverage.status.value == "SUFFICIENT"
        and coverage_ids != candidate_ids
    ):
        raise ValueError(
            "SUFFICIENT candidate coverage must enumerate the full admitted candidate set"
        )

    evidence_ids = {item.evidence_id for item in identification_input.evidence}
    if not set(candidate_coverage.evidence_ids).issubset(evidence_ids):
        raise ValueError("candidate coverage references unknown evidence_id")
    if not set(evidence_sufficiency.evidence_ids).issubset(evidence_ids):
        raise ValueError("evidence sufficiency references unknown evidence_id")

    evidence_sufficiency.validate()
    candidate_coverage.validate()
    return candidates


def _evidence_index(
    identification_input: MarketModelIdentificationInput,
) -> dict[str, object]:
    indexed = {item.evidence_id: item for item in identification_input.evidence}
    if len(indexed) != len(identification_input.evidence):
        raise ValueError("duplicate evidence_id")
    return indexed


def _current_observation_group(
    identification_input: MarketModelIdentificationInput,
) -> tuple[date, tuple[object, ...]]:
    anchor = next(
        item
        for item in identification_input.observations
        if item.observation_id == identification_input.current_observation_id
    )
    group = tuple(
        item
        for item in identification_input.observations
        if item.observation_date == anchor.observation_date
    )
    if not group:
        raise ValueError("current observation group is missing")
    return anchor.observation_date, group


def _latest_current_by_variable(group: Sequence[object]) -> dict[str, object]:
    latest: dict[str, object] = {}
    for item in group:
        existing = latest.get(item.economic_variable)
        if existing is None or (item.known_at, item.observation_id) > (
            existing.known_at,
            existing.observation_id,
        ):
            latest[item.economic_variable] = item
    return latest


def _validate_observation_evidence(
    item: object,
    evidence_index: Mapping[str, object],
) -> None:
    for evidence_id in item.evidence_ids:
        evidence = evidence_index.get(evidence_id)
        if evidence is None:
            raise ValueError(
                f"assumption observation references unknown evidence_id: {evidence_id}"
            )
        if evidence.variable != item.economic_variable:
            raise ValueError(
                f"assumption observation evidence variable mismatch: {evidence_id}"
            )
        if evidence.unit != item.unit:
            raise ValueError(
                f"assumption observation evidence unit mismatch: {evidence_id}"
            )


def _solution_for_complex(
    evaluation: CandidateEvaluation,
    candidate: CandidateMarketModel,
) -> FeasibleSolution:
    if evaluation.fit.model_id != candidate.model_id:
        raise ValueError("P3 evaluation/model_id mismatch")
    if (
        evaluation.fit.status.value != "FEASIBLE"
        or evaluation.feasible_solution_set is None
    ):
        raise ValueError("P4-C requires a feasible P3 DCF/DDM solution")
    if evaluation.feasible_solution_set.model_id != candidate.model_id:
        raise ValueError("P3 feasible solution set/model_id mismatch")
    if len(evaluation.feasible_solution_set.solutions) != 1:
        raise ValueError("P4-C requires exactly one P3 feasible solution per model")

    solution = evaluation.feasible_solution_set.solutions[0]
    if not isinstance(solution, FeasibleSolution):
        raise ValueError("P3 feasible solution has an invalid type")
    expected_variable = PRIMARY_VARIABLE[candidate.family]
    if solution.economic_variable != expected_variable:
        raise ValueError(
            f"P3 solution variable mismatch for {candidate.model_id}: "
            f"{solution.economic_variable} != {expected_variable}"
        )
    if solution.economic_variable == "market_implied_net_profit":
        raise ValueError("generic implied net profit is forbidden")
    if solution.value is None and (
        solution.range_low is None or solution.range_high is None
    ):
        raise ValueError("P3 complex solution must expose a point or complete range")
    return solution


def _build_assumptions(
    *,
    family: MarketModelFamily,
    current_group: Sequence[object],
    evidence_index: Mapping[str, object],
    period: str,
    horizon: str,
    accounting_basis: str,
) -> tuple[MIEAssumption, ...]:
    latest = _latest_current_by_variable(current_group)
    variables = CONDITIONAL_ASSUMPTIONS[family]
    missing = [variable for variable in variables if variable not in latest]
    if missing:
        raise ValueError(
            f"missing current {family.value} conditional assumptions: {sorted(missing)}"
        )

    assumptions: list[MIEAssumption] = []
    for variable in variables:
        item = latest[variable]
        _validate_observation_evidence(item, evidence_index)
        assumptions.append(
            MIEAssumption(
                variable=item.economic_variable,
                value=item.economic_value,
                unit=item.unit,
                basis=item.basis,
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                evidence_ids=item.evidence_ids,
            )
        )
    return tuple(assumptions)


def _qualification_rationale(
    model_id: str,
    identifiability: IdentifiabilityState,
    stability: StabilityResult,
    representation: MIERepresentation,
    assumptions: Sequence[MIEAssumption],
) -> str:
    variables = ", ".join(item.variable for item in assumptions)
    return (
        f"P4-C conditional MIE for {model_id}: identifiability={identifiability.value}, "
        f"stability={stability.state.value}, representation={representation.value}. "
        f"The primary variable is inverted only conditional on the observed current assumption "
        f"slice [{variables}]. This artifact is not a full multidimensional feasible assumption "
        f"space, and it is not asserted to be market truth."
    )


def build_dcf_ddm_conditional_market_implied_expectations(
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
    """Materialize P3-B DCF/DDM inversions as explicit conditional MIE slices.

    The inverse is not recomputed here. Each output binds the P3 primary
    solution to the current observed model-assumption slice. Because the
    representation is CONDITIONAL_IMPLIED_VARIABLE, P4-A qualification can
    never promote it to DECISION_GRADE.

    This deliberately does not construct a multidimensional feasible
    assumption region or claim any assumption tuple is the market's truth.
    """
    candidates = _validate_context(
        identification_input,
        candidate_coverage,
        evidence_sufficiency,
    )
    evaluations = _typed_complex_evaluations(identification, candidates)
    ident, stability = _typed_p3_states(identification)
    evidence_index = _evidence_index(identification_input)

    current_date, current_group = _current_observation_group(identification_input)
    anchor = next(
        item
        for item in current_group
        if item.observation_id == identification_input.current_observation_id
    )

    candidate_ids = {candidate.model_id for candidate in candidates}
    by_model = {
        evaluation.fit.model_id: evaluation
        for evaluation in evaluations
        if evaluation.fit.model_id in candidate_ids
    }

    feasible_model_ids = set(ident.feasible_model_ids)
    outputs: list[MarketImpliedExpectation] = []

    for model_id in sorted(feasible_model_ids):
        candidate = next(
            candidate for candidate in candidates if candidate.model_id == model_id
        )
        if candidate.family not in COMPLEX_CONDITIONAL_FAMILIES:
            raise ValueError("P4-C encountered a non-DCF/DDM candidate")
        evaluation = by_model.get(model_id)
        if evaluation is None:
            raise ValueError(
                f"P3 identifiability references unknown evaluation model_id: {model_id}"
            )

        solution = _solution_for_complex(evaluation, candidate)
        assumptions = _build_assumptions(
            family=candidate.family,
            current_group=current_group,
            evidence_index=evidence_index,
            period=period,
            horizon=horizon,
            accounting_basis=accounting_basis,
        )

        requirement = MIEEconomicRequirement(
            economic_variable=solution.economic_variable,
            unit=solution.unit,
            basis=solution.basis,
            period=period,
            horizon=horizon,
            accounting_basis=accounting_basis,
            role="IMPLIED_PRIMARY_CONDITIONAL_ON_ASSUMPTIONS",
            value=solution.value,
            range_low=solution.range_low if solution.value is None else None,
            range_high=solution.range_high if solution.value is None else None,
            evidence_ids=solution.evidence_ids,
        )

        evidence_ids = tuple(sorted(set(
            solution.evidence_ids
            + tuple(
                evidence_id
                for item in assumptions
                for evidence_id in item.evidence_ids
            )
            + candidate_coverage.evidence_ids
            + evidence_sufficiency.evidence_ids
        )))

        output = qualify_market_implied_expectation(
            expectation_id=f"mie-p4c-{model_id}",
            model_id=model_id,
            market_model=candidate.family,
            identifiability=ident.state,
            stability=stability.state,
            candidate_coverage=candidate_coverage,
            representation=MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE,
            economic_requirements=(requirement,),
            observation_basis=MIEObservationBasis(
                price_observation_id=anchor.observation_id,
                observation_date=current_date,
                cutoff_date=identification_input.cutoff_date,
                currency=currency,
                adjustment_semantics=adjustment_semantics,
            ),
            assumption_set=assumptions,
            evidence_sufficiency=evidence_sufficiency,
            evidence_ids=evidence_ids,
            qualification_rationale=_qualification_rationale(
                model_id,
                ident.state,
                stability,
                MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE,
                assumptions,
            ),
        )
        if output.qualification.value != "CONDITIONAL_ONLY":
            raise ValueError("P4-C conditional inverse cannot become decision-grade")
        outputs.append(output)

    if not outputs:
        raise ValueError(
            "no feasible DCF/DDM market model; P4-C cannot materialize a conditional MIE"
        )
    return tuple(outputs)
