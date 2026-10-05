from __future__ import annotations

from datetime import date
from decimal import Decimal
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
    MarketModelFamily,
    MarketObservableEvidence,
    StabilityResult,
)
from .market_model_identification import (
    CandidateEvaluation,
    MarketModelIdentificationInput,
    MarketValuationObservation,
)


COMPLEX_MIE_FAMILIES = frozenset({
    MarketModelFamily.SOTP,
    MarketModelFamily.RNPV,
})

PRIMARY_VARIABLE = {
    MarketModelFamily.SOTP: "residual_value",
    MarketModelFamily.RNPV: "pipeline_value",
}


def _validate_context(
    identification_input: MarketModelIdentificationInput,
    candidate_coverage: CandidateCoverageAssessment,
    evidence_sufficiency: EvidenceSufficiencyAssessment,
) -> tuple[CandidateMarketModel, ...]:
    identification_input.validate()

    candidates = identification_input.candidates
    candidate_ids = {candidate.model_id for candidate in candidates}
    coverage_ids = set(candidate_coverage.candidate_model_ids)
    if coverage_ids - candidate_ids:
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

    candidate_coverage.validate()
    evidence_sufficiency.validate()
    return candidates


def _typed_states(
    identification: Mapping[str, object],
) -> tuple[IdentifiabilityResult, StabilityResult]:
    ident = identification.get("identifiability")
    stability = identification.get("stability")
    if not isinstance(ident, IdentifiabilityResult):
        raise ValueError("P3 identifiability result has an invalid type")
    if not isinstance(stability, StabilityResult):
        raise ValueError("P3 stability result has an invalid type")
    return ident, stability


def _typed_evaluations(
    identification: Mapping[str, object],
    candidates: Sequence[CandidateMarketModel],
) -> tuple[CandidateEvaluation, ...]:
    if identification.get("status") != "PASS":
        raise ValueError("P4-D requires a PASS P3 identification result")
    if identification.get("method") != "model_specific_inverse_v0.3":
        raise ValueError("P4-D requires the accepted P3 model-specific inverse method")
    if any(candidate.family not in COMPLEX_MIE_FAMILIES for candidate in candidates):
        raise ValueError("P4-D accepts only SOTP and rNPV candidates")

    evaluations = identification.get("evaluations")
    if not isinstance(evaluations, tuple):
        raise ValueError("P3 evaluations must be a tuple of CandidateEvaluation")
    for evaluation in evaluations:
        if not isinstance(evaluation, CandidateEvaluation):
            raise ValueError("P3 evaluations contain an invalid type")
    return evaluations


def _evidence_index(
    identification_input: MarketModelIdentificationInput,
) -> dict[str, MarketObservableEvidence]:
    indexed = {item.evidence_id: item for item in identification_input.evidence}
    if len(indexed) != len(identification_input.evidence):
        raise ValueError("duplicate evidence_id")
    return indexed


def _current_group(
    identification_input: MarketModelIdentificationInput,
) -> tuple[date, tuple[MarketValuationObservation, ...]]:
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
    return anchor.observation_date, group


def _evidence_matches(
    item: MarketValuationObservation,
    evidence_index: Mapping[str, MarketObservableEvidence],
) -> None:
    for evidence_id in item.evidence_ids:
        evidence = evidence_index.get(evidence_id)
        if evidence is None:
            raise ValueError(f"observation references unknown evidence_id: {evidence_id}")
        if evidence.variable != item.economic_variable:
            raise ValueError(
                f"observation evidence variable mismatch: {evidence_id}"
            )
        if evidence.unit != item.unit:
            raise ValueError(
                f"observation evidence unit mismatch: {evidence_id}"
            )


def _solution(
    evaluation: CandidateEvaluation,
    candidate: CandidateMarketModel,
) -> FeasibleSolution:
    if evaluation.fit.model_id != candidate.model_id:
        raise ValueError("P3 evaluation/model_id mismatch")
    if evaluation.fit.status.value != "FEASIBLE" or evaluation.feasible_solution_set is None:
        raise ValueError("P4-D requires a feasible P3 SOTP/rNPV solution")
    if evaluation.feasible_solution_set.model_id != candidate.model_id:
        raise ValueError("P3 feasible solution set/model_id mismatch")
    if len(evaluation.feasible_solution_set.solutions) != 1:
        raise ValueError("P4-D requires exactly one P3 feasible solution per model")

    solution = evaluation.feasible_solution_set.solutions[0]
    solution.validate()

    expected = PRIMARY_VARIABLE[candidate.family]
    if solution.economic_variable != expected:
        raise ValueError(
            f"P3 solution variable mismatch for {candidate.model_id}: "
            f"{solution.economic_variable} != {expected}"
        )
    if solution.economic_variable == "market_implied_net_profit":
        raise ValueError("generic implied net profit is forbidden")
    return solution


def _segment_id(basis: str) -> str:
    if not basis.startswith("segment:") or len(basis) == len("segment:"):
        raise ValueError("SOTP segment basis must use segment:<id>")
    return basis.split(":", 1)[1]


