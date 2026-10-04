from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEQualification,
)
from iios_mvp.market_model_domain import CandidateMarketModel, MarketModelFamily, MarketObservableEvidence
from iios_mvp.market_model_identification import CandidateEvaluation, MarketModelIdentificationInput, MarketValuationObservation, identify_market_models
from iios_mvp.ratio_market_implied_expectation import build_ratio_market_implied_expectations


CUTOFF = date(2026, 10, 4)


def candidate(model_id: str, family: MarketModelFamily, evidence_id: str) -> CandidateMarketModel:
    semantics = {
        MarketModelFamily.FORWARD_PE: (("forward_eps",), ("forward_eps",)),
        MarketModelFamily.PS: (("revenue",), ("revenue",)),
        MarketModelFamily.PB: (("book_equity",), ("book_equity",)),
        MarketModelFamily.EV_EBITDA: (("ebitda", "enterprise_value"), ("ebitda", "enterprise_value")),
    }[family]
    return CandidateMarketModel(
        model_id=model_id,
        family=family,
        required_economic_variables=semantics[0],
        required_observable_variables=semantics[1],
        evidence_ids=(evidence_id,),
        admission_basis="P4-B ratio fixture",
        inverse_solvable=True,
    )


def build_input(candidates, variable, values, prices, net_debt="0"):
    observations = []
    evidence = []
    days = (1, 8, 15, 22)
    for idx, (day, value, price) in enumerate(zip(days, values[:-1], prices[:-1])):
        obs_id = f"h{day}-{variable}"
        ev_id = f"ev-{obs_id}"
        observation_date = date(2026, 9, day)
        observations.append(MarketValuationObservation(
            observation_id=obs_id,
            observation_date=observation_date,
            known_at=datetime(2026, 9, day, 2, tzinfo=timezone.utc),
            price=Decimal(price),
            shares_outstanding=Decimal("1"),
            economic_variable=variable,
            economic_value=Decimal(value),
            unit="CNY/share" if variable in {"forward_eps", "book_equity"} else "CNY",
            basis="forward" if variable == "forward_eps" else "TTM",
            evidence_ids=(ev_id,),
            source="test-fixture",
            net_debt=Decimal(net_debt),
        ))
        evidence.append(MarketObservableEvidence(
            evidence_id=ev_id,
            variable=variable,
            unit=observations[-1].unit,
            basis=observations[-1].basis,
            observation_date=observation_date,
            known_at=observations[-1].known_at,
            source="test-fixture",
            value=Decimal(value),
        ))
    current_obs_id = f"current-{variable}"
    current_date = CUTOFF
    current_unit = "CNY/share" if variable in {"forward_eps", "book_equity"} else "CNY"
    current_basis = "forward" if variable == "forward_eps" else "TTM"
    observations.append(MarketValuationObservation(
        observation_id=current_obs_id,
        observation_date=current_date,
        known_at=datetime(2026, 10, 4, 2, tzinfo=timezone.utc),
        price=Decimal(prices[-1]),
        shares_outstanding=Decimal("1"),
        economic_variable=variable,
        economic_value=Decimal(values[-1]),
        unit=current_unit,
        basis=current_basis,
        evidence_ids=(f"ev-{current_obs_id}",),
        source="test-fixture",
        net_debt=Decimal(net_debt),
    ))
    evidence.append(MarketObservableEvidence(
        evidence_id=f"ev-{current_obs_id}",
        variable=variable,
        unit=current_unit,
        basis=current_basis,
        observation_date=current_date,
        known_at=observations[-1].known_at,
        source="test-fixture",
        value=Decimal(values[-1]),
    ))
    for c in candidates:
        evidence.append(MarketObservableEvidence(
            evidence_id=c.evidence_ids[0],
            variable="candidate_model",
            unit="identifier",
            basis="admission",
            observation_date=CUTOFF,
            known_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
            source="test-fixture",
            value=Decimal("1"),
        ))
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id=current_obs_id,
        candidates=tuple(candidates),
        observations=tuple(observations),
        evidence=tuple(evidence),
    )


def coverage(inp):
    return CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis="P4-B admitted ratio set",
        candidate_model_ids=tuple(c.model_id for c in inp.candidates),
        evidence_ids=tuple(c.evidence_ids[0] for c in inp.candidates),
        rationale="All admitted P4-B ratio candidates are explicitly enumerated.",
    )


