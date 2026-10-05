from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEQualification,
    MIERepresentation,
)
from iios_mvp.market_model_domain import (
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
from iios_mvp.market_model_identification import (
    CandidateEvaluation,
    MarketModelIdentificationInput,
    MarketValuationObservation,
)
from iios_mvp.market_model_identification import identify_market_models
from iios_mvp.sotp_rnpv_market_implied_expectation import (
    build_sotp_rnpv_market_implied_expectations,
)


CUTOFF = date(2026, 10, 4)
KNOWN = datetime(2026, 10, 4, 2, tzinfo=timezone.utc)


def evidence(eid: str, variable: str, unit: str) -> MarketObservableEvidence:
    return MarketObservableEvidence(
        evidence_id=eid,
        variable=variable,
        unit=unit,
        basis="p4d-fixture",
        observation_date=CUTOFF,
        known_at=KNOWN,
        source="test-fixture",
        value=Decimal("1"),
    )


def obs(
    oid: str,
    day: int | None,
    price: str,
    variable: str,
    value: str,
    basis: str,
    unit: str = "CNY",
    evidence_id: str = "e",
) -> MarketValuationObservation:
    obs_date = CUTOFF if day is None else date(2026, 9, day)
    known_at = KNOWN if day is None else datetime(2026, 9, day, 2, tzinfo=timezone.utc)
    return MarketValuationObservation(
        observation_id=oid,
        observation_date=obs_date,
        known_at=known_at,
        price=Decimal(price),
        shares_outstanding=Decimal("1"),
        economic_variable=variable,
        economic_value=Decimal(value),
        unit=unit,
        basis=basis,
        evidence_ids=(evidence_id,),
        source="test-fixture",
        net_debt=Decimal("0"),
    )


def candidate(model_id: str, family: MarketModelFamily, variables: tuple[str, ...], evidence_id: str):
    return CandidateMarketModel(
        model_id=model_id,
        family=family,
        required_economic_variables=variables,
        required_observable_variables=variables,
        evidence_ids=(evidence_id,),
        admission_basis="P4-D typed fixture",
        inverse_solvable=True,
    )


def coverage(inp):
    return CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis="P4-D admitted set",
        candidate_model_ids=tuple(c.model_id for c in inp.candidates),
        evidence_ids=tuple(c.evidence_ids[0] for c in inp.candidates),
        rationale="All admitted SOTP/rNPV candidates enumerated.",
    )


def evidence_sufficient(inp, status=EvidenceSufficiencyState.SUFFICIENT):
    return EvidenceSufficiencyAssessment(
        status=status,
        rationale="Fixture evidence captured.",
        evidence_ids=tuple(item.evidence_id for item in inp.evidence),
    )


def sotp_input(candidate_item=None, price="110"):
    c = candidate_item or candidate(
        "sotp-1",
        MarketModelFamily.SOTP,
        ("segment_value", "residual_value"),
        "candidate-sotp",
    )
    rows, ev = [], []
    for day in (1, 8, 15, 22):
        rows += [
            obs(f"h{day}-a", day, price, "segment_value", "60", "segment:A", evidence_id=f"e-a-{day}"),
            obs(f"h{day}-b", day, price, "segment_value", "40", "segment:B", evidence_id=f"e-b-{day}"),
        ]
        ev += [
            evidence(f"e-a-{day}", "segment_value", "CNY"),
            evidence(f"e-b-{day}", "segment_value", "CNY"),
        ]
    rows += [
        obs("current-a", None, price, "segment_value", "60", "segment:A", evidence_id="e-a-current"),
        obs("current-b", None, price, "segment_value", "40", "segment:B", evidence_id="e-b-current"),
    ]
    ev += [
        evidence("e-a-current", "segment_value", "CNY"),
        evidence("e-b-current", "segment_value", "CNY"),
        evidence("candidate-sotp", "sotp_candidate", "identifier"),
    ]
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current-a",
        candidates=(c,),
        observations=tuple(rows),
        evidence=tuple(ev),
    )


