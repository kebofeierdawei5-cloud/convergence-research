from datetime import date, datetime, timezone
from decimal import Decimal, localcontext

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


def test_outside_support_blocks_decision_grade_mie_even_when_identification_stable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input(
        (pe,),
        "forward_eps",
        ("10", "5", "5", "5", "10"),
        ("100", "100", "100", "100", "90"),
    )
    p3 = identify_market_models(inp)
    assert p3["identifiability"].state.value == "IDENTIFIABLE"
    assert p3["stability"].state.value == "STABLE"
    assert p3["evaluations"][0].fit.historical_support.value == "BELOW_HISTORICAL_RANGE"
    with pytest.raises(ValueError, match="IN_RANGE historical support"):
        run(inp)


def test_unstable_identification_still_blocks_ratio_mie():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "candidate-pe")
    ps = candidate("ps-1", MarketModelFamily.PS, "candidate-ps")
    observations = []
    evidence = []
    for day, price, net_debt in (
        (1, "100", "-200"),
        (8, "100", "0"),
        (15, "100", "0"),
        (22, "100", "0"),
    ):
        oid = f"h{day}-revenue"
        eid = f"ev-{oid}"
        observations.append(MarketValuationObservation(
            observation_id=oid,
            observation_date=date(2026, 9, day),
            known_at=datetime(2026, 9, day, 2, tzinfo=timezone.utc),
            price=Decimal(price),
            shares_outstanding=Decimal("1"),
            economic_variable="revenue",
            economic_value=Decimal("100"),
            unit="CNY",
            basis="TTM",
            evidence_ids=(eid,),
            source="test-fixture",
            net_debt=Decimal(net_debt),
        ))
        evidence.append(MarketObservableEvidence(
            evidence_id=eid,
            variable="revenue",
            unit="CNY",
            basis="TTM",
            observation_date=observations[-1].observation_date,
            known_at=observations[-1].known_at,
            source="test-fixture",
            value=Decimal("100"),
        ))
    current_oid = "current-revenue"
    current_date = CUTOFF
    current = MarketValuationObservation(
        observation_id=current_oid,
        observation_date=current_date,
        known_at=datetime(2026, 10, 4, 2, tzinfo=timezone.utc),
        price=Decimal("100"),
        shares_outstanding=Decimal("1"),
        economic_variable="revenue",
        economic_value=Decimal("100"),
        unit="CNY",
        basis="TTM",
        evidence_ids=("ev-current",),
        source="test-fixture",
        net_debt=Decimal("0"),
    )
    observations.append(current)
    evidence.append(MarketObservableEvidence(
        evidence_id="ev-current",
        variable="revenue",
        unit="CNY",
        basis="TTM",
        observation_date=current_date,
        known_at=current.known_at,
        source="test-fixture",
        value=Decimal("100"),
    ))
    evidence.extend((
        MarketObservableEvidence(
            evidence_id="candidate-pe",
            variable="candidate_model",
            unit="identifier",
            basis="admission",
            observation_date=current_date,
            known_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
            source="test-fixture",
            value=Decimal("1"),
        ),
        MarketObservableEvidence(
            evidence_id="candidate-ps",
            variable="candidate_model",
            unit="identifier",
            basis="admission",
            observation_date=current_date,
            known_at=datetime(2026, 10, 4, 1, tzinfo=timezone.utc),
            source="test-fixture",
            value=Decimal("1"),
        ),
    ))
    # Add a valid PE candidate with its own evidence-backed observations.
    for day, price in ((1, "10"), (8, "10"), (15, "10"), (22, "10")):
        oid=f"h{day}-eps"
        eid=f"ev-{oid}"
        observations.append(MarketValuationObservation(
            observation_id=oid,
            observation_date=date(2026, 9, day),
            known_at=datetime(2026, 9, day, 2, tzinfo=timezone.utc),
            price=Decimal(price),
            shares_outstanding=Decimal("1"),
            economic_variable="forward_eps",
            economic_value=Decimal("1"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=(eid,),
            source="test-fixture",
        ))
        evidence.append(MarketObservableEvidence(
            evidence_id=eid,
            variable="forward_eps",
            unit="CNY/share",
            basis="forward",
            observation_date=date(2026, 9, day),
            known_at=datetime(2026, 9, day, 2, tzinfo=timezone.utc),
            source="test-fixture",
            value=Decimal("1"),
        ))
    observations.append(MarketValuationObservation(
        observation_id="current-forward_eps",
        observation_date=current_date,
        known_at=current.known_at,
        price=Decimal("10"),
        shares_outstanding=Decimal("1"),
        economic_variable="forward_eps",
        economic_value=Decimal("1"),
        unit="CNY/share",
        basis="forward",
        evidence_ids=("ev-current-eps",),
        source="test-fixture",
    ))
    evidence.append(MarketObservableEvidence(
        evidence_id="ev-current-eps",
        variable="forward_eps",
        unit="CNY/share",
        basis="forward",
        observation_date=current_date,
        known_at=current.known_at,
        source="test-fixture",
        value=Decimal("1"),
    ))
    inp = MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id=current_oid,
        candidates=(pe, ps),
        observations=tuple(observations),
        evidence=tuple(evidence),
    )
    p3 = identify_market_models(inp)
    assert p3["identifiability"].state.value == "IDENTIFIABLE"
    assert p3["identifiability"].selected_model_id == "pe-1"
    assert p3["stability"].state.value == "UNSTABLE"
    outputs = build_ratio_market_implied_expectations(
            identification_input=inp,
            identification=p3,
            candidate_coverage=coverage(inp),
            evidence_sufficiency=evidence_sufficient(inp),
            currency="CNY",
            adjustment_semantics="UNADJUSTED",
            period="NTM",
            horizon="12M",
            accounting_basis="reported",
        )


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