def evidence_sufficient(inp, status=EvidenceSufficiencyState.SUFFICIENT):
    ids = tuple(item.evidence_id for item in inp.evidence[:3])
    return EvidenceSufficiencyAssessment(
        status=status,
        rationale="Fixture evidence is explicitly captured." if status == EvidenceSufficiencyState.SUFFICIENT else "Fixture evidence intentionally incomplete.",
        evidence_ids=ids,
    )


def run(inp, **kwargs):
    p3 = identify_market_models(inp)
    return build_ratio_market_implied_expectations(
        identification_input=inp,
        identification=p3,
        candidate_coverage=kwargs.pop("candidate_coverage", coverage(inp)),
        evidence_sufficiency=kwargs.pop("evidence_sufficiency", evidence_sufficient(inp)),
        currency="CNY",
        adjustment_semantics="UNADJUSTED",
        period="NTM",
        horizon="12M",
        accounting_basis="reported",
        **kwargs,
    )


def test_forward_pe_mie_preserves_p3_range_and_is_decision_grade():
    inp = build_input(
        (candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe"),),
        "forward_eps",
        ("5", "5", "5", "5", "5"),
        ("90", "95", "100", "105", "100"),
    )
    ident = identify_market_models(inp)
    solution = ident["evaluations"][0].feasible_solution_set.solutions[0]
    outputs = run(inp)
    assert len(outputs) == 1
    mie = outputs[0]
    assert mie.qualification == MIEQualification.DECISION_GRADE
    assert mie.economic_requirements[0].economic_variable == "forward_eps"
    assert mie.economic_requirements[0].range_low == solution.range_low
    assert mie.economic_requirements[0].range_high == solution.range_high
    assert mie.observation_basis.price_observation_id == "current-forward_eps"


@pytest.mark.parametrize(
    ("family", "variable", "values", "unit_prices"),
    [
        (MarketModelFamily.PS, "revenue", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100")),
        (MarketModelFamily.PB, "book_equity", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100")),
        (MarketModelFamily.EV_EBITDA, "ebitda", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100")),
    ],
)
def test_other_ratio_families_preserve_native_variable(family, variable, values, unit_prices):
    net_debt = "10" if family == MarketModelFamily.EV_EBITDA else "0"
    inp = build_input((candidate(f"model-{family.value}", family, f"candidate-{family.value}"),), variable, values, unit_prices, net_debt=net_debt)
    outputs = run(inp)
    assert len(outputs) == 1
    assert outputs[0].economic_requirements[0].economic_variable == variable
    assert outputs[0].qualification == MIEQualification.DECISION_GRADE


def test_ambiguous_p3_becomes_multiple_conditional_mies_without_forced_winner():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    ps = candidate("ps-1", MarketModelFamily.PS, "candidate-ps")
    # Both models observe a 20x current multiple inside the same historical range.
    inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    ps_rows = build_input((ps,), "revenue", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    combined = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current-forward_eps",
        candidates=(pe, ps),
        observations=inp.observations + ps_rows.observations,
        evidence=inp.evidence + tuple(
            item for item in ps_rows.evidence if item.evidence_id not in {x.evidence_id for x in inp.evidence}
        ),
    )
    outputs = run(combined)
    assert {o.model_id for o in outputs} == {"pe-1", "ps-1"}
    assert all(o.qualification == MIEQualification.CONDITIONAL_ONLY for o in outputs)
    assert all(o.representation.value == "IMPLIED_RANGE" for o in outputs)


def test_insufficient_identification_blocks_the_feasible_ratio_mie():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    ps = candidate("ps-1", MarketModelFamily.PS, "candidate-ps")
    pe_inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    ps_inp = build_input((ps,), "revenue", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    ps_inp = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id=ps_inp.current_observation_id,
        candidates=ps_inp.candidates,
        observations=ps_inp.observations[:1] + ps_inp.observations[-1:],
        evidence=tuple(item for item in ps_inp.evidence if item.evidence_id in {o.evidence_ids[0] for o in ps_inp.observations} | {ps.evidence_ids[0]}),
    )
    combined = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id=pe_inp.current_observation_id,
        candidates=(pe, ps),
        observations=pe_inp.observations + ps_inp.observations,
        evidence=pe_inp.evidence + tuple(item for item in ps_inp.evidence if item.evidence_id not in {x.evidence_id for x in pe_inp.evidence}),
    )
    outputs = run(combined)
    assert len(outputs) == 1
    assert outputs[0].model_id == "pe-1"
    assert outputs[0].qualification == MIEQualification.BLOCKED


def test_unstable_p3_blocks_mie():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input(
        (pe,),
        "forward_eps",
        ("10", "5", "5", "5", "10"),
        ("100", "100", "100", "100", "100"),
    )
    outputs = run(inp)
    assert outputs[0].qualification == MIEQualification.BLOCKED


def test_insufficient_candidate_coverage_blocks_mie():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    bad_coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.INSUFFICIENT,
        scope_basis="partial",
        candidate_model_ids=("pe-1",),
        evidence_ids=("candidate-pe",),
        rationale="Candidate set intentionally incomplete.",
    )
    outputs = run(inp, candidate_coverage=bad_coverage)
    assert outputs[0].qualification == MIEQualification.BLOCKED


def test_insufficient_evidence_assessment_blocks_mie():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    outputs = run(
        inp,
        evidence_sufficiency=evidence_sufficient(inp, EvidenceSufficiencyState.INSUFFICIENT),
    )
    assert outputs[0].qualification == MIEQualification.BLOCKED


def test_non_ratio_candidate_is_rejected_before_mie_materialization():
    complex_candidate = CandidateMarketModel(
        model_id="dcf-1",
        family=MarketModelFamily.DCF,
        required_economic_variables=("fcf", "growth", "margin", "reinvestment", "terminal_value"),
        required_observable_variables=("fcf", "growth", "margin", "reinvestment", "terminal_value"),
        evidence_ids=("candidate-dcf",),
        admission_basis="P4-B negative fixture",
    )
    inp = build_input((complex_candidate,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    with pytest.raises(ValueError, match="only forward PE"):
        run(inp)


def test_nested_evidence_must_be_manifest_backed():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    bad = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState.SUFFICIENT,
        rationale="forged",
        evidence_ids=("missing",),
    )
    with pytest.raises(ValueError, match="unknown evidence_id"):
        run(inp, evidence_sufficiency=bad)


def test_wrong_p3_solution_variable_is_rejected():
    from iios_mvp.market_model_domain import FeasibleSolution, FeasibleSolutionSet, FeasibleSolutionStatus
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    p3 = identify_market_models(inp)
    evaluation = p3["evaluations"][0]
    original = evaluation.feasible_solution_set
    bad_solution = FeasibleSolution(
        economic_variable="revenue",
        unit=original.solutions[0].unit,
        basis=original.solutions[0].basis,
        model_id="pe-1",
        range_low=original.solutions[0].range_low,
        range_high=original.solutions[0].range_high,
        evidence_ids=original.solutions[0].evidence_ids,
    )
    bad_set = FeasibleSolutionSet(
        model_id=original.model_id,
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(bad_solution,),
        constraint_ids=original.constraint_ids,
        evidence_ids=original.evidence_ids,
        basis=original.basis,
    )
    bad_eval = CandidateEvaluation(
        fit=evaluation.fit,
        feasible_solution_set=bad_set,
    )
    bad_p3 = dict(p3, evaluations=(bad_eval,))
    with pytest.raises(ValueError, match="solution variable mismatch"):
        build_ratio_market_implied_expectations(
            identification_input=inp,
            identification=bad_p3,
            candidate_coverage=coverage(inp),
            evidence_sufficiency=evidence_sufficient(inp),
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
            period="NTM",
            horizon="12M",
            accounting_basis="reported",
        )


def test_invalid_p3_method_is_rejected():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input((pe,), "forward_eps", ("5", "5", "5", "5", "5"), ("90", "95", "100", "105", "100"))
    p3 = identify_market_models(inp)
    bad_p3 = dict(p3, method="legacy_inverse")
    with pytest.raises(ValueError, match="accepted P3 model-specific inverse"):
        build_ratio_market_implied_expectations(
            identification_input=inp,
            identification=bad_p3,
            candidate_coverage=coverage(inp),
            evidence_sufficiency=evidence_sufficient(inp),
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
            period="NTM",
            horizon="12M",
            accounting_basis="reported",
        )