def rnpv_input(candidate_item=None, price="92.7272727272727272727272727273"):
    c = candidate_item or candidate(
        "rnpv-1",
        MarketModelFamily.RNPV,
        ("pipeline_value", "probability", "timing", "discount_rate", "base_value"),
        "candidate-rnpv",
    )
    rows, ev = [], []
    for day in (1, 8, 15, 22):
        rows += [
            obs(f"h{day}-p1-v", day, price, "pipeline_value", "60", "pipeline:P1", evidence_id=f"e-p1-v-{day}"),
            obs(f"h{day}-p1-p", day, price, "probability", "0.80", "pipeline:P1", "ratio", f"e-p1-p-{day}"),
            obs(f"h{day}-p1-t", day, price, "timing", "1", "pipeline:P1", "years", f"e-p1-t-{day}"),
            obs(f"h{day}-p2-v", day, price, "pipeline_value", "40", "pipeline:P2", evidence_id=f"e-p2-v-{day}"),
            obs(f"h{day}-p2-p", day, price, "probability", "0.50", "pipeline:P2", "ratio", f"e-p2-p-{day}"),
            obs(f"h{day}-p2-t", day, price, "timing", "2", "pipeline:P2", "years", f"e-p2-t-{day}"),
            obs(f"h{day}-discount", day, price, "discount_rate", "0.10", "assumption", "ratio", f"e-disc-{day}"),
            obs(f"h{day}-base", day, price, "base_value", "20", "base", "CNY", f"e-base-{day}"),
        ]
        ev += [
            evidence(f"e-p1-v-{day}", "pipeline_value", "CNY"),
            evidence(f"e-p1-p-{day}", "probability", "ratio"),
            evidence(f"e-p1-t-{day}", "timing", "years"),
            evidence(f"e-p2-v-{day}", "pipeline_value", "CNY"),
            evidence(f"e-p2-p-{day}", "probability", "ratio"),
            evidence(f"e-p2-t-{day}", "timing", "years"),
            evidence(f"e-disc-{day}", "discount_rate", "ratio"),
            evidence(f"e-base-{day}", "base_value", "CNY"),
        ]
    rows += [
        obs("current-p1-v", None, price, "pipeline_value", "60", "pipeline:P1", evidence_id="e-p1-v-current"),
        obs("current-p1-p", None, price, "probability", "0.80", "pipeline:P1", "ratio", "e-p1-p-current"),
        obs("current-p1-t", None, price, "timing", "1", "pipeline:P1", "years", "e-p1-t-current"),
        obs("current-p2-v", None, price, "pipeline_value", "40", "pipeline:P2", evidence_id="e-p2-v-current"),
        obs("current-p2-p", None, price, "probability", "0.50", "pipeline:P2", "ratio", "e-p2-p-current"),
        obs("current-p2-t", None, price, "timing", "2", "pipeline:P2", "years", "e-p2-t-current"),
        obs("current-discount", None, price, "discount_rate", "0.10", "assumption", "ratio", "e-disc-current"),
        obs("current-base", None, price, "base_value", "20", "base", "CNY", "e-base-current"),
    ]
    ev += [
        evidence("e-p1-v-current", "pipeline_value", "CNY"),
        evidence("e-p1-p-current", "probability", "ratio"),
        evidence("e-p1-t-current", "timing", "years"),
        evidence("e-p2-v-current", "pipeline_value", "CNY"),
        evidence("e-p2-p-current", "probability", "ratio"),
        evidence("e-p2-t-current", "timing", "years"),
        evidence("e-disc-current", "discount_rate", "ratio"),
        evidence("e-base-current", "base_value", "CNY"),
        evidence("candidate-rnpv", "rnpv_candidate", "identifier"),
    ]
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current-p1-v",
        candidates=(c,),
        observations=tuple(rows),
        evidence=tuple(ev),
    )


