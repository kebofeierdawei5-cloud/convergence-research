from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import pytest

from iios_mvp.market_model_domain import (
    CandidateMarketModel,
    MarketModelFamily,
    MarketObservableEvidence,
)
from iios_mvp.market_model_identification import (
    MarketModelIdentificationInput,
    MarketValuationObservation,
    identify_market_models,
)


CUTOFF = date(2026, 10, 4)
KNOWN = datetime(2026, 10, 4, 2, tzinfo=timezone.utc)


def ev(eid: str, variable: str) -> MarketObservableEvidence:
    return MarketObservableEvidence(
        evidence_id=eid,
        variable=variable,
        unit="CNY/share" if variable == "forward_eps" else "CNY",
        basis="historical_market_observation",
        observation_date=CUTOFF,
        known_at=KNOWN,
        source="test-fixture",
        value=Decimal("1"),
    )


def candidate(model_id: str, family: MarketModelFamily, variable: str) -> CandidateMarketModel:
    return CandidateMarketModel(
        model_id=model_id,
        family=family,
        required_economic_variables=(variable,),
        required_observable_variables=(variable,),
        evidence_ids=("e1",),
        admission_basis="test evidence-backed candidate",
        inverse_solvable=True,
    )


def obs(oid: str, day: int, price: str, economic: str, variable: str, shares: str = "100") -> MarketValuationObservation:
    return MarketValuationObservation(
        observation_id=oid,
        observation_date=date(2026, 9, day),
        known_at=datetime(2026, 9, day, 2, tzinfo=timezone.utc),
        price=Decimal(price),
        shares_outstanding=Decimal(shares),
        economic_variable=variable,
        economic_value=Decimal(economic),
        unit="CNY/share" if variable == "forward_eps" else "CNY",
        basis="forward",
        evidence_ids=("e1",),
        source="test-fixture",
    )


def base_input(candidates, observations, evidence=None):
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current",
        candidates=tuple(candidates),
        observations=tuple(observations),
        evidence=tuple(evidence or [
            ev("e1", "forward_eps"),
        ]),
    )


def test_unique_feasible_model_is_identifiable_and_solution_is_model_semantic():
    candidate_pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([candidate_pe], observations))
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    assert result["identifiability"].selected_model_id == "pe-1"
    solution = result["evaluations"][0].feasible_solution_set.solutions[0]
    assert solution.economic_variable == "forward_eps"
    assert solution.range_low == Decimal("4.464285714285714285714285714")
    assert solution.range_high == Decimal("6.25")
    assert result["stability"].state.value == "STABLE"


def test_multiple_feasible_models_are_ambiguous():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    ps = candidate("ps-1", MarketModelFamily.PS, "revenue")
    obs_pe = (
        obs("pe-h1", 1, "100", "5", "forward_eps"),
        obs("pe-h2", 15, "120", "5", "forward_eps"),
        obs("pe-h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    obs_rev = (
        MarketValuationObservation(
            observation_id="r1",
            observation_date=date(2026, 9, 1),
            known_at=datetime(2026, 9, 1, 2, tzinfo=timezone.utc),
            price=Decimal("10"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
        MarketValuationObservation(
            observation_id="r2",
            observation_date=date(2026, 9, 15),
            known_at=datetime(2026, 9, 15, 2, tzinfo=timezone.utc),
            price=Decimal("12"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
        MarketValuationObservation(
            observation_id="r3",
            observation_date=date(2026, 9, 30),
            known_at=datetime(2026, 9, 30, 2, tzinfo=timezone.utc),
            price=Decimal("14"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
        MarketValuationObservation(
            observation_id="current-revenue",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("13"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input(
        [pe, ps],
        obs_pe + obs_rev,
        [ev("e1", "forward_eps"), ev("e2", "revenue")]
    ))
    assert result["identifiability"].state.value == "AMBIGUOUS"
    assert result["identifiability"].selected_model_id is None


def test_no_feasible_model_is_unidentifiable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("500"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "UNIDENTIFIABLE"
    assert result["stability"].state.value in {"UNSTABLE", "STABLE"}


def test_insufficient_history_is_not_called_unidentifiable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "INSUFFICIENT_EVIDENCE"


def test_dcf_is_explicitly_insufficient_until_model_specific_solver_exists():
    dcf = CandidateMarketModel(
        model_id="dcf-1",
        family=MarketModelFamily.DCF,
        required_economic_variables=(
            "fcf", "growth", "margin", "reinvestment", "terminal_value",
        ),
        required_observable_variables=(
            "fcf", "growth", "margin", "reinvestment", "terminal_value",
        ),
        evidence_ids=("e1",),
        admission_basis="test evidence-backed DCF candidate",
        inverse_solvable=True,
    )
    observations = (
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("100"),
            shares_outstanding=Decimal("100"),
            economic_variable="fcf",
            economic_value=Decimal("10"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([dcf], observations, [ev("e1", "fcf")]))
    evaluation = result["evaluations"][0]
    assert evaluation.fit.status.value == "INSUFFICIENT_EVIDENCE"


def test_historical_window_perturbation_can_make_model_unstable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "10", "forward_eps"),
        obs("h2", 15, "200", "10", "forward_eps"),
        obs("h3", 30, "300", "10", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("250"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("10"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    assert result["stability"].state.value == "UNSTABLE"


def test_candidate_unknown_provenance_is_rejected():
    bad = CandidateMarketModel(
        model_id="pe-1",
        family=MarketModelFamily.FORWARD_PE,
        required_economic_variables=("forward_eps",),
        required_observable_variables=("forward_eps",),
        evidence_ids=("missing",),
        admission_basis="bad provenance",
        inverse_solvable=True,
    )
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    with pytest.raises(ValueError, match="unknown evidence_ids"):
        identify_market_models(base_input([bad], observations))