def _pipeline_id(basis: str) -> str:
    if not basis.startswith("pipeline:") or len(basis) == len("pipeline:"):
        raise ValueError("rNPV pipeline basis must use pipeline:<id>")
    return basis.split(":", 1)[1]


def _latest_by_key(
    items: Sequence[MarketValuationObservation],
    key_fn,
) -> dict[str, MarketValuationObservation]:
    latest: dict[str, MarketValuationObservation] = {}
    for item in items:
        key = key_fn(item)
        existing = latest.get(key)
        if existing is None or (item.known_at, item.observation_id) > (
            existing.known_at,
            existing.observation_id,
        ):
            latest[key] = item
    return latest


def _sotp_assumptions(
    current_group: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    period: str,
    horizon: str,
    accounting_basis: str,
) -> tuple[MIEAssumption, ...]:
    segments = [item for item in current_group if item.economic_variable == "segment_value"]
    if not segments:
        raise ValueError("P4-D requires current SOTP segment_value observations")

    latest = _latest_by_key(segments, lambda item: _segment_id(item.basis))
    if len(latest) != len(segments):
        raise ValueError("duplicate current SOTP segment id")
    units = {item.unit for item in latest.values()}
    if len(units) != 1:
        raise ValueError("current SOTP segment units must match")

    assumptions: list[MIEAssumption] = []
    for segment_id in sorted(latest):
        item = latest[segment_id]
        _evidence_matches(item, evidence_index)
        assumptions.append(
            MIEAssumption(
                variable="segment_value",
                value=item.economic_value,
                unit=item.unit,
                basis=f"segment:{segment_id}",
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                evidence_ids=item.evidence_ids,
            )
        )
    return tuple(assumptions)


def _rnpv_context(
    current_group: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    period: str,
    horizon: str,
    accounting_basis: str,
) -> tuple[tuple[MIEAssumption, ...], dict[str, MarketValuationObservation]]:
    values = [item for item in current_group if item.economic_variable == "pipeline_value"]
    probabilities = [item for item in current_group if item.economic_variable == "probability"]
    timings = [item for item in current_group if item.economic_variable == "timing"]

    if not values or not probabilities or not timings:
        raise ValueError("P4-D requires current rNPV pipeline_value, probability and timing")
    value_by_id = _latest_by_key(values, lambda item: _pipeline_id(item.basis))
    probability_by_id = _latest_by_key(probabilities, lambda item: _pipeline_id(item.basis))
    timing_by_id = _latest_by_key(timings, lambda item: _pipeline_id(item.basis))
    pipeline_ids = set(value_by_id)
    if pipeline_ids != set(probability_by_id) or pipeline_ids != set(timing_by_id):
        raise ValueError("rNPV current pipeline IDs must align")
    if len(pipeline_ids) < 1:
        raise ValueError("rNPV requires at least one pipeline")

    assumptions: list[MIEAssumption] = []
    for pipeline_id in sorted(pipeline_ids):
        value_item = value_by_id[pipeline_id]
        probability_item = probability_by_id[pipeline_id]
        timing_item = timing_by_id[pipeline_id]
        for item in (value_item, probability_item, timing_item):
            _evidence_matches(item, evidence_index)
        assumptions.extend((
            MIEAssumption(
                variable="pipeline_value",
                value=value_item.economic_value,
                unit=value_item.unit,
                basis=f"pipeline:{pipeline_id}:observed_composition_anchor",
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                evidence_ids=value_item.evidence_ids,
            ),
            MIEAssumption(
                variable="probability",
                value=probability_item.economic_value,
                unit=probability_item.unit,
                basis=f"pipeline:{pipeline_id}:observed_probability_condition",
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                evidence_ids=probability_item.evidence_ids,
            ),
            MIEAssumption(
                variable="timing",
                value=timing_item.economic_value,
                unit=timing_item.unit,
                basis=f"pipeline:{pipeline_id}:observed_timing_condition",
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                evidence_ids=timing_item.evidence_ids,
            ),
        ))
    
    global_latest = {}
    for variable in ("discount_rate", "base_value"):
        matches = [item for item in current_group if item.economic_variable == variable]
        if not matches:
            raise ValueError(f"missing current rNPV {variable}")
        latest = max(matches, key=lambda item: (item.known_at, item.observation_id))
        _evidence_matches(latest, evidence_index)
        global_latest[variable] = latest
        assumptions.append(
            MIEAssumption(
                variable=variable,
                value=latest.economic_value,
                unit=latest.unit,
                basis="rnpv:global_condition",
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                evidence_ids=latest.evidence_ids,
            )
        )
    return tuple(assumptions), value_by_id | {f"__{k}": v for k, v in global_latest.items()}