def run(inp, **kwargs):
    p3 = identify_market_models(inp)
    return build_sotp_rnpv_market_implied_expectations(
        identification_input=inp,
        identification=p3,
        candidate_coverage=kwargs.pop("candidate_coverage", coverage(inp)),
        evidence_sufficiency=kwargs.pop("evidence_sufficiency", evidence_sufficient(inp)),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
        period="NTM",
        horizon="12M",
        accounting_basis="reported",
    )


def test_sotp_materializes_conditional_residual_and_segments():
    inp = sotp_input()
    p3 = identify_market_models(inp)
    solution = p3["evaluations"][0].feasible_solution_set.solutions[0]
    mie = run(inp)[0]
    assert mie.qualification == MIEQualification.CONDITIONAL_ONLY
    assert mie.representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE
    assert mie.economic_requirements[0].economic_variable == "residual_value"
    assert mie.economic_requirements[0].value == solution.value
    assert {item.basis for item in mie.assumption_set} == {"segment:A", "segment:B"}
    assert not any(item.variable == "residual_value" for item in mie.assumption_set)


def test_rnpv_preserves_pipeline_specific_requirements_and_conditions():
    inp = rnpv_input()
    p3 = identify_market_models(inp)
    solution = p3["evaluations"][0].feasible_solution_set.solutions[0]
    mie = run(inp)[0]
    assert mie.qualification == MIEQualification.CONDITIONAL_ONLY
    assert len(mie.economic_requirements) == 2
    assert {item.basis for item in mie.economic_requirements} == {
        "pipeline:P1:pro_rata_observed_composition",
        "pipeline:P2:pro_rata_observed_composition",
    }
    assert sum(item.value for item in mie.economic_requirements) == solution.value
    assert {item.basis for item in mie.assumption_set if item.variable == "probability"} == {
        "pipeline:P1:observed_probability_condition",
        "pipeline:P2:observed_probability_condition",
    }
    assert {item.basis for item in mie.assumption_set if item.variable == "timing"} == {
        "pipeline:P1:observed_timing_condition",
        "pipeline:P2:observed_timing_condition",
    }


def test_rnpv_does_not_create_a_market_implied_probability():
    mie = run(rnpv_input())[0]
    assert not any(
        item.economic_variable == "probability"
        for item in mie.economic_requirements
    )


def test_sotp_does_not_create_market_truth_from_segment_values():
    mie = run(sotp_input())[0]
    assert mie.qualification_rationale.find("not asserted to be market-implied") >= 0
    assert mie.representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE


def test_ambiguous_typed_p3_emits_one_conditional_slice_per_feasible_candidate():
    inp = sotp_input()
    rnpv = rnpv_input()
    combined = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current-a",
        candidates=(inp.candidates[0], rnpv.candidates[0]),
        observations=inp.observations + rnpv.observations,
        evidence=inp.evidence + rnpv.evidence,
    )
    evaluations = (
        CandidateEvaluation(
            fit=ModelFit(
                model_id="sotp-1",
                status=ModelFitStatus.FEASIBLE,
                diagnostics=(FitDiagnostic("fit-sotp", "typed", "PASS"),),
                evidence_ids=("e-a-current",),
                constraints=("typed-fixture",),
            ),
            feasible_solution_set=FeasibleSolutionSet(
                model_id="sotp-1",
                status=FeasibleSolutionStatus.NONEMPTY,
                solutions=(
                    FeasibleSolution(
                        economic_variable="residual_value",
                        unit="CNY",
                        basis="typed-p3-sotp",
                        model_id="sotp-1",
                        value=Decimal("10"),
                        evidence_ids=("e-a-current",),
                    ),
                ),
                constraint_ids=("typed-fixture",),
                evidence_ids=("e-a-current",),
                basis="typed-p3-fixture",
            ),
        ),
        CandidateEvaluation(
            fit=ModelFit(
                model_id="rnpv-1",
                status=ModelFitStatus.FEASIBLE,
                diagnostics=(FitDiagnostic("fit-rnpv", "typed", "PASS"),),
                evidence_ids=("e-p1-v-current",),
                constraints=("typed-fixture",),
            ),
            feasible_solution_set=FeasibleSolutionSet(
                model_id="rnpv-1",
                status=FeasibleSolutionStatus.NONEMPTY,
                solutions=(
                    FeasibleSolution(
                        economic_variable="pipeline_value",
                        unit="CNY",
                        basis="typed-p3-rnpv",
                        model_id="rnpv-1",
                        value=Decimal("100"),
                        evidence_ids=("e-p1-v-current",),
                    ),
                ),
                constraint_ids=("typed-fixture",),
                evidence_ids=("e-p1-v-current",),
                basis="typed-p3-fixture",
            ),
        ),
    )
    identification = {
        "status": "PASS",
        "method": "model_specific_inverse_v0.3",
        "evaluations": evaluations,
        "identifiability": IdentifiabilityResult(
            state=IdentifiabilityState.AMBIGUOUS,
            feasible_model_ids=("rnpv-1", "sotp-1"),
            selected_model_id=None,
            competing_model_ids=("rnpv-1", "sotp-1"),
            evidence_ids=("e-a-current", "e-p1-v-current"),
            rationale="Typed ambiguity fixture.",
        ),
        "stability": StabilityResult(
            state=StabilityState.STABLE,
            assessment_method="typed-fixture",
            observations=(
                StabilityObservation(
                    perturbation_id="p4d-amb-1",
                    perturbation="complete historical date",
                    resulting_state=StabilityState.STABLE,
                    selected_model_id=None,
                ),
            ),
            evidence_ids=("e-a-current", "e-p1-v-current"),
            rationale="Stable ambiguity fixture.",
        ),
    }
    outputs = build_sotp_rnpv_market_implied_expectations(
        identification_input=combined,
        identification=identification,
        candidate_coverage=coverage(combined),
        evidence_sufficiency=evidence_sufficient(combined),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
        period="NTM",
        horizon="12M",
        accounting_basis="reported",
    )
    assert {output.model_id for output in outputs} == {"rnpv-1", "sotp-1"}
    assert all(output.qualification == MIEQualification.CONDITIONAL_ONLY for output in outputs)


def test_unstable_upstream_yields_blocked_output():
    inp = sotp_input()
    p3 = identify_market_models(inp)
    identification = dict(p3)
    identification["identifiability"] = IdentifiabilityResult(
        state=IdentifiabilityState.IDENTIFIABLE,
        feasible_model_ids=p3["identifiability"].feasible_model_ids,
        selected_model_id=p3["identifiability"].selected_model_id,
        competing_model_ids=(),
        evidence_ids=p3["identifiability"].evidence_ids,
        rationale=p3["identifiability"].rationale,
    )
    identification["stability"] = StabilityResult(
        state=StabilityState.UNSTABLE,
        assessment_method="typed-red-team",
        observations=(
            StabilityObservation(
                perturbation_id="unstable",
                perturbation="historical date regime shift",
                resulting_state=StabilityState.UNSTABLE,
                selected_model_id=None,
            ),
        ),
        evidence_ids=p3["stability"].evidence_ids,
        rationale="unstable red-team",
    )
    assert run(inp)  # baseline still works
    blocked = build_sotp_rnpv_market_implied_expectations(
        identification_input=inp,
        identification=identification,
        candidate_coverage=coverage(inp),
        evidence_sufficiency=evidence_sufficient(inp),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
        period="NTM",
        horizon="12M",
        accounting_basis="reported",
    )[0]
    assert blocked.qualification == MIEQualification.BLOCKED


def test_insufficient_coverage_blocks():
    inp = sotp_input()
    bad = CandidateCoverageAssessment(
        status=CandidateCoverageState.INSUFFICIENT,
        scope_basis="partial",
        candidate_model_ids=("sotp-1",),
        evidence_ids=("candidate-sotp",),
        rationale="partial coverage",
    )
    assert run(inp, candidate_coverage=bad)[0].qualification == MIEQualification.BLOCKED