# Real CORE-04-C -> P3-A/P4-B integration
import json
from pathlib import Path


REAL_RATIO_INPUT_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_cases" / "RC-CN-A-300750-20261004_ratio_mie_input.json"


def _real_300750_ratio_input():
    payload = json.loads(REAL_RATIO_INPUT_PATH.read_text(encoding="utf-8"))
    observations = tuple(
        MarketValuationObservation(
            observation_id=item["observation_id"],
            observation_date=date.fromisoformat(item["observation_date"]),
            known_at=datetime.fromisoformat(item["known_at"]),
            price=Decimal(item["price"]),
            shares_outstanding=Decimal(item["shares_outstanding"]),
            economic_variable=item["economic_variable"],
            economic_value=Decimal(item["economic_value"]),
            unit=item["unit"],
            basis=item["basis"],
            evidence_ids=tuple(item["evidence_ids"]),
            source=item["source"],
            net_debt=Decimal(item["net_debt"]),
        )
        for item in payload["observations"]
    )
    evidence = tuple(
        MarketObservableEvidence(
            evidence_id=item["evidence_id"],
            variable=item["variable"],
            unit=item["unit"],
            basis=item["basis"],
            observation_date=date.fromisoformat(item["observation_date"]),
            known_at=datetime.fromisoformat(item["known_at"]),
            source=item["source"],
            value=Decimal(item["value"]),
            metadata=item["metadata"],
        )
        for item in payload["evidence"]
    )
    candidate_payload = payload["candidate"]
    candidate_obj = CandidateMarketModel(
        model_id=candidate_payload["model_id"],
        family=MarketModelFamily(candidate_payload["family"]),
        required_economic_variables=tuple(candidate_payload["required_economic_variables"]),
        required_observable_variables=tuple(candidate_payload["required_observable_variables"]),
        evidence_ids=tuple(candidate_payload["evidence_ids"]),
        admission_basis=candidate_payload["admission_basis"],
        inverse_solvable=candidate_payload["inverse_solvable"],
    )
    inp = MarketModelIdentificationInput(
        cutoff_date=date.fromisoformat(payload["cutoff_date"]),
        current_observation_id="CATL-EVEBITDA-CURRENT-2026-09-30",
        candidates=(candidate_obj,),
        observations=observations,
        evidence=evidence,
    )
    coverage_payload = payload["candidate_coverage"]
    coverage_obj = CandidateCoverageAssessment(
        status=CandidateCoverageState(coverage_payload["status"]),
        scope_basis=coverage_payload["scope_basis"],
        candidate_model_ids=tuple(coverage_payload["candidate_model_ids"]),
        evidence_ids=tuple(coverage_payload["evidence_ids"]),
        rationale=coverage_payload["rationale"],
    )
    suff_payload = payload["evidence_sufficiency"]
    suff_obj = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState(suff_payload["status"]),
        rationale=suff_payload["rationale"],
        evidence_ids=tuple(suff_payload["evidence_ids"]),
    )
    return payload, inp, coverage_obj, suff_obj