def _pipeline_requirements(
    solution: FeasibleSolution,
    current_values: Mapping[str, MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    period: str,
    horizon: str,
    accounting_basis: str,
) -> tuple[MIEEconomicRequirement, ...]:
    pipeline_values = {k: v for k, v in current_values.items() if not k.startswith("__")}
    if not pipeline_values:
        raise ValueError("rNPV requires at least one current pipeline")
    observed_total = sum(item.economic_value for item in pipeline_values.values())
    if observed_total <= 0:
        raise ValueError("rNPV observed pipeline composition total must be > 0")
    if solution.value is None:
        raise ValueError("P4-D requires point-valued P3 rNPV primary solution")
    implied_total = solution.value
    if implied_total < 0:
        raise ValueError("P4-D implied rNPV pipeline value cannot be negative")

    requirements: list[MIEEconomicRequirement] = []
    for pipeline_id in sorted(pipeline_values):
        item = pipeline_values[pipeline_id]
        _evidence_matches(item, evidence_index)
        implied_value = implied_total * item.economic_value / observed_total
        requirements.append(
            MIEEconomicRequirement(
                economic_variable="pipeline_value",
                unit=item.unit,
                basis=f"pipeline:{pipeline_id}:pro_rata_observed_composition",
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                role="IMPLIED_PIPELINE_CONDITIONAL_ON_OBSERVED_COMPOSITION",
                value=implied_value,
                evidence_ids=tuple(sorted(set(solution.evidence_ids + item.evidence_ids))),
            )
        )
    return tuple(requirements)


def _qualification_rationale(
    model_id: str,
    family: MarketModelFamily,
    assumptions: Sequence[MIEAssumption],
    identifiability: str,
    stability: str,
) -> str:
    if family == MarketModelFamily.SOTP:
        conditioning = "observed current segment values"
    else:
        conditioning = "observed pipeline composition, probability, timing, discount rate and base value"
    return (
        f"P4-D conditional MIE for {model_id}: identifiability={identifiability}, "
        f"stability={stability}. The market-required {PRIMARY_VARIABLE[family].replace('_', ' ')} "
        f"is represented only conditional on {conditioning}. "
        f"The conditioning values are not asserted to be market-implied beliefs, "
        f"and the output is not a full feasible assumption space or market truth."
    )


def build_sotp_rnpv_market_implied_expectations(
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
    candidates = _validate_context(
        identification_input,
        candidate_coverage,
        evidence_sufficiency,
    )
    evaluations = _typed_evaluations(identification, candidates)
    identifiability, stability = _typed_states(identification)
    evidence_index = _evidence_index(identification_input)
    current_date, current_group = _current_group(identification_input)
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

    outputs: list[MarketImpliedExpectation] = []
    for model_id in sorted(set(identifiability.feasible_model_ids)):
        candidate = next(
            candidate for candidate in candidates if candidate.model_id == model_id
        )
        if candidate.family not in COMPLEX_MIE_FAMILIES:
            raise ValueError("P4-D encountered a non-SOTP/rNPV candidate")
        evaluation = by_model.get(model_id)
        if evaluation is None:
            raise ValueError(
                f"P3 identifiability references unknown evaluation model_id: {model_id}"
            )
        solution = _solution(evaluation, candidate)

        if candidate.family == MarketModelFamily.SOTP:
            assumptions = _sotp_assumptions(
                current_group, evidence_index, period, horizon, accounting_basis
            )
            requirement = MIEEconomicRequirement(
                economic_variable="residual_value",
                unit=solution.unit,
                basis=solution.basis,
                period=period,
                horizon=horizon,
                accounting_basis=accounting_basis,
                role="IMPLIED_RESIDUAL_CONDITIONAL_ON_SEGMENTS",
                value=solution.value,
                range_low=solution.range_low if solution.value is None else None,
                range_high=solution.range_high if solution.value is None else None,
                evidence_ids=solution.evidence_ids,
            )
            requirements = (requirement,)
        else:
            assumptions, current_values = _rnpv_context(
                current_group, evidence_index, period, horizon, accounting_basis
            )
            requirements = _pipeline_requirements(
                solution, current_values, evidence_index, period, horizon, accounting_basis
            )

        evidence_ids = tuple(sorted(set(
            solution.evidence_ids
            + tuple(
                evidence_id
                for item in assumptions
                for evidence_id in item.evidence_ids
            )
            + tuple(
                evidence_id
                for item in requirements
                for evidence_id in item.evidence_ids
            )
            + candidate_coverage.evidence_ids
            + evidence_sufficiency.evidence_ids
        )))

        output = qualify_market_implied_expectation(
            expectation_id=f"mie-p4d-{model_id}",
            model_id=model_id,
            market_model=candidate.family,
            identifiability=identifiability.state,
            stability=stability.state,
            candidate_coverage=candidate_coverage,
            representation=MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE,
            economic_requirements=requirements,
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
                candidate.family,
                assumptions,
                identifiability.state.value,
                stability.state.value,
            ),
        )
        if output.qualification.value not in {"CONDITIONAL_ONLY", "BLOCKED"}:
            raise ValueError("P4-D SOTP/rNPV conditional inverse cannot become decision-grade")
        outputs.append(output)

    if not outputs:
        raise ValueError(
            "no feasible SOTP/rNPV market model; P4-D cannot materialize a conditional MIE"
        )
    return tuple(outputs)
