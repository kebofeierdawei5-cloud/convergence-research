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
    IdentifiabilityResult,
    StabilityObservation,
    StabilityResult,
    IdentifiabilityState,
    StabilityState,
    MarketModelFamily,
    MarketObservableEvidence,
)
from iios_mvp.market_model_identification import (
    CandidateEvaluation,
    MarketModelIdentificationInput,
    MarketValuationObservation,
    identify_market_models,
)
from iios_mvp.dcf_ddm_conditional_market_implied_expectation import (
    build_dcf_ddm_conditional_market_implied_expectations,
)


CUTOFF = date(2026, 10, 4)
KNOWN = datetime(2026, 10, 4, 2, tzinfo=timezone.utc)


def complex_evidence(eid: str, variable: str, unit: str) -> MarketObservableEvidence:
    return MarketObservableEvidence(
        evidence_id=eid,
        variable=variable,
        unit=unit,
        basis="p4c-fixture",
        observation_date=CUTOFF,
        known_at=KNOWN,
        source="test-fixture",
        value=Decimal("1"),
    )


def candidate(
    model_id: str,
    family: MarketModelFamily,
    variables: tuple[str, ...],
    evidence_id: str,
) -> CandidateMarketModel:
    return CandidateMarketModel(
        model_id=model_id,
        family=family,
        required_economic_variables=variables,
        required_observable_variables=variables,
        evidence_ids=(evidence_id,),
        admission_basis="P4-C typed fixture",
        inverse_solvable=True,
    )


def cobs(
    oid: str,
    day: int | None,
    price: str,
    variable: str,
    value: str,
    basis: str,
    unit: str,
    evidence_id: str,
    shares: str = "1",
    net_debt: str = "0",
) -> MarketValuationObservation:
    obs_date = CUTOFF if day is None else date(2026, 9, day)
    known_at = KNOWN if day is None else datetime(2026, 9, day, 2, tzinfo=timezone.utc)
    return MarketValuationObservation(
        observation_id=oid,
        observation_date=obs_date,
        known_at=known_at,
        price=Decimal(price),
        shares_outstanding=Decimal(shares),
        economic_variable=variable,
        economic_value=Decimal(value),
        unit=unit,
        basis=basis,
        evidence_ids=(evidence_id,),
        source="test-fixture",
        net_debt=Decimal(net_debt),
    )


def coverage(inp: MarketModelIdentificationInput) -> CandidateCoverageAssessment:
    return CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis="P4-C admitted DCF/DDM set",
        candidate_model_ids=tuple(candidate.model_id for candidate in inp.candidates),
        evidence_ids=tuple(candidate.evidence_ids[0] for candidate in inp.candidates),
        rationale="All admitted DCF/DDM candidates are explicitly enumerated.",
    )


def evidence_sufficient(
    inp: MarketModelIdentificationInput,
    status: EvidenceSufficiencyState = EvidenceSufficiencyState.SUFFICIENT,
) -> EvidenceSufficiencyAssessment:
    return EvidenceSufficiencyAssessment(
        status=status,
        rationale="Fixture evidence is explicitly captured.",
        evidence_ids=tuple(item.evidence_id for item in inp.evidence),
    )


def dcf_candidate(model_id: str = "dcf-1") -> CandidateMarketModel:
    return candidate(
        model_id,
        MarketModelFamily.DCF,
        ("fcf", "growth", "margin", "reinvestment", "terminal_value", "discount_rate"),
        f"candidate-{model_id}",
    )


def ddm_candidate(model_id: str = "ddm-1") -> CandidateMarketModel:
    return candidate(
        model_id,
        MarketModelFamily.DDM,
        ("dividend", "payout", "growth", "discount_rate"),
        f"candidate-{model_id}",
    )