def test_real_core04c_observations_are_consumed_by_p3a_and_fail_closed_on_current_range():
    payload, inp, _, _ = _real_300750_ratio_input()
    result = identify_market_models(inp)
    evaluation = result["evaluations"][0]
    diagnostics = {item.name: item for item in evaluation.fit.diagnostics}

    assert evaluation.fit.status.value == "FEASIBLE"
    assert diagnostics["historical_market_multiple_range"].status == "PASS"
    assert diagnostics["current_historical_support"].status == "OUTSIDE_HISTORICAL_SUPPORT"
    assert "current_multiple=8.375536786732361377195576638" in diagnostics["current_historical_support"].notes
    assert evaluation.fit.historical_support.value == "BELOW_HISTORICAL_RANGE"
    assert evaluation.fit.regime_interpretation.value == "POSSIBLE_REGIME_SHIFT"
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    assert result["stability"].state.value == "INSUFFICIENT_EVIDENCE"
    assert payload["source_receipt"]["artifact_sha256"] == "51e9e8c19404ef241383c99e0f9ed98bf3088fbe2b4a47778e9f5d79a26ee6c4"


def test_real_core04c_p4b_does_not_materialize_mie_when_no_ratio_model_is_feasible():
    _, inp, coverage_obj, suff_obj = _real_300750_ratio_input()
    result = identify_market_models(inp)
    with pytest.raises(ValueError, match="IN_RANGE historical support"):
        build_ratio_market_implied_expectations(
            identification_input=inp,
            identification=result,
            candidate_coverage=coverage_obj,
            evidence_sufficiency=suff_obj,
            currency="CNY",
            adjustment_semantics="UNADJUSTED_CLOSE",
            period="FY2025",
            horizon="completed_fiscal_year",
            accounting_basis="reported_completed_fiscal_year_EBITDA",
        )


def test_real_core04c_exact_historical_observations_and_pit_bindings_are_locked():
    _, inp, _, _ = _real_300750_ratio_input()
    assert [item.observation_id for item in inp.observations[:3]] == [
        "CATL-EVEBITDA-2025-10-22",
        "CATL-EVEBITDA-2026-04-17",
        "CATL-EVEBITDA-2026-07-27",
    ]
    assert [item.economic_value for item in inp.observations[:3]] == [
        Decimal("91999043000"),
        Decimal("119197217000"),
        Decimal("119197217000"),
    ]
    assert all(item.known_at.date() <= item.observation_date for item in inp.observations)
    assert all(item.known_at.date() <= inp.cutoff_date for item in inp.observations)


def test_real_current_ev_ebitda_is_exact_and_below_historical_lower_bound():
    _, inp, _, _ = _real_300750_ratio_input()
    current = next(item for item in inp.observations if item.observation_id == inp.current_observation_id)
    current_multiple = (current.price * current.shares_outstanding + current.net_debt) / current.economic_value
    assert current_multiple == Decimal("8.375536786732361377195576638")
    with localcontext() as ctx:
        ctx.prec = 80
        exact_multiple = (current.price * current.shares_outstanding + current.net_debt) / current.economic_value
    assert exact_multiple == Decimal("8.3755367867323613771955766383371182231544885817258636164299037283731213288310246")
    historical = inp.observations[:3]
    historical_multiples = [
        (item.price * item.shares_outstanding + item.net_debt) / item.economic_value
        for item in historical
    ]
    assert current_multiple < min(historical_multiples)


def test_outside_historical_support_cannot_materialize_ratio_mie():
    pe = candidate("pe-outside", MarketModelFamily.FORWARD_PE, "candidate-pe")
    inp = build_input(
        (pe,),
        "forward_eps",
        ("5", "5", "5", "5", "5"),
        ("90", "95", "100", "105", "50"),
    )
    with pytest.raises(ValueError, match="IN_RANGE historical support"):
        run(inp)
