from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from iios_mvp.market_model_domain import (
    CandidateMarketModel,
    FeasibleSolution,
    HistoricalSupportState,
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
    semantic_variables_for_model,
)


def test_model_semantics_cover_all_frozen_families():
    expected = {
        MarketModelFamily.FORWARD_PE: "forward_eps",
        MarketModelFamily.PS: "revenue",
        MarketModelFamily.PB: "book_equity",
        MarketModelFamily.EV_EBITDA: "ebitda",
        MarketModelFamily.DCF: "fcf",
        MarketModelFamily.DDM: "dividend",
        MarketModelFamily.SOTP: "segment_value",
        MarketModelFamily.RNPV: "pipeline_value",
    }
    for family, variable in expected.items():
        economic, observable = semantic_variables_for_model(family)
        assert variable in economic
        assert variable in observable


def test_inverse_solvability_alone_cannot_admit_candidate():
    candidate = CandidateMarketModel(
        model_id="pe-1",
        family=MarketModelFamily.FORWARD_PE,
        required_economic_variables=("forward_eps",),
        required_observable_variables=("forward_eps",),
        evidence_ids=(),
        admission_basis="inverse equation is solvable",
        inverse_solvable=True,
    )
    with pytest.raises(ValueError, match="inverse solvability alone"):
        candidate.validate()


def test_candidate_with_evidence_is_valid():
    candidate = CandidateMarketModel(
        model_id="pe-1",
        family=MarketModelFamily.FORWARD_PE,
        required_economic_variables=("forward_eps",),
        required_observable_variables=("forward_eps",),
        evidence_ids=("m1",),
        admission_basis="current price + historical multiple evidence",
        inverse_solvable=True,
    )
    candidate.validate()


def test_ps_domain_does_not_collapse_to_net_profit():
    candidate = CandidateMarketModel(
        model_id="ps-1",
        family=MarketModelFamily.PS,
        required_economic_variables=("revenue",),
        required_observable_variables=("revenue",),
        evidence_ids=("m1",),
        admission_basis="sales-based market evidence",
        inverse_solvable=True,
    )
    candidate.validate()
    solution = FeasibleSolution(
        economic_variable="revenue",
        unit="CNY",
        basis="forward",
        model_id="ps-1",
        value=Decimal("100000000"),
        evidence_ids=("m1",),
    )
    solution.validate()
    assert solution.economic_variable == "revenue"
    assert solution.economic_variable != "net_profit"


def test_ev_ebitda_keeps_bridge_semantics():
    candidate = CandidateMarketModel(
        model_id="ev-1",
        family=MarketModelFamily.EV_EBITDA,
        required_economic_variables=("ebitda", "enterprise_value"),
        required_observable_variables=("ebitda", "enterprise_value"),
        evidence_ids=("m1", "m2"),
        admission_basis="EV bridge and EBITDA evidence",
    )
    candidate.validate()


def test_feasible_fit_requires_evidence_and_diagnostics():
    fit = ModelFit(
        model_id="pe-1",
        status=ModelFitStatus.FEASIBLE,
        diagnostics=(FitDiagnostic("d1", "historical_consistency", "PASS", ("m1",)),),
        evidence_ids=("m1",),
        historical_support=HistoricalSupportState.IN_RANGE,
    )
    fit.validate()


def test_feasible_solution_set_is_typed_and_provenanced():
    solution = FeasibleSolution(
        economic_variable="forward_eps",
        unit="CNY/share",
        basis="forward",
        model_id="pe-1",
        range_low=Decimal("15"),
        range_high=Decimal("18"),
        evidence_ids=("m1",),
    )
    solution_set = FeasibleSolutionSet(
        model_id="pe-1",
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(solution,),
        constraint_ids=("c1",),
        evidence_ids=("m1",),
        basis="price + admissible multiple range",
    )
    solution_set.validate()