def dcf_input(
    candidate_item: CandidateMarketModel | None = None,
    *,
    current_price: str = "2100",
    fcf_value: str = "100",
) -> MarketModelIdentificationInput:
    c = candidate_item or dcf_candidate()
    rows: list[MarketValuationObservation] = []
    evidence: list[MarketObservableEvidence] = []
    variables = (
        ("fcf", fcf_value, "CNY", "fcff"),
        ("growth", "0.05", "ratio", "assumption"),
        ("margin", "0.40", "ratio", "assumption"),
        ("reinvestment", "0.25", "ratio", "assumption"),
        ("terminal_value", "2100", "CNY", "terminal"),
        ("discount_rate", "0.10", "ratio", "assumption"),
    )
    for day, price in zip((1, 8, 15, 22), ("2100", "2100", "2100", "2100")):
        for variable, value, unit, basis in variables:
            eid = f"e-{variable}-h{day}"
            rows.append(cobs(f"h{day}-{variable}", day, price, variable, value, basis, unit, eid))
            evidence.append(complex_evidence(eid, variable, unit))
    for variable, value, unit, basis in variables:
        eid = f"e-{variable}-current"
        rows.append(cobs(f"current-{variable}", None, current_price, variable, value, basis, unit, eid))
        evidence.append(complex_evidence(eid, variable, unit))
    evidence.append(complex_evidence(c.evidence_ids[0], "dcf_candidate", "identifier"))
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current-fcf",
        candidates=(c,),
        observations=tuple(rows),
        evidence=tuple(evidence),
    )


def ddm_input(
    candidate_item: CandidateMarketModel | None = None,
    *,
    current_price: str = "105",
    id_prefix: str = "",
) -> MarketModelIdentificationInput:
    c = candidate_item or ddm_candidate()
    rows: list[MarketValuationObservation] = []
    evidence: list[MarketObservableEvidence] = []
    variables = (
        ("dividend", "5", "CNY/share", "assumption"),
        ("payout", "0.40", "ratio", "assumption"),
        ("growth", "0.05", "ratio", "assumption"),
        ("discount_rate", "0.10", "ratio", "assumption"),
    )
    for day in (1, 8, 15, 22):
        for variable, value, unit, basis in variables:
            eid = f"{id_prefix}e-{variable}-h{day}"
            rows.append(cobs(f"{id_prefix}h{day}-{variable}", day, "105", variable, value, basis, unit, eid))
            evidence.append(complex_evidence(eid, variable, unit))
    for variable, value, unit, basis in variables:
        eid = f"{id_prefix}e-{variable}-current"
        rows.append(cobs(f"{id_prefix}current-{variable}", None, current_price, variable, value, basis, unit, eid))
        evidence.append(complex_evidence(eid, variable, unit))
    evidence.append(complex_evidence(c.evidence_ids[0], "ddm_candidate", "identifier"))
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current-dividend",
        candidates=(c,),
        observations=tuple(rows),
        evidence=tuple(evidence),
    )