def test_insufficient_evidence_blocks():
    inp = sotp_input()
    assert run(
        inp,
        evidence_sufficiency=evidence_sufficient(
            inp, EvidenceSufficiencyState.INSUFFICIENT
        ),
    )[0].qualification == MIEQualification.BLOCKED


def test_wrong_solution_variable_rejected():
    inp = sotp_input()
    p3 = identify_market_models(inp)
    evaluation = p3["evaluations"][0]
    original = evaluation.feasible_solution_set
    bad_solution = FeasibleSolution(
        economic_variable="pipeline_value",
        unit=original.solutions[0].unit,
        basis=original.solutions[0].basis,
        model_id=original.solutions[0].model_id,
        value=original.solutions[0].value,
        evidence_ids=original.solutions[0].evidence_ids,
    )
    bad_evaluation = CandidateEvaluation(
        fit=evaluation.fit,
        feasible_solution_set=FeasibleSolutionSet(
            model_id=original.model_id,
            status=FeasibleSolutionStatus.NONEMPTY,
            solutions=(bad_solution,),
            constraint_ids=original.constraint_ids,
            evidence_ids=original.evidence_ids,
            basis=original.basis,
        ),
    )
    with pytest.raises(ValueError, match="solution variable mismatch"):
        build_sotp_rnpv_market_implied_expectations(
            identification_input=inp,
            identification=dict(p3, evaluations=(bad_evaluation,)),
            candidate_coverage=coverage(inp),
            evidence_sufficiency=evidence_sufficient(inp),
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
            period="NTM",
            horizon="12M",
            accounting_basis="reported",
        )


def test_rnpv_pipeline_id_mismatch_is_rejected():
    inp = rnpv_input()
    rows = list(inp.observations)
    target = next(i for i, item in enumerate(rows) if item.observation_id == "current-p2-p")
    rows[target] = obs(
        "current-p2-p",
        None,
        "92.7272727272727272727272727273",
        "probability",
        "0.50",
        "pipeline:P3",
        "ratio",
        "e-p2-p-current",
    )
    broken = MarketModelIdentificationInput(
        cutoff_date=inp.cutoff_date,
        current_observation_id=inp.current_observation_id,
        candidates=inp.candidates,
        observations=tuple(rows),
        evidence=inp.evidence,
    )
    with pytest.raises(ValueError, match="no feasible SOTP/rNPV market model"):
        run(broken)


def test_missing_rnpv_probability_or_timing_is_fail_closed():
    inp = rnpv_input()
    rows = tuple(
        item
        for item in inp.observations
        if item.observation_id not in {"current-p2-p", "current-p2-t"}
    )
    broken = MarketModelIdentificationInput(
        cutoff_date=inp.cutoff_date,
        current_observation_id=inp.current_observation_id,
        candidates=inp.candidates,
        observations=rows,
        evidence=inp.evidence,
    )
    with pytest.raises(ValueError):
        run(broken)


def test_unknown_provenance_is_rejected():
    inp = sotp_input()
    rows = list(inp.observations)
    target = next(i for i, item in enumerate(rows) if item.observation_id == "current-a")
    rows[target] = obs(
        "current-a",
        None,
        "110",
        "segment_value",
        "60",
        "segment:A",
        evidence_id="missing-evidence",
    )
    broken = MarketModelIdentificationInput(
        cutoff_date=inp.cutoff_date,
        current_observation_id=inp.current_observation_id,
        candidates=inp.candidates,
        observations=tuple(rows),
        evidence=inp.evidence,
    )
    valid_p3 = identify_market_models(sotp_input())
    with pytest.raises(ValueError, match="unknown evidence_id"):
        build_sotp_rnpv_market_implied_expectations(
            identification_input=broken,
            identification=valid_p3,
            candidate_coverage=coverage(broken),
            evidence_sufficiency=evidence_sufficient(broken),
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
            period="NTM",
            horizon="12M",
            accounting_basis="reported",
        )


def test_no_generic_implied_profit():
    mie = run(sotp_input())[0]
    assert all(
        req.economic_variable != "market_implied_net_profit"
        for req in mie.economic_requirements
    )