def test_empty_feasible_set_cannot_contain_solution():
    solution = FeasibleSolution(
        economic_variable="forward_eps",
        unit="CNY/share",
        basis="forward",
        model_id="pe-1",
        value=Decimal("15"),
        evidence_ids=("m1",),
    )
    solution_set = FeasibleSolutionSet(
        model_id="pe-1",
        status=FeasibleSolutionStatus.EMPTY,
        solutions=(solution,),
        constraint_ids=("c1",),
        evidence_ids=("m1",),
        basis="no supported fit",
    )
    with pytest.raises(ValueError, match="cannot contain solutions"):
        solution_set.validate()


def test_solution_model_mismatch_is_rejected():
    solution = FeasibleSolution(
        economic_variable="forward_eps",
        unit="CNY/share",
        basis="forward",
        model_id="ps-1",
        value=Decimal("15"),
        evidence_ids=("m1",),
    )
    solution_set = FeasibleSolutionSet(
        model_id="pe-1",
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(solution,),
        constraint_ids=("c1",),
        evidence_ids=("m1",),
        basis="mismatched model",
    )
    with pytest.raises(ValueError, match="solution model_id"):
        solution_set.validate()


def test_identifiable_requires_selected_feasible_model():
    result = IdentifiabilityResult(
        state=IdentifiabilityState.IDENTIFIABLE,
        feasible_model_ids=("pe-1",),
        selected_model_id="ps-1",
        competing_model_ids=(),
        evidence_ids=("m1",),
        rationale="PE remains the uniquely supported explanation",
    )
    with pytest.raises(ValueError, match="must be feasible"):
        result.validate()


def test_ambiguous_cannot_force_winner():
    result = IdentifiabilityResult(
        state=IdentifiabilityState.AMBIGUOUS,
        feasible_model_ids=("pe-1", "ps-1"),
        selected_model_id="pe-1",
        competing_model_ids=("ps-1",),
        evidence_ids=("m1", "m2"),
        rationale="Both models remain materially feasible",
    )
    with pytest.raises(ValueError, match="cannot force"):
        result.validate()


def test_ambiguous_requires_two_feasible_models():
    result = IdentifiabilityResult(
        state=IdentifiabilityState.AMBIGUOUS,
        feasible_model_ids=("pe-1",),
        selected_model_id=None,
        competing_model_ids=(),
        evidence_ids=("m1",),
        rationale="Evidence is not sufficient to distinguish models",
    )
    with pytest.raises(ValueError, match="at least two"):
        result.validate()


def test_unidentifiable_forbids_selected_model():
    result = IdentifiabilityResult(
        state=IdentifiabilityState.UNIDENTIFIABLE,
        feasible_model_ids=(),
        selected_model_id="pe-1",
        competing_model_ids=(),
        evidence_ids=(),
        rationale="No supported feasible model",
    )
    with pytest.raises(ValueError, match="cannot force"):
        result.validate()


def test_stable_requires_explicit_perturbation_observation():
    result = StabilityResult(
        state=StabilityState.STABLE,
        assessment_method="window perturbation",
        observations=(),
        evidence_ids=("m1",),
        rationale="Stable under admissible perturbation",
    )
    with pytest.raises(ValueError, match="at least one"):
        result.validate()


def test_unstable_is_representable_without_forcing_stable_result():
    result = StabilityResult(
        state=StabilityState.UNSTABLE,
        assessment_method="regime perturbation",
        observations=(
            StabilityObservation(
                perturbation_id="p1",
                perturbation="exclude high-crowding regime",
                resulting_state=StabilityState.UNSTABLE,
                selected_model_id=None,
            ),
        ),
        evidence_ids=("m1",),
        rationale="Model interpretation changes under a reasonable perturbation",
    )
    result.validate()


def test_pit_evidence_after_cutoff_is_rejected():
    item = MarketObservableEvidence(
        evidence_id="late",
        variable="forward_eps",
        unit="CNY/share",
        basis="forward",
        observation_date=date(2026, 10, 4),
        known_at=datetime(2026, 10, 5, 1, 0, tzinfo=timezone.utc),
        source="test-fixture",
        value=Decimal("20"),
    )
    with pytest.raises(ValueError, match="known_at is after cutoff"):
        item.validate_pit(date(2026, 10, 4))