def run(inp: MarketModelIdentificationInput, **kwargs):
    p3 = identify_market_models(inp)
    return build_dcf_ddm_conditional_market_implied_expectations(
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


def test_dcf_materializes_conditional_primary_and_explicit_assumptions():
    inp = dcf_input()
    p3 = identify_market_models(inp)
    solution = p3["evaluations"][0].feasible_solution_set.solutions[0]
    mie = run(inp)[0]
    assert mie.qualification == MIEQualification.CONDITIONAL_ONLY
    assert mie.representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE
    assert mie.economic_requirements[0].economic_variable == "fcf"
    assert mie.economic_requirements[0].value == solution.value
    assert {item.variable for item in mie.assumption_set} == {
        "growth", "margin", "reinvestment", "terminal_value", "discount_rate"
    }
    assert all(item.value is not None for item in mie.assumption_set)
    assert all(item.evidence_ids for item in mie.assumption_set)


def test_ddm_materializes_conditional_dividend_and_explicit_assumptions():
    inp = ddm_input()
    p3 = identify_market_models(inp)
    solution = p3["evaluations"][0].feasible_solution_set.solutions[0]
    mie = run(inp)[0]
    assert mie.qualification == MIEQualification.CONDITIONAL_ONLY
    assert mie.representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE
    assert mie.economic_requirements[0].economic_variable == "dividend"
    assert mie.economic_requirements[0].value == solution.value
    assert {item.variable for item in mie.assumption_set} == {
        "payout", "growth", "discount_rate"
    }


def test_conditional_mie_does_not_claim_a_full_multidimensional_feasible_space():
    mie = run(dcf_input())[0]
    assert mie.representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE
    assert len(mie.economic_requirements) == 1
    assert all(item.value is not None for item in mie.assumption_set)
    assert all(item.variable != "market_implied_net_profit" for item in mie.assumption_set)


def test_ambiguous_p3_yields_multiple_conditional_slices_without_forced_winner():
    dcf = dcf_candidate()
    ddm = ddm_candidate()
    dcf_inp = dcf_input(dcf, current_price="105", fcf_value="5")
    ddm_inp = ddm_input(ddm, id_prefix="ddm-", current_price="105")
    dcf_p3 = identify_market_models(dcf_inp)
    ddm_p3 = identify_market_models(ddm_inp)
    combined = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="ddm-current-dividend",
        candidates=(dcf, ddm),
        observations=dcf_inp.observations + ddm_inp.observations,
        evidence=dcf_inp.evidence + tuple(
            item
            for item in ddm_inp.evidence
            if item.evidence_id not in {e.evidence_id for e in dcf_inp.evidence}
        ),
    )
    identification = {
        "status": "PASS",
        "method": "model_specific_inverse_v0.2",
        "evaluations": dcf_p3["evaluations"] + ddm_p3["evaluations"],
        "identifiability": IdentifiabilityResult(
            state=IdentifiabilityState.AMBIGUOUS,
            feasible_model_ids=("dcf-1", "ddm-1"),
            selected_model_id=None,
            competing_model_ids=("dcf-1", "ddm-1"),
            evidence_ids=tuple(sorted(set(
                dcf_p3["identifiability"].evidence_ids
                + ddm_p3["identifiability"].evidence_ids
            ))),
            rationale="Red-team typed ambiguity: both DCF and DDM remain materially feasible.",
        ),
        "stability": StabilityResult(
            state=StabilityState.STABLE,
            assessment_method="typed-fixture",
            observations=(
                StabilityObservation(
                    perturbation_id="p4c-amb-1",
                    perturbation="leave-one-date-out fixture",
                    resulting_state=StabilityState.STABLE,
                    selected_model_id=None,
                ),
            ),
            evidence_ids=tuple(sorted(set(
                dcf_p3["stability"].evidence_ids
                + ddm_p3["stability"].evidence_ids
            ))),
            rationale="Red-team typed stable ambiguity.",
        ),
    }
    outputs = build_dcf_ddm_conditional_market_implied_expectations(
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
    assert {output.model_id for output in outputs} == {"dcf-1", "ddm-1"}
    assert all(output.qualification == MIEQualification.CONDITIONAL_ONLY for output in outputs)


def test_unstable_p3_blocks_conditional_mie():
    inp = dcf_input()
    modified = []
    historical_prices = {"1": "2100", "8": "4200", "15": "4200", "22": "4200"}
    for item in inp.observations:
        if item.observation_id.startswith("h"):
            day = item.observation_id.split("-", 1)[0][1:]
            modified.append(
                cobs(
                    item.observation_id,
                    int(day),
                    historical_prices[day],
                    item.economic_variable,
                    str(item.economic_value),
                    item.basis,
                    item.unit,
                    item.evidence_ids[0],
                )
            )
        else:
            modified.append(item)
    unstable = MarketModelIdentificationInput(
        cutoff_date=inp.cutoff_date,
        current_observation_id=inp.current_observation_id,
        candidates=inp.candidates,
        observations=tuple(modified),
        evidence=inp.evidence,
    )
    p3 = identify_market_models(unstable)
    assert p3["stability"].state.value == "UNSTABLE"
    assert p3["evaluations"][0].fit.status.value == "FEASIBLE"
    assert run(unstable)[0].qualification == MIEQualification.BLOCKED


def test_insufficient_evidence_assessment_blocks_mie():
    inp = dcf_input()
    mie = run(
        inp,
        evidence_sufficiency=evidence_sufficient(inp, EvidenceSufficiencyState.INSUFFICIENT),
    )[0]
    assert mie.qualification == MIEQualification.BLOCKED


def test_insufficient_candidate_coverage_blocks_mie():
    inp = dcf_input()
    bad_coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.INSUFFICIENT,
        scope_basis="partial",
        candidate_model_ids=("dcf-1",),
        evidence_ids=("candidate-dcf-1",),
        rationale="Candidate set intentionally incomplete.",
    )
    assert run(inp, candidate_coverage=bad_coverage)[0].qualification == MIEQualification.BLOCKED


def test_wrong_family_is_rejected():
    inp = dcf_input(
        candidate_item=CandidateMarketModel(
            model_id="pe-1",
            family=MarketModelFamily.FORWARD_PE,
            required_economic_variables=("forward_eps",),
            required_observable_variables=("forward_eps",),
            evidence_ids=("candidate-pe",),
            admission_basis="negative fixture",
            inverse_solvable=True,
        )
    )
    # P3 itself is expected to classify this candidate as unsupported in context;
    # the P4-C boundary must reject before it can be materialized.
    with pytest.raises(ValueError, match="only DCF and DDM"):
        run(inp)


def test_wrong_p3_solution_variable_is_rejected():
    inp = dcf_input()
    p3 = identify_market_models(inp)
    evaluation = p3["evaluations"][0]
    original = evaluation.feasible_solution_set
    solution = original.solutions[0]
    bad_solution = FeasibleSolution(
        economic_variable="dividend",
        unit=solution.unit,
        basis=solution.basis,
        model_id=solution.model_id,
        value=solution.value,
        evidence_ids=solution.evidence_ids,
    )
    bad_set = FeasibleSolutionSet(
        model_id=original.model_id,
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(bad_solution,),
        constraint_ids=original.constraint_ids,
        evidence_ids=original.evidence_ids,
        basis=original.basis,
    )
    bad = dict(p3, evaluations=(
        CandidateEvaluation(
            fit=evaluation.fit,
            feasible_solution_set=bad_set,
        ),
    ))
    with pytest.raises(ValueError, match="solution variable mismatch"):
        build_dcf_ddm_conditional_market_implied_expectations(
            identification_input=inp,
            identification=bad,
            candidate_coverage=coverage(inp),
            evidence_sufficiency=evidence_sufficient(inp),
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
            period="NTM",
            horizon="12M",
            accounting_basis="reported",
        )


def test_missing_current_conditional_assumption_is_fail_closed():
    inp = dcf_input()
    observations = tuple(
        item for item in inp.observations
        if item.observation_id != "current-discount_rate"
    )
    evidence = tuple(
        item for item in inp.evidence
        if item.evidence_id != "e-discount_rate-current"
    )
    broken = MarketModelIdentificationInput(
        cutoff_date=inp.cutoff_date,
        current_observation_id=inp.current_observation_id,
        candidates=inp.candidates,
        observations=observations,
        evidence=evidence,
    )
    with pytest.raises(ValueError, match="no feasible DCF/DDM market model"):
        run(broken)


def test_assumption_evidence_variable_mismatch_is_rejected():
    inp = dcf_input()
    bad_evidence = list(inp.evidence)
    target = next(index for index, item in enumerate(bad_evidence) if item.evidence_id == "e-growth-current")
    bad_evidence[target] = complex_evidence("e-growth-current", "margin", "ratio")
    broken = MarketModelIdentificationInput(
        cutoff_date=inp.cutoff_date,
        current_observation_id=inp.current_observation_id,
        candidates=inp.candidates,
        observations=inp.observations,
        evidence=tuple(bad_evidence),
    )
    with pytest.raises(ValueError, match="observation evidence variable mismatch"):
        run(broken)


def test_p3_output_is_not_recomputed():
    inp = dcf_input(current_price="2100")
    p3 = identify_market_models(inp)
    solution = p3["evaluations"][0].feasible_solution_set.solutions[0]
    mie = run(inp)[0]
    assert mie.economic_requirements[0].value == solution.value
    assert mie.economic_requirements[0].basis == solution.basis
    assert mie.economic_requirements[0].evidence_ids == solution.evidence_ids


def test_p4c_keeps_explicit_period_horizon_accounting_basis():
    inp = dcf_input()
    mie = build_dcf_ddm_conditional_market_implied_expectations(
        identification_input=inp,
        identification=identify_market_models(inp),
        candidate_coverage=coverage(inp),
        evidence_sufficiency=evidence_sufficient(inp),
        currency="CNY",
        adjustment_semantics="ADJUSTED_CLOSE",
        period="FY+1",
        horizon="18M",
        accounting_basis="normalized",
    )[0]
    assert mie.observation_basis.adjustment_semantics == "ADJUSTED_CLOSE"
    assert mie.economic_requirements[0].period == "FY+1"
    assert mie.economic_requirements[0].horizon == "18M"
    assert mie.economic_requirements[0].accounting_basis == "normalized"
    assert all(item.period == "FY+1" for item in mie.assumption_set)


def test_p3_status_or_method_tampering_is_rejected():
    inp = dcf_input()
    p3 = identify_market_models(inp)
    for key, value in (("status", "BLOCKED"), ("method", "legacy_inverse")):
        bad = dict(p3, **{key: value})
        with pytest.raises(ValueError):
            build_dcf_ddm_conditional_market_implied_expectations(
                identification_input=inp,
                identification=bad,
                candidate_coverage=coverage(inp),
                evidence_sufficiency=evidence_sufficient(inp),
                currency="CNY",
                adjustment_semantics="UNADJUSTED",
                period="NTM",
                horizon="12M",
                accounting_basis="reported",
            )
